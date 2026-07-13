# providers/ca_nrcan.py — Canada, HRDEM Mosaic 1m via STAC NRCan
#
# Source : Natural Resources Canada — CanElevation Series HRDEM Mosaic
#   https://open.canada.ca/data/en/dataset/0fe65119-e96e-4a57-8bfe-9d9245fba06b
#
# Paradigme : STAC API + COG (même paradigme que ch_swisstopo, de_niedersachsen).
#   - CRS natif EPSG:3979 (NAD83 CSRS / LCC Canada)
#   - Résolution 1m et 2m (on cible 1m)
#   - STAC search : https://datacube.services.geo.ca/stac/api/search
#   - COG direct sur FTP NRCan (pas de restriction IP connue)
#   - Sans compte requis
#   - Dédup par (x_km, y_km) sur le millésime le plus récent
#
# Self-contained : stdlib uniquement.

import hashlib
import json
import re
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Canada — HRDEM Mosaic (NRCan)"
CODE       = "ca-nrcan"
COUNTRY    = "ca"
LICENSE    = "Open Government Licence — Canada"
DOC_URL    = "https://open.canada.ca/data/en/dataset/0fe65119-e96e-4a57-8bfe-9d9245fba06b"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3979"          # NAD83 CSRS / LCC Canada
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 200_000
# HRDEM = grandes mosaïques COG par levé (centaines de km²). Le pipeline lit la
# fenêtre bbox via /vsicurl/ (range requests) au lieu de rapatrier le COG entier.
COG_WINDOWED       = True


# ── Endpoints ────────────────────────────────────────────────────────────────
STAC_SEARCH = "https://datacube.services.geo.ca/stac/api/search"
COLLECTION  = "hrdem-lidar"
HTTP_UA     = "lidar2map/1.0 (NRCan HRDEM)"

# Étendue Canada en EPSG:3979 (approx)
COVERAGE_EXTENT = (-3000000, -1600000, 4000000, 3000000)


# ── Nommage ──────────────────────────────────────────────────────────────────
# Un item STAC = une survey entière (COG mosaïque de plusieurs centaines de km²),
# lue en fenêtre via /vsicurl. On nomme donc par identifiant de survey, pas par
# une cellule géographique : l'ancien nommage par centre de survey collapsait
# toutes les surveys d'une région sur ~1 cellule (perte de données massive).
def _safe_id(stac_id):
    """Identifiant STAC → composant de nom de fichier sûr."""
    return re.sub(r"[^A-Za-z0-9]+", "-", str(stac_id)).strip("-")[:70] or "survey"


def dalle_filename(stac_id):
    return f"ca_hrdem1m_{_safe_id(stac_id)}.tif"


def dalle_subdir(stac_id):
    return _safe_id(stac_id)[:2].lower() or "xx"


def subdir_from_name(nom):
    m = re.match(r"ca_hrdem1m_(.+)\.tif$", nom)
    return m.group(1)[:2].lower() if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("Canada : URL via STAC → utiliser discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("Canada : utiliser discover_dalles()")


# ── Découverte STAC ──────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Requête STAC NRCan → COG DTM 1 m (HRDEM) intersectant bbox_wgs84.

    Chaque item STAC est une survey entière (COG mosaïque lu en fenêtre). On
    retourne l'asset 'dtm' de chaque survey 1 m intersectant la zone ; le cœur en
    lit la fenêtre bbox via /vsicurl et compose les surveys qui se recouvrent.
    """
    if bbox_wgs84 is None:
        return {}
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Cache PAR bbox : la recherche STAC dépend de la bbox, donc son cache aussi.
    # Un fichier de cache unique partagé entre zones renvoyait les items de la
    # 1re bbox pour toutes les suivantes (relief d'une autre région, bug muet).
    bbox_str = f"{lon_min},{lat_min},{lon_max},{lat_max}"
    bbox_key = hashlib.md5(f"{COLLECTION}|{bbox_str}".encode()).hexdigest()[:12]
    cache_bbox = cache_path.with_name(f"{cache_path.stem}_{bbox_key}.json")

    items_all = []
    if cache_bbox.exists():
        try:
            items_all = json.loads(cache_bbox.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            pass

    if not items_all:
        url = f"{STAC_SEARCH}?collections={COLLECTION}&bbox={bbox_str}&limit=100"
        print(f"  NRCan STAC: query {bbox_str}...", flush=True)
        n_pages = 0
        while url:
            req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.load(r)
            except Exception as e:
                print(f"  ERROR NRCan STAC: {e}")
                return None
            items_all.extend(data.get("features", []))
            n_pages += 1
            url = None
            for link in data.get("links", []):
                if link.get("rel") == "next":
                    url = link.get("href")
                    break
        try:
            cache_bbox.write_text(json.dumps({"bbox": bbox_str, "items": items_all}),
                                  encoding="utf-8")
        except Exception:
            pass
        print(f"  NRCan : {n_pages} page(s) → {len(items_all)} items")

    # Sélection : asset 'dtm' (COG GeoTIFF) des surveys 1 m. Le DSM (surface) et
    # les résolutions 2 m sont écartés (provider déclaré 1 m, RESOLUTION_M=1.0 ;
    # une zone couverte seulement en 2 m relève d'un futur provider dédié, cf. #8).
    dalles = {}
    n_2m = 0
    for it in items_all:
        dtm = (it.get("assets") or {}).get("dtm")
        if not dtm:
            continue
        href = dtm.get("href", "")
        t = dtm.get("type", "")
        if not href or "tiff" not in t:
            continue
        low = href.lower()
        if "-1m" not in low:
            if "-2m" in low:
                n_2m += 1
            continue
        stac_id = it.get("id") or _safe_id(href)
        dalles[dalle_filename(stac_id)] = href

    if n_2m and not dalles:
        print(f"  NRCan: {n_2m} survey(s) 2 m seulement (provider 1 m) → aucune couverture")
    print(f"  NRCan: {len(dalles)} 1m DTM survey(s) selected")
    return dalles
