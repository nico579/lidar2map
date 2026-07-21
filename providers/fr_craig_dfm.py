# providers/fr_craig_dfm.py — France (Auvergne-Rhône-Alpes), CRAIG « mode LAZ »
#
# CONTEXTE : le CRAIG (Centre Régional Auvergne-Rhône-Alpes de l'Information
#   Géographique) diffuse des nuages LiDAR CLASSÉS haute densité (~60 pts/m²,
#   ~6× le LiDAR HD IGN) sur un partage Nextcloud public. Idéal pour le micro-
#   relief archéologique (murs étroits). Validé bout-en-bout 2026-07-18.
#
# JUMEAU DFM de fr-craig (raster MNT CRAIG) : toute la machinerie DFM vit dans
#   common.DfmProvider, partagée avec fr-ign-dfm / ch-swisstopo-dfm. Spécifiques
#   CRAIG : découverte multi-campagnes par index shapefile (common.craig_dalles),
#   bornes par tuile depuis la géométrie de l'index (tailles variables selon
#   campagne : 2019 = 200 m, 2021 = 500 m), CRS ABSENT du header LAS (le provider
#   déclare EPSG:2154, chemin lenient du garde CRS), download public sans auth.
#   Défaut ground=csf : schéma de classes CRAIG (2/3/4/6, bâtiments en 6, pas de
#   1/9/66) ≠ IGN, le tissu sidestep les classes.

from providers import common

# ── Identification ───────────────────────────────────────────────────────────
NAME       = "France — CRAIG/LiDARAURA mode LAZ 0,5 m (~60 pts/m², expérimental)"
CODE       = "fr-craig-dfm"
COUNTRY    = "fr"
LICENSE    = "Licence Ouverte 2.0 (Etalab) — © CRAIG"
DOC_URL    = "https://www.craig.fr/contenu/nuages-de-points-lidar"

# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2154"          # Lambert-93 (implicite : header LAS vide)
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 50_000               # tuiles CRAIG petites (200-500 m)


# ── Bornes par tuile : lookup peuplé à la découverte ─────────────────────────
# Les tailles de tuiles varient selon la campagne, donc PAS de formule : la
# géométrie de l'index TA donne les bornes exactes (anti-couture). discover
# tourne TOUJOURS avant la conversion, donc le dict est peuplé à temps.
_TILE_BOUNDS = {}


def _bounds_nominaux(x, y):
    return _TILE_BOUNDS.get((int(x), int(y)))


def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Découverte CRAIG : union des campagnes classé-.laz du registre, filtrée
    par bbox (EPSG:2154). Remplit _TILE_BOUNDS et retourne {nom_tif: url}."""
    dalles = common.craig_dalles(bbox_natif, dalle_filename, _TILE_BOUNDS, cache_path)
    if dalles:
        print(f"  FR CRAIG LAZ: {len(dalles)} tile(s) in the bbox "
              f"(high-density classified cloud, ~10-17 MB each)")
    else:
        print("  FR CRAIG LAZ: no CRAIG tile here (coverage = named survey zones)")
    return dalles


# ── Machinerie DFM (mutualisée) ──────────────────────────────────────────────
# Préfixe « fr_craig05 » (laz = nuage ; 05 = version de méthode ; bumper si
# l'algo change). Socle possible ASPRS (2=sol, 9=eau) ; défaut ground=csf.
_P = common.DfmProvider(
    prefix="fr_craig05", crs_epsg=2154, resolution=RESOLUTION_M,
    socle_possible=(2, 9),
    defaults=(0.4, 2.5, (2, 3, 4, 6), "csf"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=_bounds_nominaux, discover_fn=_discover,
    zipped=False, tile_mb=15)

# Plafond de téléchargements parallèles (lu par le cœur) : tuiles CRAIG ~10-17 Mo
# (bien plus petites que l'IGN) mais partage Nextcloud public, on reste prudent.
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


def dalle_url(x, y):
    raise NotImplementedError("fr-craig-dfm : URL via index TA → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("fr-craig-dfm : index shapefile → discover_dalles()")
