# providers/es_euskadi.py — Pays basque (Espagne), MDT LiDAR 1 m via WCS 1.0.0
#
# Source : geoEuskadi (Gobierno Vasco / Eusko Jaurlaritza)
#   GetCapabilities : https://www.geo.euskadi.eus/geoeuskadi/services/U11/WCS_KARTOGRAFIA/MapServer/WCSServer?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCapabilities
#   REST : https://www.geo.euskadi.eus/geoeuskadi/rest/services/U11/WCS_KARTOGRAFIA/MapServer
#
# Paradigme : WCS *1.0.0* GetCoverage par bbox (ArcGIS MapServer WCSServer).
#   ATTENTION, protocole différent des autres providers WCS (2.0.1) :
#     - identifiants de coverage = un simple index numérique (<name>1</name>…) ;
#     - GetCoverage prend BBOX=minx,miny,maxx,maxy + WIDTH + HEIGHT + CRS +
#       FORMAT=GeoTIFF (PAS de subset= comme en 2.0.1).
#   - Coverage "2" = MDT_LIDAR_1M_EGUNERATUENA (le plus récent, TERRAIN).
#     NE PAS prendre "1" = MDS (surface/canopée). Ordre vérifié via
#     GetCapabilities (labels). Si geoEuskadi réordonne ses coverages, re-vérifier
#     que l'index 2 pointe bien MDT_LIDAR_1M et pas MDS_LIDAR_1M.
#   - CRS natif EPSG:25830 (ETRS89 / UTM 30N) — comme es-navarra.
#   - GetCoverage renvoie un GeoTIFF float32 AVEC tag CRS embarqué → PAS de
#     post_fetch.
#   - Licence : CC BY 4.0 (geoEuskadi).
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Pays basque — MDT LiDAR 1 m (geoEuskadi, WCS)"
CODE       = "es-euskadi"
COUNTRY    = "es"
LICENSE    = "CC BY 4.0 — © geoEuskadi"
DOC_URL    = "https://www.geo.euskadi.eus/geoeuskadi/rest/services/U11/WCS_KARTOGRAFIA/MapServer"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25830"         # ETRS89 / UTM 30N
RESOLUTION_M       = 1.0                  # MDT LiDAR 1 m
DALLE_KM           = 1                     # tuile 1×1 km → 1000×1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000              # Float32 1000×1000 (>> erreur XML)


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = ("https://www.geo.euskadi.eus/geoeuskadi/services/U11/"
            "WCS_KARTOGRAFIA/MapServer/WCSServer")
COVERAGE = "2"                            # index MapServer = MDT_LIDAR_1M (terrain)
# Étendue du coverage en EPSG:25830 (depuis DescribeCoverage)
COVERAGE_EXTENT = (461031, 4700735, 606516, 4811755)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"eus_mdt1m_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"eus_mdt1m_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 1.0.0 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 1.0.0 GetCoverage : BBOX + WIDTH/HEIGHT en EPSG:25830 → GeoTIFF."""
    step = DALLE_KM * 1000
    xmin = x_km * step
    ymin = y_km * step
    params = urllib.parse.urlencode({
        "SERVICE":  "WCS",
        "VERSION":  "1.0.0",
        "REQUEST":  "GetCoverage",
        "COVERAGE": COVERAGE,
        "CRS":      CRS_NATIF,
        "BBOX":     f"{xmin},{ymin},{xmin + step},{ymin + step}",
        "WIDTH":    PX_PAR_DALLE,
        "HEIGHT":   PX_PAR_DALLE,
        "FORMAT":   "GeoTIFF",
    })
    return f"{WCS_URL}?{params}"


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
        print("  Euskadi: bbox out of the MDT extent (UTM 30N)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  ES Euskadi (MDT 1m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
