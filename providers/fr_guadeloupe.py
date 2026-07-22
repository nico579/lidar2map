# providers/fr_guadeloupe.py — Guadeloupe (DROM), MNT LiDAR HD 0,5 m (IGN)
#
# Source : IGN LiDAR HD, volet outre-mer (RGAF09 / UTM 20N). Jumeau de
#   fr-reunion ; `fr-ign` ne couvre que la métropole.
#   Doc : https://geoservices.ign.fr/lidarhd  |  Licence Ouverte 2.0 (Etalab)
#
# Paradigme : index WFS `IGNF_MNT-LIDAR-HD:dalle` (chaque dalle 1 km porte son
#   `url` de download direct : ici un lien de téléchargement IGN + apikey public
#   `interface_catalogue`, GET → GeoTIFF) → 0,5 m. Découverte mutualisée dans
#   providers/common.py::ign_lidar_hd_dalles.
#   - CRS natif EPSG:5490 (RGAF09 / UTM 20N) ; les GeoTIFF sont tagués 5490,
#     aucun post_fetch.
#   - ~4 018 dalles, 0,5 m, GeoTIFF Float32 nodata -9999.
#
# Self-contained : stdlib uniquement.

import re


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Guadeloupe — MNT LiDAR HD 0,5 m (IGN)"
CODE       = "fr-guadeloupe"
COUNTRY    = "fr"
LICENSE    = "Licence Ouverte 2.0 (Etalab) — © IGN"
DOC_URL    = "https://geoservices.ign.fr/lidarhd"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:5490"          # RGAF09 / UTM 20N
RESOLUTION_M       = 0.5
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000
SEUIL_DALLE_VALIDE = 500_000


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"fr_glp_dtm05_{int(x_km)}_{int(y_km)}.tif"


def subdir_from_name(nom):
    m = re.match(r"fr_glp_dtm05_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("fr-guadeloupe : URL via WFS dalle → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("fr-guadeloupe : index WFS → discover_dalles()")


# ── Découverte (WFS IGN LiDAR HD, mutualisée) ────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    from providers import common
    dalles = common.ign_lidar_hd_dalles(bbox_natif, 5490, dalle_filename)
    if dalles is None:
        return None
    print(f"  FR Guadeloupe (MNT LiDAR HD 0,5 m): {len(dalles)} tile(s) in the bbox")
    return dalles
