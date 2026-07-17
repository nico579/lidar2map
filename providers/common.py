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
               ground_method="classes",
               csf_threshold=0.5, csf_resolution=0.5, csf_rigidness=1,
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

    Méthode `ground_method="classes"` (heuristique, cf. tools/dfm_ruines.py) :
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

    Méthode `ground_method="csf"` (Cloth Simulation Filter, Zhang et al. 2016,
    package pip cloth-simulation-filter) : IGNORE les classes du producteur.
    Un tissu « mou » (rigidness 1) est drapé sur le nuage inversé ; ses points
    « sol » ABSORBENT les structures basses continues (murs, ruines) tout en
    rejetant la végétation — validé terrain 2026-07-16 sur les 2 sites du Var :
    fond plus propre que la réinjection par classes (pas de mouchetis), signal
    équivalent. Pas de réinjection ensuite (le tissu fait le tri) : hmin/hmax/
    classes_low/classes_ground sont IGNORÉS. Réglables par site (surface
    standard CloudCompare) : `csf_threshold` (distance point-tissu max pour
    être absorbé au sol, monter = murs plus dégradés ET plus de maquis),
    `csf_resolution` (maille du tissu en m), `csf_rigidness` (type de terrain
    Zhang : 1 pentu — défaut, calibré Var —, 2 relief doux, 3 plat ; à 3 le
    tissu tend vers un bare-earth qui efface les murs, usage « re-MNT sans les
    classes », pas ruines). time_step/itérations/pré-filtre restent figés
    (cuisine du solveur, aucun sens terrain). Pré-filtre canopée AVANT le
    tissu (grille 5 m de min-z, garde z ≤ min+3,5 m, indépendant des
    classes) : ~57 % des points gardés, sans quoi la simulation paie la
    canopée entière. Coût mesuré (dalle IGN 34 M pts) : ~3 min et 1,7 Go de
    RAM, contre ~25 s pour "classes".

    `bounds=(x0,y0,x1,y1)` : bornes NOMINALES de la dalle (ex. le km IGN) →
    grille exactement alignée entre dalles voisines (sans ça, l'origine dérive
    de la position des points réels et le VRT mosaïque des dalles décalées
    d'une fraction de pixel — coutures). Points hors bornes clippés.
    Le maquis dense revient AUSSI (mouchetis en "classes", résidus ponctuels en
    "csf") : la discrimination finale est visuelle (murs = lignes continues).
    RAM : pic ~2-3 Go pour une dalle IGN de 34 M pts — les conversions sont
    SÉRIALISÉES par _CONV_LOCK (le pool de download a 8 workers). Écriture
    ATOMIQUE (.tmp → replace) : un crash en cours de conversion ne laisse pas
    de GeoTIFF partiel pris pour valide.
    """
    import laspy
    import numpy as np
    import rasterio
    from rasterio.fill import fillnodata
    from rasterio.transform import from_bounds

    if ground_method == "csf":
        try:
            import CSF
        except ImportError:
            raise RuntimeError(
                "ground_method='csf' requires the 'cloth-simulation-filter' "
                "package (pip install cloth-simulation-filter)")
    elif ground_method != "classes":
        raise ValueError(f"ground_method inconnu: {ground_method!r} "
                         "(attendu 'classes' ou 'csf')")

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

        if ground_method == "csf":
            # Pré-filtre canopée : grille 5 m de min-z, garde z ≤ min+3,5 m
            # (marge au-dessus de la tranche murs ~2,5 m). Indépendant des
            # classes : c'est le point du CSF (ne pas dépendre du producteur).
            res5 = 5.0
            n5x = max(1, int((x1 - x0) / res5) + 1)
            n5y = max(1, int((y1 - y0) / res5) + 1)
            c5 = np.clip(((xs - x0) / res5).astype(np.int64), 0, n5x - 1)
            r5 = np.clip(((y1 - ys) / res5).astype(np.int64), 0, n5y - 1)
            f5 = r5 * n5x + c5
            g5 = np.full(n5y * n5x, np.inf)
            np.minimum.at(g5, f5, zs)
            keep = zs <= (g5[f5] + 3.5)
            del c5, r5, f5, g5
            # Tissu MOU par défaut : rigidness 1 + seuil 0,5 m → les
            # structures basses continues sont absorbées dans le « sol », la
            # canopée résiduelle est rejetée (défauts calibrés Var 2026-07-16,
            # réglables par site, cf. docstring).
            csf = CSF.CSF()
            csf.params.bSloopSmooth = True
            csf.params.cloth_resolution = float(csf_resolution)
            csf.params.rigidness = int(csf_rigidness)
            csf.params.class_threshold = float(csf_threshold)
            csf.params.time_step = 0.65
            # np-array (N,3) accepté directement (testé cloth-simulation-filter
            # 1.1.5) : pas de .tolist(), qui multiplierait la RAM par ~4.
            csf.setPointCloud(np.column_stack([xs[keep], ys[keep], zs[keep]]))
            g_idx, ng_idx = CSF.VecInt(), CSF.VecInt()
            csf.do_filtering(g_idx, ng_idx)
            sol_csf = np.zeros(xs.size, dtype=bool)
            sol_csf[np.flatnonzero(keep)[np.asarray(g_idx, dtype=np.int64)]] = True
            del csf, g_idx, ng_idx, keep
            grid = _fill(_binmin(sol_csf))             # pas de réinjection
        else:
            # RÉFÉRENCE de hauteur (toujours la classe sol, indépendante du
            # socle de SORTIE) : une « coupe à 1,5 m du sol » en terrain penté
            # exige de connaître le sol même s'il n'apparaît pas dans le
            # raster produit.
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
            dfm[holes] = low_min[holes]                # murs réintroduits
            if classes_ground:
                grid = _fill(dfm)                      # DFM : fond continu
            else:
                # COUPE (socle vide) : les objets de la tranche seuls, fond
                # nodata (transparent en aval) — pas de comblement qui
                # inventerait un fond.
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


def swisstopo_stac_dalles(collection, product_prefix, asset_ok,
                          bbox_wgs84, bbox_natif, cache_path,
                          stac_base="https://data.geo.admin.ch/api/stac/v1",
                          ua="lidar2map/1.0 (swisstopo STAC)"):
    """STAC swisstopo → {(e_km, n_km): (year, nom_asset, href)} dédupliqué au
    DERNIER millésime par tuile. Partagé par ch-swisstopo (raster COG,
    collection swissalti3d) et ch-swisstopo-dfm (nuage .las.zip, collection
    swisssurface3d) : seuls la collection, le préfixe produit et le prédicat
    d'asset changent (principe generaliser-puis-specialiser).

    collection     : ex. "ch.swisstopo.swissalti3d" / "...swisssurface3d".
    product_prefix : ex. "swissalti3d" / "swisssurface3d" — sert à extraire
                     E_km-N_km de l'ID (filtre bbox natif + dédup millésime).
    asset_ok(nom, asset) -> bool : sélectionne l'asset voulu (COG 0.5m 2056 /
                     .las.zip). Chaque appelant construit ENSUITE sa propre
                     table {clé: href} (le raster garde le nom d'asset comme
                     clé ; le DFM dérive son nom fr_laz05-style).
    Retourne None sur échec réseau. Cache PAR bbox (la requête STAC dépend de la
    bbox → son cache aussi ; un cache unique renverrait les items de la 1re bbox
    pour toutes, bug #4 vu sur ca-nrcan)."""
    import hashlib
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    bbox_str = f"{lon_min},{lat_min},{lon_max},{lat_max}"
    bbox_key = hashlib.md5(f"{collection}|{bbox_str}".encode()).hexdigest()[:12]
    cache_bbox = cache_path.with_name(f"{cache_path.stem}_{bbox_key}.json")

    items = []
    if cache_bbox.exists():
        try:
            items = json.loads(cache_bbox.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            items = []

    if not items:
        url = f"{stac_base}/collections/{collection}/items?bbox={bbox_str}&limit=100"
        print(f"  swisstopo STAC: querying {collection} bbox {bbox_str[:60]}...",
              flush=True)
        while url:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            try:
                with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
                    data = json.load(r)
            except Exception as e:
                print(f"  ERROR STAC ({type(e).__name__}): {e}")
                return None
            items.extend(data.get("features", []))
            url = None
            for link in data.get("links", []):
                if link.get("rel") == "next" and link.get("href"):
                    url = link["href"]
                    break
        try:
            cache_bbox.write_text(json.dumps({"bbox": bbox_str, "items": items}),
                                  encoding="utf-8")
        except Exception:
            pass

    # ID = "<prefix>_<year>_<E_km>-<N_km>" (le suffixe d'asset porte res/crs/elev)
    id_re = re.compile(rf"{re.escape(product_prefix)}_(\d+)_(\d+)-(\d+)")

    def _intersecte_natif(item_id):
        if bbox_natif is None:
            return True
        m = id_re.search(item_id)
        if not m:
            return True
        e_km, n_km = int(m.group(2)), int(m.group(3))
        fx0, fy0 = e_km * 1000, n_km * 1000       # coin SW (convention CH)
        fx1, fy1 = fx0 + 1000, fy0 + 1000
        zx0, zy0, zx1, zy1 = bbox_natif
        return not (fx1 < zx0 or fx0 > zx1 or fy1 < zy0 or fy0 > zy1)

    candidats = {}   # (e_km, n_km) -> (year, nom, href), dernier millésime
    n_assets = 0
    for it in items:
        iid = it.get("id", "")
        if not _intersecte_natif(iid):
            continue
        for nom, ass in (it.get("assets") or {}).items():
            if not asset_ok(nom, ass):
                continue
            href = ass.get("href")
            if not href:
                continue
            m = id_re.search(nom) or id_re.search(iid)
            if not m:
                continue
            n_assets += 1
            year, e_km, n_km = int(m.group(1)), int(m.group(2)), int(m.group(3))
            key = (e_km, n_km)
            prev = candidats.get(key)
            if prev is None or year > prev[0]:
                candidats[key] = (year, nom, href)

    print(f"  swisstopo : {len(items)} items, {n_assets} asset(s) → "
          f"{len(candidats)} tuile(s) (dernier millésime par tuile)")
    return candidats


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


# ── Machinerie commune du mode DFM (structures debout) ───────────────────────
# Partagée par les jumeaux <code>-dfm (fr-ign-dfm, ch-swisstopo-dfm…). Un seul
# endroit pour : réglages (hmin/hmax/classes/ground + tissu CSF t/r/g), encodage
# INJECTIF des réglages ≠ défauts dans le nom de dalle (pas de collision de cache
# entre essais), variant_tag (projet DFM distinct du projet MNT), et les hooks
# pre_download/post_fetch (nuage gardé en cache → reconversion sans réseau).
# Chaque jumeau instancie DfmProvider avec SES spécificités (préfixe, CRS,
# découverte, convention de bornes, download zippé ou non, socle par défaut) et
# expose des delegators module-level pour le contrat provider. Extrait de
# fr_ign_dfm 2026-07-17 quand ch-swisstopo-dfm est arrivé (2e instance =
# généralisation consciente, cf. principe generaliser-puis-specialiser).

class DfmProvider:
    """État + logique du mode DFM d'un provider nuage-de-points.

    prefix       : préfixe de nom de dalle ('laz' = source nuage), encode la
                   version de MÉTHODE (fr_laz05…). Bumper si l'algo de las_to_dfm
                   change de façon incompatible.
    crs_epsg     : EPSG natif (2154, 2056…).
    resolution   : résolution de sortie du GeoTIFF DFM (m).
    socle_possible : classes LAS qui, si sélectionnées, forment le socle terrain
                   (2/9/66 pour l'IGN). Le reste = réinjecté.
    defaults     : (hmin, hmax, classes, ground) par défaut.
    csf_defaults : (threshold, resolution, rigidness) du tissu par défaut.
    bounds_fn    : (x_km, y_km) -> (x0,y0,x1,y1) bornes NOMINALES (anti-couture
                   VRT). ATTENTION à la convention : IGN nomme par Y_MAX, la
                   plupart des STAC par coin SW.
    discover_fn  : découverte spécifique (WFS, STAC…) — signature provider.
    zipped       : True si le download est un ZIP (PK) enveloppant le nuage
                   (swisstopo .las.zip) → post_fetch dézippe ; False si LAS/LAZ
                   brut (IGN COPC, magic LASF).
    tile_mb      : taille indicative d'une dalle (message utilisateur).
    """

    def __init__(self, *, prefix, crs_epsg, resolution, socle_possible,
                 defaults, csf_defaults=(0.5, 0.5, 1),
                 bounds_fn=None, discover_fn=None, zipped=False,
                 tile_mb=205, log_tag="DFM"):
        self.prefix = prefix
        self.crs_epsg = crs_epsg
        self.resolution = resolution
        self.socle_possible = tuple(socle_possible)
        self.bounds_fn = bounds_fn
        self._discover = discover_fn
        self.zipped = zipped
        self.tile_mb = tile_mb
        self.log_tag = log_tag
        # défauts exposés (lus par le cœur pour préremplir la GUI + par les tests)
        (self.def_hmin, self.def_hmax,
         self.def_classes, self.def_ground) = defaults
        (self.def_csf_threshold, self.def_csf_resolution,
         self.def_csf_rigidness) = csf_defaults
        # état courant du run (muté par set_params)
        self.hmin, self.hmax = self.def_hmin, self.def_hmax
        self.classes, self.ground = self.def_classes, self.def_ground
        self.csf_threshold = self.def_csf_threshold
        self.csf_resolution = self.def_csf_resolution
        self.csf_rigidness = self.def_csf_rigidness
        # Toute dalle .tif porte le token de méthode (dfm_ = réinjection classes,
        # csf_ = tissu) ; le nuage caché .laz n'en a pas (partagé entre méthodes).
        self.nom_re = re.compile(
            rf"{re.escape(prefix)}_(?:dfm_(?:h[\d-]+_)?(?:c[\d-]+_)?"
            rf"|csf_(?:t\d+_)?(?:r\d+_)?(?:g\d_)?)(\d+)_(\d+)\.tif$")

    # ── socle / réinjectées ──────────────────────────────────────────────────
    def socle(self):
        """Classes du SOCLE terrain (parmi la sélection courante)."""
        return tuple(c for c in self.classes if c in self.socle_possible)

    def reinjectees(self):
        """Classes RÉINJECTÉES dans les trous du socle (tranche hmin-hmax)."""
        return tuple(c for c in self.classes if c not in self.socle_possible)

    # ── réglages du run ──────────────────────────────────────────────────────
    def set_params(self, hmin=None, hmax=None, classes=None, ground=None,
                   csf_threshold=None, csf_resolution=None, csf_rigidness=None):
        """Réglages DFM du run (appelé par _load_provider depuis --dfm-*). Les
        valeurs ≠ défauts sont ENCODÉES dans le nom des dalles (cf. suffix), et
        le nuage gardé en cache permet de reconvertir sans retélécharger."""
        if ground is not None:
            if ground not in ("classes", "csf"):
                raise ValueError(f"dfm-ground: {ground!r} (attendu 'classes' ou 'csf')")
            self.ground = ground
        # Arrondi décimètre (pas de la GUI) → encodage ·10 du nom INJECTIF
        # (0,31 et 0,34 ne peuvent pas partager un cache).
        if csf_threshold is not None:
            self.csf_threshold = round(float(csf_threshold), 1)
            if not 0.1 <= self.csf_threshold <= 3.0:
                raise ValueError(f"dfm-csf-threshold ({self.csf_threshold}) hors 0,1-3,0 m")
        if csf_resolution is not None:
            self.csf_resolution = round(float(csf_resolution), 1)
            if not 0.1 <= self.csf_resolution <= 3.0:
                raise ValueError(f"dfm-csf-resolution ({self.csf_resolution}) hors 0,1-3,0 m")
        if csf_rigidness is not None:
            self.csf_rigidness = int(csf_rigidness)
            if self.csf_rigidness not in (1, 2, 3):
                raise ValueError(f"dfm-csf-rigidness ({self.csf_rigidness}) attendu 1, 2 ou 3")
        if hmin is not None:
            self.hmin = round(float(hmin), 1)
        if hmax is not None:
            self.hmax = round(float(hmax), 1)
        if classes is not None:
            self.classes = tuple(sorted(int(c) for c in classes))
        if self.hmin >= self.hmax:
            raise ValueError(f"dfm-hmin ({self.hmin}) doit être < dfm-hmax ({self.hmax})")
        if self.ground == "csf":
            # Le tissu ignore classes et tranche : prévenir plutôt qu'interdire
            # (la GUI masque ces champs, le CLI peut encore les passer).
            if hmin is not None or hmax is not None or classes is not None:
                print("  DFM: ground=csf -> hmin/hmax/classes are IGNORED "
                      "(the cloth does the selection)", flush=True)
            if self.csf_rigidness == 3:
                print("  DFM: csf rigidness 3 (flat terrain) -> near bare-earth "
                      "cloth, standing walls may be erased (use 1 on slopes)",
                      flush=True)
            return
        if (csf_threshold is not None or csf_resolution is not None
                or csf_rigidness is not None):
            print("  DFM: ground=classes -> csf-* settings are IGNORED "
                  "(pass --dfm-ground csf)", flush=True)
        # Compositions légitimes, signalées plutôt qu'interdites :
        #   - sans classe 2 → COUPE (tranche seule, fond nodata ; la classe 2
        #     reste la référence de hauteur en interne, cf. las_to_dfm) ;
        #   - sans classe réinjectée → modèle ≈ MNT reconstruit.
        if 2 not in self.classes:
            print("  DFM: class 2 not selected -> slice mode (band objects only, "
                  "transparent background; heights still measured above class-2 "
                  "ground)", flush=True)
        if not self.reinjectees():
            print("  DFM: no re-injected class selected -> output ≈ rebuilt DTM",
                  flush=True)

    # ── nommage / cache ──────────────────────────────────────────────────────
    def suffix(self):
        """Partie variable du nom de dalle : TOUJOURS le token de méthode en tête
        ('dfm_' = réinjection classes, 'csf_' = tissu), puis les réglages ≠
        défauts en ordre FIXE. Injectif : ·10 sans perte, classes séparées par
        '-' (c1-34 ≠ c1-3-4) ; les réglages ignorés par une méthode ne sont PAS
        encodés (mêmes sorties = même cache)."""
        if self.ground == "csf":
            s = "csf_"
            if self.csf_threshold != self.def_csf_threshold:
                s += f"t{round(self.csf_threshold * 10):02d}_"
            if self.csf_resolution != self.def_csf_resolution:
                s += f"r{round(self.csf_resolution * 10):02d}_"
            if self.csf_rigidness != self.def_csf_rigidness:
                s += f"g{self.csf_rigidness}_"
            return s
        s = "dfm_"
        if (self.hmin, self.hmax) != (self.def_hmin, self.def_hmax):
            s += f"h{round(self.hmin * 10):02d}-{round(self.hmax * 10):02d}_"
        if self.classes != self.def_classes:
            s += "c" + "-".join(str(c) for c in self.classes) + "_"
        return s

    def variant_tag(self):
        """Tag injecté par le cœur dans le NOM DE ZONE → projet DISTINCT du projet
        MNT de la même zone (sans ça, un LRM MNT existant était réutilisé en
        silence après avoir coché la case). « laz_ » = la SOURCE (nuage de
        points), « dfm »/« csf » = la MÉTHODE. Ex. laz_dfm, laz_csf, laz_csf_t08,
        laz_dfm_h03-30. Le MNT (défaut) reste SANS marqueur (on marque
        l'exception, pas le cas courant — choix Nico 2026-07-17)."""
        return "laz_" + self.suffix().strip("_")

    def dalle_filename(self, x_km, y_km):
        return f"{self.prefix}_{self.suffix()}{int(x_km)}_{int(y_km)}.tif"

    def laz_filename(self, x_km, y_km):
        """Nom du nuage gardé en cache — SANS réglages (partagé entre essais).
        Suffixe .laz par convention même si le contenu est un .las non compressé
        (laspy lit selon l'en-tête, pas l'extension)."""
        return f"{self.prefix}_{int(x_km)}_{int(y_km)}.laz"

    def dalle_subdir(self, x_km):
        return f"{int(x_km)}"

    def subdir_from_name(self, nom):
        m = self.nom_re.match(nom)
        return m.group(1) if m else None

    def defaults_dict(self):
        """Défauts pour préremplir la GUI (source de vérité unique)."""
        return {
            "hmin": float(self.def_hmin), "hmax": float(self.def_hmax),
            "classes": ",".join(str(c) for c in self.def_classes),
            "ground": str(self.def_ground),
            "csf_threshold": float(self.def_csf_threshold),
            "csf_resolution": float(self.def_csf_resolution),
            "csf_rigidness": int(self.def_csf_rigidness),
        }

    # ── découverte / conversion / hooks ──────────────────────────────────────
    def discover_dalles(self, bbox_wgs84, bbox_natif, cache_path, workers=1):
        return self._discover(bbox_wgs84, bbox_natif, cache_path, workers)

    def _convert(self, cloud, tif, x_km=None, y_km=None):
        bounds = (self.bounds_fn(x_km, y_km)
                  if (self.bounds_fn and x_km is not None) else None)
        las_to_dfm(cloud, tif, crs_epsg=self.crs_epsg, resolution=self.resolution,
                   hmin=self.hmin, hmax=self.hmax,
                   classes_low=self.reinjectees(), classes_ground=self.socle(),
                   ground_method=self.ground,
                   csf_threshold=self.csf_threshold,
                   csf_resolution=self.csf_resolution,
                   csf_rigidness=self.csf_rigidness, bounds=bounds)

    def _extract_cloud(self, chemin, m):
        """Dézip du .las.zip swisstopo → le membre nuage (le plus gros .las/.laz)
        écrit DIRECTEMENT sous le nom de cache stable. On copie le flux du membre
        au lieu de zf.extract : le nom de membre distant ne touche jamais le
        système de fichiers (zip-slip impossible par construction) et deux tuiles
        dont l'archive nommerait son membre à l'identique ne se marchent pas
        dessus (pas de collision, pas de fichier résiduel au nom du membre)."""
        import shutil
        import zipfile
        cloud = (chemin.parent / self.laz_filename(m.group(1), m.group(2)) if m
                 else chemin.with_suffix(".laz"))
        with zipfile.ZipFile(chemin) as z:
            membres = [n for n in z.namelist()
                       if n.lower().endswith((".las", ".laz"))]
            if not membres:
                raise ValueError(f"Aucun .las/.laz dans {chemin.name}")
            membre = max(membres, key=lambda n: z.getinfo(n).file_size)
            tmp = Path(str(cloud) + ".part")
            with z.open(membre) as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst)
        tmp.replace(cloud)                 # atomique
        chemin.unlink(missing_ok=True)
        return cloud

    def pre_download(self, chemin):
        """Hook cœur (avant réseau) : si le nuage de cette dalle est déjà en
        cache (gardé par post_fetch), reconvertir au lieu de retélécharger.
        C'est ce qui rend les réglages DFM ajustables sans coût réseau."""
        chemin = Path(chemin)
        m = self.nom_re.match(chemin.name)
        if not m:
            return False
        cloud = chemin.parent / self.laz_filename(m.group(1), m.group(2))
        if not cloud.exists() or cloud.stat().st_size < 1_000_000:
            return False
        print(f"  {self.log_tag} {chemin.name}: rebuilding from cached point "
              f"cloud ({cloud.name}, no re-download"
              f"{', CSF ~3 min' if self.ground == 'csf' else ''})...", flush=True)
        self._convert(cloud, chemin, m.group(1), m.group(2))
        return True

    def post_fetch(self, chemin):
        """Le download est le nuage (LAS/LAZ brut = magic LASF, ou ZIP = magic PK
        si zipped), écrit sous un nom .tif par le cœur. On isole le nuage, on le
        GARDE en cache (reconversion sans réseau, cf. pre_download), puis on
        convertit via las_to_dfm. Conversion sérialisée (_CONV_LOCK, RAM)."""
        chemin = Path(chemin)
        try:
            with open(chemin, "rb") as fh:
                magic = fh.read(4)
        except OSError:
            return
        m = self.nom_re.match(chemin.name)
        if magic[:2] == b"PK":
            if not self.zipped:
                return  # ZIP inattendu pour ce provider
            cloud = self._extract_cloud(chemin, m)
        elif magic == b"LASF":
            cloud = (chemin.parent / self.laz_filename(m.group(1), m.group(2))
                     if m else chemin.with_suffix(".laz"))
            chemin.replace(cloud)
        else:
            return  # déjà un GeoTIFF (ou erreur → validateur)
        print(f"  {self.log_tag} {chemin.name}: converting point cloud "
              f"({'CSF, ~3 min' if self.ground == 'csf' else '~20-30 s'})...",
              flush=True)
        if m:
            self._convert(cloud, chemin, m.group(1), m.group(2))
        else:
            self._convert(cloud, chemin)
