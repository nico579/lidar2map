# providers/de_hessen.py — Hesse (Allemagne), DGM1 1 m via WCS INSPIRE
#
# Source : HVBG (Hessische Verwaltung für Bodenmanagement und Geoinformation)
#   GetCapabilities : https://inspire-hessen.de/raster/dgm1/ows?REQUEST=GetCapabilities&SERVICE=WCS&VERSION=2.0.1
#   Produit officiel : https://hvbg.hessen.de/landesvermessung/geotopographie/3d-daten/digitale-gelaendemodelle
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque es_cnig / at_tirol / be_flanders).
#   - CRS natif EPSG:25832 (ETRS89 / UTM 32N)
#   - Coverage "he_dgm1" = DGM1 1 m (résolutions dégradées he_dgm1_2/4/8/16/32 aussi
#     servies ; on prend le 1 m natif)
#   - axisLabels="E N" (depuis DescribeCoverage)
#   - GetCoverage renvoie un GeoTIFF (le cœur désencapsule un éventuel
#     multipart/related WCS 2.0 via _extraire_tiff_multipart)
#   - Licence : Datenlizenz Deutschland – Namensnennung 2.0 (dl-de/by-2-0)
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Hesse — DGM1 1 m (HVBG, WCS)"
CODE       = "de-hessen"
COUNTRY    = "de"
LICENSE    = "dl-de/by-2-0 — © HVBG Hessen"
DOC_URL    = "https://hvbg.hessen.de/landesvermessung/geotopographie/3d-daten/digitale-gelaendemodelle"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"         # ETRS89 / UTM 32N
RESOLUTION_M       = 1.0                  # DGM1 1 m
DALLE_KM           = 1                     # tuile 1×1 km → 1000×1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000              # Float32 1000×1000 compressé


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://inspire-hessen.de/raster/dgm1/ows"
COVERAGE = "he_dgm1"
# axisLabels="E N" (depuis DescribeCoverage)
WCS_AXIS_LABELS = ("E", "N")
# Étendue du coverage en EPSG:25832 (depuis DescribeCoverage)
COVERAGE_EXTENT = (411000, 5471000, 587000, 5724000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"he_dgm1_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"he_dgm1_(\d+)_", nom)
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
        print("  Hessen: bbox out of the DGM1 extent (UTM 32N)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  DE Hessen (DGM1 1m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
