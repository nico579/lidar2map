# providers/fr_ign_laz.py — France, DFM « ruines/structures debout » 0,5 m
# depuis le nuage classé LiDAR HD IGN (COPC LAZ)
#
# POURQUOI : le MNT IGN (fr-ign) efface PAR CONSTRUCTION les murs encore debout
#   au-delà d'environ 1 m : la chaîne IGN_AUTO les classe « végétation » (4) ou
#   « non classé » (1), et le MNT (classes 2/9/66 + TIN) interpole au travers.
#   Paradoxe documenté (spec DC_LiDAR_HD) : un muret de 40 cm survit, une ruine
#   de 1,5 m disparaît. Ce provider reconstruit un modèle façon **DFM** (Digital
#   Feature Model — le CONCEPT vient de Štular et al. 2021 ; la SÉLECTION
#   automatique des points est une heuristique maison, cf. common.las_to_dfm,
#   là où la littérature reclassifie (semi-)manuellement) : le terrain + les
#   structures debout, en réinjectant les retours bas non-sol (0,4-2,5 m,
#   classes 1/3/4) dans les trous de la classe sol. Tous les ombrages (LRM,
#   VAT…) fonctionnent ensuite tels quels. Le maquis revient aussi (mouchetis) :
#   murs = lignes continues, buissons = tavelures — l'œil discrimine (Kokalj &
#   Hesse : jamais une seule visualisation).
#
# DEUX MÉTHODES DE SOCLE (--laz-ground, cf. common.las_to_dfm) :
#   - "classes" (défaut) : réinjection par classes du producteur, ~25 s/dalle ;
#   - "csf" : Cloth Simulation Filter mou (Zhang 2016) — ignore les classes,
#     fond plus propre (pas de mouchetis), signal équivalent (validé terrain
#     2026-07-16), ~3 min/dalle. hmin/hmax/classes sont alors ignorés ;
#     réglables par site : --laz-csf-threshold / -resolution / -rigidness
#     (surface standard CloudCompare, cf. las_to_dfm).
#
# COÛT (à savoir avant de lancer) : une dalle COPC = ~205 Mo (vs 16 Mo de MNT),
#   ~34 M de points, conversion ~20-30 s/dalle ("classes") ou ~3 min ("csf"),
#   ~1-2 Go de RAM. Outil de PROSPECTION CIBLÉE (quelques km²), pas de grandes
#   cartes. Pour l'analyse fine d'un site : tools/dfm_ruines.py (GeoTIFF à
#   draper dans QGIS).
#
# Paradigme : index WFS `IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle` (chaque dalle
#   1 km porte son `url` de download direct, comme fr-reunion/fr-guadeloupe ;
#   découverte mutualisée common.ign_lidar_hd_dalles) → COPC LAZ → post_fetch
#   common.las_to_dfm → GeoTIFF 0,5 m EPSG:2154.
#   Licence : Licence Ouverte 2.0 (Etalab) — © IGN.
#
# ARCHITECTURE : la machinerie DFM (réglages, nommage injectif, variant_tag,
#   hooks pre_download/post_fetch) vit dans common.LazProvider, partagée avec
#   ch-swisstopo-laz. Ce module ne porte que les spécificités IGN : CRS 2154,
#   préfixe fr_laz05, découverte WFS, bornes nominales (convention Ymax),
#   download LAS/LAZ brut (pas zippé).
#
# Self-contained : stdlib uniquement (laspy/lazrs/rasterio requis au runtime).

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "France — mode LAZ structures debout 0,5 m (LiDAR HD, expérimental)"
CODE       = "fr-ign-laz"
COUNTRY    = "fr"
LICENSE    = "Licence Ouverte 2.0 (Etalab) — © IGN"
DOC_URL    = "https://geoservices.ign.fr/lidarhd"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2154"          # Lambert-93
RESOLUTION_M       = 0.5
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000
SEUIL_DALLE_VALIDE = 500_000              # GeoTIFF 2000² DEFLATE après conversion


# ── Bornes nominales (convention IGN : le nom porte X_km et Y_MAX_km) ─────────
def _bounds_nominaux(x_km, y_km):
    """LHD_FXX_0932_6257 couvre Y[6256000,6257000]. Passées à las_to_dfm pour
    une grille alignée au km entre dalles (pas de couture VRT)."""
    x, y = int(x_km), int(y_km)
    return (x * 1000, (y - 1) * 1000, (x + 1) * 1000, y * 1000)


# ── Découverte (WFS IGN LiDAR HD, mutualisée — typename NUAGES-DE-POINTS) ────
def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    dalles = common.ign_lidar_hd_dalles(
        bbox_natif, 2154, dalle_filename,
        typename="IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle")
    if dalles is None:
        return None
    if dalles:
        print(f"  FR LAZ (LiDAR HD): {len(dalles)} tile(s) in the bbox "
              f"(~{len(dalles) * 205} MB of point cloud to download!)")
    else:
        print("  FR LAZ: no LiDAR HD point-cloud tile here (not flown yet?)")
    return dalles


# ── Machinerie DFM (mutualisée) ──────────────────────────────────────────────
# CONVENTION préfixe « fr_laz05 » (laz = source nuage de points ; 05 = version de
# MÉTHODE de conversion). Si l'algo de las_to_dfm change de façon incompatible,
# BUMPER (fr_laz06…) pour que les dalles de l'ancienne méthode ne soient pas
# réutilisées en silence.
# UN SEUL ensemble de classes (choix Nico 2026-07-16) ; défaut 1,2,3,4,9,66 :
#   {2,9,66} = socle terrain (= classes du MNT IGN), 1/3/4 = réinjectées (murs
#   mesurés ~70% en classe 3/4 sur le site test ; ~30% en classe 5 → essayer
#   --laz-classes 1,2,3,4,5,9,66 si les murs sortent incomplets).
_P = common.LazProvider(
    prefix="fr_laz05", crs_epsg=2154, resolution=RESOLUTION_M,
    socle_possible=(2, 9, 66),
    defaults=(0.4, 2.5, (1, 2, 3, 4, 9, 66), "classes"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=_bounds_nominaux, discover_fn=_discover,
    zipped=False, tile_mb=205)

# Plafond de téléchargements parallèles (lu par le cœur) : les nuages LAZ pèsent
# ~205 Mo, à 8 en parallèle IGN throttle et tronque le transfert (cf. le retry
# transitoire 400 IGN). 3 max lisse la charge ; le tuilage/ombrage garde --workers.
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
set_laz_params  = _P.set_params
dalle_filename  = _P.dalle_filename
dalle_subdir    = _P.dalle_subdir
subdir_from_name = _P.subdir_from_name
variant_tag     = _P.variant_tag
method_label    = _P.method_label
discover_dalles = _P.discover_dalles
pre_download    = _P.pre_download
post_fetch      = _P.post_fetch
set_cloud_cache_dir = _P.set_cloud_cache_dir
laz_defaults    = _P.defaults_dict
# Internes exposés pour les tests
_socle          = _P.socle
_reinjectees    = _P.reinjectees
_laz_filename   = _P.laz_filename


def dalle_url(x_km, y_km):
    raise NotImplementedError("fr-ign-laz : URL via WFS dalle → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("fr-ign-laz : index WFS → discover_dalles()")
