# providers/nz_linz.py — Nouvelle-Zélande, LiDAR 1m DEM via LINZ S3 + STAC
#
# Source : Toitū Te Whenua Land Information New Zealand (LINZ)
#   National Elevation Programme — https://www.linz.govt.nz/guidance/data-service/linz-data-service-guide/elevation-data
#
# Paradigme : STAC API + COG sur bucket S3 public AWS ap-southeast-2
#   (même paradigme que ch_swisstopo + de_niedersachsen).
#   - CRS natif EPSG:2193 (NZGD2000 / NZTM2000)
#   - Résolution 1m → dalle 1 km = 1000×1000 px
#   - Bucket S3 public : s3://nz-elevation (ap-southeast-2, sans auth)
#   - STAC catalog : https://nz-elevation.s3-ap-southeast-2.amazonaws.com/catalog.json
#   - Dédup par (x_km, y_km) sur le millésime le plus récent
#
# Self-contained : stdlib uniquement.

import json
import re
import urllib.request
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


# ── Endpoints ────────────────────────────────────────────────────────────────
S3_BASE    = "https://nz-elevation.s3-ap-southeast-2.amazonaws.com"
STAC_ROOT  = f"{S3_BASE}/catalog.json"
# Structure réelle du catalogue (confirmée) :
# catalog.json → links[rel=child] → ./<region>/<survey>/dem_1m/2193/collection.json
# Exemple: ./auckland/auckland-north_2016-2018/dem_1m/2193/collection.json
# COG: s3://nz-elevation/<region>/<survey>/dem_1m/2193/<tile>.tiff
HTTP_UA    = "lidar2map/1.0 (LINZ NZ Elevation)"

# Étendue NZ en EPSG:2193
COVERAGE_EXTENT = (1050000, 4700000, 2100000, 6200000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"nz_dem1m_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    m = re.match(r"nz_dem1m_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("NZ : URL via STAC COG → utiliser discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("NZ : utiliser discover_dalles()")


# ── Découverte via STAC récursif ─────────────────────────────────────────────
def _stac_items_bbox(catalog_url, bbox_natif, depth=0, max_depth=4):
    """Parcourt récursivement le catalog STAC et collecte les items dans bbox."""
    if depth > max_depth:
        return []
    try:
        req = urllib.request.Request(catalog_url, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except Exception as e:
        return []

    items = []
    for link in data.get("links", []):
        rel = link.get("rel", "")
        href = link.get("href", "")
        if not href:
            continue
        # Résoudre URL relative depuis l'URL du catalogue courant (pas S3_BASE)
        # Ex: catalog_url = .../auckland/.../collection.json
        #     href = ./AY30_10000_0405.json → .../auckland/.../AY30_10000_0405.json
        if not href.startswith("http"):
            base = catalog_url.rsplit("/", 1)[0]
            if href.startswith("./"):
                href = base + "/" + href[2:]
            else:
                href = base + "/" + href

        if rel == "item":
            items.append(href)
        elif rel == "child":
            # Pré-filtrage géographique sur le bbox du sous-catalogue
            child_bbox = link.get("bbox")
            if child_bbox and bbox_natif:
                # child_bbox est en WGS84 (STAC standard)
                # On ne peut pas filtrer précisément sans pyproj ici
                # → on descend dans tous les enfants (filtrage a posteriori)
                pass
            items.extend(_stac_items_bbox(href, bbox_natif, depth + 1, max_depth))
    return items


def _bbox_intersects(item_bbox_wgs84, bbox_natif):
    """Vérification approximative intersection WGS84 bbox ↔ NZTM bbox.
    NZ : EPSG:2193 X≈1050000-2100000, Y≈4700000-6200000.
    WGS84 lon≈166-178, lat≈-47 à -34.
    Conversion approx : x_nztm ≈ (lon-173)*90000+1600000, y_nztm ≈ (lat+90)*111000."""
    if bbox_natif is None:
        return True
    lon1, lat1, lon2, lat2 = item_bbox_wgs84
    # Conversion approx WGS84 → NZTM
    def to_nztm(lon, lat):
        x = (lon - 173.0) * 90000 + 1600000
        y = (lat + 90.0) * 111000
        return x, y
    x1, y1 = to_nztm(lon1, lat1)
    x2, y2 = to_nztm(lon2, lat2)
    zx0, zy0, zx1, zy1 = bbox_natif
    return not (x2 < zx0 or x1 > zx1 or y2 < zy0 or y1 > zy1)


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Parcourt le STAC catalog NZ et retourne {nom: url_cog} pour bbox."""
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Cache items JSON
    items_cached = []
    if cache_path.exists():
        try:
            items_cached = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    if not items_cached:
        print(f"  LINZ NZ : parcours STAC catalog (peut prendre 30-60s)...", flush=True)
        item_urls = _stac_items_bbox(STAC_ROOT, bbox_natif)
        print(f"  {len(item_urls)} item URLs trouvés")
        # Charger chaque item pour récupérer l'asset COG
        items_cached = []
        for iu in item_urls[:500]:  # limite de sécurité
            try:
                req = urllib.request.Request(iu, headers={"User-Agent": HTTP_UA})
                with urllib.request.urlopen(req, timeout=15) as r:
                    it = json.load(r)
                it["_item_url"] = iu  # conserver l'URL source pour résolution hrefs relatifs
                items_cached.append(it)
            except Exception:
                pass
        try:
            cache_path.write_text(json.dumps(items_cached), encoding="utf-8")
        except Exception:
            pass

    # Extraire COG 1m + dédup par (x_km, y_km)
    _year_re = re.compile(r"(\d{4})")
    candidats = {}
    for it in items_cached:
        # Filtre géo
        bbox_item = it.get("bbox")
        if bbox_item and not _bbox_intersects(bbox_item, bbox_natif):
            continue
        # Asset COG 1m
        for k, asset in (it.get("assets") or {}).items():
            href = asset.get("href", "")
            if not href.endswith(".tiff") and not href.endswith(".tif"):
                continue
            if "1m" not in href and "1m" not in k:
                continue
            # Extraire x_km, y_km depuis la bbox de l'item
            if bbox_item:
                lon_c = (bbox_item[0] + bbox_item[2]) / 2
                lat_c = (bbox_item[1] + bbox_item[3]) / 2
                x_m = int((lon_c - 173.0) * 90000 + 1600000)
                y_m = int((lat_c + 90.0) * 111000)
                x_km = x_m // 1000
                y_km = y_m // 1000
            else:
                continue
            # Millésime
            yr_m = _year_re.search(href)
            year = int(yr_m.group(1)) if yr_m else 0
            key = (x_km, y_km)
            prev = candidats.get(key)
            if prev is None or year > prev[0]:
                candidats[key] = (year, dalle_filename(x_km, y_km), href)

    dalles = {nom: href for (_, nom, href) in candidats.values()}
    print(f"  LINZ NZ : {len(dalles)} dalle(s)")
    return dalles
