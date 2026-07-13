# providers/de_bw.py — Bade-Wurtemberg (Allemagne), DGM1 1 m via WCS INSPIRE
#
# Source : LGL Baden-Württemberg (Landesamt für Geoinformation und Landentwicklung)
#   GetCapabilities : https://owsproxy.lgl-bw.de/owsproxy/wcs/WCS_INSP_BW_Hoehe_Coverage_DGM1?REQUEST=GetCapabilities&SERVICE=WCS&version=2.0.1
#   Open Data : https://www.lgl-bw.de/Produkte/Open-Data/
#
# NB : le README annonçait « portail JS seulement » — FAUX, ce WCS 2.0.1 INSPIRE
# officiel sert le DGM1 1 m directement.
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque es_cnig / de_hessen).
#   - CRS natif EPSG:25832 (ETRS89 / UTM 32N)
#   - Coverage "EL.ElevationGridCoverage" (nommage INSPIRE) = DGM1 1 m
#   - axisLabels="E N" (depuis DescribeCoverage)
#   - GetCoverage renvoie un GeoTIFF (le cœur désencapsule un éventuel
#     multipart/related via _extraire_tiff_multipart)
#   - Licence : dl-de/by-2-0 (Open Data BW)
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Bade-Wurtemberg — DGM1 1 m (LGL, WCS)"
CODE       = "de-bw"
COUNTRY    = "de"
LICENSE    = "dl-de/by-2-0 — © LGL Baden-Württemberg"
DOC_URL    = "https://www.lgl-bw.de/Produkte/Open-Data/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"         # ETRS89 / UTM 32N
RESOLUTION_M       = 1.0                  # DGM1 1 m
DALLE_KM           = 1                     # tuile 1×1 km → 1000×1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000              # Float32 1000×1000 compressé


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://owsproxy.lgl-bw.de/owsproxy/wcs/WCS_INSP_BW_Hoehe_Coverage_DGM1"
COVERAGE = "EL.ElevationGridCoverage"     # nommage INSPIRE
# axisLabels="E N" (depuis DescribeCoverage)
WCS_AXIS_LABELS = ("E", "N")
# Étendue du coverage en EPSG:25832 (depuis DescribeCoverage, arrondie)
COVERAGE_EXTENT = (388000, 5264000, 611000, 5520000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"bw_dgm1_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"bw_dgm1_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0.1 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 2.0.1 GetCoverage, subsets E/N en EPSG:25832 → GeoTIFF."""
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
    # 2e subset ajouté manuellement (urllib ne gère pas les clés dupliquées)
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
        print("  Baden-Württemberg: bbox out of the DGM1 extent (UTM 32N)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  DE BW (DGM1 1m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
