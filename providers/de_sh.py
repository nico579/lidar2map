# providers/de_sh.py — Schleswig-Holstein (Allemagne), DGM1 1 m via index GeoJSON
#
# Source : LVermGeo SH (Landesamt für Vermessung und Geoinformation SH), OpenData.
#   Doc : https://www.schleswig-holstein.de/DE/landesregierung/ministerien-behoerden/LVERMGEOSH/Service/serviceGeobasisdaten/geodatenService_Geobasisdaten_DGM
#   Index : https://geodaten.schleswig-holstein.de/gaialight-sh/_apps/dladownload/single.php?file=DGM1_SH__Massendownload.geojson&id=4
#
# Paradigme : index spatial GeoJSON (18 685 dalles 1 km) → dalle XYZ texte brut →
#   GeoTIFF (calque de_thueringen / de_berlin ; XYZ « X Y Z » cell-centers `.50`).
#   Chaque feature porte `link_data` = l'URL de download COMPLÈTE (massen.php avec
#   file/live/km), et le nom de fichier encode E/N km + l'année de levé (variable)
#   → on prend le millésime le plus récent par dalle (champ `datum`).
#   - CRS natif EPSG:25832 (ETRS89 / UTM 32N).
#   - Résolution 1 m, dalle 1×1 km. Le download est du TEXTE (pas un ZIP).
#   - Licence : CC BY 4.0 (LVermGeo SH, GeoBasis-DE).
#   - Pas de clé, pas de compte.
#
# NB : ceci COMPLÈTE la couverture allemande (SH était noté « boutique/panier »
#   dans la roadmap ; faux, l'index GeoJSON + les URLs directes existent).
#
# Self-contained : stdlib uniquement (numpy/rasterio requis au runtime post_fetch).

import json
import re
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Schleswig-Holstein — DGM1 1 m (LVermGeo SH, XYZ)"
CODE       = "de-sh"
COUNTRY    = "de"
LICENSE    = "CC BY 4.0 — © GeoBasis-DE/LVermGeoSH"
DOC_URL    = "https://www.schleswig-holstein.de/DE/landesregierung/ministerien-behoerden/LVERMGEOSH/Service/serviceGeobasisdaten/geodatenService_Geobasisdaten_DGM"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"         # ETRS89 / UTM 32N
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000
SEUIL_DALLE_VALIDE = 100_000              # GeoTIFF 1000×1000 compressé


# ── Endpoints ────────────────────────────────────────────────────────────────
INDEX_URL = ("https://geodaten.schleswig-holstein.de/gaialight-sh/_apps/dladownload/"
             "single.php?file=DGM1_SH__Massendownload.geojson&id=4")
HTTP_UA   = "lidar2map/1.0 (SH DGM1)"

# Exemple réel pour le test de disjonction intra-pays (nommage non-formule).
SAMPLE_DALLE = "sh_dgm1_425_6002.tif"


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"sh_dgm1_{int(x_km)}_{int(y_km)}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km)}"


def subdir_from_name(nom):
    m = re.match(r"sh_dgm1_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("SH : URL via index GeoJSON → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
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


# ── Index GeoJSON (téléchargé une fois, caché) ───────────────────────────────
_FILE_RE = re.compile(r"dgm1_32_(\d+)_(\d+)_")


def _construire_index(cache_path):
    """{'<E_km>_<N_km>': url} millésime le plus récent par dalle. Caché."""
    if cache_path.exists():
        try:
            idx = json.loads(cache_path.read_text(encoding="utf-8"))
            if idx:
                return idx
        except Exception:
            pass
    print("  SH LVermGeo: downloading the tile index (~9 MB GeoJSON, once)...",
          flush=True)
    try:
        req = urllib.request.Request(INDEX_URL, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            gj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print(f"  ERROR SH index: {type(e).__name__}: {e}")
        return None
    index = {}          # key -> (datum, url)
    for feat in gj.get("features", []):
        p = feat.get("properties", {})
        url = p.get("link_data")
        if not url:
            continue
        m = _FILE_RE.search(url)
        if not m:
            continue
        key = f"{m.group(1)}_{m.group(2)}"
        datum = p.get("datum", "")
        prev = index.get(key)
        if prev is None or datum > prev[0]:   # garder le plus récent
            index[key] = (datum, url)
    index = {k: v[1] for k, v in index.items()}
    if not index:
        return None
    try:
        cache_path.write_text(json.dumps(index), encoding="utf-8")
    except Exception:
        pass
    print(f"  SH LVermGeo: {len(index)} tiles indexed")
    return index


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{sh_dgm1_<E>_<N>.tif: url_xyz} pour les dalles 1 km de bbox_natif (EPSG:25832)."""
    if bbox_natif is None:
        return {}
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    index = _construire_index(cache_path)
    if index is None:
        return None
    grille = dalles_pour_bbox(*bbox_natif)
    dalles = {}
    hors = 0
    for x_km, y_km in grille:
        url = index.get(f"{x_km}_{y_km}")
        if url:
            dalles[dalle_filename(x_km, y_km)] = url
        else:
            hors += 1
    print(f"  DE Schleswig-Holstein (DGM1 1m): {len(dalles)} tile(s) in the bbox"
          + (f" ({hors} out of coverage)" if hors else ""))
    return dalles


# ── Hook post_fetch : XYZ texte brut → GeoTIFF ───────────────────────────────
def post_fetch(chemin):
    """Le download est un fichier XYZ TEXTE (« X Y Z » espacé, cell-centers,
    grille 1 m), écrit sous un nom .tif par le cœur. On le convertit en GeoTIFF
    Float32 EPSG:25832 (placement direct sur grille, cf. de_thueringen/de_berlin).
    Si le contenu est déjà un TIFF (II/MM), no-op."""
    chemin = Path(chemin)
    try:
        with open(chemin, "rb") as fh:
            head = fh.read(4)
    except OSError:
        return
    if head[:2] in (b"II", b"MM"):
        return  # déjà un GeoTIFF

    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds

    with open(chemin, "rb") as fh:
        data = fh.read()
    vals = np.array(data.split(), dtype=np.float64)
    if vals.size < 3 or vals.size % 3:
        raise ValueError(f"XYZ SH malformé : {vals.size} valeurs (≠ 3n)")
    pts = vals.reshape(-1, 3)
    xs, ys, zs = pts[:, 0], pts[:, 1], pts[:, 2]

    ux = np.unique(xs)
    res = float(np.min(np.diff(ux))) if ux.size > 1 else RESOLUTION_M
    x0, x1 = float(xs.min()), float(xs.max())
    y0, y1 = float(ys.min()), float(ys.max())
    nx = int(round((x1 - x0) / res)) + 1
    ny = int(round((y1 - y0) / res)) + 1
    grid = np.full((ny, nx), -9999.0, dtype=np.float32)
    ci = np.rint((xs - x0) / res).astype(np.int64)
    ri = np.rint((y1 - ys) / res).astype(np.int64)   # origine haut-gauche
    grid[ri, ci] = zs

    transform = from_bounds(x0 - res / 2, y0 - res / 2,
                            x1 + res / 2, y1 + res / 2, nx, ny)
    tmp = chemin.with_suffix(".tif_tmp")
    with rasterio.open(str(tmp), "w",
                       driver="GTiff", height=ny, width=nx,
                       count=1, dtype="float32",
                       crs=rasterio.CRS.from_epsg(25832),
                       transform=transform, nodata=-9999,
                       compress="deflate", predictor=2, tiled=True) as dst:
        dst.write(grid, 1)
    tmp.replace(chemin)
