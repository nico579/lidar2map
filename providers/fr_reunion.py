# providers/fr_reunion.py — La Réunion (DROM), MNT LiDAR HD 0,5 m (IGN)
#
# Source : IGN LiDAR HD, volet outre-mer. `fr-ign` ne couvre que la métropole
#   (Lambert-93) ; ce provider ajoute La Réunion (RGR92 / UTM 40S).
#   Doc : https://geoservices.ign.fr/lidarhd  |  Licence Ouverte 2.0 (Etalab)
#
# Paradigme : index WFS `IGNF_MNT-LIDAR-HD:dalle` (chaque dalle 1 km porte son
#   `url` de download direct) → GeoTIFF 0,5 m. Découverte mutualisée dans
#   providers/common.py::ign_lidar_hd_dalles (jumeau de fr-guadeloupe).
#   - CRS déclaré EPSG:2975 (RGR92 / UTM 40S) pour la requête WFS ; les GeoTIFF
#     servis sont tagués EPSG:32740 (WGS84 / UTM 40S, quasi identique sur l'île),
#     le warp 3857 lit le tag réel de la dalle → aucun post_fetch.
#   - ~2 665 dalles, 0,5 m, GeoTIFF Float32 nodata -9999.
#
# Self-contained : stdlib uniquement.

import re


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "La Réunion — MNT LiDAR HD 0,5 m (IGN)"
CODE       = "fr-reunion"
COUNTRY    = "fr"
LICENSE    = "Licence Ouverte 2.0 (Etalab) — © IGN"
DOC_URL    = "https://geoservices.ign.fr/lidarhd"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2975"          # RGR92 / UTM 40S (requête WFS)
RESOLUTION_M       = 0.5
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000
SEUIL_DALLE_VALIDE = 500_000              # ~16 Mo par dalle 2000×2000


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"fr_reu_dtm05_{int(x_km)}_{int(y_km)}.tif"


def subdir_from_name(nom):
    m = re.match(r"fr_reu_dtm05_(\d+)_", nom)
    return m.group(1) if m else None


# ── Découverte (WFS IGN LiDAR HD, mutualisée) ────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    from providers import common
    dalles = common.ign_lidar_hd_dalles(bbox_natif, 2975, dalle_filename)
    if dalles is None:
        return None
    print(f"  FR La Réunion (MNT LiDAR HD 0,5 m): {len(dalles)} tile(s) in the bbox")
    return dalles
