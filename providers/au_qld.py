# providers/au_qld.py — Australie (Queensland), DEM LiDAR 0.5m via QSpatial
#
# Source : Queensland Government — Department of Resources (QSpatial), agrégé
#   aussi par ELVIS (elevation.fsdf.org.au, le hub national ICSM).
#   ImageServer : Elevation/QldDem (0.5 et 1 m, DTM LiDAR ortho sur le Queensland)
#
# Paradigme : ArcGIS ImageServer exportImage (calque exact de no_kartverket).
#   - CRS natif EPSG:3857 (Web Mercator, comme us-tnm / us-3dep)
#   - Résolution 0.5 m (DTM sol-nu LiDAR), F32
#   - Pas d'index : grille km synthétique clippée à l'étendue Queensland ;
#     chaque "dalle" = une requête exportImage 1×1 km.
#   - Licence : CC BY 4.0 — © State of Queensland
#
# Le LiDAR australien est par projet (côtier/urbain), pas mur-à-mur — comme
# US/CA. Le Queensland (1.85 M km²) est le 1er État intégré ; les autres
# (NSW, SA, WA…) exposent des ImageServers QSpatial/ELVIS du même type et
# s'ajouteront sur le même pattern (cf. les 3 Länder allemands).
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Australie (Queensland) — DEM LiDAR (QSpatial)"
CODE       = "au-qld"
COUNTRY    = "au"
LICENSE    = "CC BY 4.0 — © State of Queensland (Dept of Resources)"
DOC_URL    = "https://spatial-img.information.qld.gov.au/arcgis/rest/services/Elevation/QldDem/ImageServer"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3857"        # Web Mercator (natif de l'ImageServer)
RESOLUTION_M       = 0.5                # DTM LiDAR 0.5 m
DALLE_KM           = 1                  # tuiles synthétiques 1×1 km
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 2000 px
SEUIL_DALLE_VALIDE = 100_000            # seuil bas : zones hors couverture (mer,
                                        # inland sans LiDAR) → nodata compressible
# Étendue Queensland en EPSG:3857 (depuis l'ImageServer QldDem)
COVERAGE_EXTENT = (15352710, -3449670, 17810238, -1021912)


# ── Endpoints ────────────────────────────────────────────────────────────────
IMAGESERVER = "https://spatial-img.information.qld.gov.au/arcgis/rest/services/Elevation/QldDem/ImageServer"
EXPORT_URL  = f"{IMAGESERVER}/exportImage"


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"qld_dtm_{x_km:08d}_{y_km:+09d}_3857_05m.tif"


def dalle_subdir(x_km):
    return f"{x_km:08d}"


import re as _re
_SUBDIR_FROM_NAME = _re.compile(r"qld_dtm_(\d+)_")


def subdir_from_name(nom):
    m = _SUBDIR_FROM_NAME.match(nom)
    return m.group(1) if m else None


# ── Construction URL exportImage ─────────────────────────────────────────────
def dalle_url(x_km, y_km):
    """ArcGIS ImageServer exportImage pour une dalle 1×1 km en EPSG:3857."""
    step = DALLE_KM * 1000
    xmin = x_km * step
    ymin = y_km * step
    params = {
        "bbox":      f"{xmin},{ymin},{xmin + step},{ymin + step}",
        "bboxSR":    "3857",
        "imageSR":   "3857",
        "size":      f"{PX_PAR_DALLE},{PX_PAR_DALLE}",
        "format":    "tiff",
        "pixelType": "F32",
        "f":         "image",
    }
    return EXPORT_URL + "?" + urllib.parse.urlencode(params)


# ── Grille pour une bbox ─────────────────────────────────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    step = DALLE_KM * 1000
    x_start = int(x1 // step)
    x_end   = int(x2 // step)
    if x2 % step == 0 and x_end > x_start:
        x_end -= 1
    y_start = int(y1 // step)
    y_end   = int(y2 // step)
    if y2 % step == 0 and y_end > y_start:
        y_end -= 1
    return [(x_km, y_km)
            for x_km in range(x_start, x_end + 1)
            for y_km in range(y_start, y_end + 1)]


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Grille km synthétique clippée à l'étendue Queensland. Les zones sans
    LiDAR retournent du nodata que le validator filtre."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  Queensland: bbox out of extent (Web Mercator)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  QLD QSpatial (DEM 0.5m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
