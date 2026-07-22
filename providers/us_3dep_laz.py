# providers/us_3dep_laz.py — USA, « mode LAZ » nuage LiDAR USGS 3DEP (COPC)
#
# CONTEXTE : le nuage LiDAR national 3DEP reformaté en COPC (LAZ 1.4 réorganisé
#   en octree) pour Planetary Computer (collection STAC « 3dep-lidar-copc »).
#   Couverture CONUS + Alaska + Hawaii + Guam, millésimes 2012-2022, densité
#   ~2-20 pts/m² selon le projet (Quality Level QL2/QL1). On ne rapatrie PAS le
#   COPC entier : lecture FENÊTRÉE via range-requests (COPC_WINDOWED, cf.
#   telecharger_copc_fenetre) — mêmes rails que ca-nrcan-laz.
#
# JUMEAU LAZ de us-3dep (raster OpenTopography). Détail notable : le raster exige
#   une clé OpenTopography (et son 1 m est réservé à l'usage ACADÉMIQUE) ; ce
#   mode LAZ n'exige AUCUN compte, juste une signature SAS ANONYME (endpoint
#   public Planetary Computer). Le mode LAZ est donc PLUS accessible que le
#   raster parent.
#
#   Spécifique USA (le reste = common.LazProvider) :
#   - Découverte : STAC search Planetary Computer par bbox → un COPC par tuile
#     (asset « data »). L'URL blob Azure est stockée NON signée (elle est signée
#     au download, cf. sign_url). Tri millésime décroissant + dédup par coin SW :
#     on garde le levé le plus récent quand des re-vols se superposent (comme
#     l'Estonie).
#   - SIGNATURE SAS (nouveauté vs ca-nrcan) : le blob Azure refuse l'accès public
#     (HTTP 409). sign_url() échange l'URL contre une URL signée via l'endpoint
#     anonyme PC. La signature vaut ~1 h → on signe à l'instant du DOWNLOAD (hook
#     appelé dans telecharger_copc_fenetre), pas à la découverte. Clé
#     d'abonnement PC facultative (env PC_SDK_SUBSCRIPTION_KEY) pour lever la
#     limite de débit anonyme sur les gros runs.
#   - CRS MULTI-ZONES : les COPC sont en UTM NAD83 PAR ZONE ; `proj:epsg` est
#     absent des propriétés STAC → le CRS est lu dans le header du COPC et posé
#     par run via LazProvider.set_crs (dans telecharger_copc_fenetre), comme le
#     Canada. CRS_NATIF = géographique NAD83 (EPSG:4269) : cadrage + fenêtrage.
#   - bounds_fn=None ; défaut ground=csf (1254 projets, classification hétérogène
#     d'un levé à l'autre → le tissu, indépendant des classes, est plus sûr).
#   LIMITE : densité variable → sur une zone d'1 km² la fenêtre peut faire des
#   dizaines de M points (.las temporaire volumineux). Zone PETITE conseillée.
#
# Licence : domaine public (USGS 3DEP). Self-contained : stdlib (urllib) + laspy
# (CopcReader), pyproj au runtime.

import json
import os
import urllib.parse
import urllib.request

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "USA — mode LAZ nuage LiDAR USGS 3DEP (COPC, 2-20 pts/m², expérimental)"
CODE       = "us-3dep-laz"
COUNTRY    = "us"
LICENSE    = "Public domain (USGS 3DEP)"
DOC_URL    = "https://planetarycomputer.microsoft.com/dataset/3dep-lidar-copc"


# ── Géométrie ────────────────────────────────────────────────────────────────
# CRS_NATIF = géographique NAD83 (index STAC WGS84 + cadrage/fenêtrage) ; le CRS
# de SORTIE est la zone UTM du COPC, posée par run via set_crs. COPC_WINDOWED :
# lecture fenêtrée /vsicurl (range-requests).
CRS_NATIF          = "EPSG:4269"          # NAD83 géographique
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 100_000
COPC_WINDOWED      = True


# ── Endpoints STAC + signature (Planetary Computer) ──────────────────────────
_STAC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
_SIGN        = "https://planetarycomputer.microsoft.com/api/sas/v1/sign?href="
_COLLECTION  = "3dep-lidar-copc"
_UA          = "lidar2map/1.0"


def _http_json(url, data=None):
    hdr = {"User-Agent": _UA}
    if data is not None:
        hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdr)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


# ── Signature SAS (hook cœur, appelé dans telecharger_copc_fenetre) ──────────
def sign_url(url):
    """Échange l'URL blob Azure NON signée contre une URL signée (SAS) via
    l'endpoint public Planetary Computer. Anonyme (aucun compte) ; la signature
    vaut ~1 h → on signe à l'instant du download. L'env PC_SDK_SUBSCRIPTION_KEY
    (facultatif) lève la limite de débit anonyme sur les gros runs."""
    hdr = {"User-Agent": _UA}
    key = os.environ.get("PC_SDK_SUBSCRIPTION_KEY", "").strip()
    if key:
        hdr["Ocp-Apim-Subscription-Key"] = key
    req = urllib.request.Request(_SIGN + urllib.parse.quote(url, safe=""), headers=hdr)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("href", url)


# ── Découverte (STAC search par bbox) ────────────────────────────────────────
def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """STAC search Planetary Computer (collection 3dep-lidar-copc) sur la bbox
    → tuiles COPC intersectantes. (x,y) = coin SW de l'emprise géographique en
    entiers POSITIFS ((lon+180)·1e4, lat·1e4). Tri millésime décroissant + dédup
    par coin SW : on garde le levé le plus récent quand plusieurs se superposent."""
    if bbox_wgs84 is None:
        return {}
    lo1, la1, lo2, la2 = (float(v) for v in bbox_wgs84)
    body = json.dumps({
        "collections": [_COLLECTION],
        "bbox": [lo1, la1, lo2, la2],
        "limit": 100,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
    }).encode()
    dalles, vus = {}, set()
    try:
        res = _http_json(_STAC_SEARCH, data=body)
    except Exception as e:
        print(f"  ERROR US 3DEP STAC: {type(e).__name__}: {e}")
        return None
    for feat in res.get("features", []):
        asset = feat.get("assets", {}).get("data")
        if not asset or not str(asset.get("href", "")).endswith(".copc.laz"):
            continue
        bb = feat.get("bbox")           # [minx, miny, (minZ), maxx, maxy, (maxZ)]
        if not bb or len(bb) < 4:
            continue
        # bbox 3D (6 valeurs) ou 2D (4) : X/Y = les 2 premiers = coin SW géographique.
        x = int(round((bb[0] + 180.0) * 10000))    # lon SW → positif
        y = int(round(bb[1] * 10000))              # lat SW
        if (x, y) in vus:               # tri desc → 1er vu = plus récent → gardé
            continue
        vus.add((x, y))
        dalles[dalle_filename(x, y)] = str(asset["href"])
    if dalles:
        print(f"  US 3DEP LAZ (COPC): {len(dalles)} tile(s) in the bbox "
              f"(windowed read, density varies 2-20 pts/m² — keep the area small!)")
    else:
        print("  US 3DEP LAZ: no COPC tile here (coverage gap)")
    return dalles


# ── Machinerie LAZ (mutualisée) ──────────────────────────────────────────────
# Préfixe « us_laz05 ». crs_epsg initial = UTM 13N (EPSG:26913) placeholder,
# ÉCRASÉ par run via set_crs (zone lue dans le header COPC). Socle ASPRS (2/9),
# défaut csf.
_P = common.LazProvider(
    prefix="us_laz05", crs_epsg=26913, resolution=RESOLUTION_M,
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

