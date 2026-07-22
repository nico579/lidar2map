# providers/ca_nrcan_laz.py — Canada, « mode LAZ » nuage LiDAR CanElevation (COPC)
#
# CONTEXTE : NRCan diffuse le nuage LiDAR national (CanElevation Series) en
#   COPC (LAZ 1.4 réorganisé en octree) sur S3, données ouvertes. Très dense
#   (~40 pts/m² sur les levés testés) : excellent pour le micro-relief. Chaque
#   COPC = une feuille NTS de 200-750 Mo → on ne rapatrie PAS le fichier entier :
#   lecture FENÊTRÉE via range-requests (COPC_WINDOWED, cf. telecharger_copc_fenetre).
#
# JUMEAU LAZ de ca-nrcan (raster HRDEM COG) : machinerie dans common.LazProvider.
#   Spécifique Canada :
#   - Découverte : index GeoPackage des tuiles (407 Mo) requêté À DISTANCE via
#     /vsicurl (R-tree + range-requests, ~2 s/bbox, pas de download complet).
#     Chaque tuile porte son `URL` COPC directe.
#   - CRS MULTI-ZONES : les COPC sont en UTM NAD83(CSRS) PAR ZONE (compound avec
#     CGVD2013), variable selon la longitude. Lu dans le header du COPC et posé
#     par run via LazProvider.set_crs (dans telecharger_copc_fenetre) → la sortie
#     est dans la bonne zone ; le warp du cœur lit le CRS du fichier produit.
#     CRS_NATIF = géographique (EPSG:4617) : sert au cadrage et au fenêtrage WGS84.
#   - bounds_fn=None : la fenêtre lue définit l'emprise (pas de grille nominale).
#   - Défaut ground=csf.
#   LIMITE : nuage TRÈS dense → sur une zone d'1 km² la fenêtre fait ~40 M points
#   (~1 Go .las temporaire, ~3 Go RAM en conversion). Zone PETITE conseillée.
#
# Licence : Open Government Licence — Canada. Self-contained : stdlib + laspy
# (CopcReader), fiona (/vsicurl), pyproj au runtime.

import os

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Canada — mode LAZ nuage LiDAR CanElevation (COPC, ~40 pts/m², expérimental)"
CODE       = "ca-nrcan-laz"
COUNTRY    = "ca"
LICENSE    = "Open Government Licence — Canada"
DOC_URL    = "https://nrcan.github.io/CanElevation/pointclouds/"


# ── Géométrie ────────────────────────────────────────────────────────────────
# CRS_NATIF = géographique (index + cadrage) ; le CRS de SORTIE est la zone UTM
# du COPC, posée par run via set_crs. COPC_WINDOWED : lecture fenêtrée /vsicurl.
CRS_NATIF          = "EPSG:4617"          # NAD83(CSRS) géographique
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 100_000
COPC_WINDOWED      = True


# ── Index des tuiles (GeoPackage distant, requêté par /vsicurl) ──────────────
_INDEX_URL = ("https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/"
              "pointclouds_nuagespoints/Index_LiDARtiles_tuileslidar.gpkg")
_INDEX_VSICURL = "/vsicurl/" + _INDEX_URL
_LAYER = "index_lidartiles_tuileslidar"


# ── Découverte ───────────────────────────────────────────────────────────────
def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Requête spatiale À DISTANCE de l'index GPKG (R-tree /vsicurl) → tuiles COPC
    intersectant la bbox. (x,y) = coin SW de l'emprise géographique encodé en
    entiers POSITIFS ((lon+180)·1e4, lat·1e4 ; résolution ~10 m, unique par
    tuile). L'URL COPC est portée par l'attribut `URL`."""
    if bbox_wgs84 is None:
        return {}
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".gpkg")
    os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
    import fiona
    lo1, la1, lo2, la2 = (float(v) for v in bbox_wgs84)
    dalles, vus = {}, set()
    try:
        with fiona.open(_INDEX_VSICURL, layer=_LAYER) as src:
            for feat in src.filter(bbox=(lo1, la1, lo2, la2)):
                p = feat["properties"]
                url = p.get("URL")
                if not url or not str(url).endswith(".copc.laz"):
                    continue
                bb = common._geom_bbox(feat["geometry"])   # géographique (lon,lat)
                if bb is None:
                    continue
                x = int(round((bb[0] + 180.0) * 10000))    # lon SW → positif
                y = int(round(bb[1] * 10000))              # lat SW
                if (x, y) in vus:
                    continue
                vus.add((x, y))
                dalles[dalle_filename(x, y)] = str(url)
    except Exception as e:
        print(f"  ERROR NRCan index: {type(e).__name__}: {e}")
        return None
    if dalles:
        print(f"  CA NRCan LAZ (COPC): {len(dalles)} tile(s) in the bbox "
              f"(windowed read, dense ~40 pts/m² — keep the area small!)")
    else:
        print("  CA NRCan LAZ: no COPC tile here")
    return dalles


# ── Machinerie LAZ (mutualisée) ──────────────────────────────────────────────
# Préfixe « ca_laz05 ». crs_epsg initial = UTM 12N (EPSG:2956) placeholder,
# ÉCRASÉ par run via set_crs (zone lue dans le header COPC). Socle ASPRS (2/9),
# défaut csf.
_P = common.LazProvider(
    prefix="ca_laz05", crs_epsg=2956, resolution=RESOLUTION_M,
    socle_possible=(2, 9),
    defaults=(0.4, 2.5, (1, 2, 3, 4, 5, 6), "csf"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=None, discover_fn=_discover,
    zipped=False, tile_mb=200)

DOWNLOAD_WORKERS_MAX = _P.download_workers_max

# Défauts exposés (lus par le cœur pour préremplir la GUI + par les tests)
LAZ_HMIN           = _P.def_hmin
LAZ_HMAX           = _P.def_hmax
LAZ_CLASSES        = _P.def_classes
LAZ_GROUND         = _P.def_ground
LAZ_CSF_THRESHOLD  = _P.def_csf_threshold
LAZ_CSF_RESOLUTION = _P.def_csf_resolution
LAZ_CSF_RIGIDNESS  = _P.def_csf_rigidness

# Contrat provider : delegators vers l'instance partagée
set_laz_params   = _P.set_params
dalle_filename   = _P.dalle_filename
subdir_from_name = _P.subdir_from_name
variant_tag      = _P.variant_tag
method_label     = _P.method_label
discover_dalles  = _P.discover_dalles
pre_download     = _P.pre_download
post_fetch       = _P.post_fetch
set_cloud_cache_dir = _P.set_cloud_cache_dir
set_crs          = _P.set_crs          # posé par run dans telecharger_copc_fenetre
# Internes exposés pour les tests
_socle           = _P.socle
_reinjectees     = _P.reinjectees
_laz_filename    = _P.laz_filename

