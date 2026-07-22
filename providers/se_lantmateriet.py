# providers/se_lantmateriet.py — Suède, Markhöjdmodell 1 m via STAC Lantmäteriet
#
# Source : Lantmäteriet — « Markhöjdmodell Nedladdning » (DTM 1 m, données HVD
#   gratuites depuis février 2026, laser aéroporté). PRODUIT DE TÉLÉCHARGEMENT,
#   à ne pas confondre avec « Markhöjd Direkt » (API de valeurs ponctuelles).
#   Portail : https://www.lantmateriet.se/sv/geodata/vara-produkter/produktlista/markhojdmodell-nedladdning/
#
# Paradigme : COG fenêtré (calque ca-nrcan / at-bev) + découverte STAC.
#   - STAC ouvert (exploration anonyme) : api.lantmateriet.se/stac-hojd/v1,
#     collection "dtm-cog". items?bbox= (WGS84) → asset "data" = COG 10×10 km
#     (10000×10000 px @ 1 m, float32, nodata -9999, EPSG:5845 = SWEREF99 TM +
#     RH2000). Le cœur en lit la fenêtre bbox via /vsicurl.
#   - CRS natif EXPOSÉ = EPSG:3006 (SWEREF99 TM, composante horizontale) ; le
#     cœur reprojette la bbox 3006 → CRS réel du COG (5845) avant de fenêtrer
#     (identité horizontale, juste l'axe hauteur en plus).
#   - AUTH : le download dl1.lantmateriet.se exige le compte GeoTorget (Basic).
#     `gdal_env_options()` injecte GDAL_HTTP_USERPWD dans l'Env de lecture
#     (scopé : les identifiants ne fuient pas vers d'autres hosts). Identifiants
#     via env LANTMATERIET_USER / LANTMATERIET_PASS. Le STAC, lui, est anonyme.
#   - Licence : öppna data / HVD (gratuit, mention Lantmäteriet).
#
# Self-contained : stdlib uniquement.

import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Suède — Markhöjdmodell 1 m (Lantmäteriet)"
CODE       = "se-lantmateriet"
COUNTRY    = "se"
LICENSE    = "Öppna data / HVD — © Lantmäteriet"
DOC_URL    = "https://www.lantmateriet.se/sv/geodata/vara-produkter/produktlista/markhojdmodell-nedladdning/"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3006"          # SWEREF99 TM (horizontal du COG 5845)
RESOLUTION_M       = 1.0                   # DTM 1 m
DALLE_KM           = 1                     # nominal (fenêtre COG, cf. ca-nrcan)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 200_000
# COG 10×10 km @ 1 m lus en fenêtre via /vsicurl.
COG_WINDOWED       = True


# ── Endpoints ────────────────────────────────────────────────────────────────
STAC       = "https://api.lantmateriet.se/stac-hojd/v1"
COLLECTION = "dtm-cog"
HTTP_UA    = "lidar2map/1.0 (SE Markhojd)"
# Étendue Suède en EPSG:3006 (approx, clip grossier)
COVERAGE_EXTENT = (260000, 6130000, 920000, 7700000)


# ── Auth (Basic sur dl1, via env) ────────────────────────────────────────────
def _credentials():
    u = os.environ.get("LANTMATERIET_USER")
    p = os.environ.get("LANTMATERIET_PASS")
    return (u, p) if (u and p) else (None, None)


def gdal_env_options():
    """Options GDAL injectées (scopées) dans l'Env de lecture du COG par le cœur.
    GDAL_HTTP_USERPWD = auth Basic du download dl1. {} si identifiants absents
    (le download renverra alors 403, remonté en erreur visible)."""
    u, p = _credentials()
    return {"GDAL_HTTP_USERPWD": f"{u}:{p}"} if u else {}


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(tile_id):
    safe = re.sub(r"[^A-Za-z0-9]+", "_", str(tile_id)).strip("_") or "tile"
    return f"se_dtm1m_{safe}.tif"


def subdir_from_name(nom):
    m = re.match(r"se_dtm1m_(\d+)", nom)
    return m.group(1) if m else None


# ── Découverte STAC (cache PAR bbox, calque ca-nrcan) ────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{se_dtm1m_<tile>.tif: url_cog} des tuiles DTM 1 m intersectant bbox_wgs84.

    STAC anonyme, cache par-bbox (pas de poisoning inter-zones). Le download des
    COG exige les identifiants Lantmäteriet (cf. gdal_env_options) : on échoue
    tôt et clairement s'ils manquent."""
    if bbox_wgs84 is None:
        return {}
    # Garde fail-fast hors couverture : bbox entièrement hors de la Suède (3006)
    # → {} sans exiger les identifiants ni interroger STAC (emprise lâche).
    if bbox_natif is not None:
        cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
        nx1, ny1, nx2, ny2 = bbox_natif
        if max(nx1, cx0) >= min(nx2, cx1) or max(ny1, cy0) >= min(ny2, cy1):
            print("  SE Lantmateriet: bbox outside Sweden (EPSG:3006) coverage")
            return {}
    if _credentials() == (None, None):
        print("  ERROR se-lantmateriet: set LANTMATERIET_USER and "
              "LANTMATERIET_PASS (free GeoTorget account, order "
              "'Markhojdmodell Nedladdning')")
        return None

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    bbox_str = f"{lon_min},{lat_min},{lon_max},{lat_max}"
    bbox_key = hashlib.md5(f"{COLLECTION}|{bbox_str}".encode()).hexdigest()[:12]
    cache_bbox = cache_path.with_name(f"{cache_path.stem}_{bbox_key}.json")

    items = []
    if cache_bbox.exists():
        try:
            items = json.loads(cache_bbox.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            items = []

    if not items:
        url = f"{STAC}/collections/{COLLECTION}/items?bbox={bbox_str}&limit=100"
        print(f"  Lantmateriet STAC: query {bbox_str}...", flush=True)
        n_pages = 0
        while url:
            req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA,
                                                       "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    data = json.load(r)
            except Exception as e:
                print(f"  ERROR SE STAC: {type(e).__name__}: {e}")
                return None
            items.extend(data.get("features", []))
            n_pages += 1
            url = None
            for link in data.get("links", []):
                if link.get("rel") == "next" and link.get("href"):
                    url = link["href"]
                    break
        try:
            cache_bbox.write_text(json.dumps({"bbox": bbox_str, "items": items}),
                                  encoding="utf-8")
        except Exception:
            pass
        print(f"  Lantmateriet: {n_pages} page(s) → {len(items)} items")

    # Sélection : asset 'data' (COG GeoTIFF) ; millésime le plus récent par tuile.
    meilleurs = {}   # tile_id -> (datetime, href)
    for it in items:
        data_asset = (it.get("assets") or {}).get("data")
        if not data_asset:
            continue
        href = data_asset.get("href", "")
        t = data_asset.get("type", "")
        if not href or "tiff" not in t:
            continue
        tid = it.get("id") or href.rsplit("/", 1)[-1]
        dt = (it.get("properties") or {}).get("datetime", "")
        prev = meilleurs.get(tid)
        if prev is None or dt > prev[0]:
            meilleurs[tid] = (dt, href)

    dalles = {dalle_filename(tid): href for tid, (_dt, href) in meilleurs.items()}
    print(f"  SE (Markhojd 1 m): {len(dalles)} tile(s) selected")
    return dalles
