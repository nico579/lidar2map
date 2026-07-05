# providers/gb_wales.py — Royaume-Uni (Pays de Galles), LiDAR DTM 1m via DataMapWales
#
# Source : Welsh Government / Natural Resources Wales, catalogue LiDAR 2020-2023
#   https://datamap.gov.wales/maps/lidar-data-download/
#
# Paradigme : catalogue de tuiles WFS (GeoServer GeoNode) → URL GeoTIFF directe
# par tuile (pattern index, comme NRW). Le catalogue
# `welsh_government_lidar_tile_catalogue_2020_2023` (22 473 tuiles 1 km OS grid)
# porte un champ `dtm_link` = GeoTIFF direct sur Azure blob (malgré le dossier
# "lidar-zips", ce sont bien des .tif, vérifié : content-type image/tiff).
#   - CRS natif EPSG:27700 (British National Grid).
#   - Tuiles 1 km alignées OS grid, 1 m. Nom = ref OS grid (ex. SH2281).
#   - URL non synthétisable (chemin Azure projet-spécifique) → discover via WFS.
#
# NB : couvre le programme gallois 2020-2023 (pas 100 % du pays). Angleterre =
# gb-england (EA, WCS). Écosse = à part.
#
# Self-contained : stdlib uniquement.

import json
import urllib.parse
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Royaume-Uni (Pays de Galles) — LiDAR DTM (DataMapWales)"
CODE       = "gb-wales"
COUNTRY    = "gb"
LICENSE    = "Open Government Licence v3 — © Welsh Government / NRW"
DOC_URL    = "https://datamap.gov.wales/maps/lidar-data-download/"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:27700"         # British National Grid (OSGB36)
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 500_000


# ── Endpoints ────────────────────────────────────────────────────────────────
WFS_URL = "https://datamap.gov.wales/geoserver/ows"
LAYER   = "geonode:welsh_government_lidar_tile_catalogue_2020_2023"
HTTP_UA = "lidar2map/1.0 (DataMapWales WFS)"


# ── Nommage : non synthétisable (chemin Azure par projet) → WFS requis ───────
import re as _re
_GR_RE = _re.compile(r"^([A-Z]{2}\d{4})")


def dalle_filename(x_km, y_km):
    raise NotImplementedError(
        "Pays de Galles : URL via catalogue WFS (chemin projet) → discover_dalles()")


def dalle_subdir(x_km):
    return ""


def subdir_from_name(nom):
    # Sous-dossier par carré OS 100 km (les 2 lettres, ex. SH)
    m = _re.match(r"dtm_wales_([A-Z]{2})", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("Voir discover_dalles().")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("Voir discover_dalles().")


# ── Découverte via le catalogue WFS ──────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Interroge le catalogue WFS pour les tuiles intersectant bbox_natif
    (EPSG:27700), retourne {nom: url_geotiff} depuis le champ dtm_link.

    bbox_wgs84 : ignoré (on filtre en 27700, natif).
    bbox_natif : (x_min, y_min, x_max, y_max) EPSG:27700.
    """
    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = bbox_natif
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # bbox WFS en EPSG:27700 (axe x,y pour un CRS projeté côté GeoServer)
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": LAYER, "outputFormat": "application/json",
        "srsName": "EPSG:27700",
        "bbox": f"{x1},{y1},{x2},{y2},EPSG:27700",
        "count": 5000,
    }
    url = WFS_URL + "?" + urllib.parse.urlencode(params)
    print(f"  DataMapWales WFS: bbox 27700 {x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.load(r)
    except Exception as e:
        print(f"  ERROR WFS Wales ({type(e).__name__}): {e}")
        return None

    feats = data.get("features", [])
    try:
        cache_path.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass

    # Dédup par carré OS grid (british_gr) en gardant la 1re livraison vue.
    dalles = {}
    for f in feats:
        p = f.get("properties", {}) or {}
        gr = p.get("british_gr")
        link = p.get("dtm_link")
        if not gr or not link:
            continue
        if not link.startswith("http"):
            link = "https://" + link
        nom = f"dtm_wales_{gr}.tif"
        dalles.setdefault(nom, link)

    print(f"  Wales: {len(feats)} WFS feature(s) → {len(dalles)} tile(s)")
    return dalles
