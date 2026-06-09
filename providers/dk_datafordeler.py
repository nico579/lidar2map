# providers/dk_datafordeler.py — Danemark, DHM DTM 0.4m via Datafordeler WCS
#
# Source : Klimadatastyrelsen / Styrelsen for Dataforsyning og Infrastruktur
#   https://dataforsyningen.dk/data/4462
#
# Paradigme : WCS 2.0 avec api-key (même pattern que us_3dep).
#   - CRS natif EPSG:25832 (ETRS89 / UTM 32N)
#   - Résolution 0,4 m → dalle 1 km = 2500×2500 px
#   - GetCoverage WCS 2.0 subsets E/N → GeoTIFF Float32
#   - Clé API gratuite sur https://datafordeler.dk/
#   - APIKEY_REQUISE = True (même flag que us_3dep)
#
# Self-contained : stdlib uniquement.

import os
import urllib.parse
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Danemark — DHM DTM 0.4m (Datafordeler)"
CODE       = "dk-datafordeler"
COUNTRY    = "dk"
LICENSE    = "CC BY — © Klimadatastyrelsen / SDFI"
DOC_URL    = "https://dataforsyningen.dk/data/4462"
APIKEY_REQUISE = True


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"
RESOLUTION_M       = 0.4
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 2500 px
SEUIL_DALLE_VALIDE = 500_000


# ── Endpoints ────────────────────────────────────────────────────────────────
# URL confirmée via documentation officielle datafordeler.dk
WCS_URL  = "https://wcs.datafordeler.dk/DHMNedboer/dhm_wcs/1.0.0/WCS"
COVERAGE = "dhm_terraen"   # terrain (DTM 0.4m) ; dhm_overflade = DSM
# Étendue Danemark continental en EPSG:25832
COVERAGE_EXTENT = (441000, 6048000, 893000, 6403000)


# ── API Key ──────────────────────────────────────────────────────────────────
_APIKEY = ""


def set_apikey(key):
    global _APIKEY
    _APIKEY = (key or "").strip()


def _get_api_key():
    key = _APIKEY or os.environ.get("DATAFORDELER_API_KEY", "").strip()
    if not key:
        print("  ⚠ Clé API Datafordeler manquante — passer --apikey <cle> ou "
              "définir DATAFORDELER_API_KEY. "
              "Inscription : https://datafordeler.dk/ "
              "Administration > Opret IT-system > Generer API-nokle", flush=True)
    return key


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"dk_dhm_dtm_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"dk_dhm_dtm_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0 ─────────────────────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 1.0.0 GetCoverage avec apikey, BBOX, GeoTIFF.
    Le service Datafordeler DHM WCS est en version 1.0.0 (pas 2.0.1).
    Paramètre auth : apikey= (pas token=)."""
    step = DALLE_KM * 1000
    xmin = x_km * step
    ymin = y_km * step
    params = {
        "apikey":   _get_api_key(),
        "SERVICE":  "WCS",
        "VERSION":  "1.0.0",
        "REQUEST":  "GetCoverage",
        "COVERAGE": COVERAGE,
        "CRS":      CRS_NATIF,
        "RESPONSE_CRS": CRS_NATIF,
        "BBOX":     f"{xmin},{ymin},{xmin + step},{ymin + step}",
        "WIDTH":    PX_PAR_DALLE,
        "HEIGHT":   PX_PAR_DALLE,
        "FORMAT":   "GTiff",
    }
    return WCS_URL + "?" + urllib.parse.urlencode(params)


# ── Grille ───────────────────────────────────────────────────────────────────
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
    if not _get_api_key():
        return None
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  Danemark : bbox hors de l'étendue du coverage")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
