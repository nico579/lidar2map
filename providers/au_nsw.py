# providers/au_nsw.py — Australie (Nouvelle-Galles du Sud), DEM 5m via Spatial Services NSW
#
# Source : Spatial Services (NSW Government) — service NSW_5M_Elevation.
#   ImageServer : public/NSW_5M_Elevation (couverture state-wide).
#
# Paradigme : ArcGIS ImageServer exportImage (calque de au_qld / no_kartverket).
#   - CRS natif EPSG:3857 (Web Mercator)
#   - Résolution 5 m, F32. NB : DEM dérivé de stéréo-photogrammétrie (PAS du
#     LiDAR) → échelle paysage, pas le micro-relief archéo. Le LiDAR NSW est
#     par-projet (fragmenté, via ELVIS) ; ce service donne la couverture
#     state-wide propre au prix de la résolution.
#   - Licence : CC BY 4.0 — © State of New South Wales (Spatial Services)
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Australie (NSW) — DEM 5m (Spatial Services NSW)"
CODE       = "au-nsw"
COUNTRY    = "au"
LICENSE    = "CC BY 4.0 — © State of New South Wales (Spatial Services)"
DOC_URL    = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_5M_Elevation/ImageServer"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3857"        # Web Mercator
RESOLUTION_M       = 5.0                # DEM 5 m (stéréo, pas LiDAR)
DALLE_KM           = 5                  # tuiles 5×5 km → 1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000 px
SEUIL_DALLE_VALIDE = 100_000
# Étendue NSW en EPSG:3857 (depuis l'ImageServer)
COVERAGE_EXTENT = (15696048, -4510665, 17143733, -3248630)


# ── Endpoints ────────────────────────────────────────────────────────────────
IMAGESERVER = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_5M_Elevation/ImageServer"
EXPORT_URL  = f"{IMAGESERVER}/exportImage"


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"nsw_dem5m_{x_km:08d}_{y_km:+09d}_3857.tif"


import re as _re
_SUBDIR_FROM_NAME = _re.compile(r"nsw_dem5m_(\d+)_")


def subdir_from_name(nom):
    m = _SUBDIR_FROM_NAME.match(nom)
    return m.group(1) if m else None


# ── Construction URL exportImage ─────────────────────────────────────────────
def dalle_url(x_km, y_km):
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
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  NSW: bbox out of extent (Web Mercator)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  NSW Spatial Services (DEM 5m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
