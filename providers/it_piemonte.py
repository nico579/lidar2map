# providers/it_piemonte.py — Italie (Piémont), DTM 5 m LiDAR via WCS 1.0.0
#
# Source : Regione Piemonte — DTM dérivé du LiDAR ICE 2009-2011.
#   Métadonnées : https://www.geoportale.piemonte.it/geonetwork/srv/api/records/r_piemon:224de2ac-023e-441c-9ae0-ea493b217a8e
#   WCS : https://geomap.reteunitaria.piemonte.it/ws/taims/rp-01/taimsdtmwcs/wcs_ice_2009_2011_dtm
#
# Paradigme : WCS *1.0.0* GetCoverage par bbox (MapServer ; calque es-euskadi).
#   ATTENTION FORMAT : `format=image/tiff` renvoie le DTM Float32 réel ;
#   `format=GTiff` renvoie une version UInt8 quantifiée (inutilisable pour le
#   micro-relief). On force donc image/tiff.
#   - CRS natif EPSG:32632 (WGS84 / UTM 32N).
#   - Coverage « DTM », résolution 5 m (offsetVector 5), NoData -99.
#   - GetCoverage 1.0.0 = BBOX + WIDTH/HEIGHT + CRS + FORMAT (pas de subset 2.0.1 ;
#     le service renvoie une ExtentError en 2.0.1 sur ce MapServer). GeoTIFF direct
#     (pas multipart en 1.0.0), CRS + NoData embarqués → pas de post_fetch.
#   - Licence : CC BY 4.0 (dati aperti Regione Piemonte).
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Italie (Piémont) — DTM 5 m (Regione Piemonte, WCS)"
CODE       = "it-piemonte"
COUNTRY    = "it"
LICENSE    = "CC BY 4.0 — © Regione Piemonte"
DOC_URL    = "https://www.geoportale.piemonte.it/geonetwork/srv/api/records/r_piemon:224de2ac-023e-441c-9ae0-ea493b217a8e"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:32632"         # WGS84 / UTM 32N
RESOLUTION_M       = 5.0                   # DTM 5 m (offsetVector du WCS)
DALLE_KM           = 5                     # tuile 5×5 km → 1000×1000 px à 5 m
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000
SEUIL_DALLE_VALIDE = 100_000              # Float32 1000×1000 (>> erreur XML)


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://geomap.reteunitaria.piemonte.it/ws/taims/rp-01/taimsdtmwcs/wcs_ice_2009_2011_dtm"
COVERAGE = "DTM"
# Étendue du coverage en EPSG:32632 (depuis DescribeCoverage)
COVERAGE_EXTENT = (290748, 4861375, 536649, 5165171)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"it_pie_dtm5_{int(x_km)}_{int(y_km)}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km)}"


def subdir_from_name(nom):
    import re
    m = re.match(r"it_pie_dtm5_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 1.0.0 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 1.0.0 GetCoverage : BBOX + WIDTH/HEIGHT en EPSG:32632 → GeoTIFF Float32.
    FORMAT=image/tiff impératif (GTiff = UInt8 quantifié)."""
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
        "FORMAT":   "image/tiff",
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
        print("  Piemonte: bbox out of the DTM extent (UTM 32N)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  IT Piemonte (DTM 5m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
