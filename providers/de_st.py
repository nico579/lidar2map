# providers/de_st.py — Saxe-Anhalt (Allemagne), DGM1 1 m via WCS INSPIRE
#
# Source : LVermGeo Sachsen-Anhalt (Landesamt für Vermessung und Geoinformation)
#   GetCapabilities : https://geodatenportal.sachsen-anhalt.de/ows_INSPIRE_LVermGeo_ATKIS_EL_DGM_WCS?REQUEST=GetCapabilities&SERVICE=WCS&VERSION=2.0.1
#   Open data : dl-de/by-2-0.
#
# Découvert automatiquement (2026-07-14) via le CSW GDI-DE (services d'élévation)
# + auto-sonde WCS : coverage `Coverage1`, EPSG:25832, offsetVector 1 m, download
# réel validé (Magdebourg 46-63 m).
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque es_cnig / it_emilia_romagna).
#   - CRS natif EPSG:25832 (ETRS89 / UTM 32N).
#   - axisLabels="x y" (minuscules) ; GetCoverage renvoie un multipart/related
#     dont le GeoTIFF a une géoréf correcte mais SANS tag CRS → post_fetch
#     réétiquette EPSG:25832 (comme it-emilia-romagna).
#   - Licence : dl-de/by-2-0.
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Saxe-Anhalt — DGM1 1 m (LVermGeo, WCS)"
CODE       = "de-st"
COUNTRY    = "de"
LICENSE    = "dl-de/by-2-0 — © GeoBasis-DE/LVermGeo ST"
DOC_URL    = "https://www.lvermgeo.sachsen-anhalt.de/de/gdp-dgm1.html"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"         # ETRS89 / UTM 32N
RESOLUTION_M       = 1.0                   # DGM1 1 m
DALLE_KM           = 1                     # tuile 1×1 km → 1000×1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://geodatenportal.sachsen-anhalt.de/ows_INSPIRE_LVermGeo_ATKIS_EL_DGM_WCS"
COVERAGE = "Coverage1"
WCS_AXIS_LABELS = ("x", "y")
# Étendue du coverage en EPSG:25832 (depuis DescribeCoverage)
COVERAGE_EXTENT = (606000, 5646000, 790000, 5882000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"st_dgm1_{x_km}_{y_km}.tif"


def subdir_from_name(nom):
    import re
    m = re.match(r"st_dgm1_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0.1 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 2.0.1 GetCoverage, subsets x/y en EPSG:25832 → GeoTIFF (multipart)."""
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
        print("  Sachsen-Anhalt: bbox out of the DGM1 extent (UTM 32N)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  DE ST (DGM1 1m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}


# ── Hook post_fetch : réétiqueter le CRS EPSG:25832 ──────────────────────────
def post_fetch(chemin):
    """Le WCS ST renvoie un GeoTIFF à la géoréf correcte mais SANS tag CRS
    (src.crs → None). On réétiquette en EPSG:25832 EN PLACE (métadonnée seule).
    S'exécute APRÈS la désencapsulation multipart du cœur ; le cœur re-valide."""
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
            src.crs = rasterio.CRS.from_epsg(25832)
