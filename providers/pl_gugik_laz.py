# providers/pl_gugik_laz.py — Pologne, « mode LAZ » depuis le nuage LiDAR ISOK
#
# CONTEXTE : GUGiK (geoportal.gov.pl) diffuse le nuage LiDAR national (projet
#   ISOK) en données OUVERTES. La 2e génération (2019+, visible dans l'index)
#   est CLASSÉE à ~20 pts/m² (2× le LiDAR HD IGN), erreur altimétrique ~2 cm :
#   excellent pour le micro-relief archéologique (murs étroits).
#
# JUMEAU DFM de pl-gugik (raster DTM WCS 1 m) : toute la machinerie DFM vit dans
#   common.LazProvider, partagée avec fr-ign-laz / ch-swisstopo-laz / fr-craig-laz.
#   Spécifiques Pologne :
#   - Découverte : WFS « skorowidze » GUGiK (un typename par année) où chaque
#     feuille porte son URL de download LAZ (attribut gugik:url_do_pobrania) =
#     même paradigme que le WFS IGN (common.gugik_dalles).
#   - CRS MULTI-ZONES : l'INDEX est en EPSG:2180 (PL-1992, d'où CRS_NATIF ci-
#     dessous, utilisé par le cœur pour le WFS + le cadrage Mercator), mais le
#     NUAGE est en PL-2000 PAR ZONE (EPSG:2176-2179 selon la longitude). Le
#     provider calcule la zone du bbox à la découverte et la pose via
#     LazProvider.set_crs → las_to_dfm sort dans la bonne zone, le garde CRS
#     compare le header à cette zone (le warp du cœur lit le CRS DU FICHIER, pas
#     CRS_NATIF, donc la zone est respectée jusqu'aux tuiles Mercator).
#     LIMITE : une bbox à cheval sur deux zones PL-2000 ne convertit que celles
#     de la zone du centre (les autres sont refusées par le garde CRS = sûr, pas
#     de sortie fausse ; zone petite conseillée de toute façon).
#   - Bornes anti-couture : NON fournies (bounds_fn=None) → las_to_dfm grille sur
#     l'emprise propre du nuage. Les feuilles ISOK ne sont pas km-alignées ; un
#     léger raccord de bord inter-feuilles est possible (roadmap : halo inter-
#     dalles, cf. docs/dfm_reviews.md), acceptable sur les petites zones du DFM.
#
# Licence : dane otwarte GUGiK (données ouvertes, gratuit, sans compte).
# Self-contained : stdlib uniquement (laspy/lazrs/rasterio requis au runtime).

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Pologne — mode LAZ nuage LiDAR ISOK 0,5 m (~20 pts/m², expérimental)"
CODE       = "pl-gugik-laz"
COUNTRY    = "pl"
LICENSE    = "Dane otwarte — GUGiK (données ouvertes, gratuit)"
DOC_URL    = "https://www.geoportal.gov.pl/pl/dane/pomiary-lidarowe-lidar/"


# ── Géométrie ────────────────────────────────────────────────────────────────
# CRS_NATIF = celui de l'INDEX WFS (PL-1992). Le CRS des tuiles produites est la
# ZONE PL-2000, posée par run via set_crs (cf. _discover). RESOLUTION 0,5 m : la
# densité ~20 pts/m² (espacement ~0,22 m) la supporte largement.
CRS_NATIF          = "EPSG:2180"          # PL-1992 (index/skorowidze)
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 100_000              # .tif produit (feuilles ~0,4 km²)


# ── CRS du nuage : PL-2000 par zone (longitude) ──────────────────────────────
def _zone_epsg(lon):
    """Zone PL-2000 depuis la longitude : méridiens centraux 15/18/21/24°E =
    strefy 5/6/7/8 = EPSG:2176/2177/2178/2179. Bornée au territoire polonais."""
    z = max(5, min(8, round(lon / 3.0)))
    return 2176 + (z - 5), z


# ── Découverte (WFS skorowidze GUGiK, mutualisée) ────────────────────────────
def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Pose la zone PL-2000 du bbox (set_crs) puis interroge le WFS index : union
    des années, chaque feuille rend son URL LAZ directe."""
    if bbox_wgs84 is None:
        return {}
    lon_c = (float(bbox_wgs84[0]) + float(bbox_wgs84[2])) / 2.0
    epsg, zone = _zone_epsg(lon_c)
    _P.set_crs(epsg)
    dalles = common.gugik_dalles(bbox_natif, dalle_filename)
    if dalles is None:
        return None
    if dalles:
        print(f"  PL GUGiK LAZ (ISOK): {len(dalles)} tile(s) in the bbox "
              f"(PL-2000 strefa {zone} / EPSG:{epsg}, ~20 pts/m², classified — "
              f"~{len(dalles) * _P.tile_mb} MB of point cloud to download!)")
    else:
        print("  PL GUGiK LAZ: no LiDAR tile here (or bbox spans >1 PL-2000 zone)")
    return dalles


# ── Machinerie DFM (mutualisée) ──────────────────────────────────────────────
# Préfixe « pl_laz05 » (laz = nuage ; 05 = version de méthode ; bumper si l'algo
# change). CRS initial = zone 7 (EPSG:2178, Pologne centrale) — écrasé par run
# via set_crs. Socle ASPRS (2=sol, 9=eau) ; défaut ground=csf : le tissu ignore
# le schéma de classes (ISOK = ASPRS standard mais on reste provider-agnostique,
# comme CRAIG).
_P = common.LazProvider(
    prefix="pl_laz05", crs_epsg=2178, resolution=RESOLUTION_M,
    socle_possible=(2, 9),
    defaults=(0.4, 2.5, (2, 3, 4, 6), "csf"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=None, discover_fn=_discover,
    zipped=False, tile_mb=80)

# Plafond de téléchargements parallèles : nuages lourds (~80 Mo) sur opendata
# public → prudent, 3 max (comme fr-ign-laz).
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
# Internes exposés pour les tests
_socle           = _P.socle
_reinjectees     = _P.reinjectees
_laz_filename    = _P.laz_filename

