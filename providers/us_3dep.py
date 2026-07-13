# providers/us_3dep.py — USA, USGS 3DEP via OpenTopography API
#
# Source : USGS 3D Elevation Program (3DEP) servi par OpenTopography.
# Distribution : API REST simple bbox WGS84 → GeoTIFF EPSG:4269 (NAD83 géo).
#
# 3 datasets disponibles :
#   - USGS1m  : 1 m natif (ACADEMIQUE seulement, max 250 km² par requête)
#   - USGS10m : 10 m / 1/3 arc-seconde, libre
#   - USGS30m : 30 m / 1 arc-seconde, libre
#
# Particularité majeure de ce provider :
#   OT retourne ses tiles en EPSG:4269 (NAD83 géographique, lat/lon degrés).
#   Le pipeline lidar2map (VRT, SVF, ombrages) suppose un CRS projeté en
#   mètres. Sans reprojection, le calcul gradient et la grille VRT échouent.
#   → Solution : on déclare CRS_NATIF = EPSG:3857 (Web Mercator) et on
#     reprojette CHAQUE tile post-download via le hook PROVIDER.post_download().
#   → Mercator au lieu d'UTM-zone parce qu'universel (pas de zone à calculer)
#     et c'est le CRS cible final du pipeline MBTiles → warp identité.
#   → Distorsion Mercator à 37°N (Mesa Verde) : ~0.8x — acceptable archéo.
#
# Spécifs config :
#   --apikey TA_CLE  ou  env OPENTOPOGRAPHY_API_KEY  (gratuit, inscription)
#   env OPENTOPOGRAPHY_DATASET = USGS10m (défaut) | USGS1m | USGS30m

import os
import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
# Dataset OpenTopography (pilote la résolution) : USGS10m (10 m, DÉFAUT, libre,
# couverture nationale) | USGS1m (1 m LiDAR, accès ACADÉMIQUE) | USGS30m. Pour
# du 1 m PUBLIC sans compte académique, préférer us-tnm. Le NAME reflète le
# dataset choisi pour éviter de laisser croire à du 1 m par défaut.
DATASET            = os.environ.get("OPENTOPOGRAPHY_DATASET", "USGS10m")
_RES_PAR_DATASET   = {"USGS1m": 1, "USGS10m": 10, "USGS30m": 30}
RESOLUTION_M       = _RES_PAR_DATASET.get(DATASET, 10)

NAME       = f"USA — USGS 3DEP {DATASET} ({RESOLUTION_M:g} m, via OpenTopography)"
CODE       = "us-3dep"
COUNTRY    = "us"
LICENSE    = "Public domain (USGS) + OT terms"
DOC_URL    = "https://opentopography.org/news/api-access-usgs-3dep-rasters-now-available"

# Flag lu par la GUI (_discover_providers) pour décider d'afficher le champ
# "Clé API" à côté de la dropdown provider.
APIKEY_REQUISE = True


# ── Géométrie ────────────────────────────────────────────────────────────────
# CRS_NATIF Web Mercator pour avoir des mètres : c'est dans cette unité que
# le pipeline calcule SVF/hillshade. Les tiles OT (NAD83 géo) sont reprojetées
# au download via post_download() ci-dessous.
CRS_NATIF          = "EPSG:3857"
# DATASET / RESOLUTION_M définis plus haut (section Identification) car le NAME
# les reflète désormais.
DALLE_KM           = 1                  # tuiles 1×1 km en Mercator
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)
SEUIL_DALLE_VALIDE = 5_000              # 100×100 pixel float32 compressé : variable


# ── Endpoints ────────────────────────────────────────────────────────────────
API_BASE = "https://portal.opentopography.org/API/usgsdem"


# ── API Key ──────────────────────────────────────────────────────────────────
_APIKEY = ""


def set_apikey(key):
    global _APIKEY
    _APIKEY = (key or "").strip()


def _get_api_key():
    key = _APIKEY or os.environ.get("OPENTOPOGRAPHY_API_KEY", "").strip()
    if not key:
        print("  ⚠ OpenTopography API key missing, pass --apikey <key> or "
              "set OPENTOPOGRAPHY_API_KEY. Free sign up: "
              "https://portal.opentopography.org/myopentopo", flush=True)
    return key


# ── Helpers Mercator <-> WGS84 ───────────────────────────────────────────────
def _merc_to_wgs(x_m, y_m):
    """EPSG:3857 (x, y) en mètres → EPSG:4326 (lon, lat) en degrés."""
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    return t.transform(x_m, y_m)


# ── Nommage des dalles (en km Mercator) ──────────────────────────────────────
def dalle_filename(x_km, y_km):
    """Nom basé sur les km Mercator. Couvre négatifs (USA = X < 0)."""
    return f"us3dep_{DATASET}_{x_km:+06d}_{y_km:+06d}_3857.tif"


def dalle_subdir(x_km):
    return f"{x_km:+06d}"


import re as _re
_SUBDIR_FROM_NAME = _re.compile(r"us3dep_[^_]+_([+-]?\d+)_")


def subdir_from_name(nom):
    m = _SUBDIR_FROM_NAME.match(nom)
    return f"{int(m.group(1)):+06d}" if m else None


# ── Construction URL pour une dalle (bbox Mercator -> WGS84 pour OT) ─────────
# Marge en mètres Mercator élargissant la bbox source demandée à OT.
# Sans marge, la reprojection NAD83->Mercator laisse une frange nodata sur les
# bords (~2 pixels) car le grid sample tombe en dehors de la couverture source
# vue depuis Mercator. Avec ~30m de marge, on garantit assez de pixels source
# pour remplir tout le target sans bord vide.
_MARGE_MERCATOR_M = 30


def dalle_url(x_km, y_km):
    """Pour une tuile 1 km × 1 km en Mercator (x_km, y_km en km), convertit
    les coins en WGS84 pour appeler l'API OT (qui ne sait que lat/lon).
    On élargit la bbox source de _MARGE_MERCATOR_M pour éviter les bords nodata
    après reprojection."""
    m = _MARGE_MERCATOR_M
    xmin_m = x_km * 1000 - m
    ymin_m = y_km * 1000 - m
    xmax_m = (x_km + 1) * 1000 + m
    ymax_m = (y_km + 1) * 1000 + m
    west,  south = _merc_to_wgs(xmin_m, ymin_m)
    east,  north = _merc_to_wgs(xmax_m, ymax_m)
    params = {
        "datasetName": DATASET,
        "south": south, "north": north,
        "west":  west,  "east":  east,
        "outputFormat": "GTiff",
        "API_Key": _get_api_key(),
    }
    return API_BASE + "?" + urllib.parse.urlencode(params)


# ── Grille en km Mercator ────────────────────────────────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    """Bbox en EPSG:3857 (mètres) → liste de (x_km, y_km)."""
    step = DALLE_KM * 1000
    x_start = int(x1 // step)
    x_end   = int(x2 // step)
    y_start = int(y1 // step)
    y_end   = int(y2 // step)
    return [(x_km, y_km)
            for x_km in range(x_start, x_end + 1)
            for y_km in range(y_start, y_end + 1)]


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """bbox_natif en EPSG:3857 — c'est le pipeline qui le passe correctement
    depuis _get_transformer(CRS_NATIF, ...)."""
    if not _get_api_key():
        return None
    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = bbox_natif
    dalles = {}
    for x_km, y_km in dalles_pour_bbox(x1, y1, x2, y2):
        dalles[dalle_filename(x_km, y_km)] = dalle_url(x_km, y_km)
    if len(dalles) > 50:
        print(f"  ⚠ {len(dalles)} tiles → OT non-academic rate limit is 50/24h. "
              f"Reduce the bbox.")
    print(f"  US 3DEP: {len(dalles)} tile(s) generated (km Mercator grid, {DATASET})")
    return dalles


# ── Hook post-download : reproject NAD83 -> Mercator aligné sur grille ───────
_NAME_PATTERN = _re.compile(r"us3dep_[^_]+_([+-]?\d+)_([+-]?\d+)_")


def post_download(path):
    """Reprojette la tile OT (EPSG:4269 NAD83 géo) vers EPSG:3857 (Web Mercator),
    EN FORÇANT l'output sur la grille km Mercator partagée.

    Sans cet alignement strict, chaque tile a une origine légèrement différente
    (décalages ~0.2m) et le VRT mosaiqué produit des seams visibles (= effet
    quadrillage signalé par l'utilisateur).
    """
    import rasterio
    from rasterio.warp import reproject, Resampling
    from rasterio.transform import from_bounds
    from pathlib import Path
    path = Path(path)

    # Extraire (x_km, y_km) du nom pour calculer les bounds cibles exacts
    m = _NAME_PATTERN.search(path.name)
    if not m:
        print(f"  ⚠ post_download : nom non parsable {path.name}", flush=True)
        return
    x_km = int(m.group(1))
    y_km = int(m.group(2))

    # Grille cible : tile [x_km*1000, (x_km+1)*1000] × [y_km*1000, (y_km+1)*1000]
    target_left   = x_km * 1000
    target_bottom = y_km * 1000
    target_right  = target_left + 1000
    target_top    = target_bottom + 1000
    target_w      = int(1000 / RESOLUTION_M)
    target_h      = int(1000 / RESOLUTION_M)
    target_transform = from_bounds(target_left, target_bottom,
                                   target_right, target_top,
                                   target_w, target_h)

    with rasterio.open(str(path)) as src:
        if src.crs and "3857" in src.crs.to_wkt() and src.width == target_w and src.height == target_h:
            return   # idempotent
        src_data      = src.read()
        src_transform = src.transform
        src_crs       = src.crs
        src_nodata    = src.nodata
        src_dtype     = src.dtypes[0]
        src_count     = src.count

    kwargs = {
        "driver":     "GTiff",
        "height":     target_h,
        "width":      target_w,
        "count":      src_count,
        "dtype":      src_dtype,
        "crs":        rasterio.CRS.from_epsg(3857),
        "transform":  target_transform,
        "nodata":     src_nodata,
        "compress":   "deflate", "predictor": 2, "tiled": True,
        "blockxsize": 256, "blockysize": 256,
    }
    tmp = path.with_suffix(".reproj.tif")
    with rasterio.open(str(tmp), "w", **kwargs) as dst:
        for i in range(src_count):
            reproject(source=src_data[i],
                      destination=rasterio.band(dst, i + 1),
                      src_transform=src_transform, src_crs=src_crs,
                      dst_transform=target_transform,
                      dst_crs=rasterio.CRS.from_epsg(3857),
                      src_nodata=src_nodata, dst_nodata=src_nodata,
                      resampling=Resampling.bilinear)
    os.replace(str(tmp), str(path))
