# providers/at_bev.py — Autriche, ALS-DGM 1 m NATIONAL (BEV) via COG + ATOM
#
# Source : Bundesamt für Eich- und Vermessungswesen (BEV) — Airborne Laser
#   Scanning DGM (terrain) 1 m, open data CC-BY-4.0. Millésime 2019-2023 selon
#   la région (relevé national coopératif Bund/Länder).
#   Produit : https://www.bev.gv.at/Services/Produkte/Digitales-Gelaendehoehenmodell/ALS-Hoehenraster.html
#   Index ATOM (service feed) : geonetwork describe/service?uuid=208cff7a-...
#
# Paradigme : COG fenêtré (calque ca-nrcan) + index ATOM à 2 niveaux (calque
#   cz-cuzk / de-thueringen).
#   - CRS natif EPSG:3035 (ETRS89-LAEA Europe) ; grille de tuiles 50×50 km.
#   - Chaque tuile = un GeoTIFF COG 50001×50001 px @ 1 m (float32, nodata -9999,
#     tuilage interne 256×256) → le cœur en lit UNIQUEMENT la fenêtre bbox via
#     /vsicurl (telecharger_cog_fenetre), pas les ~10 Go du fichier entier.
#   - La DATE d'acquisition est encodée dans l'URL et varie par tuile (ex.
#     20190915 vs 20230915) → URL non constructible : l'index ATOM donne l'URL
#     .tif exacte de chaque tuile (service feed → dataset feed → lien image/tiff).
#   - On sert le DTM (terrain) ; le DSM (surface) est écarté.
#
# Self-contained : stdlib uniquement.

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Autriche — ALS-DGM 1 m national (BEV)"
CODE       = "at-bev"
COUNTRY    = "at"
LICENSE    = "CC BY 4.0 — © BEV (Geodaten Österreich)"
DOC_URL    = "https://www.bev.gv.at/Services/Produkte/Digitales-Gelaendehoehenmodell/ALS-Hoehenraster.html"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3035"          # ETRS89-LAEA Europe (mètres)
RESOLUTION_M       = 1.0                   # DGM 1 m
DALLE_KM           = 1                     # nominal (fenêtre COG, cf. ca-nrcan)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000 (estimation disque)
SEUIL_DALLE_VALIDE = 200_000
# Grandes mosaïques COG (50 km @ 1 m) lues en fenêtre via /vsicurl.
COG_WINDOWED       = True

# Grille BEV : tuiles de 50 km en EPSG:3035, origine (E, N) multiple de 50 000.
GRID_M     = 50_000


# ── Endpoints ────────────────────────────────────────────────────────────────
SERVICE_FEED = ("https://data.bev.gv.at/geonetwork/srv/atom/describe/service"
                "?uuid=208cff7a-c8aa-42fe-bf4f-2b8156e37528")
HTTP_UA      = "lidar2map/1.0 (AT BEV ALS-DGM)"
_ATOM        = "{http://www.w3.org/2005/Atom}"
# Étendue Autriche en EPSG:3035 (approx, clippe la grille)
COVERAGE_EXTENT = (4_200_000, 2_600_000, 4_900_000, 2_950_000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(n, e):
    return f"at_bev_dtm_{int(n)}_{int(e)}.tif"


def dalle_subdir(n):
    return f"{int(n)}"


def subdir_from_name(nom):
    m = re.match(r"at_bev_dtm_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("AT-BEV : URL via index ATOM → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("AT-BEV : utiliser discover_dalles()")


# ── Index ATOM (service feed → {(N,E): dataset_feed_url}) ─────────────────────
# Chaque tuile CRS3035 apparaît une fois PAR millésime (Stichtag 2019..2025) ;
# on ne garde que le plus récent par (N,E), comme ca-nrcan garde la dernière
# année. Les entrées DSM et les autres CRS sont écartées par le motif CRS3035/DTM.
_TITLE_NE   = re.compile(r"ALS\s+DTM\s+CRS3035RES\d+mN(\d+)E(\d+)")
_TITLE_YEAR = re.compile(r"Stichtag\s+\d{2}\.\d{2}\.(\d{4})")


def _charger_index(cache_path):
    """Charge (ou construit+cache) l'index du service feed : {'N_E': ds_feed_url}
    pour les tuiles DTM CRS3035, millésime le plus récent par tuile. Bbox-
    indépendant (toute l'Autriche, ~55 tuiles 50 km). None si échec réseau."""
    cache = _lire_cache(cache_path)
    if cache.get("service"):
        return cache["service"]
    print("  AT BEV: downloading the ATOM service index (~55 DTM tiles, once)...",
          flush=True)
    try:
        req = urllib.request.Request(SERVICE_FEED, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        print(f"  ERROR AT BEV service feed: {type(e).__name__}: {e}")
        return None
    best = {}   # "N_E" -> (year, ds_url)
    for entry in root.findall(f"{_ATOM}entry"):
        titre = (entry.findtext(f"{_ATOM}title") or "")
        m = _TITLE_NE.search(titre)
        if not m:
            continue                    # entrées DSM / autres CRS → ignorées
        ym = _TITLE_YEAR.search(titre)
        year = int(ym.group(1)) if ym else 0
        ds_url = None
        for ln in entry.findall(f"{_ATOM}link"):
            if "atom+xml" in (ln.get("type") or ""):
                ds_url = ln.get("href")
                break
        if not ds_url:
            continue
        key = f"{int(m.group(1))}_{int(m.group(2))}"
        prev = best.get(key)
        if prev is None or year > prev[0]:
            best[key] = (year, ds_url)
    service = {k: v[1] for k, v in best.items()}
    if not service:
        print("  AT BEV: no DTM tile found in the service feed")
        return None
    cache["service"] = service
    _ecrire_cache(cache_path, cache)
    print(f"  AT BEV: {len(service)} DTM tile(s) indexed (latest Stichtag)")
    return service


def _resoudre_tif(ds_url):
    """Dataset feed d'une tuile → URL .tif (lien type image/tiff). None si échec."""
    try:
        req = urllib.request.Request(ds_url, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            root = ET.fromstring(r.read())
    except Exception:
        return None
    for ln in root.iter(f"{_ATOM}link"):
        href = ln.get("href") or ""
        if "image/tiff" in (ln.get("type") or "") or href.lower().endswith(".tif"):
            return href
    return None


def _lire_cache(cache_path):
    try:
        return json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ecrire_cache(cache_path, obj):
    try:
        Path(cache_path).write_text(json.dumps(obj), encoding="utf-8")
    except Exception:
        pass


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{at_bev_dtm_<N>_<E>.tif: url_cog} pour les tuiles 50 km DTM intersectant
    bbox_natif (EPSG:3035). Chaque COG est lu en fenêtre par le cœur.

    Résout l'URL .tif (datée) de chaque tuile INTERSECTANTE via son dataset feed
    (1-4 requêtes pour une zone normale), en cachant les URLs résolues."""
    if bbox_natif is None:
        return {}
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    service = _charger_index(cache_path)
    if service is None:
        return None

    x1, y1, x2, y2 = bbox_natif
    e0 = (int(x1) // GRID_M) * GRID_M
    e1 = (int(x2) // GRID_M) * GRID_M
    n0 = (int(y1) // GRID_M) * GRID_M
    n1 = (int(y2) // GRID_M) * GRID_M

    cache = _lire_cache(cache_path)
    resolved = cache.get("resolved", {})
    dalles = {}
    hors = 0
    modifie = False
    for n in range(n0, n1 + 1, GRID_M):
        for e in range(e0, e1 + 1, GRID_M):
            key = f"{n}_{e}"
            ds_url = service.get(key)
            if not ds_url:
                hors += 1
                continue
            tif = resolved.get(key)
            if not tif:
                tif = _resoudre_tif(ds_url)
                if tif:
                    resolved[key] = tif
                    modifie = True
            if tif:
                dalles[dalle_filename(n, e)] = tif
    if modifie:
        cache["resolved"] = resolved
        _ecrire_cache(cache_path, cache)

    print(f"  AT BEV (ALS-DGM 1 m): {len(dalles)} tile(s) in the bbox"
          + (f" ({hors} out of coverage)" if hors else ""))
    return dalles


# ── Hook post-download : réétiqueter le CRS en EPSG:3035 ─────────────────────
def post_download(chemin):
    """Le COG BEV porte un LOCAL_CS "ETRS89 / LAEA Europe" SANS code d'autorité
    (src.crs.to_epsg() → None). Les pixels sont déjà en EPSG:3035 (LAEA) : on
    RÉÉTIQUETTE le CRS en 3035 en place (métadonnée seule, aucune reprojection).
    Sans ça, le warp final vers web-mercator ignorerait la projection réelle.
    Le cœur (telecharger_cog_fenetre) re-valide la dalle après ce hook."""
    import rasterio
    with rasterio.open(chemin, "r+") as src:
        if src.crs is None or src.crs.to_epsg() != 3035:
            src.crs = rasterio.CRS.from_epsg(3035)
