# providers/ca_quebec_laz.py — Québec, « mode LAZ » nuage LiDAR provincial
#
# CONTEXTE : le Québec (MRNF) diffuse son nuage LiDAR provincial en LAZ, données
#   ouvertes (CC BY 4.0, sans compte). Couverture en expansion (levés par projet),
#   densité 2,5-10+ pts/m² selon le projet, classé (ASPRS). Bon pour le
#   micro-relief archéologique.
#
# JUMEAU LAZ de ca-quebec (raster MNT 1 m) : toute la machinerie vit dans
#   common.LazProvider (partagée avec fr-ign-laz / pl-gugik-laz / …).
#   Spécifique Québec :
#   - Découverte : couche WFS `IndexTelechargementLidarPlusRecent` (GeoServer RGQ) ;
#     chaque feuille porte son URL LAZ directe (TELECHARGEMENT_TUILE) + son
#     CODE_EPSG. La couche « PlusRecent » ne rend QUE le levé le plus récent par
#     emprise (dédup de millésime GRATUITE, côté serveur). common.quebec_wfs_features.
#   - CRS MULTI-ZONES : le nuage est en MTM PAR FUSEAU, NAD83(CSRS) (EPSG:2949-2952
#     pour MTM 7-10), donné explicitement par tuile (CODE_EPSG). On pose la zone
#     DOMINANTE du lot via LazProvider.set_crs. Contrairement à la Pologne, le
#     header LAZ PORTE le CRS → le garde _verifie_crs_las REFUSE activement une
#     tuile d'un autre fuseau (bbox à cheval sur 2 fuseaux = les minoritaires
#     erreurent, pas de sortie fausse ; zone petite conseillée de toute façon).
#   - Nommage : (x,y) = coin SW géographique (EPSG:4617) en entiers positifs
#     (les NOM_TUILE ne sont pas numériques km-alignés). bounds_fn=None.
#   - Défaut ground=csf (classification hétérogène d'un projet à l'autre :
#     « Données brutes » 0,1,2,8 vs « Données classifiées » 1,2,7,9).
#
# Licence : CC BY 4.0 — Gouvernement du Québec. Self-contained : stdlib + laspy.

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Québec — mode LAZ nuage LiDAR provincial 0,5 m (~2,5-10 pts/m², expérimental)"
CODE       = "ca-quebec-laz"
COUNTRY    = "ca"
LICENSE    = "Creative Commons Attribution 4.0 (CC BY 4.0) — Gouvernement du Québec"
DOC_URL    = "https://www.donneesquebec.ca/recherche/dataset/donnees-lidar-du-quebec"


# ── Géométrie ────────────────────────────────────────────────────────────────
# CRS_NATIF = géographique NAD83(CSRS) (index WFS + cadrage/fenêtrage) ; le CRS
# de SORTIE est le fuseau MTM du nuage, posé par run via set_crs (cf. _discover).
CRS_NATIF          = "EPSG:4617"          # NAD83(CSRS) géographique
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 100_000


# ── Index WFS (GeoServer RGQ, couche PlusRecent = millésime récent par emprise) ─
_WS    = "Index_Telechargement_Lidar_Pub"
_LAYER = "IndexTelechargementLidarPlusRecent"


# ── Découverte (WFS PlusRecent, mutualisée) ──────────────────────────────────
def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """WFS PlusRecent par bbox → {dalle_filename(x,y): url LAZ}. Pose le fuseau
    MTM DOMINANT du lot (set_crs). (x,y) = coin SW géographique (EPSG:4617) en
    entiers positifs, dédupliqué."""
    feats = common.quebec_wfs_features(_WS, _LAYER, bbox_wgs84)
    if feats is None:
        return None
    dalles, vus, zones = {}, set(), {}
    for f in feats:
        p = f.get("properties", {})
        url = p.get("TELECHARGEMENT_TUILE")
        epsg = p.get("CODE_EPSG")
        bb = common._geom_bbox(f.get("geometry") or {})
        if not url or not epsg or bb is None:
            continue
        lon, lat = bb[0], bb[1]
        if lon > 0:                       # garde-fou axe (GeoServer lat,lon)
            lon, lat = bb[1], bb[0]
        x = int(round((lon + 180.0) * 10000))     # coin SW → positif
        y = int(round(lat * 10000))
        if (x, y) in vus:
            continue
        vus.add((x, y))
        zones[int(epsg)] = zones.get(int(epsg), 0) + 1
        dalles[dalle_filename(x, y)] = str(url)
    if zones:
        dom = max(zones, key=zones.get)   # fuseau MTM dominant du lot
        _P.set_crs(dom)
        if len(zones) > 1:
            print(f"  QC LAZ: bbox spanning {len(zones)} MTM zones {sorted(zones)}; "
                  f"using EPSG:{dom} (other-zone tiles refused by the CRS guard)")
    if dalles:
        print(f"  QC LiDAR LAZ (RGQ): {len(dalles)} tile(s) in the bbox "
              f"(classified, ~{len(dalles) * _P.tile_mb} MB of point cloud to download!)")
    else:
        print("  QC LiDAR LAZ: no tile here (coverage gap)")
    return dalles


# ── Machinerie LAZ (mutualisée) ──────────────────────────────────────────────
# Préfixe « qc_laz05 » (distinct de ca_nrcan_laz « ca_laz05 » : même pays 'ca',
# caches séparés). CRS initial = MTM 7 (EPSG:2949) placeholder, ÉCRASÉ par run via
# set_crs (fuseau lu du CODE_EPSG). Socle ASPRS (2/9), défaut csf.
_P = common.LazProvider(
    prefix="qc_laz05", crs_epsg=2949, resolution=RESOLUTION_M,
    socle_possible=(2, 9),
    defaults=(0.4, 2.5, (1, 2, 3, 4, 5, 6), "csf"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=None, discover_fn=_discover,
    zipped=False, tile_mb=70)

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
set_crs          = _P.set_crs          # posé par run dans _discover
# Internes exposés pour les tests
_socle           = _P.socle
_reinjectees     = _P.reinjectees
_laz_filename    = _P.laz_filename


def dalle_url(x, y):
    raise NotImplementedError("ca-quebec-laz : URL via WFS PlusRecent → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("ca-quebec-laz : index WFS → discover_dalles()")
