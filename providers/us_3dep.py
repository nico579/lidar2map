# providers/us_3dep.py — USA, USGS 3DEP via OpenTopography API
#
# Source : USGS 3D Elevation Program (3DEP) servi par OpenTopography.
# Distribution : API REST simple bbox → GeoTIFF (https://portal.opentopography.org/API/usgsdem)
#
# 3 datasets disponibles :
#   - USGS1m  : 1 m natif (ACADEMIQUE seulement, max 250 km² par requête)
#   - USGS10m : 10 m / 1/3 arc-seconde, libre
#   - USGS30m : 30 m / 1 arc-seconde, libre
#
# Spécificités vs FR/NL/CH/NO :
#   - Pas un portail national mais un agrégateur académique (OT)
#   - Coverage : USA entiers (incl. Alaska, Hawaii)
#   - **API Key requise** (gratuite après inscription opentopography.org)
#     → variable d'environnement OPENTOPOGRAPHY_API_KEY
#   - CRS de sortie : NAD83 géographique (EPSG:4269) — degrees, pas mètres
#     → Le pipeline downstream SVF/ombrages perd en précision sur des CRS
#       géographiques. Pour usage archéo sérieux, prévoir une étape de
#       reprojection vers UTM dans un futur fix.
#
# Limitations connues :
#   - USGS1m restreint aux comptes "academic" sur opentopography.org
#   - Rate limit : 50 calls/24h non-academic, 200/24h academic
#   - 1m max 250 km² par requête
#
# Status POC : structure validée. URL pattern correct. Test live nécessite
# un API key OpenTopography (gratuit après inscription).

import os
import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "USA — USGS 3DEP (via OpenTopography)"
CODE       = "us-3dep"
COUNTRY    = "us"
LICENSE    = "Public domain (USGS) + OT terms"
DOC_URL    = "https://opentopography.org/news/api-access-usgs-3dep-rasters-now-available"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:4269"       # NAD83 géographique (lat/lon decimal degrees)
                                       # ⚠ Pas un CRS projeté → SVF/ombrages
                                       # sous-optimaux sans reprojection UTM.
# Dataset par défaut. Configurable via env OPENTOPOGRAPHY_DATASET.
# USGS1m nécessite un compte "academic" + max 250 km² par requête.
DATASET            = os.environ.get("OPENTOPOGRAPHY_DATASET", "USGS10m")
_RES_PAR_DATASET   = {"USGS1m": 1, "USGS10m": 10, "USGS30m": 30}
RESOLUTION_M       = _RES_PAR_DATASET.get(DATASET, 10)

# Taille de tuile : on choisit 0.01° (~1.1 km à l'équateur, ~0.85 km à 40°N).
# Compromis entre nombre de requêtes (rate limit OT) et granularité.
DALLE_DEG          = 0.01
DALLE_KM           = 1                 # approximation pour le code générique
PX_PAR_DALLE       = int(DALLE_DEG * 111000 / RESOLUTION_M)   # ~110 à 10 m/px
SEUIL_DALLE_VALIDE = 5_000             # raster geographic petit en bytes


# ── Endpoints ────────────────────────────────────────────────────────────────
API_BASE = "https://portal.opentopography.org/API/usgsdem"


# ── API Key (requise pour toutes les requêtes OT) ────────────────────────────
# Source de la clé, par ordre de priorité :
#   1. CLI : --apikey <cle>  (via set_apikey() appelé depuis main)
#   2. env : OPENTOPOGRAPHY_API_KEY
_APIKEY = ""


def set_apikey(key):
    """Permet à lidar2map.py de transmettre args.apikey au provider depuis la CLI."""
    global _APIKEY
    _APIKEY = (key or "").strip()


def _get_api_key():
    key = _APIKEY or os.environ.get("OPENTOPOGRAPHY_API_KEY", "").strip()
    if not key:
        print("  ⚠ Clé API OpenTopography manquante — passer --apikey <cle> ou "
              "définir OPENTOPOGRAPHY_API_KEY. Inscription gratuite : "
              "https://portal.opentopography.org/myopentopo", flush=True)
    return key


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_lon, y_lat):
    """Pour US 3DEP les coords sont en degrés décimaux NAD83. On code en
    centièmes de degré pour avoir des noms de fichiers stables."""
    return f"us3dep_{DATASET}_{int(x_lon * 100):06d}_{int(y_lat * 100):05d}.tif"


def dalle_subdir(x_lon):
    """Sous-dossier par degré entier de longitude (12 zones pour les USA)."""
    return f"lon{int(x_lon):+04d}"


import re as _re
_SUBDIR_FROM_NAME = _re.compile(r"us3dep_[^_]+_(-?\d+)_")


def subdir_from_name(nom):
    m = _SUBDIR_FROM_NAME.match(nom)
    if not m:
        return None
    x_lon_cent = int(m.group(1))
    return f"lon{x_lon_cent // 100:+04d}"


# ── Construction URL pour une dalle ──────────────────────────────────────────
def dalle_url(x_lon, y_lat):
    """URL OpenTopography exportImage 3DEP pour une tuile DALLE_DEG° × DALLE_DEG°.
    Convention : (x_lon, y_lat) = coin SW de la tuile en centièmes de degré.
    """
    west  = x_lon
    south = y_lat
    east  = west + DALLE_DEG
    north = south + DALLE_DEG
    params = {
        "datasetName": DATASET,
        "south": south, "north": north,
        "west": west, "east": east,
        "outputFormat": "GTiff",
        "API_Key": _get_api_key(),
    }
    return API_BASE + "?" + urllib.parse.urlencode(params)


# ── Grille pour une bbox ─────────────────────────────────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    """Pour US 3DEP, la bbox est en degrés NAD83. La grille est en 0.01°."""
    step = DALLE_DEG
    # Index par centièmes de degré (intégers pour avoir des keys stables)
    lon_start = int(x1 / step)
    lon_end   = int(x2 / step)
    lat_start = int(y1 / step)
    lat_end   = int(y2 / step)
    dalles = []
    for i_lon in range(lon_start, lon_end + 1):
        for i_lat in range(lat_start, lat_end + 1):
            dalles.append((i_lon * step, i_lat * step))
    return dalles


# ── Découverte des dalles ────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Construit {nom: url} depuis la grille deg en NAD83.

    bbox_wgs84 : (lon_min, lat_min, lon_max, lat_max) — identique à bbox_natif
                 puisque NAD83 ≈ WGS84 pour des usages non-géodésiques
                 (différence < 1 m à l'échelle continentale USA).
    bbox_natif : (x1, y1, x2, y2) où x = lon, y = lat (degrés NAD83).
    """
    key = _get_api_key()
    if not key:
        print("  ERREUR : OPENTOPOGRAPHY_API_KEY manquante.")
        return None

    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = bbox_natif
    dalles = {}
    for x_lon, y_lat in dalles_pour_bbox(x1, y1, x2, y2):
        nom = dalle_filename(x_lon, y_lat)
        dalles[nom] = dalle_url(x_lon, y_lat)

    # Rate limit OT : 50 calls/24h non-academic. Si la bbox génère >50 dalles,
    # l'utilisateur va se faire bloquer après ~50.
    if len(dalles) > 50:
        print(f"  ⚠ {len(dalles)} dalles → dépasse le rate limit OT non-academic "
              f"(50/24h). Réduire la bbox ou changer pour USGS10m/30m.")
    print(f"  US 3DEP : {len(dalles)} dalle(s) générées (grille 0.01° {DATASET})")
    return dalles
