# providers/ee_maaamet_dfm.py — Estonie, « mode LAZ » depuis le nuage LiDAR ALS
#
# CONTEXTE : Maa-amet (Estonian Land and Spatial Development Board) diffuse le
#   nuage LiDAR national (aerolaserskaneerimine) en données OUVERTES, LAZ 1.4
#   CLASSÉ, tuiles 1 km², produit STANDARD (« tava ») ~4 pts/m². Densité
#   MARGINALE pour du micro-relief 0,5 m (vs 20 IGN, 28 Pologne) mais couverture
#   nationale complète et rejouée (plusieurs millésimes).
#
# JUMEAU DFM de ee-maaamet (raster DTM 1 m, FORMULE de feuilles 5 km) : la
#   machinerie DFM vit dans common.DfmProvider (partagée fr/ch/pl). Spécifique
#   Estonie : le nuage exige l'ANNÉE de scan par feuille (nom
#   `{NR}_{année}_tava.laz`), non dérivable des coords → on lit l'INDEX 1:2000
#   officiel (epk2T, ~1,3 Mo, caché) qui porte par feuille 1 km le numéro NR, les
#   années standard (ALS_TAVA_1..4) et la géométrie (common.ee_maaamet_dalles).
#   On prend le millésime tava le plus récent. Les feuilles à basse altitude
#   « madal » (~280 Mo/km², zones denses) ne sont PAS utilisées (le tava suffit
#   et pèse ~30-45 Mo).
#
# CRS EPSG:3301 (L-EST97) UNIQUE, national : pas de wrinkle multi-zones. Le
#   header LAZ déclare un CRS COMPOUND (3301 + EVRF2007) → le garde CRS dénoue
#   le sous-CRS horizontal (3301) et valide. Défaut ground=csf (le tissu ignore
#   le schéma de classes : en Estonie le sursol est surtout classe 5, peu de 3/4).
#
# Licence : Maa-amet open data (libre, perso et commerciale, sans compte).
# Self-contained : stdlib uniquement (laspy/lazrs/rasterio requis au runtime).

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Estonie — mode LAZ nuage LiDAR ALS 0,5 m (~4 pts/m², expérimental)"
CODE       = "ee-maaamet-dfm"
COUNTRY    = "ee"
LICENSE    = "Maa-amet open data — utilisation libre"
DOC_URL    = "https://geoportaal.maaamet.ee/est/Ruumiandmed/Korgusandmed-p114.html"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3301"          # L-EST97 (national, unique)
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 100_000              # .tif produit (feuille 1 km²)


# ── Bornes par feuille : lookup peuplé à la découverte (géométrie de l'index) ─
_TILE_BOUNDS = {}


def _bounds_nominaux(x_km, y_km):
    return _TILE_BOUNDS.get((int(x_km), int(y_km)))


# ── Découverte (index 1:2000 epk2T, mutualisée) ──────────────────────────────
def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    dalles = common.ee_maaamet_dalles(bbox_natif, dalle_filename, _TILE_BOUNDS, cache_path)
    if dalles is None:
        return None
    if dalles:
        print(f"  EE Maa-amet LAZ (ALS tava): {len(dalles)} tile(s) in the bbox "
              f"(classified cloud ~4 pts/m², ~{len(dalles) * _P.tile_mb} MB)")
    else:
        print("  EE Maa-amet LAZ: no standard (tava) tile here")
    return dalles


# ── Machinerie DFM (mutualisée) ──────────────────────────────────────────────
# Préfixe « ee_laz05 » (laz = nuage ; 05 = version de méthode). Socle ASPRS
# (2=sol, 9=eau) ; classes réinjectables incluent 5 (haute végé, dominante en
# Estonie) — filtrées par la tranche hmin-hmax de toute façon. Défaut ground=csf.
_P = common.DfmProvider(
    prefix="ee_laz05", crs_epsg=3301, resolution=RESOLUTION_M,
    socle_possible=(2, 9),
    defaults=(0.4, 2.5, (2, 3, 4, 5, 6), "csf"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=_bounds_nominaux, discover_fn=_discover,
    zipped=False, tile_mb=44)

# Plafond de téléchargements parallèles : tuiles tava ~30-45 Mo sur le portail
# public Maa-amet → prudent, 3 max.
DOWNLOAD_WORKERS_MAX = _P.download_workers_max

# Défauts exposés (lus par le cœur pour préremplir la GUI + par les tests)
DFM_HMIN           = _P.def_hmin
DFM_HMAX           = _P.def_hmax
DFM_CLASSES        = _P.def_classes
DFM_GROUND         = _P.def_ground
DFM_CSF_THRESHOLD  = _P.def_csf_threshold
DFM_CSF_RESOLUTION = _P.def_csf_resolution
DFM_CSF_RIGIDNESS  = _P.def_csf_rigidness

# Contrat provider : delegators vers l'instance partagée
set_dfm_params   = _P.set_params
dalle_filename   = _P.dalle_filename
dalle_subdir     = _P.dalle_subdir
subdir_from_name = _P.subdir_from_name
variant_tag      = _P.variant_tag
method_label     = _P.method_label
discover_dalles  = _P.discover_dalles
pre_download     = _P.pre_download
post_fetch       = _P.post_fetch
set_cloud_cache_dir = _P.set_cloud_cache_dir
dfm_defaults     = _P.defaults_dict
# Internes exposés pour les tests
_socle           = _P.socle
_reinjectees     = _P.reinjectees
_laz_filename    = _P.laz_filename


def dalle_url(x_km, y_km):
    raise NotImplementedError("ee-maaamet-dfm : URL via index epk2T → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("ee-maaamet-dfm : index epk2T → discover_dalles()")
