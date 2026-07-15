# providers/de_berlin.py — Berlin (Allemagne), DGM1 1 m via ATOM INSPIRE (XYZ zippé)
#
# Source : Senatsverwaltung für Stadtentwicklung, Bauen und Wohnen Berlin (geoportal Berlin)
#   ATOM : https://gdi.berlin.de/data/dgm1/atom  (flux top → dataset feed 0.atom)
#   Vue  : https://gdi.berlin.de/view/dgm1
#
# Paradigme : ATOM INSPIRE 2 niveaux (calque de_thueringen) — le flux top pointe
#   UN dataset feed `0.atom` qui liste ~297 dalles 2×2 km comme ZIP directs
#   `.../DGM1_<E_km>_<N_km>.zip`. Les coordonnées sont dans le NOM DU ZIP (les
#   <title> du feud sont génériques), grille 2 km, coin SW en km.
#   - CRS natif EPSG:25833 (ETRS89 / UTM 33N) — comme de-mv/de-brandenburg.
#   - Résolution 1 m, dalle 2×2 km (2000×2000 px).
#   - Chaque ZIP contient UN fichier XYZ texte « X Y Z » (espacé, cell-centers
#     `.500`, malgré le libellé « CSV » du feed). post_fetch : dézip + grille
#     régulière XYZ → GeoTIFF (calque de_thueringen/si_arso, pas d'interpolation).
#   - Licence : Datenlizenz Deutschland Zero 2.0 (dl-de/zero-2-0), domaine public.
#   - Pas de clé, pas de compte.
#
# Self-contained : stdlib uniquement (numpy/rasterio requis au runtime post_fetch).

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Berlin — DGM1 1 m (SenStadt, ATOM/XYZ)"
CODE       = "de-berlin"
COUNTRY    = "de"
LICENSE    = "dl-de/zero-2-0 — © GeoBasis-DE/SenStadt Berlin"
DOC_URL    = "https://gdi.berlin.de/view/dgm1"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25833"         # ETRS89 / UTM 33N
RESOLUTION_M       = 1.0                  # DGM1 1 m
DALLE_KM           = 2                     # blattschnitt 2×2 km → 2000×2000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000
SEUIL_DALLE_VALIDE = 100_000              # GeoTIFF 2000×2000 (>> erreur)


# ── Endpoints ────────────────────────────────────────────────────────────────
ATOM_TOP = "https://gdi.berlin.de/data/dgm1/atom"
HTTP_UA  = "lidar2map/1.0 (BE DGM1)"
_ATOM    = "{http://www.w3.org/2005/Atom}"

# Exemple réel pour le test de disjonction intra-pays (nommage non-formule).
SAMPLE_DALLE = "be_dgm1_390_5818.tif"


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"be_dgm1_{int(x_km)}_{int(y_km)}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km)}"


def subdir_from_name(nom):
    m = re.match(r"be_dgm1_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("BE : URL via flux ATOM → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    """Grille 2 km EPSG:25833 → coins SW en km (multiples de 2). Borne haute
    demi-ouverte (cf. de_thueringen). step=2000 m, coin SW km = (m // 2000) * 2."""
    step = DALLE_KM * 1000
    xs0 = (int(x1) // step) * 2
    xs1 = (int(x2) // step) * 2
    if x2 % step == 0 and xs1 > xs0:
        xs1 -= 2
    ys0 = (int(y1) // step) * 2
    ys1 = (int(y2) // step) * 2
    if y2 % step == 0 and ys1 > ys0:
        ys1 -= 2
    return [(x_km, y_km)
            for x_km in range(xs0, xs1 + 1, 2)
            for y_km in range(ys0, ys1 + 1, 2)]


# ── Index ATOM (téléchargé une fois, caché) ──────────────────────────────────
def _dataset_feed_url(top_xml):
    """Flux top → href du dataset feed (lien alternate atom+xml de l'entry)."""
    root = ET.fromstring(top_xml)
    for entry in root.findall(f"{_ATOM}entry"):
        for link in entry.findall(f"{_ATOM}link"):
            if (link.get("rel") == "alternate"
                    and "atom+xml" in (link.get("type") or "")):
                return link.get("href")
    return None


def _construire_index(cache_path):
    """{'<E_km>_<N_km>': url_zip} pour les ~297 dalles. Caché sur disque.
    Coords extraites du NOM du ZIP (DGM1_<E>_<N>.zip). None si échec réseau."""
    if cache_path.exists():
        try:
            idx = json.loads(cache_path.read_text(encoding="utf-8"))
            if idx:
                return idx
        except Exception:
            pass
    print("  BE SenStadt: downloading the ATOM index (once)...", flush=True)
    try:
        req = urllib.request.Request(ATOM_TOP, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            top = r.read()
        ds_url = _dataset_feed_url(top)
        if not ds_url:
            print("  BE: dataset feed not found in the top-level feed")
            return None
        req = urllib.request.Request(ds_url, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  ERROR BE ATOM index: {type(e).__name__}: {e}")
        return None
    index = {}
    for href in re.findall(r'href="([^"]+/DGM1_(\d+)_(\d+)\.zip)"', body):
        url, e_km, n_km = href
        index[f"{e_km}_{n_km}"] = url
    if not index:
        return None
    try:
        cache_path.write_text(json.dumps(index), encoding="utf-8")
    except Exception:
        pass
    print(f"  BE SenStadt: {len(index)} tiles indexed")
    return index


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{be_dgm1_<E>_<N>.tif: url_zip} pour les dalles 2 km de bbox_natif
    (EPSG:25833). Le contenu est un ZIP(XYZ) → GeoTIFF par post_fetch."""
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
    print(f"  BE Berlin (DGM1 1m): {len(dalles)} tile(s) in the bbox"
          + (f" ({hors} out of coverage)" if hors else ""))
    return dalles


# ── Hook post_fetch : ZIP(XYZ) → GeoTIFF ─────────────────────────────────────
def post_fetch(chemin):
    """Dézip + conversion XYZ (« X Y Z » texte, grille régulière 1 m) → GeoTIFF
    Float32 EPSG:25833. Détection ZIP par magic PK. Placement direct sur grille
    (cf. de_thueringen), pas d'interpolation ; trous = nodata −9999."""
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
        membres = [n for n in z.namelist()
                   if n.lower().endswith((".xyz", ".csv", ".txt"))]
        if not membres:
            raise ValueError(f"Aucun XYZ/CSV dans {chemin.name}")
        data = z.read(membres[0])

    # « X Y Z » espacé (Berlin) ; tolère aussi la virgule si un jour CSV.
    if b"," in data[:200]:
        data = data.replace(b",", b" ")
    vals = np.array(data.split(), dtype=np.float64)
    if vals.size % 3:
        raise ValueError(f"XYZ BE malformé : {vals.size} valeurs (≠ 3n)")
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
                       crs=rasterio.CRS.from_epsg(25833),
                       transform=transform, nodata=-9999,
                       compress="deflate", predictor=2, tiled=True) as dst:
        dst.write(grid, 1)
    tmp.replace(chemin)
