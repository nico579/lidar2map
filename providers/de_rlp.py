# providers/de_rlp.py — Rhénanie-Palatinat (Allemagne), DGM1 1 m via Metalink
#
# Source : LVermGeo Rheinland-Pfalz (GeoShop / OpenData « Geodaten für alle »)
#   Produit : https://geoshop.rlp.de/opendata-dgm1.html
#   Metalink état-entier : https://geobasis-rlp.de/data/dgm1/current/meta4/dgm1_tif_07.meta4
#   Fiche : csw registry.gdi-de.org id de.rp.vermkv/ab69aa3d-e786-41f8-95dc-7b34abb06c41
#
# Paradigme : Metalink 4.0 (.meta4) → index de tuiles (calque de_bayern), MAIS
#   l'URL n'est PAS déterministe (le nom encode l'ANNÉE de levé, variable par
#   tuile : dgm1_32_<E>_<N>_1_rp_<année>.tif) → on stocke {(<E>,<N>): url} depuis
#   le Metalink (comme de_thueringen), pas juste un set de coordonnées.
#   - CRS natif EPSG:25832 (ETRS89 / UTM 32N). Les GeoTIFF portent un CRS
#     COMPOSÉ (25832 + hauteur DHHN2016) dont `to_epsg()` = None → post_fetch
#     réétiquette en 25832 pur (métadonnée seule, comme de_st).
#   - Résolution 1 m, dalle 1×1 km (1000×1000), GeoTIFF DIRECT (pas de ZIP).
#   - Licence : dl-de/zero-2-0 (Datenlizenz Deutschland Zero 2.0), domaine public.
#   - Pas de clé, pas de compte. ~21 000 tuiles couvrant tout le Land.
#
# Self-contained : stdlib uniquement (rasterio requis au runtime post_fetch).

import json
import re
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Rhénanie-Palatinat — DGM1 1 m (LVermGeo, Metalink)"
CODE       = "de-rlp"
COUNTRY    = "de"
LICENSE    = "dl-de/zero-2-0 — © GeoBasis-DE/LVermGeoRP"
DOC_URL    = "https://geoshop.rlp.de/opendata-dgm1.html"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25832"         # ETRS89 / UTM 32N
RESOLUTION_M       = 1.0                  # DGM1 1 m
DALLE_KM           = 1                     # tuile 1×1 km → 1000×1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000
SEUIL_DALLE_VALIDE = 500_000              # GeoTIFF 1000×1000 ~1,3 Mo


# ── Endpoints ────────────────────────────────────────────────────────────────
METALINK_URL = "https://geobasis-rlp.de/data/dgm1/current/meta4/dgm1_tif_07.meta4"
HTTP_UA      = "lidar2map/1.0 (RP DGM1)"

# Exemple réel pour le test de disjonction intra-pays (nommage non-formule).
SAMPLE_DALLE = "rp_dgm1_446_5537.tif"


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"rp_dgm1_{int(x_km)}_{int(y_km)}.tif"


def subdir_from_name(nom):
    m = re.match(r"rp_dgm1_(\d+)_", nom)
    return m.group(1) if m else None


def dalles_pour_bbox(x1, y1, x2, y2):
    """Grille 1 km EPSG:25832 — borne haute demi-ouverte (cf. de_bayern)."""
    step = DALLE_KM * 1000
    x_start, x_end = int(x1 // step), int(x2 // step)
    if x2 % step == 0 and x_end > x_start:
        x_end -= 1
    y_start, y_end = int(y1 // step), int(y2 // step)
    if y2 % step == 0 and y_end > y_start:
        y_end -= 1
    return [(x_km, y_km)
            for x_km in range(x_start, x_end + 1)
            for y_km in range(y_start, y_end + 1)]


# ── Index Metalink (téléchargé une fois, caché) ──────────────────────────────
# <url>...dgm1_32_<E>_<N>_1_rp_<année>.tif</url> — coords + année dans l'URL.
_URL_RE = re.compile(r"<url[^>]*>(\s*\S*dgm1_32_(\d+)_(\d+)_[^<]+\.tif)\s*</url>")


def _construire_index(cache_path):
    """{'<E_km>_<N_km>': url_tif} pour les ~21 000 tuiles. Caché sur disque
    (Metalink ~6 Mo, change rarement). None si échec réseau total."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        try:
            idx = json.loads(cache_path.read_text(encoding="utf-8"))
            if idx:
                return idx
        except Exception:
            pass
    print("  RP LVermGeo: downloading the Metalink index (~6 MB, once)...",
          flush=True)
    try:
        req = urllib.request.Request(METALINK_URL, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            texte = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  ERROR RP Metalink: {type(e).__name__}: {e}")
        return None
    index = {}
    for url, e_km, n_km in _URL_RE.findall(texte):
        index[f"{e_km}_{n_km}"] = url.strip()
    if not index:
        return None
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(index), encoding="utf-8")
    except Exception:
        pass
    print(f"  RP LVermGeo: {len(index)} tiles in the Land coverage")
    return index


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{rp_dgm1_<E>_<N>.tif: url_tif} pour les tuiles 1 km de bbox_natif (EPSG:25832)."""
    if bbox_natif is None:
        return {}
    index = _construire_index(cache_path)
    if index is None:
        return None
    grille = dalles_pour_bbox(*bbox_natif)
    dalles = {}
    hors = 0
    for x_km, y_km in grille:
        url = index.get(f"{x_km}_{y_km}")
        if url:
            dalles[dalle_filename(x_km, y_km)] = url
        else:
            hors += 1
    print(f"  DE Rheinland-Pfalz (DGM1 1m): {len(dalles)} tile(s) in the bbox"
          + (f" ({hors} out of coverage)" if hors else ""))
    return dalles


# ── Hook post_fetch : CRS composé → EPSG:25832 pur ───────────────────────────
def post_fetch(chemin):
    """Les GeoTIFF RP portent un CRS COMPOSÉ (25832 + hauteur DHHN2016) dont
    `to_epsg()` = None (gêne le warp 3857 et le contrôle CRS du smoke). On
    réétiquette en EPSG:25832 pur EN PLACE (la donnée EST en UTM 32N ; on ne
    fait que retirer la composante verticale, pas de reprojection)."""
    from pathlib import Path as _P
    p = _P(chemin)
    try:
        with open(p, "rb") as fh:
            if fh.read(2) not in (b"II", b"MM"):
                return
    except OSError:
        return
    import rasterio
    with rasterio.open(p, "r+") as src:
        if src.crs is None or src.crs.to_epsg() != 25832:
            src.crs = rasterio.CRS.from_epsg(25832)
