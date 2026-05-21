# providers/nl_ahn.py — Pays-Bas, AHN (Actueel Hoogtebestand Nederland) via PDOK
#
# Source : Rijkswaterstaat / PDOK (Publieke Dienstverlening Op de Kaart).
# Distribution : ATOM feed + COG (Cloud-Optimized GeoTIFF) téléchargeables
# directement par URL stable. Pas de WMS GetMap par dalle comme l'IGN —
# AHN expose des fichiers pré-construits via un index JSON.
#
# Différences architecturales notables vs IGN :
#   - CRS natif EPSG:28992 (RD New), pas Lambert-93
#   - Tuiles "kaartblad" 6.25 × 5 km (et non 1×1 km comme IGN)
#   - Nommage par identifiant alphanumérique (R_31HZ2.tif) sans (x, y) numérique
#   - Découverte via JSON index (pas TMS vectoriel PBF)
#   - Pas de WMS GetMap par tuile (pas d'équivalent de PROVIDER.dalle_url)
#
# Ces différences valident que le pattern provider est assez souple pour
# accommoder des paradigmes d'accès très différents.
#
# Status POC : metadata + discover_dalles fonctionnels. La pipeline actuelle
# de lidar2map.py suppose une grille (x_km, y_km) → ne fonctionnera pas
# encore tel quel avec ce provider. Un refacto supplémentaire serait nécessaire
# pour permettre une exécution complète NL — out-of-scope POC.

import json
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Pays-Bas — AHN5 (Actueel Hoogtebestand Nederland)"
CODE       = "nl-ahn"
LICENSE    = "CC-0 (domaine public)"
DOC_URL    = "https://www.ahn.nl/"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:28992"      # Rijksdriehoek (RD New)
RESOLUTION_M       = 0.5               # AHN5 DTM/DSM 0.5 m
# Kaartblad AHN 2/3/4/5 : tuiles 6.25 km (N-S) × 5 km (E-O). AHN6 prévoira
# des tuiles 1×1 km. On expose les deux dimensions séparément.
TUILE_NS_KM        = 6.25
TUILE_EO_KM        = 5
DALLE_KM           = max(TUILE_NS_KM, TUILE_EO_KM)   # alias compat ; à utiliser avec prudence
PX_PAR_DALLE       = int(TUILE_NS_KM * 1000 / RESOLUTION_M)   # ~12500 px (1 dim)
SEUIL_DALLE_VALIDE = 5_000_000     # AHN COG plus volumineux qu'IGN — ajuster à l'usage


# ── Endpoints ────────────────────────────────────────────────────────────────
BASE_URL    = "https://service.pdok.nl/rws/ahn"
WMS_URL     = f"{BASE_URL}/wms/v1_0"
WCS_URL     = f"{BASE_URL}/wcs/v1_0"
ATOM_URL    = f"{BASE_URL}/atom/index.xml"
DOWNLOAD_BASE = f"{BASE_URL}/atom/downloads"
# Layers WMS pour visualisation : ahn5_05m_dtm, ahn5_05m_dsm, ahn4_05m_dtm, etc.
WMS_LAYER   = "ahn5_05m_dtm"
# Produit pour téléchargement direct (chemin URL) :
PRODUIT     = "dtm_05m"   # alternatives : dsm_05m, dtm_5m, dsm_5m


# ── Nommage des dalles ───────────────────────────────────────────────────────
# Les tuiles AHN ne suivent pas une grille (x_km, y_km) régulière mais un
# système kaartblad alphanumérique (ex: R_31HZ2). Le nom ne peut donc PAS
# être dérivé de coordonnées — il faut interroger l'index pour le découvrir.

def dalle_filename(x_km, y_km):
    """Non applicable pour AHN — les noms de tuiles sont alphanumériques.
    Cette fonction existe pour respecter le contrat provider mais ne devrait
    jamais être appelée. Utiliser discover_dalles() qui retourne {nom: url}."""
    raise NotImplementedError(
        "AHN n'utilise pas une grille (x_km, y_km) — utiliser discover_dalles()")


def dalle_subdir(x_km):
    """Pas de sous-dossier par colonne — toutes les dalles AHN dans un seul
    dossier (~1200 tuiles, gérable)."""
    return ""


def subdir_from_name(nom):
    """Pas de sous-dossier (cf. dalle_subdir)."""
    return None


# ── Construction URL pour une dalle (par nom, pas par x_km, y_km) ────────────
def dalle_url_by_name(nom):
    """URL directe de téléchargement d'un kaartblad AHN (COG GeoTIFF).
    Ex: dalle_url_by_name('R_31HZ2.tif') → https://.../atom/downloads/dtm_05m/R_31HZ2.tif"""
    if not nom.endswith(".tif"):
        nom = nom + ".tif"
    return f"{DOWNLOAD_BASE}/{PRODUIT}/{nom}"


def dalle_url(x_km, y_km):
    """Non applicable pour AHN — voir dalle_filename()."""
    raise NotImplementedError(
        "AHN n'utilise pas une grille (x_km, y_km) — utiliser discover_dalles()")


# ── Calcul de la liste des dalles couvrant une bbox ──────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    """Non applicable pour AHN — l'index des tuiles n'est pas dérivable
    d'une grille géométrique. Appeler discover_dalles() à la place."""
    raise NotImplementedError(
        "AHN n'a pas de grille régulière — utiliser discover_dalles((lon,lat,...))")


# ── Découverte des dalles via l'index JSON de l'ATOM feed ────────────────────
HTTP_UA = "lidar2map/1.0 (PDOK AHN)"
# Le JSON index est référencé dans l'ATOM feed sous forme d'enclosure
# de type application/json. Sa structure (best-effort, à vérifier au
# premier appel réel) ressemble à :
#   {
#     "type": "FeatureCollection",
#     "features": [
#       {"properties": {"naam": "R_31HZ2"}, "geometry": {... bbox RD New ...}},
#       ...
#     ]
#   }
JSON_INDEX_URL = f"{BASE_URL}/atom/downloads/{PRODUIT}/index.json"


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Interroge l'index JSON AHN pour les dalles intersectant bbox_natif.

    bbox_wgs84 : (lon_min, lat_min, lon_max, lat_max) — non utilisé directement
                 mais conservé pour compat de signature avec PROVIDER.discover_dalles.
    bbox_natif : (x_min, y_min, x_max, y_max) en EPSG:28992 (RD New) — filtre
                 les tuiles par intersection.
    cache_path : Path JSON où mettre en cache l'index AHN complet (le fichier
                 fait ~few hundred Ko, change rarement).
    workers : ignoré (un seul fetch d'index suffit).

    Retourne {nom_dalle: url_telechargement} ou None si erreur.
    """
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Cache de l'index complet (~quelques centaines de Ko, change rarement)
    index = None
    if cache_path.exists():
        try:
            index = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    if index is None:
        print(f"  AHN : téléchargement index {JSON_INDEX_URL}...", flush=True)
        try:
            req = urllib.request.Request(JSON_INDEX_URL,
                                         headers={"User-Agent": HTTP_UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                index = json.loads(resp.read())
            cache_path.write_text(json.dumps(index), encoding="utf-8")
        except Exception as e:
            print(f"  ERREUR AHN index : {e}")
            return None

    # Filtre bbox (intersection rectangle) sur les features GeoJSON
    if bbox_natif is None:
        zx0, zy0, zx1, zy1 = -1e12, -1e12, 1e12, 1e12
    else:
        zx0, zy0, zx1, zy1 = bbox_natif

    dalles = {}
    features = index.get("features", []) if isinstance(index, dict) else []
    for feat in features:
        props = feat.get("properties", {}) or {}
        nom   = props.get("naam") or props.get("name") or props.get("kaartblad")
        if not nom:
            continue
        # bbox de la tuile, conventionnellement [xmin, ymin, xmax, ymax] en RD New
        b = feat.get("bbox") or props.get("bbox")
        if b and len(b) == 4:
            fx0, fy0, fx1, fy1 = map(float, b)
            if fx1 < zx0 or fx0 > zx1 or fy1 < zy0 or fy0 > zy1:
                continue
        dalles[f"{nom}.tif" if not nom.endswith(".tif") else nom] = dalle_url_by_name(nom)

    print(f"  AHN : {len(dalles)} dalle(s) dans la bbox")
    return dalles
