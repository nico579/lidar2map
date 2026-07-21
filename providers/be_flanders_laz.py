# providers/be_flanders_laz.py — Belgique (Flandre), « mode LAZ » DHMV II
#
# CONTEXTE : Digitaal Vlaanderen diffuse le nuage LiDAR brut DHMV II (campagne
#   2013-2015) en données ouvertes, LAZ CLASSÉ, tuiles 500 m, ~11-16 pts/m²
#   (8 pts/m² par bande, ~16 avec recouvrement). Très dense : excellent pour le
#   micro-relief archéologique (murs étroits), meilleur que l'Estonie (4 pts/m²),
#   comparable au bon LiDAR HD. Petite région (Flandre + Bruxelles) mais complète.
#
# JUMEAU LAZ de be-flanders (raster DTM 1 m WCS) : la machinerie vit dans
#   common.LazProvider (partagée fr/ch/pl/ee). Spécifique Flandre :
#   - Découverte : WFS OpenLidar `openlidar:LiDAR_DHMV_II_LAZtiles` où chaque
#     tuile 500 m porte son chemin `tile_location` ; l'URL de download = base
#     fixe + chemin (common.be_flanders_dalles).
#   - CRS EPSG:31370 (Lambert belge 1972) UNIQUE → pas de wrinkle multi-zones.
#     Le header LAZ est vide → chemin lenient du garde CRS.
#   - Bornes = bloc 500 m nominal depuis la géométrie de l'index (anti-couture).
#   - Défaut ground=csf : la classification Flandre est minimale (1/2/9, le
#     sursol est en « non classé » 1), le tissu CSF s'en affranchit.
#
# Licence : Gratis Open Data Licentie Vlaanderen. Self-contained : stdlib.
# (laspy/lazrs/rasterio requis au runtime.)

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Belgique (Flandre) — mode LAZ DHMV II 0,5 m (~11 pts/m², expérimental)"
CODE       = "be-flanders-laz"
COUNTRY    = "be"
LICENSE    = "Gratis Open Data Licentie Vlaanderen"
DOC_URL    = "https://remotesensing.vlaanderen.be/apps/openlidar/"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:31370"         # Belge Lambert 1972 (unique)
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 100_000              # .tif produit (tuile 500 m)


# ── Bornes par tuile : lookup peuplé à la découverte (géométrie de l'index) ──
_TILE_BOUNDS = {}


def _bounds_nominaux(x, y):
    return _TILE_BOUNDS.get((int(x), int(y)))


# ── Découverte (WFS OpenLidar, mutualisée) ───────────────────────────────────
def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    dalles = common.be_flanders_dalles(bbox_natif, dalle_filename, _TILE_BOUNDS)
    if dalles is None:
        return None
    if dalles:
        print(f"  BE Flanders LAZ (DHMV II): {len(dalles)} tile(s) in the bbox "
              f"(classified cloud ~11 pts/m², ~{len(dalles) * _P.tile_mb} MB)")
    else:
        print("  BE Flanders LAZ: no DHMV II tile here")
    return dalles


# ── Machinerie LAZ (mutualisée) ──────────────────────────────────────────────
# Préfixe « be_laz05 » (laz = nuage ; 05 = version de méthode). Socle ASPRS
# (2=sol, 9=eau) ; classes réinjectables incluent 1 (non classé, où vivent les
# murs en Flandre). Défaut ground=csf.
_P = common.LazProvider(
    prefix="be_laz05", crs_epsg=31370, resolution=RESOLUTION_M,
    socle_possible=(2, 9),
    defaults=(0.4, 2.5, (1, 2, 3, 4, 6, 9), "csf"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=_bounds_nominaux, discover_fn=_discover,
    zipped=False, tile_mb=17)

# Plafond de téléchargements parallèles : tuiles ~17 Mo sur le portail public
# Digitaal Vlaanderen → prudent, 3 max.
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
dalle_subdir     = _P.dalle_subdir
subdir_from_name = _P.subdir_from_name
variant_tag      = _P.variant_tag
method_label     = _P.method_label
discover_dalles  = _P.discover_dalles
pre_download     = _P.pre_download
post_fetch       = _P.post_fetch
set_cloud_cache_dir = _P.set_cloud_cache_dir
laz_defaults     = _P.defaults_dict
# Internes exposés pour les tests
_socle           = _P.socle
_reinjectees     = _P.reinjectees
_laz_filename    = _P.laz_filename


def dalle_url(x, y):
    raise NotImplementedError("be-flanders-laz : URL via WFS OpenLidar → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("be-flanders-laz : index WFS → discover_dalles()")
