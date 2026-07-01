# providers/ch_swisstopo.py — Suisse, swissALTI3D via swisstopo STAC API
#
# Source : Bundesamt für Landestopografie swisstopo (data.geo.admin.ch).
# Distribution : STAC API (Spatial Temporal Asset Catalog) — paradigme
# encore différent de FR (TMS PBF) et NL (ATOM JSON statique).
#
# Différences architecturales vs FR/NL :
#   - CRS natif EPSG:2056 (CH1903+ / LV95 Mercator suisse)
#   - Découverte via STAC API REST (collection + bbox query → items JSON)
#   - Chaque "item" a 4 assets (COG 0.5m, COG 2m, XYZ 0.5m, XYZ 2m)
#     → on filtre sur le COG 0.5m EPSG:2056
#   - Nommage : swissalti3d_<year>_<E_km>-<N_km>_0.5_2056_<elev>.tif
#     où l'élévation suffixe (5728, etc.) est metadata par tuile, non
#     dérivable de (x, y) seul → URL impossible à construire sans STAC
#
# Status POC : provider validé live contre swisstopo STAC. discover_dalles
# fonctionne, retourne les URLs COG signées. Téléchargement direct OK.

import json
import urllib.parse
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Suisse — swissALTI3D (swisstopo)"
CODE       = "ch-swisstopo"
COUNTRY    = "ch"
LICENSE    = "Free (BGDI Bundesgeodaten-Verordnung)"
DOC_URL    = "https://www.swisstopo.admin.ch/en/height-model-swissalti3d"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2056"       # CH1903+ / LV95 (Swiss Mercator)
RESOLUTION_M       = 0.5
DALLE_KM           = 1                 # tuiles 1×1 km en LV95
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000 px
SEUIL_DALLE_VALIDE = 2_000_000         # COG 0.5m ~2-10 Mo (terrain Swiss)


# ── Endpoints ────────────────────────────────────────────────────────────────
STAC_BASE   = "https://data.geo.admin.ch/api/stac/v1"
COLLECTION  = "ch.swisstopo.swissalti3d"
ITEMS_URL   = f"{STAC_BASE}/collections/{COLLECTION}/items"


# ── Nommage des dalles ───────────────────────────────────────────────────────
# Le nommage Swiss inclut une "élévation" suffixe propre à chaque tuile,
# non dérivable de (E_km, N_km) seuls. discover_dalles est obligatoire.

def dalle_filename(x_km, y_km):
    raise NotImplementedError(
        "swissALTI3D nomme par swissalti3d_<year>_<E>-<N>_<res>_<crs>_<elev>.tif "
        "— l'élévation n'est connue que via STAC API. Utiliser discover_dalles().")


def dalle_subdir(x_km):
    return ""   # COG cachés à plat


def subdir_from_name(nom):
    return None


def dalle_url(x_km, y_km):
    raise NotImplementedError("Voir dalle_filename : STAC requis.")


def dalle_url_by_name(nom):
    """URL conventionnelle. NB : STAC retourne déjà l'URL exacte signée
    dans assets[].href, c'est préférable d'utiliser celle-là."""
    return f"https://data.geo.admin.ch/{COLLECTION}/{nom.rsplit('_', 3)[0]}/{nom}"


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError(
        "swissALTI3D : utiliser discover_dalles() — pas de grille dérivable.")


# ── Découverte via STAC API ──────────────────────────────────────────────────
HTTP_UA = "lidar2map/1.0 (swisstopo STAC)"


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Interroge la STAC API swisstopo pour les items de swissALTI3D dans la
    bbox WGS84. Pour chaque item, filtre sur le COG 0.5m EPSG:2056 et
    construit {nom: url} prêt à télécharger.

    bbox_wgs84 : (lon_min, lat_min, lon_max, lat_max) — STAC accepte WGS84
    bbox_natif : ignoré ici (STAC retourne déjà filtré par bbox WGS)
    cache_path : JSON où mettre en cache les réponses (pagination par 100)
    workers    : ignoré (STAC paginated, séquentiel)

    Retourne {nom_fichier: url_telechargement_direct} ou None si erreur.
    """
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Pagination STAC : on suit les liens "next" jusqu'à épuisement
    bbox_str = f"{lon_min},{lat_min},{lon_max},{lat_max}"
    url = f"{ITEMS_URL}?bbox={bbox_str}&limit=100"

    items = []
    print(f"  swisstopo STAC: querying {COLLECTION} bbox {bbox_str[:60]}...",
          flush=True)
    n_pages = 0
    while url:
        req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
        except Exception as e:
            print(f"  ERROR STAC ({type(e).__name__}): {e}")
            return None
        items.extend(data.get("features", []))
        n_pages += 1
        # Lien "next" pour pagination (si existe)
        url = None
        for link in data.get("links", []):
            if link.get("rel") == "next" and link.get("href"):
                url = link["href"]
                break

    # Cache les items bruts (utile pour debug, ré-utilisable)
    try:
        cache_path.write_text(json.dumps({"items": items}), encoding="utf-8")
    except Exception:
        pass

    # Filtre 1 : retient le COG 0.5m EPSG:2056 (asset nommé *_0.5_2056_*.tif)
    # Filtre 2 : intersection STRICTE avec bbox_natif (LV95). La caller passe
    # une bbox_wgs84 élargie de ±0.05° (~5.5 km) pour les providers TMS (FR) ;
    # sans ce 2e filtre, STAC retourne des dizaines de dalles hors zone réelle
    # (genève 1 km → 251 dalles au lieu de 4).
    # On dérive la bbox de chaque dalle depuis son ID :
    #   swissalti3d_<year>_<E_km>-<N_km>_... → couvre (E*1000, N*1000) → +1000m
    import re as _re
    # Feature ID = "swissalti3d_<year>_<E_km>-<N_km>" (sans suffixe)
    # Asset name = "...-<N_km>_<res>_<crs>_<elev>.tif" (avec suffixe)
    # On match les deux : E_km-N_km optionnellement suivi de _.
    _id_pattern = _re.compile(r"swissalti3d_\d+_(\d+)-(\d+)(?:_|$)")

    def _dalle_intersect_bbox_natif(item_id):
        if bbox_natif is None:
            return True
        m = _id_pattern.search(item_id)
        if not m:
            return True
        e_km, n_km = int(m.group(1)), int(m.group(2))
        fx0, fy0 = e_km * 1000, n_km * 1000
        fx1, fy1 = fx0 + 1000, fy0 + 1000
        zx0, zy0, zx1, zy1 = bbox_natif
        return not (fx1 < zx0 or fx0 > zx1 or fy1 < zy0 or fy0 > zy1)

    # swissALTI3D peut avoir plusieurs millésimes par tuile (ex: 2019, 2021).
    # On collecte tout, puis on dédupplique en gardant la dernière année par
    # couple (E_km, N_km) — la plus fraîche acquisition.
    _year_pattern = _re.compile(r"swissalti3d_(\d+)_(\d+)-(\d+)")
    candidats = {}   # (E_km, N_km) -> (year, nom, url)
    n_filtered_geo = 0
    n_total_assets = 0
    for it in items:
        if not _dalle_intersect_bbox_natif(it.get("id", "")):
            n_filtered_geo += 1
            continue
        assets = it.get("assets", {}) or {}
        for nom, ass in assets.items():
            if not (nom.endswith(".tif")
                    and "_0.5_2056_" in nom
                    and ass.get("type", "").startswith("image/tiff")):
                continue
            href = ass.get("href")
            if not href:
                continue
            n_total_assets += 1
            m = _year_pattern.search(nom)
            if not m:
                continue
            year = int(m.group(1))
            e_km = int(m.group(2))
            n_km = int(m.group(3))
            key = (e_km, n_km)
            prev = candidats.get(key)
            if prev is None or year > prev[0]:
                candidats[key] = (year, nom, href)

    dalles = {nom: href for (_y, nom, href) in candidats.values()}

    msg = (f"  swisstopo : {n_pages} page(s) STAC → {len(items)} items, "
           f"{n_total_assets} COG 0.5m → {len(dalles)} dalles retenues "
           f"(dernier millésime par tuile)")
    if n_filtered_geo:
        msg += f" — {n_filtered_geo} hors bbox LV95 filtrées"
    print(msg)
    return dalles
