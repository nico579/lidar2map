# providers/de_thueringen.py — Allemagne (Thuringe), DGM 2m via TLBG (ATOM INSPIRE)
#
# Source : Thüringer Landesamt für Bodenmanagement und Geoinformation (TLBG) —
#   Digitales Geländemodell, données ouvertes (GDI-Th).
#   ATOM : https://geoportal.geoportal-th.de/dienste/atom_th_hoehendaten_dgm
#   Doc : https://tlbg.thueringen.de/geobasisdaten/3d-informationen/digitale-gelaendemodelle
#
# Paradigme : ATOM INSPIRE (comme cz_cuzk) MAIS en UN seul niveau utile —
#   le flux dataset liste 17 127 <link rel="section"> directs, chacun :
#     href = .../hoehendaten/DGM/<campagne>/dgm2_<E_km>_<N_km>_1_th_<millésime>.zip
#     title = "<E_km>_<N_km>_1x1km"  (coin SW en km, EPSG:25832 → filtre spatial)
#   Le millésime/campagne varie selon la zone → l'index ATOM est indispensable
#   (pas d'URL purement formulaire). Index téléchargé une fois et caché sur disque.
#
#   - CRS natif EPSG:25832 (ETRS89 / UTM 32N) — même que de_bayern/nrw/niedersachsen,
#     aucune reprojection (tuiles déjà en 25832).
#   - Résolution 2 m (produit « dgm2 »), dalle 1×1 km.
#   - Chaque .zip contient un .meta + un .xyz (texte « X Y Z », pas de virgule).
#     post_fetch : dézip + grille régulière XYZ → GeoTIFF (calque si_arso, res=2).
#   - Licence dl-de/by-2-0 (Datenlizenz Deutschland Namensnennung 2.0), ouverte.
#   - Pas de clé, pas de compte.
#
# Self-contained : stdlib uniquement (numpy/rasterio requis au runtime pour post_fetch).

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Allemagne (Thuringe) — DGM (TLBG, LiDAR)"
CODE       = "de-thueringen"
COUNTRY    = "de"
LICENSE    = "dl-de/by-2-0 — GDI-Th / Freistaat Thüringen (TLBG)"
DOC_URL    = "https://tlbg.thueringen.de/geobasisdaten/3d-informationen/digitale-gelaendemodelle"


# ── Géométrie ────────────────────────────────────────────────────────────────
# Le flux MÉLANGE les résolutions selon la campagne : 1 m (récent, 2020-2025)
# et 2 m (ancien, 2010-2013). post_fetch détecte le pas réel de chaque tuile ;
# RESOLUTION_M n'est que nominal (dimensionnement grille + estimation disque).
CRS_NATIF          = "EPSG:25832"         # ETRS89 / UTM 32N
RESOLUTION_M       = 1.0                  # nominal (réel = détecté par tuile)
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000 (nominal)
SEUIL_DALLE_VALIDE = 20_000               # tuiles de bord petites


# ── Endpoints ────────────────────────────────────────────────────────────────
ATOM_TOP = "https://geoportal.geoportal-th.de/dienste/atom_th_hoehendaten_dgm"
HTTP_UA  = "lidar2map/1.0 (TH DGM2)"
_ATOM    = "{http://www.w3.org/2005/Atom}"


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"th_dgm_{int(x_km)}_{int(y_km)}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km)}"


def subdir_from_name(nom):
    m = re.match(r"th_dgm_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("TH : URL via flux ATOM → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    """Grille 1 km EPSG:25832 — borne haute demi-ouverte (cf. de_bayern)."""
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


# ── Index ATOM (téléchargé une fois, caché) ──────────────────────────────────
def _dataset_feed_url(top_xml):
    """Flux top-level → href du flux dataset (lien alternate atom+xml de l'entry)."""
    root = ET.fromstring(top_xml)
    for entry in root.findall(f"{_ATOM}entry"):
        for link in entry.findall(f"{_ATOM}link"):
            if (link.get("rel") == "alternate"
                    and "atom+xml" in (link.get("type") or "")):
                return link.get("href")
    return None


def _construire_index(cache_path):
    """{'<E_km>_<N_km>': url_zip} pour les 17 000+ tuiles. Caché sur disque
    (téléchargé une fois). None si échec réseau total."""
    if cache_path.exists():
        try:
            idx = json.loads(cache_path.read_text(encoding="utf-8"))
            if idx:
                return idx
        except Exception:
            pass
    print("  TH TLBG: downloading the ATOM index (~17k tiles, once)...",
          flush=True)
    try:
        req = urllib.request.Request(ATOM_TOP, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            top = r.read()
        ds_url = _dataset_feed_url(top)
        if not ds_url:
            print("  TH TLBG: dataset feed not found in the top-level feed")
            return None
        req = urllib.request.Request(ds_url, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=180) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        print(f"  ERROR TH ATOM index: {type(e).__name__}: {e}")
        return None
    index = {}
    for link in root.iter(f"{_ATOM}link"):
        if link.get("rel") != "section":
            continue
        href = link.get("href")
        m = re.match(r"(\d+)_(\d+)_", link.get("title") or "")
        if href and m:
            index[f"{m.group(1)}_{m.group(2)}"] = href
    if not index:
        return None
    try:
        cache_path.write_text(json.dumps(index), encoding="utf-8")
    except Exception:
        pass
    print(f"  TH TLBG: {len(index)} tiles indexed")
    return index


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{th_dgm2_<E>_<N>.tif: url_zip} pour les tuiles 1 km de bbox_natif
    (EPSG:25832). Le contenu est un ZIP → GeoTIFF par post_fetch."""
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
    print(f"  TH TLBG (DGM 1-2 m): {len(dalles)} tile(s) in the bbox"
          + (f" ({hors} out of coverage)" if hors else ""))
    return dalles


# ── Hook post_fetch : ZIP(.xyz) → GeoTIFF ────────────────────────────────────
def post_fetch(chemin):
    """Dézip + conversion XYZ (« X Y Z » texte, grille régulière) → GeoTIFF
    Float32 EPSG:25832. Détection ZIP par magic bytes PK (le pipeline a nommé le
    fichier .tif en y écrivant le ZIP). La résolution (1 m ou 2 m selon campagne)
    est DÉTECTÉE depuis les données. Pas d'interpolation : placement direct sur
    grille (cf. si_arso) ; trous éventuels = nodata −9999."""
    chemin = Path(chemin)
    try:
        with open(chemin, "rb") as fh:
            magic = fh.read(4)
    except OSError:
        return
    if magic[:2] != b"PK":
        return  # déjà un GeoTIFF (ou réponse non-ZIP → le validateur tranchera)

    import zipfile
    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds

    with zipfile.ZipFile(chemin) as z:
        xyz = [n for n in z.namelist() if n.lower().endswith(".xyz")]
        if not xyz:
            raise ValueError(f"Aucun .xyz dans {chemin.name}")
        data = z.read(xyz[0])

    vals = np.array(data.split(), dtype=np.float64)
    if vals.size % 3:
        raise ValueError(f"XYZ TH malformé : {vals.size} valeurs (≠ 3n)")
    pts = vals.reshape(-1, 3)
    xs, ys, zs = pts[:, 0], pts[:, 1], pts[:, 2]

    # Pas réel de la grille (1 m ou 2 m selon la campagne) = plus petit écart
    # entre x uniques voisins — robuste même pour une tuile de bord trouée.
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

    # Coordonnées XYZ = centres de cellules → bornes décalées d'un demi-pixel
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
