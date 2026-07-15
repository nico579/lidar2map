# providers/lv_lgia.py — Lettonie, DTM 1 m depuis le LiDAR national (LĢIA, LAS)
#
# Source : Latvijas Ģeotelpiskās informācijas aģentūra (LĢIA), open data
#   https://www.lgia.gov.lv/en/atvertie-dati
#   Liste des LAS : https://s3.storage.pub.lvdc.gov.lv/lgia-opendata/las/LGIA_OpenData_las_saites.txt
#
# Paradigme : index statique (S3) de ~66 000 nuages LAS 1 km² classifiés →
#   téléchargement du LAS → binning classe 2 (sol) → GeoTIFF (schéma cz_cuzk,
#   conversion mutualisée dans providers/common.py::las_to_dtm).
#   - CRS natif EPSG:3059 (LKS-92 / Latvia TM).
#   - LAS 1.2, format point 1, classifiés (classe 2 = sol présente, densité sol
#     >= 1,5 pt/m²). Fichiers ~50-100 Mo (nuages denses) → binning min-z (pas
#     d'interpolation Delaunay, qui exploserait à ~7 M points/tuile).
#   - Résolution cible 1 m, dalle 1×1 km.
#   - Licence : CC BY 4.0 (LĢIA open data).
#   - NÉCESSITE laspy (+ scipy/rasterio) au runtime pour post_fetch.
#
# GÉOMÉTRIE (dérivée empiriquement + mesurée) : les LAS sont nommés selon la
#   nomenclature TKS-93 « <feuille50k>-<QQ>-<CC> » (ex. 2434-15-25). Une feuille
#   1:50000 = 25×25 km ; QQ = sous-bloc 5 km (q1=ligne, q2=colonne) ; CC = cellule
#   1 km dans ce bloc (row=CC[0], col=CC[1]), 1..5 chacun. Dans une feuille :
#     x_km = Ax + q2*5 + (col-1) ;  y_km = Ay + q1*5 + (row-1)   (coin SW, km)
#   Le couple (Ax, Ay) d'une feuille N'EST PAS dérivable proprement du numéro
#   (nomenclature entrelacée) → on le MESURE une fois par feuille (144 au total)
#   en lisant l'en-tête LAS d'UNE tuile de la feuille (HTTP Range 260 octets,
#   bornes min X/Y). Index {las_name: [x_km, y_km]} caché sur disque ensuite.
#
# Self-contained : stdlib uniquement (laspy/scipy/rasterio requis au runtime).

import concurrent.futures
import json
import math
import re
import ssl
import struct
import urllib.request
from pathlib import Path

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _CTX = ssl.create_default_context()


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Lettonie — DTM 1 m (LĢIA, LiDAR LAS)"
CODE       = "lv-lgia"
COUNTRY    = "lv"
LICENSE    = "CC BY 4.0 — © Latvijas Ģeotelpiskās informācijas aģentūra (LĢIA)"
DOC_URL    = "https://www.lgia.gov.lv/en/atvertie-dati"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3059"          # LKS-92 / Latvia TM
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000
SEUIL_DALLE_VALIDE = 100_000              # GeoTIFF 1000×1000 compressé


# ── Endpoints ────────────────────────────────────────────────────────────────
S3_BASE  = "https://s3.storage.pub.lvdc.gov.lv/lgia-opendata/las"
INDEX_TXT = f"{S3_BASE}/LGIA_OpenData_las_saites.txt"
HTTP_UA  = "lidar2map/1.0 (LV LGIA)"

# Exemple réel pour le test de disjonction intra-pays (nommage non-formule).
SAMPLE_DALLE = "lv_dtm1_649_176.tif"


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"lv_dtm1_{int(x_km)}_{int(y_km)}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km)}"


def subdir_from_name(nom):
    m = re.match(r"lv_dtm1_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("LV : URL via index LAS S3 → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("LV : intersection via l'index LAS → discover_dalles()")


# ── Géométrie des noms TKS-93 ────────────────────────────────────────────────
def _las_url(name):
    return f"{S3_BASE}/{name.split('-')[0]}/{name}.las"


def _parse(name):
    """'2434-15-25' → (sheet, q1, q2, row, col)."""
    s, q, c = name.split("-")
    return s, int(q[0]), int(q[1]), int(c[0]), int(c[1])


def _base_de_feuille(name):
    """Mesure (Ax, Ay) en km pour la feuille de `name`, en lisant l'en-tête LAS
    (bornes min X/Y). None si échec."""
    try:
        req = urllib.request.Request(_las_url(name),
                                     headers={"User-Agent": HTTP_UA,
                                              "Range": "bytes=0-260"})
        with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
            hdr = r.read()
    except Exception:
        return None
    if len(hdr) < 227 or hdr[:4] != b"LASF":
        return None
    minx = struct.unpack("<d", hdr[187:195])[0]
    miny = struct.unpack("<d", hdr[203:211])[0]
    _, q1, q2, row, col = _parse(name)
    ax = math.floor(minx / 1000) - q2 * 5 - (col - 1)
    ay = math.floor(miny / 1000) - q1 * 5 - (row - 1)
    return ax, ay


# ── Index (téléchargé + mesuré une fois, caché) ──────────────────────────────
def _construire_index(cache_path, workers):
    """{las_name: [x_km, y_km]} pour les ~66 000 tuiles. Le corps de la liste
    vient d'un seul GET (S3) ; les origines de feuille sont mesurées (1 en-tête
    LAS par feuille, ~144, en parallèle). Caché sur disque. None si échec réseau."""
    if cache_path.exists():
        try:
            idx = json.loads(cache_path.read_text(encoding="utf-8"))
            if idx:
                return idx
        except Exception:
            pass
    print("  LV LĢIA: downloading the LAS index (once)...", flush=True)
    try:
        req = urllib.request.Request(INDEX_TXT, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=120, context=_CTX) as r:
            texte = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  ERROR LV index: {type(e).__name__}: {e}")
        return None
    noms = re.findall(r"/las/\d+/(\d+-\d+-\d+)\.las", texte)
    if not noms:
        return None
    par_feuille = {}
    for nm in noms:
        par_feuille.setdefault(nm.split("-")[0], nm)
    print(f"  LV LĢIA: {len(noms)} tiles, measuring {len(par_feuille)} sheet "
          f"origins (LAS headers)...", flush=True)

    bases = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for sheet, base in zip(par_feuille,
                               ex.map(_base_de_feuille, par_feuille.values())):
            if base:
                bases[sheet] = base

    index = {}
    for nm in noms:
        s, q1, q2, row, col = _parse(nm)
        base = bases.get(s)
        if not base:
            continue
        ax, ay = base
        index[nm] = [ax + q2 * 5 + (col - 1), ay + q1 * 5 + (row - 1)]
    if not index:
        return None
    try:
        cache_path.write_text(json.dumps(index), encoding="utf-8")
    except Exception:
        pass
    print(f"  LV LĢIA: {len(index)} tiles indexed ({len(bases)} sheets)")
    return index


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=8):
    """{lv_dtm1_<x>_<y>.tif: url_las} pour les tuiles 1 km intersectant bbox_natif
    (EPSG:3059). Le contenu téléchargé est un .las → GeoTIFF par post_fetch."""
    if bbox_natif is None:
        return {}
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    index = _construire_index(cache_path, workers)
    if index is None:
        return None

    x1, y1, x2, y2 = bbox_natif
    dalles = {}
    for nm, (x_km, y_km) in index.items():
        tx1, ty1 = x_km * 1000, y_km * 1000
        tx2, ty2 = tx1 + 1000, ty1 + 1000
        if tx2 <= x1 or tx1 >= x2 or ty2 <= y1 or ty1 >= y2:
            continue
        dalles[dalle_filename(x_km, y_km)] = _las_url(nm)
    print(f"  LV Latvia (DTM 1m, LiDAR): {len(dalles)} tile(s) in the bbox")
    return dalles


# ── Hook post_fetch : LAS → GeoTIFF DTM (binning classe sol) ──────────────────
def post_fetch(chemin):
    """Le téléchargement est un .las brut (magic LASF), écrit sous un nom .tif par
    le cœur. On convertit en GeoTIFF DTM (binning min-z classe 2) via
    common.las_to_dtm. Détection par magic LASF (pas suffixe)."""
    chemin = Path(chemin)
    try:
        with open(chemin, "rb") as fh:
            magic = fh.read(4)
    except OSError:
        return
    if magic != b"LASF":
        return  # déjà un GeoTIFF (ou réponse d'erreur → le validateur tranchera)

    from providers import common
    las_tmp = chemin.with_suffix(".las")
    chemin.replace(las_tmp)
    try:
        common.las_to_dtm(las_tmp, chemin, crs_epsg=3059,
                          resolution=RESOLUTION_M, classes=(2,))
    finally:
        las_tmp.unlink(missing_ok=True)
