# providers/pl_gugik.py — Pologne, NMT 1m (LiDAR ISOK) via WCS GUGiK
#
# Source : Główny Urząd Geodezji i Kartografii (GUGiK) — geoportal.gov.pl
#   GetCapabilities : https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModelFormatTIFF?request=GetCapabilities&service=WCS
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque at_tirol / es_cnig).
#   - CRS natif EPSG:2180 (PUWG 1992 / Poland CS92)
#   - Coverage "DTM_PL-KRON86-NH_TIFF" = NMT GRID1 = 1 m (LiDAR ISOK national)
#   - axisLabels="y x" côté serveur ; en GetCoverage on subsette par x/y
#     (x = easting, y = northing, mêmes valeurs que la bbox EPSG:2180 always_xy)
#   - GetCoverage renvoie un GeoTIFF brut (pas de multipart)
#   - Données ouvertes (gratuites, sans compte) depuis 2020
#
# Le NMT 1 m polonais (projet ISOK) couvre tout le pays et est dérivé du LiDAR
# aéroporté → micro-relief exploitable pour la prospection archéologique.
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Pologne — NMT LiDAR (GUGiK / ISOK)"
CODE       = "pl-gugik"
COUNTRY    = "pl"
LICENSE    = "Dane otwarte — GUGiK (données ouvertes, gratuit)"
DOC_URL    = "https://www.geoportal.gov.pl/pl/dane/numeryczny-model-terenu-nmt/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2180"          # PUWG 1992 / Poland CS92
RESOLUTION_M       = 1.0                  # NMT GRID1 = 1 m
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 200_000


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModelFormatTIFF"
COVERAGE = "DTM_PL-KRON86-NH_TIFF"
# Subsets par x/y (x = easting, y = northing) — acceptés malgré axisLabels "y x".
WCS_AXIS_LABELS = ("x", "y")
# Étendue du coverage en EPSG:2180 (x=easting, y=northing) depuis DescribeCoverage
COVERAGE_EXTENT = (160828, 98928, 876029, 796521)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"pl_nmt1m_{x_km}_{y_km}.tif"


def subdir_from_name(nom):
    import re
    m = re.match(r"pl_nmt1m_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0.1 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 2.0.1 GetCoverage, subsets x/y en EPSG:2180 → GeoTIFF."""
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
        print("  Poland: bbox out of the NMT extent (EPSG:2180)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  PL GUGiK (NMT 1m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
