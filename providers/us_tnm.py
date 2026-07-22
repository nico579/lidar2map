# providers/us_tnm.py — USA, USGS 3DEP via TNMAccess (direct S3, sans compte)
#
# Source : USGS 3D Elevation Program (3DEP), accédé via l'API publique
# TNMAccess (The National Map). Pas de compte requis (contrairement à us-3dep
# qui passe par OpenTopography).
#
# Pipeline :
#   1. discover_dalles : GET tnmaccess.nationalmap.gov/api/v1/products
#      → JSON listant les tiles DEM 1m intersectant la bbox WGS84
#   2. Téléchargement direct depuis prd-tnm.s3.amazonaws.com (publique)
#   3. post_download : reproject UTM <zone> → EPSG:3857 (Web Mercator)
#
# Caractéristiques des tiles USGS 1m :
#   - Format : COG GeoTIFF Float32
#   - Taille : ~10000×10000 px = 10×10 km à 1m natif
#   - Volume : 150-300 Mo par tile (compressed)
#   - CRS : UTM zone projetée (10-19N pour continental USA, variable)
#   - Naming : USGS_1M_<utm_zone>_x<E_div_10k>y<N_div_10k>_<projet>.tif
#
# Compromis vs us-3dep :
#   + Accès libre (pas de compte OT requis)
#   + Resolution native 1m (au lieu de 10m USGS10m OT free tier)
#   + Pas de rate limit visible (S3 direct)
#   - Tiles très volumineuses (150-300 Mo chacune)
#   - Pour 1 km² archéo, on télécharge 10×10 km autour → overshoot 100x

import os
import json
import urllib.error
import urllib.parse
import urllib.request


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "USA — USGS 3DEP 1 m LiDAR (TNMAccess, sans compte)"
CODE       = "us-tnm"
COUNTRY    = "us"
LICENSE    = "Public domain (USGS / TNM)"
DOC_URL    = "https://www.usgs.gov/3d-elevation-program"
APIKEY_REQUISE = False


# ── Géométrie ────────────────────────────────────────────────────────────────
# CRS_NATIF Web Mercator — uniforme pour tout USA. Les tiles UTM (zone variable
# 10-19N selon longitude) sont reprojettées au post_download.
CRS_NATIF          = "EPSG:3857"
RESOLUTION_M       = 1                  # 1 m natif
DALLE_KM           = 10                 # tiles TNM = 10x10 km
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 10000 px
SEUIL_DALLE_VALIDE = 200_000            # tuiles fenêtrées (pas les 295 Mo entiers)
# Les tuiles 3DEP StagedProducts sont des COG → lecture FENÊTRÉE /vsicurl/ sur
# la bbox (le pipeline reprojette la bbox vers l'UTM du COG, puis post_download
# UTM->3857). Évite de rapatrier 100-300 Mo par tuile 10×10 km pour une zone archéo.
COG_WINDOWED       = True


# ── Endpoints ────────────────────────────────────────────────────────────────
TNM_API = "https://tnmaccess.nationalmap.gov/api/v1/products"
DATASET = "Digital Elevation Model (DEM) 1 meter"


# ── Nommage (extrait depuis le title TNM) ────────────────────────────────────
# TNM titles : "USGS 1 Meter 10 x54y528 WA_KingCounty_2021_B21"
import re as _re
_TITLE_PATTERN = _re.compile(r"USGS\s+1\s+Meter\s+(\d+)\s+x(\d+)y(\d+)")
# Exemple réel pour le test de disjonction intra-pays (nommage non-formule).
SAMPLE_DALLE = "usgs_1m_10_x54y528.tif"


def _filename_from_title(title):
    """Convention : usgs_1m_<zone>_x<E>y<N>.tif."""
    m = _TITLE_PATTERN.search(title or "")
    if m:
        return f"usgs_1m_{m.group(1)}_x{m.group(2)}y{m.group(3)}.tif"
    # Fallback : sanitize le title
    safe = _re.sub(r"\W+", "_", (title or "unknown")).strip("_")[:60]
    return f"usgs_1m_{safe}.tif"


def dalle_filename(x_km, y_km):
    raise NotImplementedError(
        "TNM nomme par projet+UTM grid, non dérivable d'une grille km arbitraire. "
        "Utiliser discover_dalles().")


def subdir_from_name(nom):
    # Sous-dossier par UTM zone (10, 11, 12, ...)
    m = _re.match(r"usgs_1m_(\d+)_", nom)
    return f"utm{m.group(1)}" if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("Voir discover_dalles().")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("Voir discover_dalles().")


# ── Découverte via TNM API ───────────────────────────────────────────────────
HTTP_UA = "lidar2map/1.0 (TNMAccess)"


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Query TNM API pour les tiles DEM 1m intersectant bbox_wgs84.

    bbox_wgs84 : (lon_min, lat_min, lon_max, lat_max). TNM accepte bbox WGS84.
    bbox_natif : ignoré (TNM ne sait que WGS84 pour les requêtes).
    cache_path : JSON cache des résultats API.
    """
    if bbox_wgs84 is None:
        return {}
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84

    from pathlib import Path
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Pagination TNM : max items par page = 50
    all_items = []
    offset = 0
    max_per_page = 50
    print(f"  TNM API : query bbox {lon_min:.4f},{lat_min:.4f},{lon_max:.4f},{lat_max:.4f}...",
          flush=True)
    while True:
        params = urllib.parse.urlencode({
            "datasets": DATASET,
            "bbox":     f"{lon_min},{lat_min},{lon_max},{lat_max}",
            "max":      max_per_page,
            "offset":   offset,
        })
        url = f"{TNM_API}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
            data = json.loads(raw)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read(300).decode("utf-8", "replace").strip()
            except Exception:
                pass
            print(f"  ERROR TNM API HTTP {e.code} {e.reason}"
                  + (f": {body[:200]}" if body else ""))
            if e.code in (429, 503):
                print("  TNM: rate limit or service unavailable, retry in a few minutes.")
            elif e.code == 403:
                print("  TNM: access denied (IP blocked or restricted service).")
            return None
        except json.JSONDecodeError as e:
            preview = ""
            try:
                preview = raw[:200].decode("utf-8", "replace")
            except Exception:
                pass
            print(f"  ERROR TNM API: non-JSON response ({e})"
                  + (f"\n  Preview: {preview}" if preview else ""))
            # Panne backend USGS : le serveur Lambda renvoie une erreur non-JSON
            if preview and "errorMessage" in preview and "Connection aborted" in preview:
                print("  TNM: USGS backend outage (connection aborted server-side).")
                print("  → Retry in a few minutes: https://apps.nationalmap.gov/services-checker/")
            return None
        except Exception as e:
            print(f"  ERROR TNM API: {type(e).__name__}: {e}")
            return None
        items = data.get("items", [])
        all_items.extend(items)
        total = data.get("total", len(items))
        if offset + len(items) >= total or not items:
            break
        offset += len(items)

    if not all_items:
        print("  TNM: no 1m DEM tile found for this bbox.")
        return {}

    try:
        cache_path.write_text(json.dumps({"items": all_items}), encoding="utf-8")
    except Exception:
        pass

    dalles = {}
    total_size = 0
    for it in all_items:
        title = it.get("title", "")
        url_d = it.get("downloadURL", "")
        if not url_d or not url_d.endswith(".tif"):
            continue
        nom = _filename_from_title(title)
        dalles[nom] = url_d
        total_size += int(it.get("sizeInBytes") or 0)

    size_mb = total_size / 1e6
    print(f"  TNM: {len(dalles)} 1m DEM tile(s) selected "
          f"(~{size_mb:.0f} MB total)")
    if size_mb > 1000:
        print(f"  ⚠ Large volume ({size_mb:.0f} MB). USGS 1m tiles are "
              f"10×10 km, a lot of data for a small archaeological area.")
    return dalles


# ── Hook post-download : reproject UTM -> EPSG:3857 aligné sur grille ────────
def post_download(path):
    """Reprojette la tile TNM (UTM zone, EPSG:26910/11/12/...) vers EPSG:3857.

    Le pipeline lidar2map a besoin d'un CRS unique (déclaré CRS_NATIF=3857).
    Sans cette étape, le VRT mixant des tiles de différentes zones UTM échoue.

    Reprojection alignée sur la grille km Mercator pour éviter les seams
    quand plusieurs tiles voisines sont mosaiquées.
    """
    import rasterio
    from rasterio.warp import reproject, Resampling, transform_bounds
    from rasterio.transform import from_bounds
    from pathlib import Path
    path = Path(path)

    with rasterio.open(str(path)) as src:
        if src.crs and "3857" in src.crs.to_wkt():
            return   # idempotent
        src_crs    = src.crs
        src_data   = src.read()
        src_trans  = src.transform
        src_nodata = src.nodata
        src_dtype  = src.dtypes[0]
        src_count  = src.count
        src_bounds = src.bounds

    # Bounds en Mercator alignés sur le m près (sans forcer multiple de 1000m
    # parce qu'un tile TNM de 10 km ne fait PAS 10 km en Mercator après reproj
    # — distortion ~10-30% selon la latitude)
    merc_bounds = transform_bounds(src_crs, "EPSG:3857", *src_bounds, densify_pts=21)
    left, bottom, right, top = merc_bounds
    # Snap les bords sur des multiples de RESOLUTION_M
    res = RESOLUTION_M
    left   = (left   // res) * res
    bottom = (bottom // res) * res
    right  = ((right  // res) + 1) * res
    top    = ((top    // res) + 1) * res
    width  = int(round((right - left) / res))
    height = int(round((top - bottom) / res))
    target_transform = from_bounds(left, bottom, right, top, width, height)

    kwargs = {
        "driver":     "GTiff",
        "height":     height,
        "width":      width,
        "count":      src_count,
        "dtype":      src_dtype,
        "crs":        rasterio.CRS.from_epsg(3857),
        "transform":  target_transform,
        "nodata":     src_nodata,
        "compress":   "deflate", "predictor": 2, "tiled": True,
        "blockxsize": 512, "blockysize": 512,
    }
    tmp = path.with_suffix(".reproj.tif")
    with rasterio.open(str(tmp), "w", **kwargs) as dst:
        for i in range(src_count):
            reproject(source=src_data[i],
                      destination=rasterio.band(dst, i + 1),
                      src_transform=src_trans, src_crs=src_crs,
                      dst_transform=target_transform,
                      dst_crs=rasterio.CRS.from_epsg(3857),
                      src_nodata=src_nodata, dst_nodata=src_nodata,
                      resampling=Resampling.bilinear)
    os.replace(str(tmp), str(path))
