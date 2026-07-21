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

# Concurrence des conversions LAS→raster. Le post_fetch tourne DANS le pool de
# téléchargement et une dalle IGN de 34 M pts pique à ~3 Go de RAM : par DÉFAUT
# une seule à la fois (sémaphore 1 = ex-verrou, anti-OOM sur 8 Go). `--laz-parallel
# N` élargit à N (VM multi-cœurs + RAM) : CSF scale mal en threads (optimum ~2),
# donc N conversions à OMP=cœurs/N remplissent mieux les cœurs qu'une seule à
# OMP=tous. Les téléchargements restent parallèles (le sémaphore n'entoure que la
# conversion). Réglé par set_laz_parallelism() avant tout run.
_CONV_SEM = threading.Semaphore(1)


def set_laz_parallelism(k):
    """Fixe le nombre de conversions LAS→raster simultanées (défaut 1). Appelé
    par le cœur quand --laz-parallel N est passé, AVANT toute conversion."""
    global _CONV_SEM
    _CONV_SEM = threading.Semaphore(max(1, int(k)))

# Source UNIQUE des pays : code ISO, nom EN, nom FR. L'ORDRE est l'ordre
# d'affichage (READMEs, carte de couverture, dropdown provider de la GUI), pas
# un tri alphabétique. Un COUNTRY de provider absent d'ici fait échouer la
# génération de la carte (garde-fou anti-drift dans coverage_map.py).
# Vit ici plutôt que dans coverage_map.py depuis 2026-07-20 : la GUI groupe sa
# liste de providers par pays et a besoin des mêmes noms — deux tables auraient
# dérivé. Ajouter un pays = 1 ligne ici.
COUNTRY_NAMES = [
    ("fr", "France", "France"),
    ("gb", "UK", "Royaume-Uni"),
    ("de", "Germany", "Allemagne"),
    ("at", "Austria", "Autriche"),
    ("nl", "Netherlands", "Pays-Bas"),
    ("ch", "Switzerland", "Suisse"),
    ("no", "Norway", "Norvège"),
    ("be", "Belgium", "Belgique"),
    ("lu", "Luxembourg", "Luxembourg"),
    ("fi", "Finland", "Finlande"),
    ("dk", "Denmark", "Danemark"),
    ("se", "Sweden", "Suède"),
    ("ie", "Ireland", "Irlande"),
    ("cz", "Czechia", "Tchéquie"),
    ("si", "Slovenia", "Slovénie"),
    ("ee", "Estonia", "Estonie"),
    ("lv", "Latvia", "Lettonie"),
    ("es", "Spain", "Espagne"),
    ("pt", "Portugal", "Portugal"),
    ("it", "Italy", "Italie"),
    ("pl", "Poland", "Pologne"),
    ("us", "USA", "USA"),
    ("ca", "Canada", "Canada"),
    ("nz", "New Zealand", "Nouvelle-Zélande"),
    ("au", "Australia", "Australie"),
    ("ph", "Philippines", "Philippines"),
    ("jp", "Japan", "Japon"),
]

# code ISO → (rang d'affichage, nom EN, nom FR)
COUNTRY_INFO = {c: (i, en, fr) for i, (c, en, fr) in enumerate(COUNTRY_NAMES)}

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
    classé COPC LAZ (`IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle`, cf. fr-ign-laz).

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


# === Pologne GUGiK (nuage LiDAR ISOK) ========================================
# GUGiK publie l'INDEX des nuages LiDAR (« skorowidze ») en WFS, un typename par
# année. Chaque feature porte l'URL de download LAZ DIRECTE (attribut
# `gugik:url_do_pobrania`) — même paradigme que le WFS IGN. Deux subtilités
# validées par sondage (2026-07-21) :
#   1. l'INDEX est en EPSG:2180 (PL-1992) mais le WFS attend le BBOX en ordre
#      (Nord, Est) — l'inverse de always_xy (Est, Nord) — d'où le swap ;
#   2. le NUAGE lui-même est en PL-2000 PAR ZONE (EPSG:2176-2179 selon la
#      longitude), pas en 2180 : c'est le provider qui pose la zone via set_crs.
_GUGIK_WFS = ("https://mapy.geoportal.gov.pl/wss/service/PZGIK/"
              "DanePomiaroweLidarKRON86/WFS/Skorowidze")
_GUGIK_TN = "gugik:SkorowidzDanychPomiarowychLIDAR{year}"


def gugik_dalles(bbox_natif, filename_fn, years=tuple(range(2019, 2009, -1)),
                 ua="lidar2map/1.0"):
    """WFS skorowidze GUGiK → {filename_fn(x, y): url_laz}. `bbox_natif` =
    EPSG:2180 en always_xy (E, N) ; le WFS veut (N, E) → swap. UNION des années
    (newest-first), dédup par tuile (une feuille reprise garde le millésime le
    plus récent = le plus dense). (x, y) = coin SW de la feuille en 2180 (entiers,
    unique par tuile ; le nommage n'a pas besoin d'être km-aligné). None sur échec
    réseau total, {} si aucune tuile dans la bbox."""
    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = (float(v) for v in bbox_natif)      # always_xy (E, N)
    bbox = f"{y1},{x1},{y2},{x2},EPSG:2180"              # WFS veut (N, E)
    dalles, vus, any_ok = {}, set(), False
    for year in years:
        q = (f"{_GUGIK_WFS}?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
             f"&TYPENAMES={_GUGIK_TN.format(year=year)}&SRSNAME=EPSG:2180"
             f"&BBOX={bbox}&COUNT=2000")
        try:
            req = urllib.request.Request(q, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=90, context=_CTX) as r:
                body = r.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"  WARN GUGiK WFS {year}: {type(e).__name__}: {e}")
            continue
        any_ok = True
        # Un membre = une feuille. On parse par membre pour associer chaque
        # url_do_pobrania à SON lowerCorner (pas au boundedBy du document).
        for member in re.split(r"<(?:gml|wfs):(?:featureMember|member)\b", body)[1:]:
            u = re.search(r"<gugik:url_do_pobrania>([^<]+)</", member)
            lc = re.search(r"<gml:lowerCorner>([^<]+)</", member)
            if not u or not lc:
                continue
            p = lc.group(1).split()
            if len(p) < 2:
                continue
            x, y = int(float(p[0])), int(float(p[1]))    # coin SW (N, E) brut
            if (x, y) in vus:
                continue
            vus.add((x, y))
            dalles[filename_fn(x, y)] = u.group(1).strip()
    return dalles if any_ok else None


# === Belgique / Flandre (DHMV II, nuage LiDAR OpenLidar) =====================
# Digitaal Vlaanderen publie un WFS d'INDEX des tuiles LAZ 500 m (campagne DHMV
# II 2013-2015, ~11-16 pts/m² classées). Chaque feature porte `tile_location`
# (chemin RELATIF du .laz) + la géométrie de la tuile. Le download direct est
# la BASE fixe ci-dessous + le chemin (le .laz brut, pas zippé ; validé par
# sondage du featureInfoHandler.js de l'app OpenLidar, 2026-07-21). CRS EPSG:31370
# UNIQUE (pas de wrinkle). Le WFS accepte le BBOX en ordre always_xy (E, N).
_BE_WFS = "https://remotesensing.vlaanderen.be/services/openlidar/wfs"
_BE_TN = "openlidar:LiDAR_DHMV_II_LAZtiles"
_BE_DL = "https://remotesensing.vlaanderen.be/download/openlidar/"


def be_flanders_dalles(bbox_natif, filename_fn, bounds_sink, ua="lidar2map/1.0"):
    """Découverte Flandre (EPSG:31370) : WFS OpenLidar → {filename_fn(x,y): url}.
    Par tuile 500 m : `tile_location` (chemin .laz) → URL = base + chemin ;
    bounds = bloc 500 m nominal (coin SW arrondi, anti-couture) dans
    `bounds_sink[(x,y)]`. Dédup par bloc (une tuile par bloc, plusieurs bandes de
    vol sinon). None sur échec réseau, {} si aucune tuile."""
    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = (float(v) for v in bbox_natif)      # always_xy (E, N)
    q = (f"{_BE_WFS}?service=WFS&version=2.0.0&request=GetFeature"
         f"&typeNames={_BE_TN}&srsName=EPSG:31370&outputFormat=application/json"
         f"&count=4000&bbox={x1},{y1},{x2},{y2},EPSG:31370")
    try:
        req = urllib.request.Request(q, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=90, context=_CTX) as r:
            gj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print(f"  ERROR BE Flanders WFS: {type(e).__name__}: {e}")
        return None
    dalles = {}
    for feat in gj.get("features", []):
        p = feat.get("properties", {})
        loc = p.get("tile_location")
        bbox = _geom_bbox(feat.get("geometry") or {})
        if not loc or bbox is None:
            continue
        bx = int(bbox[0] // 500) * 500                    # bloc 500 m (coin SW)
        by = int(bbox[1] // 500) * 500
        if (bx, by) in bounds_sink:
            continue
        bounds_sink[(bx, by)] = (float(bx), float(by), float(bx + 500), float(by + 500))
        dalles[filename_fn(bx, by)] = _BE_DL + loc
    return dalles


# === CRAIG / LiDARAURA (Auvergne-Rhône-Alpes) ================================
# CRAIG publie ses nuages classés sur un partage Nextcloud PUBLIC (validé
# 2026-07-18 : PROPFIND 207 stable, download `/s/<token>/download?...` SANS auth).
# L'archive est MULTI-CAMPAGNES et chacune a son propre micro-format (champ
# d'index, dossier, nommage, tailles de tuiles) : câbler les ~19 en aveugle =
# mouton à 5 pattes. On décrit donc explicitement (config-as-data) les campagnes
# nuage-classé .laz VALIDÉES ; la découverte fait l'UNION filtrée par bbox. Les
# bornes de chaque tuile viennent de la GÉOMÉTRIE de l'index (tailles variables
# selon campagne : 2019 = 200 m, 2021 = 500 m), pas d'une formule.
CRAIG_BASE = "https://drive.opendata.craig.fr"
CRAIG_SHARE = "opendata"          # token du partage public (download sans auth)
# (campagne, index TA du nuage classé, champ-sous-dossier, préfixe-dossier)
CRAIG_CLOUD_CAMPAIGNS = [
    ("2019_lidar", "TA_LiDAR_2019_semis_classe_L93.shp.zip", "zone", "02.2_Semis_classe"),
    ("2021_lidar", "TA_LiDAR_2021_semis_classe_L93.shp.zip", "dossier", ""),
]
# MNT raster (parent) : 2019 a un index MNT propre (.asc 0,5 m) ; 2021 n'a qu'un
# index `MN.gpkg` (schéma différent), différé. Le raster CRAIG est secondaire
# (le MNT IGN couvre déjà la France) ; le parent existe surtout pour héberger le
# mode LAZ (case LAZ) et le remap `--laz`.
CRAIG_MNT_CAMPAIGNS = [
    ("2019_lidar", "TA_LiDAR_2019_MNT_L93.shp.zip", "zone", "03_MNT"),
]


def _craig_public_url(campaign, subdir, filename):
    """URL de download PUBLIC du partage Nextcloud (aucune auth)."""
    from urllib.parse import quote
    path = ("/altimetrie/" + campaign + "/" + subdir).rstrip("/")
    return (f"{CRAIG_BASE}/s/{CRAIG_SHARE}/download"
            f"?path={quote(path)}&files={quote(filename)}")


def _geom_bbox(geom):
    """(xmin,ymin,xmax,ymax) d'une géométrie GeoJSON (Polygon/MultiPolygon).
    Gère les coordonnées 2D ET 3D (Flandre DHMV : [X, Y, Z]) : un sommet = une
    liste d'AU MOINS 2 nombres (on prend X=o[0], Y=o[1], Z ignoré). Un anneau
    (liste de sommets) a des éléments-listes → on récurse."""
    xs, ys = [], []

    def walk(o):
        if isinstance(o, (list, tuple)):
            if len(o) >= 2 and all(isinstance(v, (int, float)) for v in o):
                xs.append(o[0]); ys.append(o[1])
            else:
                for e in o:
                    walk(e)
    walk(geom.get("coordinates"))
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def _craig_ta_local(campaign, ta_index, cache_dir, ua):
    """Télécharge+cache le shapefile zippé d'assemblage (index) d'une campagne."""
    cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)
    local = cache_dir / f"{campaign}__{ta_index}"
    if local.exists() and local.stat().st_size > 1000:
        return local
    url = _craig_public_url(campaign, "01_TA", ta_index)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        tmp = local.with_suffix(local.suffix + ".part")
        with urllib.request.urlopen(req, timeout=90, context=_CTX) as r, \
                open(tmp, "wb") as f:
            f.write(r.read())
        tmp.replace(local)
        return local
    except Exception as e:
        print(f"  ERROR CRAIG index {campaign}/{ta_index}: {type(e).__name__}: {e}")
        return None


def craig_dalles(bbox_natif, filename_fn, bounds_sink, cache_dir,
                 campaigns=CRAIG_CLOUD_CAMPAIGNS, ua="lidar2map/1.0"):
    """Découverte CRAIG (EPSG:2154) : UNION des campagnes du registre. Pour
    chacune, télécharge+cache l'index TA (shapefile), garde les tuiles dont la
    géométrie intersecte `bbox_natif`, remplit `bounds_sink[(x,y)]` avec les
    bornes EXACTES de la tuile (anti-couture, tailles variables) et retourne
    {filename_fn(x,y): url_download_public}. `dalle` = 'X-Y' (hectomètres)."""
    import fiona
    if bbox_natif is None:
        return {}
    bb = tuple(float(v) for v in bbox_natif)
    dalles = {}
    for (camp, ta, field, prefix) in campaigns:
        ta_local = _craig_ta_local(camp, ta, cache_dir, ua)
        if ta_local is None:
            continue
        try:
            with fiona.open(f"zip://{ta_local}") as src:
                for feat in src.filter(bbox=bb):
                    p = feat["properties"]
                    m = re.match(r"^(\d+)-(\d+)$", str(p.get("dalle") or ""))
                    if not m:
                        continue
                    x, y = int(m.group(1)), int(m.group(2))
                    bbox = _geom_bbox(feat["geometry"])
                    if bbox is None:
                        continue
                    bounds_sink[(x, y)] = bbox
                    fmt = str(p.get("format") or ".laz")
                    sub = str(p.get(field) or "").strip("/")
                    subdir = (prefix + "/" if prefix else "") + sub
                    dalles[filename_fn(x, y)] = _craig_public_url(
                        camp, subdir, m.group(0) + fmt)
        except Exception as e:
            print(f"  ERROR CRAIG index {camp}: {type(e).__name__}: {e}")
    return dalles


# === Estonie Maa-amet (nuage LiDAR ALS) ======================================
# Le nuage LiDAR 1 km est en LAZ tava (standard, ~4 pts/m²) — le DTM raster
# (ee_maaamet) est une FORMULE de feuilles 5 km, mais le nuage exige l'ANNÉE de
# scan par feuille (le nom `{NR}_{année}_tava.laz`), non dérivable des coords.
# On lit donc l'index 1:2000 officiel (epk2T, ~1,3 Mo, caché) qui porte, par
# feuille 1 km : NR (numéro), ALS_TAVA_1..4 (années standard), géométrie. CRS
# EPSG:3301 unique (pas de wrinkle). Validé bout-en-bout 2026-07-21.
_EE_INDEX_URL = "https://geoportaal.maaamet.ee/docs/pohikaart/epk2T_SHP.zip"
_EE_LAZ_TMPL = ("https://geoportaal.maaamet.ee/index.php?lang_id=1&page_id=614"
                "&plugin_act=otsing&andmetyyp=lidar_laz_tava&kaardiruut={nr}"
                "&dl=1&f={nr}_{year}_tava.laz")


def _cache_download(url, local, ua):
    """Télécharge+cache un fichier (index). Retourne le Path local ou None."""
    local = Path(local)
    local.parent.mkdir(parents=True, exist_ok=True)
    if local.exists() and local.stat().st_size > 1000:
        return local
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        tmp = local.with_suffix(local.suffix + ".part")
        with urllib.request.urlopen(req, timeout=120, context=_CTX) as r, \
                open(tmp, "wb") as f:
            f.write(r.read())
        tmp.replace(local)
        return local
    except Exception as e:
        print(f"  ERROR index {url}: {type(e).__name__}: {e}")
        return None


def ee_maaamet_dalles(bbox_natif, filename_fn, bounds_sink, cache_dir,
                      ua="lidar2map/1.0"):
    """Découverte Estonie (EPSG:3301) : index 1:2000 epk2T (caché) filtré par
    bbox. Par feuille 1 km : NR + année tava la plus récente (ALS_TAVA_1..4) →
    URL LAZ standard ; bounds = géométrie de la feuille (1 km, anti-couture) dans
    `bounds_sink[(x_km,y_km)]`. Feuilles sans acquisition standard (madal/mets
    seuls) ignorées. {filename_fn(x_km,y_km): url}. None sur échec index."""
    import fiona
    if bbox_natif is None:
        return {}
    idx = _cache_download(_EE_INDEX_URL, Path(cache_dir) / "ee_epk2T_SHP.zip", ua)
    if idx is None:
        return None
    bb = tuple(float(v) for v in bbox_natif)
    dalles = {}
    try:
        with fiona.open(f"zip://{idx}") as src:
            for feat in src.filter(bbox=bb):
                p = feat["properties"]
                nr = p.get("NR")
                years = [p.get(f"ALS_TAVA_{i}") for i in (1, 2, 3, 4)]
                years = [int(y) for y in years if y]
                if nr is None or not years:
                    continue
                bbox = _geom_bbox(feat["geometry"])
                if bbox is None:
                    continue
                x_km, y_km = int(bbox[0] // 1000), int(bbox[1] // 1000)
                bounds_sink[(x_km, y_km)] = bbox
                dalles[filename_fn(x_km, y_km)] = _EE_LAZ_TMPL.format(
                    nr=int(nr), year=max(years))
    except Exception as e:
        print(f"  ERROR EE index: {type(e).__name__}: {e}")
        return None
    return dalles


def _verifie_crs_las(nom, las, expected_epsg):
    """Garde défensif (revue LAZ 2026-07-18) : refuse la conversion si le header
    LAS déclare un CRS incompatible avec celui que le provider annonce, plutôt
    que de produire un GeoTIFF SILENCIEUSEMENT FAUX. Deux motifs de refus :
      1. EPSG horizontal RÉSOLUBLE et différent de `expected_epsg` ;
      2. unité horizontale non-métrique (ex. LAS USGS en ftUS : la grille 0,5 m
         et les seuils 0,4-2,5 m sont en mètres, un fichier en pieds sortirait
         faux d'un facteur ~3,28).
    LENIENT sur l'incertain : CRS absent, compound non dénouable, ou non
    résoluble -> on PROCÈDE en faisant confiance au provider (comportement
    historique). Objectif = bloquer le mismatch CONFIANT, pas faux-refuser les
    sources (fr/ch validées : IGN LAZ porte EPSG:2154 métrique propre).
    """
    try:
        crs = las.header.parse_crs()
    except Exception:
        return                        # header illisible -> confiance provider
    if crs is None:
        return                        # pas de CRS -> confiance provider
    horiz = crs
    try:
        if crs.is_compound and crs.sub_crs_list:
            horiz = crs.sub_crs_list[0]   # dénoue 2056+hauteur & co.
    except Exception:
        pass
    try:
        epsg = horiz.to_epsg()
    except Exception:
        epsg = None
    if epsg is not None and int(epsg) != int(expected_epsg):
        raise ValueError(
            f"{nom}: le nuage déclare EPSG:{epsg}, le provider attend "
            f"EPSG:{expected_epsg} (projection/unités incompatibles, la sortie "
            f"serait silencieusement fausse)")
    try:
        unites = {ax.unit_name.lower() for ax in horiz.axis_info}
    except Exception:
        unites = set()
    if unites and not (unites <= {"metre", "meter", "m"}):
        raise ValueError(
            f"{nom}: unité horizontale {sorted(unites)} non-métrique (grille et "
            f"seuils sont en mètres) ; conversion d'unités requise avant de "
            f"brancher ce provider")


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
    canopée entière. Coût mesuré (dalle IGN 45 M pts, machine 4 cœurs) : ~4 min
    de sim CSF (machine-dépendant), contre ~25 s pour "classes".

    `bounds=(x0,y0,x1,y1)` : bornes NOMINALES de la dalle (ex. le km IGN) →
    grille exactement alignée entre dalles voisines (sans ça, l'origine dérive
    de la position des points réels et le VRT mosaïque des dalles décalées
    d'une fraction de pixel — coutures). Points hors bornes clippés.
    Le maquis dense revient AUSSI (mouchetis en "classes", résidus ponctuels en
    "csf") : la discrimination finale est visuelle (murs = lignes continues).
    RAM : pic ~2,9 Go/dalle 45 M pts (mesuré 3,2 Go avant optim ; pic dominé par
    les copies float64 de PRÉPA, pas par la sim). On saute la copie du clip si
    tout est déjà dans les bornes, sinon dim par dim (del progressif). Le passage
    en float32 relatif a été ESSAYÉ puis rejeté : il fait basculer la classif CSF
    (8k cellules, jusqu'à 3,3 m) pour un gain RAM dérisoire. Conversions
    SÉRIALISÉES par _CONV_SEM (anti-OOM : sur 8 Go on ne tient pas 2 en
    parallèle). Écriture ATOMIQUE (.tmp → replace) : un crash en cours de
    conversion ne laisse pas de GeoTIFF partiel pris pour valide.
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

    with _CONV_SEM:
        las = laspy.read(str(src_las))
        _verifie_crs_las(Path(src_las).name, las, crs_epsg)
        xs = np.asarray(las.x); ys = np.asarray(las.y)
        zs = np.asarray(las.z); cls = np.asarray(las.classification)
        try:
            # .astype(bool) OBLIGATOIRE : laspy renvoie le flag WITHHELD (LAS 1.4
            # pf6+) en uint8. Sans le cast, `bruit(bool) | wh(uint8)` promeut en
            # uint8, puis `~bruit` fait un complément BITWISE et `xs[garde]` un
            # indexage ENTIER (fancy) au lieu d'un masque → l'emprise collapse.
            # Invisible sur fr/ch (0 bruit → bloc filtre sauté) ; révélé par la
            # Pologne (classe 7 présente), cf. docs/dfm_reviews.md.
            wh = np.asarray(las.withheld).astype(bool)
        except Exception:
            wh = None
        del las
        if xs.size == 0:
            raise ValueError(f"{Path(src_las).name}: nuage vide")

        # Robustesse min-z (revue LAZ 2026-07-18) : le BRUIT (classes ASPRS 7 bas
        # / 18 haut) et les points WITHHELD ne doivent pas définir le sol — un
        # seul point aberrant bas creuse le DFM puis se propage au fillnodata. On
        # les écarte avant tout binning (modes classes ET csf en profitent ; la
        # spec ASPRS LAS 1.4 dit que les withheld ne se traitent pas comme les
        # autres).
        bruit = np.isin(cls, (7, 18))
        if wh is not None:
            bruit = bruit | wh
        if bruit.any():
            garde = ~bruit
            xs, ys, zs, cls = xs[garde], ys[garde], zs[garde], cls[garde]
            if xs.size == 0:
                raise ValueError(f"{Path(src_las).name}: que du bruit/withheld")

        res = float(resolution)
        if bounds is not None:
            x0, y0, x1, y1 = (float(v) for v in bounds)
            nx = max(1, int(round((x1 - x0) / res)))
            ny = max(1, int(round((y1 - y0) / res)))
            # Clip aux bornes. (a) SAUTÉ si tout est déjà dedans (la copie ne
            # filtrerait rien, cas fréquent) ; (b) sinon dim par dim avec del
            # progressif (jamais anciens+nouveaux des 4 tableaux en double : ce
            # doublement momentané était le pic RAM mesuré, 3,2 Go/dalle 45M).
            # Coords gardées en float64 ABSOLU : le CSF n'est PAS invariant en
            # flottant au décalage/arrondi (float32 relatif essayé 2026-07-18 ->
            # 8k cellules divergentes jusqu'à 3,3 m pour ~66 Mo, rejeté).
            dedans = (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)
            if not dedans.all():
                xs = xs[dedans]; ys = ys[dedans]; zs = zs[dedans]; cls = cls[dedans]
                if xs.size == 0:
                    raise ValueError(f"{Path(src_las).name}: aucun point dans les "
                                     f"bornes nominales {bounds}")
            del dedans
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
            # 1.1.5) : pas de .tolist(), qui multiplierait la RAM par ~4. Coords
            # ABSOLUES float64 : ne PAS décaler/arrondir (le CSF y est sensible,
            # cf. commentaire clip).
            csf.setPointCloud(np.column_stack([xs[keep], ys[keep], zs[keep]]))
            g_idx, ng_idx = CSF.VecInt(), CSF.VecInt()
            # exportCloth=False (revue perf 2026-07-18) : le wrapper CSF.py met le
            # défaut à True, ce qui écrit le tissu dans un cloth_nodes.txt (~188 Mo
            # sur une dalle 1 km, std::endl = flush par ligne) DANS le cwd APRÈS la
            # simulation. L'export ne touche PAS la classification (prouvé : la
            # variance run-to-run est la même avec/sans, = non-détermination OpenMP
            # de CSF, pas l'export) : -40,6 s/dalle et plus de fichier parasite,
            # sortie inchangée. (cloth_nodes.txt n'est PAS une sortie de lidar2map.)
            csf.do_filtering(g_idx, ng_idx, False)
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
    Conversion sérialisée (_CONV_SEM, RAM) ; écriture atomique (.tmp → replace).
    """
    import laspy
    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds

    with _CONV_SEM:
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
    collection swissalti3d) et ch-swisstopo-laz (nuage .las.zip, collection
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


# ── Machinerie commune du mode LAZ (structures debout) ───────────────────────
# Partagée par les jumeaux <code>-laz (fr-ign-laz, ch-swisstopo-laz…). Un seul
# endroit pour : réglages (hmin/hmax/classes/ground + tissu CSF t/r/g), encodage
# INJECTIF des réglages ≠ défauts dans le nom de dalle (pas de collision de cache
# entre essais), variant_tag (projet DFM distinct du projet MNT), et les hooks
# pre_download/post_fetch (nuage gardé en cache → reconversion sans réseau).
# Chaque jumeau instancie LazProvider avec SES spécificités (préfixe, CRS,
# découverte, convention de bornes, download zippé ou non, socle par défaut) et
# expose des delegators module-level pour le contrat provider. Extrait de
# fr_ign_laz 2026-07-17 quand ch-swisstopo-laz est arrivé (2e instance =
# généralisation consciente, cf. principe generaliser-puis-specialiser).

class LazProvider:
    """État + logique du mode LAZ d'un provider nuage-de-points.

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
    download_workers_max : plafond de téléchargements PARALLÈLES (le cœur lit
                   DOWNLOAD_WORKERS_MAX exposé par le module). Les nuages LAZ
                   pèsent ~200 Mo : à 8 en parallèle, IGN throttle et coupe la
                   connexion en silence (transferts tronqués) ; 3 max lisse ça.
    """

    def __init__(self, *, prefix, crs_epsg, resolution, socle_possible,
                 defaults, csf_defaults=(0.5, 0.5, 1),
                 bounds_fn=None, discover_fn=None, zipped=False,
                 tile_mb=205, download_workers_max=3):
        self.prefix = prefix
        self.crs_epsg = crs_epsg
        self.resolution = resolution
        self.socle_possible = tuple(socle_possible)
        self.bounds_fn = bounds_fn
        self._discover = discover_fn
        self.zipped = zipped
        self.tile_mb = tile_mb
        self.download_workers_max = download_workers_max
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
        # Racine (hors du dossier des .tif) où le nuage .laz est GARDÉ. Posée par
        # le cœur en mode LAZ : le .tif descend en production (produit), le nuage
        # reste au cache (download). None (défaut) = nuage co-localisé avec le
        # .tif (ancien comportement, gardé pour les tests unitaires).
        self.cloud_cache_dir = None
        # Toute dalle .tif porte le token de méthode (dfm_ = réinjection classes,
        # csf_ = tissu) ; le nuage caché .laz n'en a pas (partagé entre méthodes).
        self.nom_re = re.compile(
            rf"{re.escape(prefix)}_(?:dfm_(?:h[\d-]+_)?(?:c[\d-]+_)?"
            rf"|csf_(?:t\d+_)?(?:r\d+_)?(?:g\d_)?)(\d+)_(\d+)\.tif$")

    def method_label(self):
        """Étiquette du mode ACTIF, alignée sur le nom de sortie (laz_dfm /
        laz_csf) : le log ne dit plus 'DFM' quand on tourne le tissu CSF. La
        méthode (DFM = réinjection classes, CSF = tissu) reste sous l'ombrelle
        LAZ (nuage), cohérent avec la case GUI « Mode LAZ »."""
        return "LAZ_CSF" if self.ground == "csf" else "LAZ_DFM"

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
        """Réglages DFM du run (appelé par _load_provider depuis --laz-*). Les
        valeurs ≠ défauts sont ENCODÉES dans le nom des dalles (cf. suffix), et
        le nuage gardé en cache permet de reconvertir sans retélécharger."""
        if ground is not None:
            if ground not in ("classes", "csf"):
                raise ValueError(f"laz-ground: {ground!r} (attendu 'classes' ou 'csf')")
            self.ground = ground
        # Arrondi décimètre (pas de la GUI) → encodage ·10 du nom INJECTIF
        # (0,31 et 0,34 ne peuvent pas partager un cache).
        if csf_threshold is not None:
            self.csf_threshold = round(float(csf_threshold), 1)
            if not 0.1 <= self.csf_threshold <= 3.0:
                raise ValueError(f"laz-csf-threshold ({self.csf_threshold}) hors 0,1-3,0 m")
        if csf_resolution is not None:
            self.csf_resolution = round(float(csf_resolution), 1)
            if not 0.1 <= self.csf_resolution <= 3.0:
                raise ValueError(f"laz-csf-resolution ({self.csf_resolution}) hors 0,1-3,0 m")
        if csf_rigidness is not None:
            self.csf_rigidness = int(csf_rigidness)
            if self.csf_rigidness not in (1, 2, 3):
                raise ValueError(f"laz-csf-rigidness ({self.csf_rigidness}) attendu 1, 2 ou 3")
        if hmin is not None:
            self.hmin = round(float(hmin), 1)
        if hmax is not None:
            self.hmax = round(float(hmax), 1)
        if classes is not None:
            self.classes = tuple(sorted(int(c) for c in classes))
        if self.hmin >= self.hmax:
            raise ValueError(f"laz-hmin ({self.hmin}) doit être < laz-hmax ({self.hmax})")
        if self.ground == "csf":
            # Le tissu ignore classes et tranche : prévenir plutôt qu'interdire
            # (la GUI masque ces champs, le CLI peut encore les passer).
            if hmin is not None or hmax is not None or classes is not None:
                print(f"  {self.method_label()}: hmin/hmax/classes are IGNORED "
                      "(the cloth does the selection)", flush=True)
            if self.csf_rigidness == 3:
                print(f"  {self.method_label()}: rigidness 3 (flat terrain) -> "
                      "near bare-earth cloth, standing walls may be erased "
                      "(use 1 on slopes)", flush=True)
            return
        if (csf_threshold is not None or csf_resolution is not None
                or csf_rigidness is not None):
            print(f"  {self.method_label()}: csf-* settings are IGNORED "
                  "(pass --laz-ground csf)", flush=True)
        # Compositions légitimes, signalées plutôt qu'interdites :
        #   - sans classe 2 → COUPE (tranche seule, fond nodata ; la classe 2
        #     reste la référence de hauteur en interne, cf. las_to_dfm) ;
        #   - sans classe réinjectée → modèle ≈ MNT reconstruit.
        if 2 not in self.classes:
            print(f"  {self.method_label()}: class 2 not selected -> slice mode "
                  "(band objects only, transparent background; heights still "
                  "measured above class-2 ground)", flush=True)
        if not self.reinjectees():
            print(f"  {self.method_label()}: no re-injected class selected -> "
                  "output ≈ rebuilt DTM", flush=True)

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
    def _check_deps(self):
        """Deps vérifiées AVANT le download lourd (revue LAZ 2026-07-18) : sans
        ça on tirait ~200 Mo de nuage puis on échouait à la conversion faute de
        laspy / CSF."""
        try:
            import laspy  # noqa: F401
        except ImportError:
            raise RuntimeError("le mode LAZ requiert laspy (pip install laspy lazrs)")
        if self.ground == "csf":
            try:
                import CSF  # noqa: F401
            except ImportError:
                raise RuntimeError("--laz-ground csf requiert 'cloth-simulation-filter' "
                                   "(pip install cloth-simulation-filter)")

    def discover_dalles(self, bbox_wgs84, bbox_natif, cache_path, workers=1):
        self._check_deps()
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
        cloud = self._cloud_path(chemin, m)
        with zipfile.ZipFile(chemin) as z:
            membres = [n for n in z.namelist()
                       if n.lower().endswith((".las", ".laz"))]
            if not membres:
                raise ValueError(f"Aucun .las/.laz dans {chemin.name}")
            # ZIP multi-nuages (bandes de vol superposées : cf. Danemark/Flandre
            # dans la revue) : on garde le plus gros mais on le SIGNALE (le drop
            # silencieux perdait des points sans trace).
            if len(membres) > 1:
                print(f"  WARN {chemin.name}: {len(membres)} nuages dans le ZIP, "
                      f"seul le plus gros est gardé (fusion non implémentée)",
                      flush=True)
            membre = max(membres, key=lambda n: z.getinfo(n).file_size)
            tmp = Path(str(cloud) + ".part")
            with z.open(membre) as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst)
        tmp.replace(cloud)                 # atomique
        chemin.unlink(missing_ok=True)
        return cloud

    def set_cloud_cache_dir(self, path):
        """Le cœur indique où GARDER le nuage .laz (le cache), distinct du dossier
        des .tif produits (la production). None = co-localisé avec le .tif."""
        self.cloud_cache_dir = Path(path) if path is not None else None

    def set_crs(self, epsg):
        """Fixe le CRS EPSG du run. Défaut = celui de l'init (mono-CRS, fr/ch).
        Sert aux sources MULTI-ZONES (ex. Pologne PL-2000, EPSG:2176-2179 selon
        la longitude) : le provider calcule la zone du bbox à la découverte et
        la pose ici → las_to_dfm sort le GeoTIFF dans la bonne zone, et le garde
        CRS (_verifie_crs_las) compare le header à cette zone."""
        if epsg is not None:
            self.crs_epsg = int(epsg)

    def _cloud_path(self, chemin, m):
        """Chemin du nuage .laz. Avec cloud_cache_dir posé, il vit sous
        <cache>/<colonne>/ indépendamment du dossier du .tif (produit → production) ;
        sinon co-localisé avec le .tif (parent), comme avant."""
        if m is None:
            return chemin.with_suffix(".laz")
        if self.cloud_cache_dir is not None:
            d = self.cloud_cache_dir / self.dalle_subdir(m.group(1))
            d.mkdir(parents=True, exist_ok=True)
            return d / self.laz_filename(m.group(1), m.group(2))
        return chemin.parent / self.laz_filename(m.group(1), m.group(2))

    def pre_download(self, chemin):
        """Hook cœur (avant réseau) : si le nuage de cette dalle est déjà en
        cache (gardé par post_fetch), reconvertir au lieu de retélécharger.
        C'est ce qui rend les réglages LAZ ajustables sans coût réseau."""
        chemin = Path(chemin)
        m = self.nom_re.match(chemin.name)
        if not m:
            return False
        cloud = self._cloud_path(chemin, m)
        if not cloud.exists() or cloud.stat().st_size < 1_000_000:
            return False
        print(f"  {self.method_label()} {chemin.name}: rebuilding from cached "
              f"point cloud ({cloud.name}, no re-download"
              f"{', CSF ~3 min' if self.ground == 'csf' else ''})...", flush=True)
        self._convert(cloud, chemin, m.group(1), m.group(2))
        return True

    def post_fetch(self, chemin):
        """Le download est le nuage (LAS/LAZ brut = magic LASF, ou ZIP = magic PK
        si zipped), écrit sous un nom .tif par le cœur. On isole le nuage, on le
        GARDE en cache (reconversion sans réseau, cf. pre_download), puis on
        convertit via las_to_dfm. Conversion sérialisée (_CONV_SEM, RAM)."""
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
            cloud = self._cloud_path(chemin, m)
            try:
                chemin.replace(cloud)          # atomique si même volume
            except OSError:
                # cache et production sur des volumes différents (--production-dir) :
                # os.rename échoue cross-device (EXDEV), shutil.move copie+supprime.
                import shutil
                shutil.move(str(chemin), str(cloud))
        else:
            return  # déjà un GeoTIFF (ou erreur → validateur)
        print(f"  {self.method_label()} {chemin.name}: converting point cloud "
              f"({'CSF, ~3 min' if self.ground == 'csf' else '~20-30 s'})...",
              flush=True)
        if m:
            self._convert(cloud, chemin, m.group(1), m.group(2))
        else:
            self._convert(cloud, chemin)
