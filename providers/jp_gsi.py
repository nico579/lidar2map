# providers/jp_gsi.py — Japon, DEM 5 m via tuiles d'altitude GSI (標高タイル)
#
# Source : Geospatial Information Authority of Japan (GSI / 国土地理院) —
#   service de tuiles d'altitude « 標高タイル » (DEM5A, dérivé LiDAR aérien).
#   Doc : https://maps.gsi.go.jp/development/ichiran.html#dem
#
# Paradigme : pyramide de tuiles XYZ (web-mercator z/x/y) de VALEURS en TEXTE
#   — chaque tuile = 256×256 altitudes en CSV (« e » = nodata), accès libre,
#   SANS compte (contrairement au download FGD GML qui exige un compte).
#   On évite ainsi le format JPGIS GML + l'inscription.
#
#   1. discover_dalles : énumère les tuiles z=15 (DEM5A ≈ 5 m) couvrant la bbox
#      web-mercator, renvoie {jp_dem5a_<z>_<x>_<y>.tif: url_txt}.
#   2. post_fetch : chaque .txt (256×256 CSV) → GeoTIFF EPSG:3857, géoréférencé
#      depuis z/x/y (bornes de la tuile web-mercator). « e » → nodata −9999.
#
#   - CRS de travail EPSG:3857 (le schéma de tuiles). Distorsion mercator à la
#     latitude du Japon (~×1,22) — acceptée, comme us-3dep/us-tnm.
#   - Couverture DEM5A : PARTIELLE (cours d'eau, plaines, zones habitées,
#     montagnes moyennes/hautes) — les tuiles hors couverture renvoient 404 et
#     sont simplement absentes. DEM10B (10 m) couvre tout le pays mais n'est pas
#     ciblé ici (on privilégie le 5 m).
#   - Licence : 国土地理院コンテンツ利用規約 (réutilisation libre avec mention
#     « 出典：国土地理院 »).
#
# Self-contained : stdlib uniquement (numpy/rasterio requis au runtime pour post_fetch).

import math
import re


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Japon — DEM 5m (GSI 標高タイル DEM5A, LiDAR)"
CODE       = "jp-gsi"
COUNTRY    = "jp"
LICENSE    = "GSI コンテンツ利用規約 — réutilisation libre (出典：国土地理院)"
DOC_URL    = "https://maps.gsi.go.jp/development/ichiran.html#dem"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3857"          # Web Mercator (schéma de tuiles XYZ)
RESOLUTION_M       = 5                     # DEM5A ≈ 5 m (z=15)
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 200 (nominal)
SEUIL_DALLE_VALIDE = 20_000

ZOOM       = 15                            # niveau XYZ de DEM5A
LAYER      = "dem5a"
TUILE_PX   = 256
URL_TMPL   = "https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.txt"
HTTP_UA    = "lidar2map/1.0 (GSI dem5a)"

# Constantes web-mercator
_R    = 20037508.342789244                 # demi-circonférence (m)
_STEP = 2 * _R / (2 ** ZOOM)               # côté d'une tuile z=15 (m)

# Étendue Japon en EPSG:3857 (clippe la grille de tuiles).
COVERAGE_EXTENT = (13_580_000, 2_750_000, 17_150_000, 5_790_000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(z, x, y):
    return f"jp_dem5a_{z}_{x}_{y}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km)}"


def subdir_from_name(nom):
    m = re.match(r"jp_dem5a_\d+_(\d+)_", nom)
    return f"{int(m.group(1)) // 64}" if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("JP : tuiles XYZ → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("JP : tuiles XYZ → discover_dalles()")


# ── Découverte : tuiles XYZ z=15 couvrant la bbox web-mercator ───────────────
def _tile_bounds(z, x, y):
    """Bornes web-mercator (left, bottom, right, top) de la tuile z/x/y."""
    step = 2 * _R / (2 ** z)
    left = -_R + x * step
    top = _R - y * step
    return left, top - step, left + step, top


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{jp_dem5a_z_x_y.tif: url_txt} pour les tuiles DEM5A z=15 de bbox_natif
    (EPSG:3857). Le contenu est un CSV 256×256 → GeoTIFF par post_fetch ; les
    tuiles hors couverture DEM5A renvoient 404 (écartées par le pipeline)."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  JP-GSI: bbox outside Japan extent")
        return {}

    tx0 = int((ix1 + _R) / _STEP)
    tx1 = int((ix2 + _R) / _STEP)
    ty0 = int((_R - iy2) / _STEP)        # y croît vers le sud
    ty1 = int((_R - iy1) / _STEP)
    dalles = {}
    for x in range(tx0, tx1 + 1):
        for y in range(ty0, ty1 + 1):
            dalles[dalle_filename(ZOOM, x, y)] = URL_TMPL.format(
                layer=LAYER, z=ZOOM, x=x, y=y)
    print(f"  JP-GSI (DEM5A 5 m): {len(dalles)} z{ZOOM} tile(s) in the bbox "
          f"(partial DEM5A coverage, tiles outside zone ignored at download)")
    return dalles


# ── Hook post_fetch : CSV 256×256 → GeoTIFF ──────────────────────────────────
def post_fetch(chemin):
    """Convertit en place une tuile GSI .txt (256×256 altitudes CSV, « e » =
    nodata) en GeoTIFF Float32 EPSG:3857. Détection par contenu (pas TIFF) ;
    géoréférencement depuis z/x/y lus dans le nom de fichier."""
    from pathlib import Path
    chemin = Path(chemin)
    try:
        with open(chemin, "rb") as fh:
            tete = fh.read(4)
    except OSError:
        return
    if tete[:2] in (b"II", b"MM"):
        return  # déjà un GeoTIFF

    m = re.match(r"jp_dem5a_(\d+)_(\d+)_(\d+)", chemin.name)
    if not m:
        return  # nom inattendu → laisser le validateur trancher
    z, x, y = int(m.group(1)), int(m.group(2)), int(m.group(3))

    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds

    txt = chemin.read_text(encoding="ascii", errors="replace")
    lignes = [ln for ln in txt.splitlines() if ln.strip()]
    grid = np.full((TUILE_PX, TUILE_PX), -9999.0, dtype=np.float32)
    for r, ln in enumerate(lignes[:TUILE_PX]):
        for c, val in enumerate(ln.split(",")[:TUILE_PX]):
            if val and val != "e":
                try:
                    grid[r, c] = float(val)
                except ValueError:
                    pass

    left, bottom, right, top = _tile_bounds(z, x, y)
    transform = from_bounds(left, bottom, right, top, TUILE_PX, TUILE_PX)
    tmp = chemin.with_suffix(".tif_tmp")
    with rasterio.open(str(tmp), "w",
                       driver="GTiff", height=TUILE_PX, width=TUILE_PX,
                       count=1, dtype="float32",
                       crs=rasterio.CRS.from_epsg(3857),
                       transform=transform, nodata=-9999,
                       compress="deflate", predictor=2, tiled=True) as dst:
        dst.write(grid, 1)
    tmp.replace(chemin)
