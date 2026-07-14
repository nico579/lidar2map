# providers/de_mv.py — Mecklembourg-Poméranie-Occidentale (Allemagne), DGM1 1 m via WCS
#
# Source : LAiV-MV (Landesamt für innere Verwaltung, Amt für Geoinformation)
#   GetCapabilities : https://www.geodaten-mv.de/dienste/inspire_el_dgm_wcs?REQUEST=GetCapabilities&SERVICE=WCS&VERSION=2.0.1
#   Open data : GeoPortal.MV, dl-de/by-2-0.
#
# Découvert automatiquement (2026-07-14) via le CSW GDI-DE (services d'élévation)
# + auto-sonde WCS : coverage `mv_dgm`, EPSG:25833, offsetVector 1 m, download réel
# validé (Schwerin 37-64 m).
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque es_cnig / de_hessen).
#   - CRS natif EPSG:25833 (ETRS89 / UTM 33N) — Allemagne de l'Est.
#   - axisLabels="x y" (minuscules) ; GetCoverage renvoie un GeoTIFF avec CRS.
#   - Licence : dl-de/by-2-0.
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Mecklembourg-Poméranie — DGM1 1 m (LAiV-MV, WCS)"
CODE       = "de-mv"
COUNTRY    = "de"
LICENSE    = "dl-de/by-2-0 — © GeoBasis-DE/MV"
DOC_URL    = "https://www.geodaten-mv.de/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25833"         # ETRS89 / UTM 33N
RESOLUTION_M       = 1.0                   # DGM1 1 m
DALLE_KM           = 1                     # tuile 1×1 km → 1000×1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://www.geodaten-mv.de/dienste/inspire_el_dgm_wcs"
COVERAGE = "mv_dgm"
WCS_AXIS_LABELS = ("x", "y")
# Étendue du coverage en EPSG:25833 (depuis DescribeCoverage)
COVERAGE_EXTENT = (200000, 5886000, 465000, 6075000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"mv_dgm1_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"mv_dgm1_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0.1 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 2.0.1 GetCoverage, subsets x/y en EPSG:25833 → GeoTIFF."""
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
        print("  Mecklenburg-Vorpommern: bbox out of the DGM1 extent (UTM 33N)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  DE MV (DGM1 1m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
