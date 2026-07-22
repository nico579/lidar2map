# providers/es_navarra.py — Navarre (Espagne), MDT LiDAR 2 m via WCS
#
# Source : Gobierno de Navarra — IDENA (Infraestructura de Datos Espaciales de Navarra)
#   GetCapabilities : https://idena.navarra.es/ogc/wcs?service=WCS&version=2.0.1&request=GetCapabilities
#   Servicios IDENA : https://www.navarra.es/es/web/geoportal/idena/servicios
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque de_hessen).
#   - CRS natif EPSG:25830 (ETRS89 / UTM 30N) — comme es-euskadi.
#   - Coverage "IDENA.WCS__ELEVAC_Ras_MDT_2M" = MDT (terrain) 2 m (offsetVector 2,
#     confirmé). NE PAS confondre avec les couches AltMed/AltDom (modèles de
#     surface/canopée) ni les 10 m.
#   - axisLabels="E N" (depuis DescribeCoverage) ; E=Est, N=Nord.
#   - GetCoverage renvoie un GeoTIFF float32 AVEC tag CRS embarqué → PAS de
#     post_fetch.
#   - NoData = 3.4028235e38 (float32 max) : porté par le tag TIFF, honoré par le
#     cœur (rendu transparent hors donnée). Ne pas le réécrire.
#   - Licence : CC BY 4.0 (Gobierno de Navarra).
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Navarre — MDT LiDAR 2 m (IDENA, WCS)"
CODE       = "es-navarra"
COUNTRY    = "es"
LICENSE    = "CC BY 4.0 — © Gobierno de Navarra"
DOC_URL    = "https://www.navarra.es/es/web/geoportal/idena/servicios"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25830"         # ETRS89 / UTM 30N
RESOLUTION_M       = 2.0                  # MDT 2 m (offsetVector du WCS)
DALLE_KM           = 2                     # tuile 2×2 km → 1000×1000 px à 2 m
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000              # Float32 1000×1000 (>> erreur XML)


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://idena.navarra.es/ogc/wcs"
COVERAGE = "IDENA.WCS__ELEVAC_Ras_MDT_2M"
# axisLabels="E N" (depuis DescribeCoverage) — E=Est, N=Nord
WCS_AXIS_LABELS = ("E", "N")
# Étendue du coverage en EPSG:25830 (depuis DescribeCoverage)
COVERAGE_EXTENT = (539160, 4640000, 686575, 4797000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"nav_mdt2m_{x_km}_{y_km}.tif"


def subdir_from_name(nom):
    import re
    m = re.match(r"nav_mdt2m_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0.1 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 2.0.1 GetCoverage, subsets E/N en EPSG:25830 → GeoTIFF."""
    step = DALLE_KM * 1000
    xmin = x_km * step
    ymin = y_km * step
    ax1, ax2 = WCS_AXIS_LABELS
    params = urllib.parse.urlencode({
        "service":    "WCS",
        "version":    "2.0.1",
        "request":    "GetCoverage",
        "coverageId": COVERAGE,
        "format":     "image/tiff",
        "subset":     f"{ax1}({xmin},{xmin + step})",
    })
    return f"{WCS_URL}?{params}&subset={ax2}({ymin},{ymin + step})"


# ── Grille de dalles ─────────────────────────────────────────────────────────
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
    """Grille synthétique clippée à l'étendue du coverage. WCS continu → pas d'index."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  Navarra: bbox out of the MDT extent (UTM 30N)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  ES Navarra (MDT 2m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
