# providers/se_lantmateriet.py — Suède, Laserdata NH 1m via Lantmäteriet
#
# Source : Lantmäteriet (Swedish mapping authority)
#   https://www.lantmateriet.se/en/geodata/geodata-products/product-list/laser-data/
#
# Paradigme : index JSON → URL directe ZIP contenant un fichier LAZ.
#   - CRS natif EPSG:3006 (SWEREF99 TM)
#   - Résolution ~1m (Laserdata NH, densité ≥ 0.5 pts/m²)
#   - Tuiles 2500×2500 m, nommées par coin SW (E_m / N_m)
#   - Distribution : ZIP par tuile contenant un .laz
#   - Licence : CC0 (domaine public)
#   - NÉCESSITE post_fetch : dézip + conversion LAZ → GeoTIFF (PDAL ou laspy)
#
# post_fetch chaîne : .zip → dézip → .laz → PDAL/laspy → .tif (float32, 1m)
#
# Self-contained : stdlib uniquement (PDAL / laspy requis au runtime uniquement).

import json
import re
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Suède — Laserdata NH 1m (Lantmäteriet)"
CODE       = "se-lantmateriet"
COUNTRY    = "se"
LICENSE    = "CC0 — Lantmäteriet"
DOC_URL    = "https://www.lantmateriet.se/en/geodata/geodata-products/product-list/laser-data/"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3006"          # SWEREF99 TM
RESOLUTION_M       = 1.0
DALLE_KM           = 2.5                  # tuiles 2500×2500 m
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 2500
SEUIL_DALLE_VALIDE = 500_000              # après dézip + conversion


# ── Endpoints ────────────────────────────────────────────────────────────────
# API Lantmäteriet Laserdata NH — index JSON paginé
API_BASE = "https://api.lantmateriet.se/distribution/products/v2"
PRODUCT  = "laserdata"
HTTP_UA  = "lidar2map/1.0 (Lantmateriet Laserdata)"

# Étendue Suède en EPSG:3006
COVERAGE_EXTENT = (260000, 6133000, 920000, 7700000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    """Nom interne basé sur le coin SW en km (grille 2.5 km)."""
    return f"se_nh_{int(x_km*10):06d}_{int(y_km*10):07d}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km):04d}"


def subdir_from_name(nom):
    m = re.match(r"se_nh_(\d+)_", nom)
    return str(int(m.group(1)) // 10 // 10 * 10) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("SE : URL via API index → utiliser discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("SE : utiliser discover_dalles()")


# ── Découverte via API Lantmäteriet ─────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Retourne {nom: url_zip} pour les tuiles LAZ intersectant bbox_natif."""
    if bbox_natif is None:
        return {}
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    x1, y1, x2, y2 = bbox_natif
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  Suède : bbox hors étendue SWEREF99 TM")
        return {}

    # Grille synthétique 2500m
    step = int(DALLE_KM * 1000)
    xs = range(int(ix1 // step) * step, int(ix2 // step + 1) * step, step)
    ys = range(int(iy1 // step) * step, int(iy2 // step + 1) * step, step)
    tuiles = [(x, y) for x in xs for y in ys]

    # Cache existant
    dalles = {}
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            dalles = {k: v for k, v in cached.items()
                      if any(f"_{x}_{y}" in k or f"_{x//1000}" in k
                             for x, y in tuiles)}
            if dalles:
                print(f"  Suède : {len(dalles)} dalle(s) depuis cache")
                return dalles
        except Exception:
            pass

    # Requête API par bbox SWEREF99 TM
    print(f"  Lantmäteriet API : query bbox {ix1},{iy1},{ix2},{iy2}...", flush=True)
    params = urllib.parse.urlencode({
        "bbox":   f"{ix1},{iy1},{ix2},{iy2}",
        "crs":    "EPSG:3006",
        "limit":  500,
    }) if False else ""  # API nécessite inscription → fallback grille

    # Fallback : URL synthétique depuis la grille (pattern Lantmäteriet)
    # Format URL : https://download.lantmateriet.se/laserdata/nh/<E>_<N>.zip
    DOWNLOAD_BASE = "https://download.lantmateriet.se/laserdata/nh"
    for x, y in tuiles:
        # Nommage Lantmäteriet : coin SW en m, pas de padding standard connu
        # À valider en testant l'URL réelle — plusieurs patterns possibles
        nom_interne = dalle_filename(x / 1000, y / 1000)
        # URL synthétique (pattern à valider)
        url = f"{DOWNLOAD_BASE}/{x}_{y}.zip"
        dalles[nom_interne] = url

    print(f"  Suède : {len(dalles)} tuile(s) (URLs synthétiques — à valider)")
    try:
        cache_path.write_text(json.dumps(dalles), encoding="utf-8")
    except Exception:
        pass
    return dalles


# ── Hook post_fetch : dézip + conversion LAZ → GeoTIFF ───────────────────────
def post_fetch(chemin):
    """Convertit une tuile LAZ zippée en GeoTIFF DTM 1m.

    Pipeline :
      1. Dézip du .zip → extrait le .laz
      2. Conversion LAZ → GeoTIFF via PDAL (préféré) ou laspy+scipy (fallback)
      3. Suppression du .zip et du .laz intermédiaire

    PDAL doit être installé (conda install -c conda-forge pdal python-pdal).
    Fallback laspy+scipy : pip install laspy scipy (plus lent, ~10× plus lent sur gros nuages).
    """
    chemin = Path(chemin)
    dossier = chemin.parent

    # ── Étape 1 : dézip ──────────────────────────────────────────────────────
    import zipfile
    laz_path = None
    if chemin.suffix.lower() == ".zip":
        with zipfile.ZipFile(chemin) as z:
            members = [m for m in z.namelist() if m.lower().endswith(".laz")]
            if not members:
                raise ValueError(f"Aucun fichier .laz dans {chemin.name}")
            z.extract(members[0], dossier)
            laz_path = dossier / members[0]
        chemin.unlink(missing_ok=True)
    elif chemin.suffix.lower() == ".laz":
        laz_path = chemin
    else:
        return  # déjà un GeoTIFF ou autre — ne rien faire

    tif_path = laz_path.with_suffix(".tif")

    # ── Étape 2 : LAZ → GeoTIFF via PDAL ────────────────────────────────────
    try:
        _laz_to_tif_pdal(laz_path, tif_path)
    except Exception as e_pdal:
        # Fallback laspy + scipy
        try:
            _laz_to_tif_laspy(laz_path, tif_path)
        except Exception as e_laspy:
            raise RuntimeError(
                f"LAZ→GeoTIFF échoué.\n"
                f"  PDAL : {e_pdal}\n"
                f"  laspy: {e_laspy}\n"
                f"  Installer PDAL : conda install -c conda-forge pdal python-pdal"
            )

    # ── Étape 3 : nettoyage + renommage vers chemin attendu ──────────────────
    laz_path.unlink(missing_ok=True)
    # Renommer vers le chemin original (avec .tif) si différent
    target = chemin.with_suffix(".tif")
    if tif_path != target:
        tif_path.rename(target)


def _laz_to_tif_pdal(laz_path, tif_path):
    """Conversion LAZ → GeoTIFF DTM via PDAL (pipeline JSON)."""
    import subprocess, json as _json, tempfile
    pipeline = {
        "pipeline": [
            str(laz_path),
            {
                "type":   "filters.range",
                "limits": "Classification[2:2]"  # ground points only
            },
            {
                "type":        "writers.gdal",
                "filename":    str(tif_path),
                "resolution":  RESOLUTION_M,
                "output_type": "min",
                "gdaldriver":  "GTiff",
                "gdalopts":    "COMPRESS=DEFLATE,PREDICTOR=2,TILED=YES",
                "nodata":      -9999,
            }
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                     delete=False, encoding="utf-8") as f:
        _json.dump(pipeline, f)
        pipeline_path = f.name
    try:
        subprocess.check_call(["pdal", "pipeline", pipeline_path],
                              timeout=300)
    finally:
        Path(pipeline_path).unlink(missing_ok=True)


def _laz_to_tif_laspy(laz_path, tif_path):
    """Conversion LAZ → GeoTIFF DTM via laspy + scipy (fallback sans PDAL).
    ~10× plus lent que PDAL sur les grands nuages (>10M points).
    """
    import laspy
    import numpy as np
    from scipy.interpolate import griddata

    las = laspy.read(str(laz_path))
    # Filtrer les points sol (classification 2)
    mask = las.classification == 2
    if mask.sum() < 100:
        # Pas de points sol → utiliser tous les points
        mask = np.ones(len(las.x), dtype=bool)

    xs = las.x[mask]
    ys = las.y[mask]
    zs = las.z[mask]

    # Grille régulière 1m
    x_min, x_max = float(xs.min()), float(xs.max())
    y_min, y_max = float(ys.min()), float(ys.max())
    nx = int((x_max - x_min) / RESOLUTION_M) + 1
    ny = int((y_max - y_min) / RESOLUTION_M) + 1
    grid_x, grid_y = np.meshgrid(
        np.linspace(x_min, x_max, nx),
        np.linspace(y_min, y_max, ny)
    )
    grid_z = griddata((xs, ys), zs, (grid_x, grid_y), method="linear")
    grid_z = np.flipud(grid_z.astype(np.float32))

    # Écriture GeoTIFF
    import rasterio
    from rasterio.transform import from_bounds
    transform = from_bounds(x_min, y_min, x_max, y_max, nx, ny)
    crs = rasterio.CRS.from_epsg(3006)
    with rasterio.open(str(tif_path), "w",
                       driver="GTiff", height=ny, width=nx,
                       count=1, dtype="float32", crs=crs,
                       transform=transform, nodata=-9999,
                       compress="deflate", predictor=2, tiled=True) as dst:
        dst.write(grid_z, 1)
