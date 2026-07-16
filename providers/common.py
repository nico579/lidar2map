"""Utilitaires partagés entre providers.

Point de mutualisation (cf. audit providers 2026-07) : extraction ZIP sûre
(anti zip-slip #10) et conversion LAS/LAZ → GeoTIFF DTM (mutualisée 2026-07-15
quand un 3e provider LAZ est arrivé : cz + lv + uy ; avant, DIFFÉRÉE à raison).
Vocation à accueillir aussi le HTTP / pagination / retry communs.
"""
import json
import re
import ssl
import threading
import urllib.request
from pathlib import Path

# Une seule conversion LAS→raster à la fois : le post_fetch tourne DANS le pool
# de téléchargement (8 workers par défaut) et une dalle IGN de 34 M pts pique à
# ~2-3 Go de RAM — 8 conversions parallèles = OOM (revue DFM 2026-07-16). Les
# téléchargements, eux, restent parallèles (le verrou n'entoure que la conversion).
_CONV_LOCK = threading.Lock()

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _CTX = ssl.create_default_context()

_IGN_WFS = "https://data.geopf.fr/wfs/ows"
_IGN_TN = "IGNF_MNT-LIDAR-HD:dalle"
_IGN_TN_LAZ = "IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle"
_IGN_NAME_RE = re.compile(r"LHD_[A-Z0-9]+_(\d+)_(\d+)_")


def ign_lidar_hd_dalles(bbox_natif, epsg, filename_fn, ua="lidar2map/1.0",
                        typename=_IGN_TN):
    """Interroge le WFS IGN `IGNF_MNT-LIDAR-HD:dalle` (0,5 m LiDAR HD, tuiles
    1 km) pour la bbox EN EPSG:`epsg`, et retourne {filename_fn(e_km,n_km): url}.
    `typename` permet de viser un autre produit LiDAR HD du même WFS : le nuage
    classé COPC LAZ (`IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle`, cf. fr-ign-dfm).

    Chaque feature de dalle porte un attribut `url` = le download DIRECT du
    GeoTIFF (WMS GetMap pour la Réunion, lien de téléchargement + apikey public
    pour la Guadeloupe ; les deux sont de simples GET → GeoTIFF 0,5 m). On garde
    l'url telle quelle (toujours fraîche depuis le WFS). Le filtre `projection`
    évite de mélanger des territoires si la bbox chevauche plusieurs CRS.
    Retourne None sur échec réseau, {} si aucune dalle. Utilisé par fr-reunion /
    fr-guadeloupe (mutualisation : mêmes jumeaux, seuls CRS + préfixe changent)."""
    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = bbox_natif
    q = (f"{_IGN_WFS}?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
         f"&TYPENAMES={typename}&SRSNAME=EPSG:{epsg}"
         f"&BBOX={x1},{y1},{x2},{y2},EPSG:{epsg}"
         f"&COUNT=2000&OUTPUTFORMAT=application/json")
    try:
        req = urllib.request.Request(q, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=90, context=_CTX) as r:
            gj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print(f"  ERROR IGN LiDAR-HD WFS: {type(e).__name__}: {e}")
        return None
    dalles = {}
    for feat in gj.get("features", []):
        p = feat.get("properties", {})
        url = p.get("url")
        if not url or str(p.get("projection", "")).upper() != f"EPSG:{epsg}":
            continue
        m = _IGN_NAME_RE.match(p.get("name_download", "") or p.get("name", "") or "")
        if not m:
            continue
        dalles[filename_fn(int(m.group(1)), int(m.group(2)))] = url
    return dalles


def las_to_dfm(src_las, tif_path, crs_epsg, resolution=0.5,
               hmin=0.4, hmax=2.5, classes_low=(1, 3, 4),
               classes_ground=(2, 9, 66), ref_ground=(2,),
               nodata=-9999.0, bounds=None):
    """LAS/LAZ classé → GeoTIFF façon **DFM** (Digital Feature Model) :
    le terrain PLUS les structures encore debout que le bare-earth efface.

    ÉTIQUETAGE HONNÊTE : le CONCEPT vient de la littérature (Štular et al. 2021 :
    DEM interpolé depuis sol + bâtiments + structures archéo ; la tranche de
    hauteur normalisée comme premier tri est une pratique nDSM standard). Mais
    la SÉLECTION automatique ci-dessous (réinjection des classes basses dans les
    lacunes de la classe sol, seuils 0,4-2,5 m) est une HEURISTIQUE maison
    calibrée sur 2 sites du Var — la littérature fait cette étape par
    reclassification (semi-)manuelle du nuage (cas canonique : ruine de château
    sous forêt). Première passe de prospection, pas la méthode publiée.

    Méthode (heuristique, cf. tools/dfm_ruines.py) :
      1. binning min-z du sol (`classes_ground`, défaut 2/9/66 = les classes du
         MNT IGN officiel : sol + eau + points virtuels) — les murs y font des
         TROUS ;
      2. hauteur des points au-dessus du sol comblé ;
      3. les trous de sol sont comblés par le min-z des points bas NON-sol
         (`classes_low`, hauteur hmin-hmax) : sur un mur c'est le mur (le
         classificateur l'a mis en « végétation »/« non classé ») ; sur un
         buisson pénétré, la cellule a du sol → le sol est gardé ;
      4. comblement final IDW borné (rasterio fillnodata) ; les cellules HORS
         portée restent nodata (jamais 0 : un faux z=0 ferait une falaise
         artificielle dans le LRM).
    `bounds=(x0,y0,x1,y1)` : bornes NOMINALES de la dalle (ex. le km IGN) →
    grille exactement alignée entre dalles voisines (sans ça, l'origine dérive
    de la position des points réels et le VRT mosaïque des dalles décalées
    d'une fraction de pixel — coutures). Points hors bornes clippés.
    Le maquis dense revient AUSSI (mouchetis) : la discrimination finale est
    visuelle (murs = lignes continues). RAM : pic ~2-3 Go pour une dalle IGN de
    34 M pts — les conversions sont SÉRIALISÉES par _CONV_LOCK (le pool de
    download a 8 workers). Écriture ATOMIQUE (.tmp → replace) : un crash en
    cours de conversion ne laisse pas de GeoTIFF partiel pris pour valide.
    """
    import laspy
    import numpy as np
    import rasterio
    from rasterio.fill import fillnodata
    from rasterio.transform import from_bounds

    with _CONV_LOCK:
        las = laspy.read(str(src_las))
        xs = np.asarray(las.x); ys = np.asarray(las.y)
        zs = np.asarray(las.z); cls = np.asarray(las.classification)
        del las
        if xs.size == 0:
            raise ValueError(f"{Path(src_las).name}: nuage vide")

        res = float(resolution)
        if bounds is not None:
            x0, y0, x1, y1 = (float(v) for v in bounds)
            dedans = (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)
            xs, ys, zs, cls = xs[dedans], ys[dedans], zs[dedans], cls[dedans]
            if xs.size == 0:
                raise ValueError(f"{Path(src_las).name}: aucun point dans les "
                                 f"bornes nominales {bounds}")
            nx = max(1, int(round((x1 - x0) / res)))
            ny = max(1, int(round((y1 - y0) / res)))
        else:
            x0, x1 = float(xs.min()), float(xs.max())
            y0, y1 = float(ys.min()), float(ys.max())
            nx = int(np.floor((x1 - x0) / res)) + 1
            ny = int(np.floor((y1 - y0) / res)) + 1
            y1 = y0 + ny * res      # bord haut du raster = grille, pas max(ys)
        col = np.clip(((xs - x0) / res).astype(np.int64), 0, nx - 1)
        row = np.clip(((y1 - ys) / res).astype(np.int64), 0, ny - 1)
        flat = row * nx + col

        def _binmin(mask):
            g = np.full(ny * nx, np.inf)
            np.minimum.at(g, flat[mask], zs[mask])
            return g

        def _fill(g):
            """Comblement IDW borné. Les cellules hors portée restent NaN
            (PAS 0), converties en nodata à l'écriture."""
            G = g.reshape(ny, nx).astype(np.float32)
            m = np.isfinite(G)
            if (~m).any() and m.any():
                G = fillnodata(np.where(m, G, np.nan).astype(np.float32),
                               mask=m.astype("uint8"),
                               max_search_distance=200.0 / res,
                               smoothing_iterations=0)
            return G

        # RÉFÉRENCE de hauteur (toujours la classe sol, indépendante du socle
        # de SORTIE) : une « coupe à 1,5 m du sol » en terrain penté exige de
        # connaître le sol même s'il n'apparaît pas dans le raster produit.
        if tuple(ref_ground) == tuple(classes_ground):
            sol_ref_raw = _binmin(np.isin(cls, ref_ground))
            sol_raw = sol_ref_raw
        else:
            sol_ref_raw = _binmin(np.isin(cls, ref_ground))
            sol_raw = (_binmin(np.isin(cls, classes_ground))
                       if classes_ground else np.full(ny * nx, np.inf))
        sol_ref = _fill(sol_ref_raw)
        h = zs - np.where(np.isfinite(sol_ref), sol_ref, np.inf)[row, col]
        low = np.isin(cls, classes_low) & (h >= hmin) & (h <= hmax)
        low_min = _binmin(low)

        dfm = sol_raw.copy()
        holes = ~np.isfinite(dfm)
        dfm[holes] = low_min[holes]                    # murs réintroduits
        if classes_ground:
            grid = _fill(dfm)                          # DFM : fond continu
        else:
            # COUPE (socle vide) : les objets de la tranche seuls, fond nodata
            # (transparent en aval) — pas de comblement qui inventerait un fond.
            grid = dfm.reshape(ny, nx).astype(np.float32)
        grid = np.where(np.isfinite(grid), grid, nodata).astype(np.float32)

        transform = from_bounds(x0, y0, x0 + nx * res, y0 + ny * res, nx, ny)
        tmp = Path(str(tif_path) + ".conv.tmp")
        with rasterio.open(str(tmp), "w",
                           driver="GTiff", height=ny, width=nx,
                           count=1, dtype="float32",
                           crs=rasterio.CRS.from_epsg(crs_epsg),
                           transform=transform, nodata=nodata,
                           compress="deflate", predictor=3, tiled=True) as dst:
            dst.write(grid, 1)
        tmp.replace(tif_path)


def las_to_dtm(src_las, tif_path, crs_epsg, resolution=1.0,
               classes=(2,), nodata=-9999.0, fill_holes=True, max_fill_m=100,
               bounds=None):
    """LAS/LAZ (fichier LOCAL déjà décompressé du transport) → GeoTIFF DTM.

    Méthode = BINNING min-z de la classe sol (équivalent de PDAL
    ``writers.gdal output_type=min``, mais en laspy+numpy, sans PDAL). Adapté aux
    nuages SOL denses (Lettonie ~1,5 pt/m² au sol, Montevideo) : chaque point sol
    tombe dans sa cellule `resolution` m, on garde le min (terrain). Cellules sans
    point sol = nodata. O(n), pas d'interpolation Delaunay (qui explose au-delà de
    ~10⁶ points) — c'est le bon levier pour du dense classifié, là où le fallback
    interpolé de cz_cuzk vise les nuages ÉPARS.

    `classes` : classifications LAS gardées (2 = sol ; ASPRS). Si < 100 points de
    ces classes, on retombe sur TOUS les points (nuage peut-être déjà ground-only)
    en le signalant. laspy lit le .las ; pour un .laz il faut un backend (lazrs).
    `bounds=(x0,y0,x1,y1)` : bornes NOMINALES de la dalle → grille alignée entre
    dalles voisines (sinon l'origine dérive des points réels → coutures au VRT).
    Conversion sérialisée (_CONV_LOCK, RAM) ; écriture atomique (.tmp → replace).
    """
    import laspy
    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds

    with _CONV_LOCK:
        las = laspy.read(str(src_las))
        cls = np.asarray(las.classification)
        mask = np.isin(cls, classes)
        if int(mask.sum()) < 100:
            print(f"  WARN {Path(src_las).name}: < 100 ground points (class {classes}),"
                  f" falling back to ALL points (DTM≈DSM if the cloud is not ground-only)",
                  flush=True)
            mask = np.ones(len(las.x), dtype=bool)

        xs = np.asarray(las.x, dtype=np.float64)[mask]
        ys = np.asarray(las.y, dtype=np.float64)[mask]
        zs = np.asarray(las.z, dtype=np.float64)[mask]
        del las
        if xs.size == 0:
            raise ValueError(f"{Path(src_las).name}: aucun point exploitable")

        res = float(resolution)
        if bounds is not None:
            x0, y0, x1, y1 = (float(v) for v in bounds)
            dedans = (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)
            xs, ys, zs = xs[dedans], ys[dedans], zs[dedans]
            if xs.size == 0:
                raise ValueError(f"{Path(src_las).name}: aucun point dans les "
                                 f"bornes nominales {bounds}")
            nx = max(1, int(round((x1 - x0) / res)))
            ny = max(1, int(round((y1 - y0) / res)))
        else:
            x0, x1 = float(xs.min()), float(xs.max())
            y0, y1 = float(ys.min()), float(ys.max())
            nx = int(np.floor((x1 - x0) / res)) + 1
            ny = int(np.floor((y1 - y0) / res)) + 1
            y1 = y0 + ny * res      # bord haut = grille (pas max(ys) brut)
        # indices cellule (origine haut-gauche : y1 en haut)
        col = np.clip(((xs - x0) / res).astype(np.int64), 0, nx - 1)
        row = np.clip(((y1 - ys) / res).astype(np.int64), 0, ny - 1)
        flat = row * nx + col
        grid = np.full(ny * nx, np.inf, dtype=np.float64)
        np.minimum.at(grid, flat, zs)          # min-z par cellule
        valid = np.isfinite(grid)
        grid[~valid] = nodata
        grid = grid.reshape(ny, nx).astype(np.float32)

        # Combler les trous (cellules sans point sol : sous canopée, bâti sur DTM
        # urbain…) par IDW borné : `max_fill_m` mètres de distance de recherche max,
        # pour raccorder un DTM continu SANS inventer de terrain à travers un grand
        # vide (lac, tuile de bord) qui doit rester nodata (transparent).
        if fill_holes and (~valid).any() and valid.any():
            try:
                from rasterio.fill import fillnodata
                m = valid.reshape(ny, nx).astype("uint8")   # 1 = valide
                grid = fillnodata(grid, mask=m,
                                  max_search_distance=float(max_fill_m / res),
                                  smoothing_iterations=0)
            except Exception as _e:
                print(f"  WARN fillnodata KO ({type(_e).__name__}): DTM à trous conservé",
                      flush=True)

        transform = from_bounds(x0, y0, x0 + nx * res, y0 + ny * res, nx, ny)
        tmp = Path(str(tif_path) + ".conv.tmp")
        with rasterio.open(str(tmp), "w",
                           driver="GTiff", height=ny, width=nx,
                           count=1, dtype="float32",
                           crs=rasterio.CRS.from_epsg(crs_epsg),
                           transform=transform, nodata=nodata,
                           compress="deflate", predictor=2, tiled=True) as dst:
            dst.write(grid, 1)
        tmp.replace(tif_path)


def _membre_sous(nom, cible_resolue):
    """True si le membre d'archive `nom` reste sous `cible_resolue` (déjà
    resolue). Refuse les chemins absolus (/ \\ ou lettre de lecteur) et les
    traversées `..` qui sortiraient du dossier cible."""
    if nom.startswith(("/", "\\")) or (len(nom) > 1 and nom[1] == ":"):
        return False
    dest = (cible_resolue / nom).resolve()
    return dest == cible_resolue or cible_resolue in dest.parents


def extraire_membre(zf, member, dest_dir):
    """Extrait le membre `member` d'un ZipFile OUVERT `zf` sous `dest_dir`, en
    refusant les chemins absolus et les traversées `..` (zip-slip).

    Le cœur valide déjà ses extractions (`_safe_zip_extractall`) ; les
    providers doivent passer par ici plutôt qu'un `zf.extract()` nu, où le nom
    de membre venu d'une archive distante pourrait s'échapper du cache.
    Retourne le Path du fichier extrait. Lève ValueError sur membre suspect."""
    dest_dir = Path(dest_dir).resolve()
    if not _membre_sous(member, dest_dir):
        raise ValueError(f"Chemin de membre ZIP suspect (zip-slip) : {member!r}")
    zf.extract(member, dest_dir)
    return dest_dir / member
