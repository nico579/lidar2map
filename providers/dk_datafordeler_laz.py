# providers/dk_datafordeler_laz.py — Danemark, « mode LAZ » nuage DHM Punktsky
#
# CONTEXTE : le nuage LiDAR national (DHM/Punktsky) diffusé par la
#   Klimadatastyrelsen (ex-SDFI) via la Datafordeler. Couverture NATIONALE,
#   classifié ASPRS (sol/végé/bâti/eau/bruit/pont), densité ~12 pts/m²
#   (millésime récent) — excellent pour le micro-relief archéologique.
#
# JUMEAU LAZ de dk-datafordeler (raster DHM DTM 0,4 m via WCS) : la machinerie
#   DFM/CSF vit dans common.LazProvider (partagée avec fr-ign-laz / ee-maaamet-laz
#   / us-3dep-laz…). Spécifique Danemark :
#   - Compte : MÊME clé Datafordeler que le raster (APIKEY_REQUISE, env
#     DATAFORDELER_API_KEY). Le raster tire la WCS DHM, ce mode LAZ tire le nuage
#     de points — deux services, une seule clé.
#   - Découverte : grille DDKN 1 km PAR FORMULE (pas d'index à télécharger). Le
#     nuage est servi par tuile via l'API REST FileDownloads GetPointCloudFile,
#     nom de tuile DÉTERMINISTE `DHM_PUNKTSKY_1km_<Nkm>_<Ekm>.laz`
#     (Nkm = N//1000, Ekm = E//1000 en EPSG:25832). Renvoie le LAZ brut (LASF).
#   - CRS mono-zone EPSG:25832 (ETRS89/UTM32N ; le Danemark entier, y compris
#     Bornholm, est diffusé en zone 32 par convention nationale). bounds_fn =
#     bornes km nominales (grille alignée, anti-couture VRT).
#   - Défaut ground=csf : classes ASPRS ≠ schéma IGN et le tissu, indépendant des
#     classes, est plus sûr sur une source nationale hétérogène (cf. ch-swisstopo).
#   LIMITE : ~82 Mo par tuile 1 km (12 pts/m²) → garder la zone PETITE.
#   DÉPRÉCIATION : l'API REST Datafordeler est annoncée « udfases ultimo 2026 »
#     (migration GraphQL) ; FileDownloads (accès fichier en masse) est la brique
#     récente liée au modèle IT-system/API-key et devrait survivre — à
#     re-vérifier avant fin 2026.
#
# Licence : CC BY — © Klimadatastyrelsen / SDFI. Self-contained : stdlib + laspy.

import os
import urllib.parse

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Danemark — mode LAZ nuage DHM Punktsky 0,5 m (~12 pts/m², expérimental)"
CODE       = "dk-datafordeler-laz"
COUNTRY    = "dk"
LICENSE    = "CC BY — © Klimadatastyrelsen / SDFI"
DOC_URL    = "https://datafordeler.dk/dataoversigt/danmarks-hoejdemodel-dhm/dhm-fildownload-punktsky/"
APIKEY_REQUISE = True


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"          # ETRS89 / UTM 32N (Danemark entier)
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 100_000
# Étendue Danemark continental + Bornholm en EPSG:25832 (miroir du raster parent
# dk-datafordeler : même pays, filtre les tuiles hors couverture).
COVERAGE_EXTENT    = (441000, 6048000, 893000, 6403000)


# ── Endpoint (REST FileDownloads, méthode point cloud par nom de tuile) ──────
_PC_URL = "https://api.datafordeler.dk/FileDownloads/GetPointCloudFile"


# ── API Key (même clé que le raster dk-datafordeler) ─────────────────────────
_APIKEY = ""


def set_apikey(key):
    global _APIKEY
    _APIKEY = (key or "").strip()


def _get_api_key():
    key = _APIKEY or os.environ.get("DATAFORDELER_API_KEY", "").strip()
    if not key:
        print("  ⚠ Datafordeler API key missing, pass --apikey <key> or "
              "set DATAFORDELER_API_KEY. "
              "Sign up: https://datafordeler.dk/ "
              "Administration > Opret IT-system > Generer API-nokle", flush=True)
    return key


def _tile_url(nkm, ekm, key):
    """URL GetPointCloudFile pour la tuile DDKN 1 km (Nkm, Ekm). Nom déterministe
    (pas d'index) ; l'API renvoie le LAZ brut classifié (magic LASF)."""
    params = {
        "apikey":      key,
        "Register":    "DHM",
        "Version":     "1",
        "DataSetName": "Punktsky",
        "filename":    f"DHM_PUNKTSKY_1km_{int(nkm)}_{int(ekm)}.laz",
    }
    return _PC_URL + "?" + urllib.parse.urlencode(params)


# ── Bornes nominales (coin SW en km ; tuiles DDKN alignées) ───────────────────
def _bounds_nominaux(x_km, y_km):
    """(x_km, y_km) = (easting_km, northing_km) du coin SW → bornes 1 km alignées
    entre tuiles voisines (pas de couture au VRT)."""
    x, y = int(x_km) * 1000, int(y_km) * 1000
    return (x, y, x + 1000, y + 1000)


# ── Découverte (grille DDKN 1 km par formule) ────────────────────────────────
def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Grille DDKN 1 km couvrant bbox_natif (EPSG:25832) → {dalle_filename(Ekm,
    Nkm): url GetPointCloudFile}. (x,y) = coin SW en km (easting, northing)."""
    key = _get_api_key()
    if not key:
        return None
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    x1, y1 = max(x1, cx0), max(y1, cy0)
    x2, y2 = min(x2, cx1), min(y2, cy1)
    if x1 >= x2 or y1 >= y2:
        print("  Denmark LAZ: bbox out of coverage extent")
        return {}
    e0, e1 = int(x1 // 1000), int(x2 // 1000)
    if x2 % 1000 == 0 and e1 > e0:      # bord exact sur une couture → pas de tuile en trop
        e1 -= 1
    n0, n1 = int(y1 // 1000), int(y2 // 1000)
    if y2 % 1000 == 0 and n1 > n0:
        n1 -= 1
    dalles = {}
    for ekm in range(e0, e1 + 1):
        for nkm in range(n0, n1 + 1):
            dalles[dalle_filename(ekm, nkm)] = _tile_url(nkm, ekm, key)
    if dalles:
        print(f"  DK DHM LAZ (Punktsky): {len(dalles)} tile(s) in the bbox "
              f"(classified ~12 pts/m², ~{len(dalles) * _P.tile_mb} MB of point "
              f"cloud to download!)")
    else:
        print("  DK DHM LAZ: no tile here (coverage gap)")
    return dalles


# ── Machinerie DFM (mutualisée) ──────────────────────────────────────────────
# Préfixe « dk_laz05 » (laz = nuage ; 05 = version de méthode). CRS mono-zone
# 25832. Socle ASPRS (2=sol, 9=eau) ; classes réinjectables 3/4/5/6. Défaut csf.
_P = common.LazProvider(
    prefix="dk_laz05", crs_epsg=25832, resolution=RESOLUTION_M,
    socle_possible=(2, 9),
    defaults=(0.4, 2.5, (2, 3, 4, 5, 6), "csf"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=_bounds_nominaux, discover_fn=_discover,
    zipped=False, tile_mb=85)

# Plafond de téléchargements parallèles : tuiles ~82 Mo → prudent, 3 max.
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


def dalle_url(x_km, y_km):
    raise NotImplementedError("dk-datafordeler-laz : URL via GetPointCloudFile → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("dk-datafordeler-laz : grille DDKN → discover_dalles()")
