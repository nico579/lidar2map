# providers/be_flanders.py — Belgique (Flandre), DHMV II DTM 1m via WCS
#
# Source : agentschap Digitaal Vlaanderen — Digitaal Hoogtemodel Vlaanderen II
#   https://geo.api.vlaanderen.be/dhmv/wcs
#
# Paradigme : WCS 2.0.1 sans auth (calque exact de at_tirol / gb_england).
#   - CRS natif EPSG:31370 (Belge Lambert 1972)
#   - Résolution 1m → dalle 1 km = 1000×1000 px
#   - GetCoverage WCS 2.0.1 subsets E/N → GeoTIFF Float32
#   - Pas d'index, pas de compte requis, service gratuit
#   - Couverture : Flandre + Bruxelles (lon 2.52–5.94, lat 50.64–51.51)
#
# Coverages disponibles sur ce service (confirmés 06/06/2026) :
#   DHMVII_DTM_1m       — DTM 1m (ce provider)
#   DHMVII_DSM_1m       — DSM 1m
#   DHMV_II_HILL_25cm   — Hillshade multi-directionnel 25cm (8 directions)
#   DHMV_II_SVF_25cm    — Sky-View Factor 25cm (16 directions, r=2.5m)
#   DHMVI_DTM_5m        — ancien DTM 5m (DHMV I, 2001-2004)
#
# NB : DHMV_II_HILL_25cm et DHMV_II_SVF_25cm sont des ombrages précalculés
# par Digitaal Vlaanderen — à terme, un provider séparé pourrait les exposer
# directement dans lidar2map sans recalcul.
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Belgique (Flandre) — DHMV II DTM (Digitaal Vlaanderen WCS)"
CODE       = "be-flanders"
COUNTRY    = "be"
LICENSE    = "Gratis Open Data Licentie Vlaanderen"
DOC_URL    = "https://geo.api.vlaanderen.be/dhmv/wcs?request=GetCapabilities&service=WCS"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:31370"         # Belge Lambert 1972
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 1000 px
SEUIL_DALLE_VALIDE = 200_000              # Float32 1000×1000 compressé ~1-3 Mo


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://geo.api.vlaanderen.be/dhmv/wcs"
COVERAGE = "DHMVII_DTM_1m"
# MapServer Digitaal Vlaanderen : axisLabels="x y" (minuscules) dans le
# DescribeCoverage — PAS E/N. GetCoverage avec E → InvalidAxisLabel (404).
# Lu par dalle_url et par _fetch_provider_shadings (ombrages précalculés).
WCS_AXIS_LABELS = ("x", "y")
# Étendue Flandre en EPSG:31370 (depuis WGS84BoundingBox du GetCapabilities)
# lon 2.52–5.94 / lat 50.64–51.51 → Lambert 1972 approx
COVERAGE_EXTENT = (22000, 153000, 259000, 245000)   # (x_min, y_min, x_max, y_max)


# ── Ombrages précalculés (PROVIDES_SHADINGS) ─────────────────────────────────
# Le WCS Digitaal Vlaanderen expose trois produits dérivés précalculés à 25cm
# que lidar2map peut télécharger directement sans recalcul depuis le DEM 1m.
# Avantage : résolution 4× supérieure et calcul déjà optimisé par Digitaal Vlaanderen.
#
# Coverages disponibles (confirmés 06/06/2026 via GetCapabilities) :
#   DHMV_II_SVF_25cm  : Sky-View Factor, 16 directions, r=2.5m, filtrage bruit
#   DHMV_II_HILL_25cm : Hillshade multi-directionnel, 8 directions, élév. 35°, facteur 2
#
# Format : {cle_ombrage_lidar2map: (coverage_id, resolution_m, wcs_url)}
PROVIDES_SHADINGS = {
    "svf":   ("DHMV_II_SVF_25cm",  0.25, WCS_URL),
    "multi": ("DHMV_II_HILL_25cm", 0.25, WCS_URL),
}


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"be_dhmvii_dtm1m_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"be_dhmvii_dtm1m_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0.1 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 2.0.1 GetCoverage avec subsets E/N en EPSG:31370 → GeoTIFF.
    Même paradigme que gb_england / at_tirol."""
    step = DALLE_KM * 1000
    xmin = x_km * step
    ymin = y_km * step
    ax1, ax2 = WCS_AXIS_LABELS
    # WCS 2.0.1 : deux paramètres subset (double clé → construction manuelle)
    params = urllib.parse.urlencode({
        "service":    "WCS",
        "version":    "2.0.1",
        "request":    "GetCoverage",
        "coverageId": COVERAGE,
        "format":     "image/tiff",
        "subset":     f"{ax1}({xmin},{xmin + step})",
    })
    # Ajouter le 2e subset manuellement (urllib ne gère pas les clés dupliquées)
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
    """Grille synthétique clippée à l'étendue Flandre. WCS continu → pas d'index."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  BE Flanders: bbox out of the DHMV II coverage extent")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  BE Flanders (DHMVII_DTM_1m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
