# providers/au_ga.py — Australie (national), DEM 5 m dérivé LiDAR via Geoscience Australia
#
# Source : Geoscience Australia — "DEM of Australia derived from LiDAR 5 m Grid"
#   Service : https://services.ga.gov.au/gis/rest/services/DEM_LiDAR_5m_2025/MapServer
#   Fiche : https://ecat.ga.gov.au/geonetwork/srv/.../22be4b55-2466-4320-e053-10a3070a5236
#
# Couverture : mosaïque de 236 levés LiDAR (2001-2015), ~245 000 km² (≈3 % du
#   continent), dispersés sur le littoral + bassin Murray-Darling. Complète QLD
#   (au-qld 0,5 m) et NSW (au-nsw 5 m) en ouvrant les AUTRES états (SA, VIC, TAS,
#   WA, ACT…) là où GA a des données, à l'échelle paysage (5 m).
#
# Paradigme : WCS 1.0.0 GetCoverage par dalle (comme at_tirol/gb_england), MAIS
#   le service ArcGIS n'accepte QUE son CRS natif EPSG:4283 (GDA94 géographique)
#   en requête — pas de reprojection serveur (3857/4326 → HTTP 400). On requête
#   donc en degrés, puis post_download reprojette en EPSG:3857 (comme us_tnm,
#   CRS de travail uniforme pour le continent). FORMAT=GeoTIFF, COVERAGE="1".
#
#   - CRS natif (pipeline) EPSG:3857 (Web Mercator) ; tuiles servies en 4283.
#   - Résolution native 5 m (~5,5e-5° lon / 5,16e-5° lat).
#   - Licence CC BY 4.0 — Commonwealth of Australia / Geoscience Australia.
#   - Pas de clé, pas de compte.
#
# Self-contained : stdlib (pyproj/rasterio requis au runtime pour conv./reproj).

import os


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Australie (national) — DEM 5 m LiDAR (Geoscience Australia)"
CODE       = "au-ga"
COUNTRY    = "au"
LICENSE    = "CC BY 4.0 — Commonwealth of Australia (Geoscience Australia)"
DOC_URL    = "https://ecat.ga.gov.au/geonetwork/srv/eng/catalog.search#/metadata/22be4b55-2466-4320-e053-10a3070a5236"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3857"          # Web Mercator (uniforme continent ; tuiles 4283 reprojetées)
RESOLUTION_M       = 5
DALLE_KM           = 10                    # dalle 10 km → ~1600 px (sous la limite WCS)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000 (nominal)
SEUIL_DALLE_VALIDE = 100_000

# Service WCS et résolution native (degrés, depuis DescribeCoverage)
WCS_URL      = "https://services.ga.gov.au/gis/services/DEM_LiDAR_5m_2025/MapServer/WCSServer"
COVERAGE_ID  = "1"                         # nom de coverage WCS 1.0.0
NATIVE_DEG_X = 5.5063478185957097e-05      # ~5 m en longitude
NATIVE_DEG_Y = 5.16012325277870332e-05     # ~5 m en latitude
MAX_WH       = 2000                        # garde-fou taille image WCS

# Enveloppe de couverture en WGS84 (depuis DescribeCoverage) — clippe la grille.
COVERAGE_LONLAT = (114.0986, -43.4628, 153.6775, -9.8661)   # (lon_min, lat_min, lon_max, lat_max)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"au_ga5m_{int(x_km):+06d}_{int(y_km):+06d}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km):+06d}"


def subdir_from_name(nom):
    import re
    m = re.match(r"au_ga5m_([+-]?\d+)_", nom)
    return f"{int(m.group(1)):+06d}" if m else None


# ── Transformateurs (lazy) ───────────────────────────────────────────────────
_TF_M2D = None
_TF_D2M = None


def _to_deg(x, y):
    global _TF_M2D
    if _TF_M2D is None:
        from pyproj import Transformer
        _TF_M2D = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    return _TF_M2D.transform(x, y)


def _to_merc(lon, lat):
    global _TF_D2M
    if _TF_D2M is None:
        from pyproj import Transformer
        _TF_D2M = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    return _TF_D2M.transform(lon, lat)


# ── Construction URL : WCS 1.0.0 GetCoverage en EPSG:4283 ────────────────────
def dalle_url(x_km, y_km):
    """URL WCS 1.0.0 GetCoverage. La dalle est définie sur la grille 3857 (coin
    SW = x_km/y_km × 10 km) ; on convertit ses coins en lon/lat (4283) car le
    service ne sert que son CRS natif. WIDTH/HEIGHT ≈ résolution native 5 m."""
    step = DALLE_KM * 1000
    e0, n0 = x_km * step, y_km * step
    e1, n1 = e0 + step, n0 + step
    # Coins 3857 → WGS84 ; prendre l'enveloppe lon/lat
    lons, lats = [], []
    for ex, ny in ((e0, n0), (e0, n1), (e1, n0), (e1, n1)):
        lo, la = _to_deg(ex, ny)
        lons.append(lo); lats.append(la)
    lon0, lon1 = min(lons), max(lons)
    lat0, lat1 = min(lats), max(lats)
    w = max(1, min(MAX_WH, round((lon1 - lon0) / NATIVE_DEG_X)))
    h = max(1, min(MAX_WH, round((lat1 - lat0) / NATIVE_DEG_Y)))
    return (f"{WCS_URL}?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage"
            f"&COVERAGE={COVERAGE_ID}&CRS=EPSG:4283"
            f"&BBOX={lon0},{lat0},{lon1},{lat1}"
            f"&WIDTH={w}&HEIGHT={h}&FORMAT=GeoTIFF")


def dalles_pour_bbox(x1, y1, x2, y2):
    """Grille 10 km EPSG:3857 — borne haute demi-ouverte (cf. gb_england)."""
    step = DALLE_KM * 1000
    x_start, x_end = int(x1 // step), int(x2 // step)
    if x2 % step == 0 and x_end > x_start:
        x_end -= 1
    y_start, y_end = int(y1 // step), int(y2 // step)
    if y2 % step == 0 and y_end > y_start:
        y_end -= 1
    return [(x_km, y_km)
            for x_km in range(x_start, x_end + 1)
            for y_km in range(y_start, y_end + 1)]


# ── Découverte : grille clippée à l'enveloppe de couverture ──────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{nom: url_wcs} pour les dalles de bbox_natif (EPSG:3857) dans l'enveloppe
    GA. Pas d'index réseau : grille synthétique clippée. Les dalles hors des 236
    levés renvoient une erreur/tuile vide que le pipeline écarte."""
    if bbox_natif is None:
        return {}
    lo0, la0, lo1, la1 = COVERAGE_LONLAT
    cx0, cy0 = _to_merc(lo0, la0)
    cx1, cy1 = _to_merc(lo1, la1)
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  AU-GA : bbox hors de l'enveloppe Australie")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    dalles = {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
    print(f"  AU-GA (DEM 5 m) : {len(dalles)} dalle(s) WCS dans la bbox "
          f"(couverture GA dispersée — dalles hors levés ignorées au download)")
    return dalles


# ── Hook post-download : reproject EPSG:4283 → EPSG:3857 ──────────────────────
def post_download(path):
    """Reprojette la tuile WCS (GDA94 géographique 4283) vers EPSG:3857 (CRS de
    travail uniforme). Sans ça, le shading lirait des pas de grille en degrés
    (gradients faux). Snap des bords sur RESOLUTION_M (cf. us_tnm)."""
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

    merc_bounds = transform_bounds(src_crs, "EPSG:3857", *src_bounds, densify_pts=21)
    left, bottom, right, top = merc_bounds
    res = RESOLUTION_M
    left   = (left   // res) * res
    bottom = (bottom // res) * res
    right  = ((right  // res) + 1) * res
    top    = ((top    // res) + 1) * res
    width  = int(round((right - left) / res))
    height = int(round((top - bottom) / res))
    target_transform = from_bounds(left, bottom, right, top, width, height)

    kwargs = {
        "driver":     "GTiff", "height": height, "width": width,
        "count":      src_count, "dtype": src_dtype,
        "crs":        rasterio.CRS.from_epsg(3857),
        "transform":  target_transform, "nodata": src_nodata,
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
