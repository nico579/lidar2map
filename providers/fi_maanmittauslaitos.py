# providers/fi_maanmittauslaitos.py — Finlande, Elevation Model 2m (NLS Finland)
#
# Source : Maanmittauslaitos (NLS Finland)
#   https://www.maanmittauslaitos.fi/en/maps-and-spatial-data/expert-users/product-descriptions/elevation-model-2-m
#
# Paradigme : WCS 2.0 sans auth (calque exact de at_tirol).
#   - CRS natif EPSG:3067 (ETRS-TM35FIN)
#   - Résolution 2 m → dalle 1 km = 500×500 px
#   - GetCoverage WCS 2.0 par bbox → GeoTIFF Float32
#   - Pas d'index : grille synthétique clippée à l'étendue du coverage
#   - Nommage par coin SW (x_km, y_km)
#
# NB : NLS propose aussi un DEM 5m plus léger et un modèle de surface 2m.
# On cible le DTM 2m (LAYER = korkeusmalli_2m) qui est le meilleur disponible
# librement sans compte. Un DEM 1m existe mais requiert inscription.
#
# Self-contained : stdlib uniquement.
# NB : le serveur NLS Finland présente un certificat auto-signé dans sa chaîne
# SSL. Le pipeline doit utiliser _SSL_CTX (exposé par ce module) lors du
# téléchargement, ou passer ssl=False dans les requêtes urllib.

import os
import ssl
import urllib.parse

# NLS Finland utilise un certificat auto-signé dans la chaîne SSL → bypass nécessaire
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Finlande — Elevation Model 2m (Maanmittauslaitos)"
CODE       = "fi-maanmittauslaitos"
COUNTRY    = "fi"
LICENSE    = "CC BY 4.0 — © Maanmittauslaitos (NLS Finland)"
DOC_URL    = "https://www.maanmittauslaitos.fi/en/maps-and-spatial-data/expert-users/product-descriptions/elevation-model-2-m"
# Le service avoin-karttakuva exige une clé API gratuite (param api-key=).
# Sans clé → HTTP 401. Inscription : https://www.maanmittauslaitos.fi/rajapinnat/api-avaimen-ohje
APIKEY_REQUISE = True


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3067"          # ETRS89 / TM35FIN
RESOLUTION_M       = 2.0                  # DTM 2 m
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 500 px
SEUIL_DALLE_VALIDE = 100_000              # octets (500×500 float32 compressé ~200 Ko)


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://avoin-karttakuva.maanmittauslaitos.fi/ortokuvat-ja-korkeusmallit/wcs/v2"
# Layer name depuis GetCapabilities NLS
COVERAGE = "korkeusmalli_2m"
# Étendue du coverage en EPSG:3067 (Finlande continentale)
# X (Est) : 61000 → 733000  |  Y (Nord) : 6582000 → 7777000
COVERAGE_EXTENT = (61000, 6582000, 733000, 7777000)


# ── API Key ──────────────────────────────────────────────────────────────────
_APIKEY = ""


def set_apikey(key):
    global _APIKEY
    _APIKEY = (key or "").strip()


def _get_api_key():
    key = _APIKEY or os.environ.get("NLS_FINLAND_API_KEY", "").strip()
    if not key:
        print("  ⚠ Maanmittauslaitos API key missing, pass --apikey <key> or "
              "set NLS_FINLAND_API_KEY. "
              "Sign up: https://www.maanmittauslaitos.fi/rajapinnat/api-avaimen-ohje",
              flush=True)
    return key


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"fi_dem2m_{x_km}_{y_km}.tif"


def subdir_from_name(nom):
    import re
    m = re.match(r"fi_dem2m_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0 GetCoverage ─────────────────────────────────────
def dalle_url(x_km, y_km):
    """URL WCS 2.0 GetCoverage pour une dalle 1×1 km en EPSG:3067."""
    step = DALLE_KM * 1000
    xmin = x_km * step
    ymin = y_km * step
    # WCS 2.0 : subsets par axe nommé (E, N) — NLS utilise les axes EPSG:3067
    # format : subset=E(xmin,xmax)&subset=N(ymin,ymax)
    params = {
        "api-key":    _get_api_key(),
        "service":    "WCS",
        "version":    "2.0.1",
        "request":    "GetCoverage",
        "coverageId": COVERAGE,
        "format":     "image/tiff",
        "subset":     f"E({xmin},{xmin + step})",
    }
    # Le 2e subset doit être passé en doublon de clé → construction manuelle
    base = WCS_URL + "?" + urllib.parse.urlencode(params)
    base += f"&subset=N({ymin},{ymin + step})"
    return base


# ── Grille dalles pour une bbox ──────────────────────────────────────────────
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
    """Grille clippée à l'étendue du coverage NLS Finland."""
    if not _get_api_key():
        return None
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  Finland: bbox out of the NLS coverage extent")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
