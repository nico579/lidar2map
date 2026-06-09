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

import json
import re
import urllib.request
import urllib.parse
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Canada — HRDEM Mosaic 1m (NRCan)"
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
def dalle_filename(x_km, y_km):
    return f"ca_hrdem1m_{x_km:+07d}_{y_km:+07d}.tif"


def dalle_subdir(x_km):
    return f"{x_km:+07d}"


def subdir_from_name(nom):
    m = re.match(r"ca_hrdem1m_([+-]?\d+)_", nom)
    return f"{int(m.group(1)):+07d}" if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("Canada : URL via STAC → utiliser discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("Canada : utiliser discover_dalles()")


# ── Découverte STAC ──────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Requête STAC NRCan pour les COG 1m HRDEM dans bbox_wgs84."""
    if bbox_wgs84 is None:
        return {}
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Cache
    items_all = []
    if cache_path.exists():
        try:
            items_all = json.loads(cache_path.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            pass

    if not items_all:
        bbox_str = f"{lon_min},{lat_min},{lon_max},{lat_max}"
        url = (f"{STAC_SEARCH}?collections={COLLECTION}"
               f"&bbox={bbox_str}&limit=100")
        print(f"  NRCan STAC : query {bbox_str}...", flush=True)
        n_pages = 0
        while url:
            req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.load(r)
            except Exception as e:
                print(f"  ERREUR NRCan STAC : {e}")
                return None
            items_all.extend(data.get("features", []))
            n_pages += 1
            url = None
            for link in data.get("links", []):
                if link.get("rel") == "next":
                    url = link.get("href")
                    break
        try:
            cache_path.write_text(json.dumps({"items": items_all}), encoding="utf-8")
        except Exception:
            pass
        print(f"  NRCan : {n_pages} page(s) → {len(items_all)} items")

    # Filtrer assets DTM 1m + dédup par position
    def _bbox_lcc(item_bbox_wgs84):
        """Conversion approx WGS84 → EPSG:3979 LCC Canada pour filtrage."""
        # Formule approche : pas de pyproj en stdlib
        # LCC Canada : lon_0=-96, lat_0=60, SP1=49, SP2=77
        # Approximation linéaire valide sur le Canada
        lon, lat = (item_bbox_wgs84[0]+item_bbox_wgs84[2])/2, (item_bbox_wgs84[1]+item_bbox_wgs84[3])/2
        x = (lon + 96) * 75000
        y = (lat - 60) * 111000
        return int(x // 1000), int(y // 1000)

    candidats = {}
    _yr_re = re.compile(r"(\d{4})")
    for it in items_all:
        for k, asset in (it.get("assets") or {}).items():
            href = asset.get("href", "")
            t = asset.get("type", "")
            if not href or ("tiff" not in t and not href.endswith(".tif")):
                continue
            # Préférer DTM sur DSM (asset key 'dtm' ou URL contenant '-dtm')
            is_dtm = ("dtm" in k.lower() or "-dtm" in href.lower() or
                      "dem" in k.lower() or "-dem" in href.lower())
            is_dsm_only = "dsm" in k.lower() and "-dsm" in href.lower() and not is_dtm
            if is_dsm_only:
                continue  # sauter les assets DSM purs
            if "1m" not in href.lower() and not is_dtm:
                continue
            bbox_item = it.get("bbox")
            if not bbox_item:
                continue
            x_km, y_km = _bbox_lcc(bbox_item)
            yr_m = _yr_re.search(href)
            year = int(yr_m.group(1)) if yr_m else 0
            key = (x_km, y_km)
            prev = candidats.get(key)
            if prev is None or year > prev[0]:
                candidats[key] = (year, dalle_filename(x_km, y_km), href)

    dalles = {nom: href for (_, nom, href) in candidats.values()}
    print(f"  NRCan : {len(dalles)} dalle(s) 1m retenues")
    return dalles
