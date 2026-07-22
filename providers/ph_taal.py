# providers/ph_taal.py — Philippines (volcan Taal), DTM 1 m LiDAR (UP TCAGP / DREAM)
#
# Source : University of the Philippines TCAGP — Phil-LiDAR / DREAM open data,
#   « Taal Open LiDAR » (zone d'environ 20 km autour du volcan Taal seulement).
#   Portail : https://phillidar-dad.github.io/taal-open-lidar.html
#   Grille  : https://phillidar-dad.github.io/data/taal-20km-grid.js  (GeoJSON)
#   Tuiles  : https://phil-lidar-taal-s3.s3.us-east-2.amazonaws.com/Taal_DTM/<GRIDREF>_DTM.tif
#
# Paradigme : index statique (grille GeoJSON) → GeoTIFF direct par tuile (comme
#   de_bayern/gb_scotland). La grille liste des tuiles 1 km avec MINX/MINY (UTM)
#   + GRIDREF (« E303N1550 ») + un flag DTM ; l'URL S3 se dérive du GRIDREF.
#   - CRS natif EPSG:32651 (WGS84 / UTM 51N).
#   - Résolution 1 m, dalle 1×1 km (le GeoTIFF fait 1100×1100 : ~50 px de recouvrement).
#   - GeoTIFF Float32, nodata −3.4e38 (porté par le tag). Pas de post_fetch.
#   - COUVERTURE LOCALE : le pourtour du volcan Taal, PAS le pays. Marqué comme tel.
#   - Licence : open data UP TCAGP (attribution DREAM/Phil-LiDAR).
#
# Self-contained : stdlib uniquement.

import json
import re
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Philippines (volcan Taal) — DTM 1 m (UP TCAGP, LiDAR)"
CODE       = "ph-taal"
COUNTRY    = "ph"
LICENSE    = "Open data — UP TCAGP / DREAM (Phil-LiDAR), attribution"
DOC_URL    = "https://phillidar-dad.github.io/taal-open-lidar.html"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:32651"         # WGS84 / UTM 51N
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000 (nominal ; tif 1100²)
SEUIL_DALLE_VALIDE = 100_000


# ── Endpoints ────────────────────────────────────────────────────────────────
GRID_JS  = "https://phillidar-dad.github.io/data/taal-20km-grid.js"
DTM_BASE = "https://phil-lidar-taal-s3.s3.us-east-2.amazonaws.com/Taal_DTM"
HTTP_UA  = "lidar2map/1.0 (PH Taal)"

# Exemple réel pour le test de disjonction intra-pays (nommage non-formule).
SAMPLE_DALLE = "taal_dtm1_303_1550.tif"


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"taal_dtm1_{int(x_km)}_{int(y_km)}.tif"


def subdir_from_name(nom):
    m = re.match(r"taal_dtm1_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("PH-Taal : URL via GRIDREF de la grille → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("PH-Taal : intersection via la grille → discover_dalles()")


# ── Index (grille GeoJSON, téléchargée une fois, cachée) ─────────────────────
def _construire_index(cache_path):
    """{'<E_km>_<N_km>': gridref} pour les tuiles ayant un DTM. La grille est un
    GeoJSON servi comme `var taal20kmGrid = {...};`. Caché. None si échec réseau."""
    if cache_path.exists():
        try:
            idx = json.loads(cache_path.read_text(encoding="utf-8"))
            if idx:
                return idx
        except Exception:
            pass
    print("  PH Taal: downloading the tile grid (once)...", flush=True)
    try:
        req = urllib.request.Request(GRID_JS, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            texte = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  ERROR PH Taal grid: {type(e).__name__}: {e}")
        return None
    m = re.search(r"=\s*(\{.*\})\s*;?\s*$", texte, re.S)
    if not m:
        return None
    try:
        gj = json.loads(m.group(1))
    except Exception:
        return None
    index = {}
    for feat in gj.get("features", []):
        p = feat.get("properties", {})
        if not p.get("DTM"):
            continue
        gref = p.get("GRIDREF")
        try:
            e_km = int(round(float(p["MINX"]) / 1000))
            n_km = int(round(float(p["MINY"]) / 1000))
        except Exception:
            continue
        if gref:
            index[f"{e_km}_{n_km}"] = gref
    if not index:
        return None
    try:
        cache_path.write_text(json.dumps(index), encoding="utf-8")
    except Exception:
        pass
    print(f"  PH Taal: {len(index)} DTM tile(s) indexed")
    return index


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{taal_dtm1_<E>_<N>.tif: url_tif} pour les tuiles 1 km intersectant
    bbox_natif (EPSG:32651)."""
    if bbox_natif is None:
        return {}
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    index = _construire_index(cache_path)
    if index is None:
        return None

    x1, y1, x2, y2 = bbox_natif
    dalles = {}
    for key, gref in index.items():
        e_km, n_km = (int(v) for v in key.split("_"))
        tx1, ty1 = e_km * 1000, n_km * 1000
        tx2, ty2 = tx1 + 1000, ty1 + 1000
        if tx2 <= x1 or tx1 >= x2 or ty2 <= y1 or ty1 >= y2:
            continue
        dalles[dalle_filename(e_km, n_km)] = f"{DTM_BASE}/{gref}_DTM.tif"
    print(f"  PH Taal (DTM 1m, ~volcan): {len(dalles)} tile(s) in the bbox")
    return dalles
