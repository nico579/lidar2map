# providers/de_niedersachsen.py — Allemagne (Basse-Saxe), DGM1 LiDAR (COG via STAC)
#
# Source : LGLN (Landesamt für Geoinformation und Landesvermessung Niedersachsen)
#   STAC API : https://dgm.stac.lgln.niedersachsen.de
#
# Étend la couverture allemande (après Bavière + NRW). Basse-Saxe = nord-ouest,
# plat — pas de montagne, mais grosse surface + données impeccables.
#
# Paradigme : identique à ch_swisstopo (STAC API), donc on le calque.
#   - CRS natif EPSG:25832 (UTM 32N), grille 1 km, 1 m/px (1000×1000).
#   - Distribution en COG (Cloud-Optimized GeoTIFF, float32 LZW) sur S3 — chaque
#     item STAC porte l'asset "dgm1-tif" avec son href direct.
#   - Nommage par coin SW (Xmin, Ymin) : dgm1_32_<E_km>_<N_km>_1_ni_<année>.tif
#     (même convention que NRW, vérifiée empiriquement coin SW). L'année varie
#     par tuile → URL non synthétisable → la découverte passe par STAC.
#
# Self-contained : stdlib uniquement.

import json
import re
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Allemagne (Basse-Saxe) — DGM1 LiDAR (COG)"
CODE       = "de-niedersachsen"
COUNTRY    = "de"          # ISO 3166-1 alpha-2 — utilisé pour cache/lidar/<country>/
LICENSE    = "CC BY 4.0 — © LGLN (Niedersachsen)"
DOC_URL    = "https://opengeodata.lgln.niedersachsen.de/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"         # ETRS89 / UTM zone 32N
RESOLUTION_M       = 1.0                  # DGM1 = grille 1 m
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 1000 px
SEUIL_DALLE_VALIDE = 500_000              # octets


# ── Endpoints STAC ───────────────────────────────────────────────────────────
STAC_BASE   = "https://dgm.stac.lgln.niedersachsen.de"
COLLECTION  = "dgm1"
SEARCH_URL  = f"{STAC_BASE}/search"
HTTP_UA     = "lidar2map/1.0 (LGLN Niedersachsen STAC)"


# ── Nommage : non synthétisable (année dans le nom) → STAC requis ────────────
_ID_RE = re.compile(r"dgm1_32_(\d+)_(\d+)_1_ni_(\d+)")


def dalle_filename(x_km, y_km):
    raise NotImplementedError(
        "Basse-Saxe : nom dépendant de l'année de levé → utiliser discover_dalles()")


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    """Sous-dossier (colonne Est) déduit du nom, ou None."""
    m = re.match(r"dgm1_32_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError(
        "Basse-Saxe : URL dépendante de l'année → utiliser discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError(
        "Basse-Saxe : pas de grille dérivable (URL via STAC) — discover_dalles()")


# ── Découverte via STAC API (calqué sur ch_swisstopo) ────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Interroge la STAC API LGLN pour les tuiles DGM1 dans la bbox WGS84, filtre
    l'asset COG (dgm1-tif), et retourne {nom: url_cog}.

    bbox_wgs84 : (lon_min, lat_min, lon_max, lat_max) — STAC filtre dessus.
    bbox_natif : (x_min, y_min, x_max, y_max) EPSG:25832 — 2e filtre strict
                 (la bbox WGS passée par le pipeline est élargie de ±0.05°).
    cache_path : JSON où cacher les items bruts.
    workers    : ignoré (STAC paginé séquentiel).

    Retourne {nom_fichier: href} ou None si erreur réseau.
    """
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    bbox_str = f"{lon_min},{lat_min},{lon_max},{lat_max}"
    url = f"{SEARCH_URL}?collections={COLLECTION}&bbox={bbox_str}&limit=100"

    items, n_pages = [], 0
    print(f"  LGLN STAC: querying {COLLECTION} bbox {bbox_str[:60]}...", flush=True)
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
        url = None
        for link in data.get("links", []):
            if link.get("rel") == "next" and link.get("href"):
                url = link["href"]
                break

    try:
        cache_path.write_text(json.dumps({"items": items}), encoding="utf-8")
    except Exception:
        pass

    def _intersecte_natif(e_km, n_km):
        if bbox_natif is None:
            return True
        fx0, fy0 = e_km * 1000, n_km * 1000      # coin SW
        fx1, fy1 = fx0 + 1000, fy0 + 1000
        zx0, zy0, zx1, zy1 = bbox_natif
        return not (fx1 < zx0 or fx0 > zx1 or fy1 < zy0 or fy0 > zy1)

    # Dédup par (E_km, N_km) en gardant l'année la plus récente.
    candidats = {}   # (E, N) -> (year, nom, href)
    for it in items:
        m = _ID_RE.search(it.get("id", ""))
        if not m:
            continue
        e_km, n_km, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not _intersecte_natif(e_km, n_km):
            continue
        # asset COG : "dgm1-tif" (type image/tiff cloud-optimized)
        href = None
        for nom_a, ass in (it.get("assets") or {}).items():
            t = ass.get("type", "")
            if "tiff" in t and ass.get("href"):
                href = ass["href"]
                break
        if not href:
            continue
        nom = href.rsplit("/", 1)[-1]            # dgm1_32_E_N_1_ni_year.tif
        key = (e_km, n_km)
        prev = candidats.get(key)
        if prev is None or year > prev[0]:
            candidats[key] = (year, nom, href)

    dalles = {nom: href for (_y, nom, href) in candidats.values()}
    print(f"  Lower Saxony: {n_pages} STAC page(s) → {len(items)} items "
          f"→ {len(dalles)} tiles (latest vintage per tile)")
    return dalles
