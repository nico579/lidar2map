# providers/de_bayern.py — Allemagne (Bavière), DGM1 LiDAR (LDBV)
#
# Source : Bayerische Vermessungsverwaltung (LDBV), portail OpenData
#   https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=dgm1
#
# L'Allemagne n'a PAS de source LiDAR nationale gratuite : le DGM1 fédéral du
# BKG est payant (≥ 8 000 €). L'open-data est par Land. La Bavière sert son
# DGM1 gratuitement, ce qui couvre les Alpes allemandes + le sud du pays.
#
# Paradigme d'accès (différent de fr_ign / nl_ahn) :
#   - CRS natif EPSG:25832 (ETRS89 / UTM zone 32N), pas Lambert-93.
#   - Grille RÉGULIÈRE 1 km × 1 km, 1 m/px (1000×1000) → le pipeline (x_km,y_km)
#     fonctionne tel quel (contrairement à nl_ahn dont les kaartblad ne sont pas
#     une grille). C'est un provider PLEINEMENT opérationnel, pas un POC.
#   - Nommage par coin SW (Xmin, Ymin) : "{Est_km}_{Nord_km}.tif" → INVERSE de
#     l'IGN qui nomme par le coin NW (Ymax). Vérifié empiriquement contre les
#     bounds raster d'une vraie tuile (600_5477 → bottom=5477000).
#   - Téléchargement GeoTIFF DIRECT, URL déterministe (pas de WMS GetMap, pas
#     d'année dans le nom) → dalle_url se synthétise depuis les coordonnées.
#   - Découverte : un seul Metalink (.meta4) pour tout le Land liste les tuiles
#     existantes (couverture non-rectangulaire). On le cache et on filtre.
#
# Self-contained : stdlib uniquement (pas de mapbox-vector-tile, pas de TMS).

import json
import re
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Allemagne (Bavière) — DGM1 LiDAR (LDBV)"
CODE       = "de-bayern"
COUNTRY    = "de"          # ISO 3166-1 alpha-2 — utilisé pour cache/lidar/<country>/
LICENSE    = "CC BY 4.0 — © Bayerische Vermessungsverwaltung (attribution requise)"
DOC_URL    = "https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=dgm1"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"         # ETRS89 / UTM zone 32N
RESOLUTION_M       = 1.0                  # DGM1 = grille 1 m
DALLE_KM           = 1                    # côté d'une dalle (km)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 1000 px

# Une tuile 1000×1000 GeoTIFF pèse ~3 Mo. En dessous de 0,5 Mo = réponse
# d'erreur / hors-couverture → ignorée.
SEUIL_DALLE_VALIDE = 500_000              # octets


# ── Endpoints ────────────────────────────────────────────────────────────────
# Deux miroirs de téléchargement (download1 / download2) ; on privilégie le 1.
DOWNLOAD_HOSTS = [
    "https://download1.bayernwolke.de/a/dgm/dgm1",
    "https://download2.bayernwolke.de/a/dgm/dgm1",
]
# Metalink listant TOUTES les tuiles DGM1 de Bavière (~70 000 entrées, ~15 Mo).
METALINK_URL = "https://geodaten.bayern.de/odd/a/dgm/dgm1/meta/metalink/09.meta4"

HTTP_UA = "lidar2map/1.0 (Bayern OpenData DGM1)"


# ── Conventions de nommage des dalles ────────────────────────────────────────
def dalle_filename(x_km, y_km):
    """Nom du fichier .tif pour la dalle dont le coin SW = (x_km, y_km) en km
    EPSG:25832. Convention Bavière : "{Est_km}_{Nord_km}.tif" = coin SW
    (Xmin, Ymin), sans année ni padding. Vérifié empiriquement (la tuile
    600_5477 couvre [600000,601000]×[5477000,5478000])."""
    return f"{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    """Sous-dossier par colonne Est (évite ~70 000 fichiers dans un seul
    dossier sur un run à l'échelle du Land)."""
    return f"{x_km}"


_SUBDIR_FROM_NAME = re.compile(r"^(\d+)_\d+")


def subdir_from_name(nom):
    """Sous-dossier (colonne Est) déduit du nom de tuile, ou None."""
    m = _SUBDIR_FROM_NAME.match(nom)
    return m.group(1) if m else None


# ── Construction URL (déterministe, pas de WMS) ──────────────────────────────
def dalle_url(x_km, y_km):
    """URL de téléchargement direct du GeoTIFF de la dalle (x_km, y_km).
    Déterministe : le nom et l'URL se déduisent des coordonnées, aucune requête
    d'index nécessaire pour télécharger une tuile dont on sait qu'elle existe."""
    return f"{DOWNLOAD_HOSTS[0]}/{x_km}_{y_km}.tif"


# ── Calcul de la liste des dalles couvrant une bbox ──────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    """Liste (x_km, y_km) des coins SW des dalles couvrant la bbox EPSG:25832.

    Borne haute demi-ouverte quand x2/y2 tombe pile sur une ligne de grille :
    la dalle commençant exactement à x2 (resp. y2) est hors bbox → exclue.
    (Même règle que fr_ign, pour ne pas générer une rangée/colonne en trop sur
    une bbox alignée.)"""
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


# ── Découverte des tuiles existantes via le Metalink du Land ──────────────────
_NAME_RE = re.compile(r'name="(\d+)_(\d+)\.tif"')


def _charger_couverture(cache_path):
    """Retourne le set des tuiles existantes {(x_km, y_km)} pour toute la
    Bavière, en cachant le résultat (le Metalink fait ~15 Mo, change rarement).
    Retourne None si le Metalink est inaccessible et qu'aucun cache n'existe."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            return {tuple(t) for t in data}
        except Exception:
            pass

    print("  Bayern: downloading the Metalink index (~15 MB, first time)...",
          flush=True)
    try:
        req = urllib.request.Request(METALINK_URL, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=120) as resp:
            texte = resp.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  ERROR Bayern Metalink: {e}")
        return None

    couverture = {(int(e), int(n)) for e, n in _NAME_RE.findall(texte)}
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(sorted(couverture)), encoding="utf-8")
    except Exception:
        pass
    print(f"  Bayern: {len(couverture)} tiles in the Land coverage")
    return couverture


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Retourne {nom_dalle: url} pour les tuiles DGM1 existantes intersectant
    bbox_natif (EPSG:25832).

    bbox_wgs84 : ignoré (la grille est en CRS natif ; conservé pour la signature).
    bbox_natif : (x_min, y_min, x_max, y_max) en EPSG:25832.
    cache_path : JSON où cacher la couverture du Land (set des tuiles).
    workers    : ignoré (un seul fetch d'index).

    Si le Metalink est inaccessible (et pas de cache), on tombe en repli grille
    pure : toutes les tuiles de la bbox, URL déterministe — quitte à ce que les
    bords hors-couverture renvoient 404 au téléchargement (géré en aval)."""
    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = bbox_natif
    grille = dalles_pour_bbox(x1, y1, x2, y2)

    couverture = _charger_couverture(cache_path)
    if couverture is None:
        print("  Bayern: index unavailable, pure grid fallback (404 possible at edges)")
        return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}

    return {dalle_filename(x, y): dalle_url(x, y)
            for x, y in grille if (x, y) in couverture}
