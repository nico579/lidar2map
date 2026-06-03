# providers/de_nrw.py — Allemagne (Rhénanie-du-Nord-Westphalie), DGM1 LiDAR
#
# Source : Geobasis NRW / OpenGeodata.NRW
#   https://www.opengeodata.nrw.de/produkte/geobasis/hm/dgm1_tiff/dgm1_tiff/
#
# NRW est le Land allemand pionnier de l'open LiDAR (DGM1 1 m, sans restriction).
# Pas dans les Alpes — c'est l'Allemagne du nord-ouest, le plus peuplé — mais ça
# étend la couverture allemande au-delà de la Bavière.
#
# Paradigme (proche de de_bayern, mais l'URL n'est PAS synthétisable) :
#   - CRS natif EPSG:25832 (UTM 32N), grille régulière 1 km, 1 m/px (1000×1000).
#   - Nommage par coin SW (Xmin, Ymin), vérifié empiriquement (la tuile
#     dgm1_32_280_5652 couvre [280000,281000]×[5652000,5653000]).
#   - MAIS le nom encode l'ANNÉE de levé, qui varie par tuile
#     (dgm1_32_280_5652_1_nw_2022.tif) → on ne peut pas construire l'URL depuis
#     les seules coordonnées. La découverte passe OBLIGATOIREMENT par index.json
#     (liste tous les noms exacts + permet de bâtir l'URL). dalle_url/
#     dalle_filename par coordonnées ne sont donc pas applicables (cf. NotImpl.).
#   - Téléchargement GeoTIFF direct (sibling de l'index).
#
# Self-contained : stdlib uniquement.

import json
import re
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Allemagne (Rhénanie-du-Nord-Westphalie) — DGM1 LiDAR"
CODE       = "de-nrw"
COUNTRY    = "de"          # ISO 3166-1 alpha-2 — utilisé pour cache/lidar/<country>/
LICENSE    = "Datenlizenz Deutschland Zero 2.0 (sans restriction)"
DOC_URL    = "https://www.opengeodata.nrw.de/produkte/geobasis/hm/dgm1_tiff/dgm1_tiff/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"         # ETRS89 / UTM zone 32N
RESOLUTION_M       = 1.0                  # DGM1 = grille 1 m
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 1000 px
SEUIL_DALLE_VALIDE = 500_000              # octets (tuile ~2 Mo ; <0.5 Mo = vide)


# ── Endpoints ────────────────────────────────────────────────────────────────
BASE_URL  = "https://www.opengeodata.nrw.de/produkte/geobasis/hm/dgm1_tiff/dgm1_tiff/"
INDEX_URL = BASE_URL + "index.json"
HTTP_UA   = "lidar2map/1.0 (OpenGeodata.NRW DGM1)"


# ── Nommage des dalles ───────────────────────────────────────────────────────
# Le nom contient l'année de levé (variable) → non synthétisable depuis (x,y).
_NAME_RE = re.compile(r"dgm1_32_(\d+)_(\d+)_")


def dalle_filename(x_km, y_km):
    """Non applicable : le nom NRW encode l'année de levé (variable par tuile),
    pas dérivable des coordonnées. Utiliser discover_dalles()."""
    raise NotImplementedError(
        "NRW : nom dépendant de l'année → utiliser discover_dalles()")


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    """Sous-dossier (colonne Est) déduit du nom, ou None."""
    m = _NAME_RE.match(nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    """Non applicable (cf. dalle_filename) — l'URL exacte vient de index.json."""
    raise NotImplementedError(
        "NRW : URL dépendante de l'année → utiliser discover_dalles()")


# ── Calcul de la liste des dalles couvrant une bbox ──────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    """Liste (x_km, y_km) des coins SW couvrant la bbox EPSG:25832.
    Borne haute demi-ouverte sur ligne de grille (cf. de_bayern)."""
    step = DALLE_KM * 1000
    x_start = int(x1 // step)
    x_end   = int(x2 // step)
    if x2 % step == 0 and x_end > x_start:
        x_end -= 1
    y_start = int(y1 // step)
    y_end   = int(y2 // step)
    if y2 % step == 0 and y_end > y_start:
        y_end -= 1
    return [(x_km, y_km)
            for x_km in range(x_start, x_end + 1)
            for y_km in range(y_start, y_end + 1)]


# ── Découverte via index.json ────────────────────────────────────────────────
def _charger_index(cache_path):
    """Retourne {(x_km, y_km): nom_fichier} depuis index.json (cache local, ~3.5
    Mo). None si inaccessible et pas de cache."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            return {(int(e), int(n)): nom for e, n, nom in data}
        except Exception:
            pass

    print("  NRW : téléchargement de l'index DGM1 (~3.5 Mo, 1re fois)...", flush=True)
    try:
        req = urllib.request.Request(INDEX_URL, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            idx = json.loads(resp.read())
    except Exception as e:
        print(f"  ERREUR NRW index : {e}")
        return None

    tuiles = {}
    for dataset in idx.get("datasets", []):
        for f in dataset.get("files", []):
            nom = f.get("name", "")
            m = _NAME_RE.match(nom)
            if m:
                tuiles[(int(m.group(1)), int(m.group(2)))] = nom
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps([[e, n, nom] for (e, n), nom in tuiles.items()]),
            encoding="utf-8")
    except Exception:
        pass
    print(f"  NRW : {len(tuiles)} tuiles dans l'index")
    return tuiles


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Retourne {nom_dalle: url} pour les tuiles DGM1 NRW intersectant bbox_natif
    (EPSG:25832). Source : index.json (noms exacts avec année). bbox_wgs84
    ignoré. Retourne {} si bbox hors zone, None si index inaccessible."""
    if bbox_natif is None:
        return {}
    index = _charger_index(cache_path)
    if index is None:
        return None
    x1, y1, x2, y2 = bbox_natif
    grille = dalles_pour_bbox(x1, y1, x2, y2)
    return {index[(x, y)]: BASE_URL + index[(x, y)]
            for x, y in grille if (x, y) in index}
