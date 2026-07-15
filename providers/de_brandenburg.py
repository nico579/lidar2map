# providers/de_brandenburg.py — Brandebourg (Allemagne), DGM1 1 m via WCS INSPIRE
#
# Source : LGB (Landesvermessung und Geobasisinformation Brandenburg)
#   GetCapabilities : https://inspire.brandenburg.de/services/el_dgm1_wcs?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities
#   Fiche GeoBroker : https://geobroker.geobasis-bb.de/ (produit DGM1, OpenData)
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque it_emilia_romagna / es_cnig).
#   - CRS natif EPSG:25833 (ETRS89 / UTM 33N) — comme de-mv.
#   - Coverage "el_elevationgridcoverage" = DGM1 1 m (offsetVector 1, confirmé).
#   - axisLabels="x y" (minuscules, comme es_cnig/it_emilia) ; x=Est, y=Nord.
#   - GetCoverage renvoie un GeoTIFF float32 à la géoréf correcte mais SANS tag
#     CRS (src.crs → None) → post_fetch réétiquette EPSG:25833 en place (comme
#     it-emilia-romagna et de-st).
#   - Licence : Datenlizenz Deutschland – Namensnennung 2.0 (dl-de/by-2-0).
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Brandebourg — DGM1 1 m (LGB, WCS)"
CODE       = "de-brandenburg"
COUNTRY    = "de"
LICENSE    = "dl-de/by-2-0 — © GeoBasis-DE/LGB"
DOC_URL    = "https://geobroker.geobasis-bb.de/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25833"         # ETRS89 / UTM 33N
RESOLUTION_M       = 1.0                  # DGM1 1 m
DALLE_KM           = 1                     # tuile 1×1 km → 1000×1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000              # Float32 1000×1000 (>> erreur XML/HTML)


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://inspire.brandenburg.de/services/el_dgm1_wcs"
COVERAGE = "el_elevationgridcoverage"
# axisLabels="x y" (depuis DescribeCoverage) — minuscules, x=Est y=Nord
WCS_AXIS_LABELS = ("x", "y")
# Étendue du coverage en EPSG:25833 (depuis DescribeCoverage)
COVERAGE_EXTENT = (248000, 5690000, 466000, 5936000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"bb_dgm1_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"bb_dgm1_(\d+)_", nom)
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
        print("  Brandenburg: bbox out of the DGM1 extent (UTM 33N)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  DE Brandenburg (DGM1 1m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}


# ── Hook post_fetch : réétiqueter le CRS EPSG:25833 ──────────────────────────
def post_fetch(chemin):
    """Le WCS LGB renvoie un GeoTIFF à la géoréf correcte mais SANS tag CRS
    (src.crs → None). On réétiquette en EPSG:25833 EN PLACE (métadonnée seule,
    pas de reprojection). Le cœur re-valide ensuite la dalle."""
    from pathlib import Path as _P
    p = _P(chemin)
    try:
        with open(p, "rb") as fh:
            if fh.read(2) not in (b"II", b"MM"):
                return          # pas un TIFF brut (erreur/HTML) → laisser le validateur
    except OSError:
        return
    import rasterio
    with rasterio.open(p, "r+") as src:
        if src.crs is None:
            src.crs = rasterio.CRS.from_epsg(25833)
