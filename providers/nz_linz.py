# providers/nz_linz.py — Nouvelle-Zélande, LiDAR 1m DEM via LINZ S3 + STAC
#
# Source : Toitū Te Whenua Land Information New Zealand (LINZ)
#   National Elevation Programme — https://www.linz.govt.nz/products-services/data/types-linz-data/elevation-data
#
# Paradigme : STAC statique + COG seamless national sur bucket S3 public.
#   - CRS natif EPSG:2193 (NZGD2000 / NZTM2000)
#   - On cible le DEM 1m NATIONAL composite (seamless, dédupliqué par LINZ) :
#       .../new-zealand/new-zealand/dem_1m/2193/collection.json  (424 feuilles)
#     plutôt que les ~100 levés régionaux qui se recouvrent (sinon doublons +
#     parcours de ~30 000 items). Les feuilles sont des dalles 1:50k (~24×36 km)
#     → grosses COG → on lit la FENÊTRE bbox via /vsicurl/ (COG_WINDOWED), comme
#     ca-nrcan, au lieu de rapatrier la feuille entière.
#   - Bucket S3 public : s3://nz-elevation (ap-southeast-2, sans auth).
#
# L'index {feuille: bbox+url} est construit une fois (~424 fetches, parallèle)
# puis caché sur disque : les requêtes suivantes ne touchent plus le réseau.
#
# Self-contained : stdlib uniquement.

import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Nouvelle-Zélande — LiDAR 1m DEM (LINZ)"
CODE       = "nz-linz"
COUNTRY    = "nz"
LICENSE    = "CC BY 4.0 — © Toitū Te Whenua Land Information New Zealand"
DOC_URL    = "https://registry.opendata.aws/nz-elevation/"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2193"          # NZGD2000 / NZTM2000
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 200_000
# Feuilles nationales = grosses dalles 1:50k → lecture COG fenêtrée /vsicurl/.
COG_WINDOWED       = True


# ── Endpoints ────────────────────────────────────────────────────────────────
S3_BASE    = "https://nz-elevation.s3-ap-southeast-2.amazonaws.com"
NATIONAL_COLLECTION = f"{S3_BASE}/new-zealand/new-zealand/dem_1m/2193/collection.json"
HTTP_UA    = "lidar2map/1.0 (LINZ NZ Elevation)"


# ── Nommage (par code de feuille Topo50, ex. AS21 / BA31) ─────────────────────
def dalle_filename(code):
    return f"nz_dem1m_{code}.tif"


def dalle_subdir(code):
    m = re.match(r"([A-Za-z]{2}\d{2})", str(code))
    return m.group(1).upper() if m else str(code)[:4]


def subdir_from_name(nom):
    m = re.match(r"nz_dem1m_([A-Za-z]{2}\d{2})", nom)
    return m.group(1).upper() if m else None


def dalle_url(code):
    raise NotImplementedError("NZ : URL via STAC COG → utiliser discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("NZ : utiliser discover_dalles()")


# ── Helpers STAC ─────────────────────────────────────────────────────────────
def _get_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception:
        return None


def _resolve(base, href):
    if href.startswith("http"):
        return href
    return base + "/" + (href[2:] if href.startswith("./") else href.lstrip("/"))


def _intersecte(bbox_a, qlon_min, qlat_min, qlon_max, qlat_max):
    """bbox_a = [lon_min, lat_min, lon_max, lat_max] (WGS84)."""
    if not bbox_a or len(bbox_a) < 4:
        return False
    alon_min, alat_min, alon_max, alat_max = bbox_a[:4]
    return not (alon_max < qlon_min or alon_min > qlon_max
                or alat_max < qlat_min or alat_min > qlat_max)


# ── Index national (construit une fois, caché) ───────────────────────────────
def _construire_index(cache_path, workers):
    """{feuille: {"bbox":[lon_min,lat_min,lon_max,lat_max], "url":cog}}.
    Retourne None si le réseau échoue totalement."""
    if cache_path.exists():
        try:
            idx = json.loads(cache_path.read_text(encoding="utf-8"))
            if idx:
                return idx
        except Exception:
            pass
    col = _get_json(NATIONAL_COLLECTION)
    if not col:
        print("  LINZ NZ : collection nationale inaccessible")
        return None
    cbase = NATIONAL_COLLECTION.rsplit("/", 1)[0]
    item_urls = [_resolve(cbase, l.get("href", ""))
                 for l in col.get("links", []) if l.get("rel") == "item"]
    print(f"  LINZ NZ: indexing the national 1m DEM "
          f"({len(item_urls)} sheets, once)...", flush=True)

    def _fetch(iu):
        it = _get_json(iu)
        if not it or not it.get("bbox"):
            return None
        ibase = iu.rsplit("/", 1)[0]
        url = None
        for _k, a in (it.get("assets") or {}).items():
            h = a.get("href", "")
            if h.endswith(".tiff") or h.endswith(".tif"):
                url = _resolve(ibase, h)
                break
        if not url:
            return None
        code = iu.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return (code, it["bbox"][:4], url)

    index = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(_fetch, item_urls):
            if res:
                index[res[0]] = {"bbox": res[1], "url": res[2]}
    try:
        cache_path.write_text(json.dumps(index), encoding="utf-8")
    except Exception:
        pass
    print(f"  LINZ NZ: {len(index)} sheets indexed")
    return index


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=8):
    """Retourne {nom.tif: url_cog} pour les feuilles DEM 1m intersectant la bbox.
    Lecture fenêtrée ensuite (COG_WINDOWED) : seule la fenêtre bbox est lue."""
    if bbox_wgs84 is None:
        return {}
    lo1, la1, lo2, la2 = bbox_wgs84
    qlon_min, qlon_max = min(lo1, lo2), max(lo1, lo2)
    qlat_min, qlat_max = min(la1, la2), max(la1, la2)

    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    index = _construire_index(cache_path, workers)
    if index is None:
        return None

    dalles = {}
    for code, info in index.items():
        if _intersecte(info["bbox"], qlon_min, qlat_min, qlon_max, qlat_max):
            dalles[dalle_filename(code)] = info["url"]
    print(f"  LINZ NZ: {len(dalles)} sheet(s) in the bbox")
    return dalles
