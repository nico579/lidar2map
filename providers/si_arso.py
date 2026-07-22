# providers/si_arso.py — Slovénie, DMR1 1m (LiDAR national) via ARSO/eVode
#
# Source : ARSO (Agencija RS za okolje) — laser scanning national 2011-2015
#   Viewer eVode : http://gis.arso.gov.si/evode/
#   Index : ArcGIS REST Lidar_fishnet_D96 (couche lay_LIDAR_fishnet_D96)
#
# Paradigme : index REST + dalles fichiers directes (validé par sondage 2026-06-11).
#   1. Query du fishnet par enveloppe EPSG:3794 → attributs NAME ("462_101",
#      coin SW de la dalle en km) et BLOK ("b_35", répertoire de distribution).
#   2. Dalle : http://gis.arso.gov.si/lidar/dmr1/{blok}/D96TM/TM1_{x}_{y}.asc
#      → TEXTE "x;y;z" (1 ligne/pixel), 1 m posting, dalle 1 km = 10⁶ lignes
#      (~28 Mo). Conversion .asc → GeoTIFF en place par post_fetch (grille
#      régulière → reshape numpy, pas d'interpolation).
#   - CRS natif EPSG:3794 (Slovenia 1996 / Slovene National Grid, D96/TM)
#   - Couverture nationale complète (acquisitions 2011-2015)
#   - Pas de clé, pas de compte. HTTP simple (pas de https sur gis.arso.gov.si).
#   - La Slovénie est LE terrain historique de l'archéo-LiDAR européenne
#     (Kokalj/ZRC SAZU, auteurs de RVT) — données très utilisées en prospection.
#
# Self-contained : stdlib uniquement (numpy/rasterio requis au runtime
# pour post_fetch, comme cz_cuzk/se_lantmateriet).

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Slovénie — DMR1 (ARSO eVode, LiDAR 2011-2015)"
CODE       = "si-arso"
COUNTRY    = "si"
LICENSE    = "Donnée publique ARSO/MOP — réutilisation libre avec attribution"
DOC_URL    = "http://gis.arso.gov.si/evode/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3794"          # D96/TM (Slovene National Grid)
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000 px
SEUIL_DALLE_VALIDE = 200_000              # Float32 1000×1000 deflate ~1-3 Mo


# ── Endpoints ────────────────────────────────────────────────────────────────
FISHNET_URL = ("http://gis.arso.gov.si/arcgis/rest/services/"
               "Lidar_fishnet_D96/MapServer/1/query")
DALLE_TMPL  = "http://gis.arso.gov.si/lidar/dmr1/{blok}/D96TM/TM1_{x}_{y}.asc"
HTTP_UA     = "lidar2map/1.0 (ARSO DMR1)"


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"si_dmr1_{x_km}_{y_km}.tif"


def subdir_from_name(nom):
    m = re.match(r"si_dmr1_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    # L'URL exige le BLOK (répertoire de distribution), connu seulement via
    # l'index fishnet → passer par discover_dalles().
    raise NotImplementedError("SI : URL via index fishnet → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    """Grille 1 km D96/TM — sert au comptage à priori ; les URLs réelles
    viennent de discover_dalles (qui filtre aussi les dalles inexistantes)."""
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


# ── Découverte via l'index fishnet (ArcGIS REST) ─────────────────────────────
def _query_fishnet(x1, y1, x2, y2):
    """Query par enveloppe EPSG:3794 → {NAME: BLOK}. Paginé (ArcGIS limite
    typiquement à 1000 enregistrements par réponse)."""
    mapping = {}
    offset = 0
    while True:
        params = urllib.parse.urlencode({
            "geometry":      json.dumps({"xmin": x1, "ymin": y1,
                                         "xmax": x2, "ymax": y2,
                                         "spatialReference": {"wkid": 3794}}),
            "geometryType":  "esriGeometryEnvelope",
            "inSR":          3794,
            "spatialRel":    "esriSpatialRelIntersects",
            "outFields":     "NAME,BLOK",
            "returnGeometry": "false",
            "resultOffset":  offset,
            "f":             "json",
        })
        req = urllib.request.Request(f"{FISHNET_URL}?{params}",
                                     headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        if "error" in data:
            raise RuntimeError(f"fishnet ARSO : {data['error']}")
        feats = data.get("features", [])
        for f in feats:
            a = f.get("attributes", {})
            nom, blok = a.get("NAME"), a.get("BLOK")
            if nom and blok:
                mapping[nom] = blok
        if not data.get("exceededTransferLimit") or not feats:
            break
        offset += len(feats)
    return mapping


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Retourne {si_dmr1_X_Y.tif: url_asc} pour les dalles existantes dans
    bbox_natif (EPSG:3794). Le mapping NAME→BLOK est mis en cache cumulatif
    sur disque : les zones déjà interrogées ne re-touchent pas le réseau.

    Les clés finissent en .tif : le contenu téléchargé est du texte x;y;z,
    converti en place en GeoTIFF par post_fetch (détection par contenu).
    """
    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = bbox_natif
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    # Si toutes les dalles de la grille théorique sont déjà connues du cache
    # (présentes OU absentes — les absentes sont mémorisées avec blok=None),
    # pas de requête réseau.
    grille = dalles_pour_bbox(x1, y1, x2, y2)
    noms_grille = [f"{x}_{y}" for x, y in grille]
    if not all(n in cache for n in noms_grille):
        try:
            mapping = _query_fishnet(x1, y1, x2, y2)
        except Exception as e:
            print(f"  ARSO fishnet : {type(e).__name__}: {e}")
            # Repli sur le cache seul (zones déjà vues) — sinon échec total.
            mapping = None
        if mapping is not None:
            for n in noms_grille:
                cache[n] = mapping.get(n)   # None = hors couverture
            try:
                cache_path.write_text(json.dumps(cache), encoding="utf-8")
            except Exception:
                pass
        elif not any(n in cache for n in noms_grille):
            return None   # réseau KO et rien en cache

    dalles = {}
    hors_couv = 0
    for n in noms_grille:
        blok = cache.get(n)
        if not blok:
            hors_couv += 1
            continue
        x_km, y_km = n.split("_")
        dalles[dalle_filename(x_km, y_km)] = DALLE_TMPL.format(
            blok=blok, x=x_km, y=y_km)
    print(f"  ARSO DMR1: {len(dalles)} tile(s) in the bbox"
          + (f" ({hors_couv} out of coverage)" if hors_couv else ""))
    return dalles


# ── Hook post_fetch : .asc « x;y;z » → GeoTIFF ───────────────────────────────
def post_fetch(chemin):
    """Convertit en place une dalle ASC ARSO (texte 'x;y;z' par ligne, grille
    régulière 1 m) en GeoTIFF Float32 deflate. Détection par CONTENU (chiffre
    en tête + ';' dans la 1re ligne), pas par suffixe : le pipeline nomme le
    fichier .tif en y écrivant la réponse brute du serveur.

    Pas d'interpolation : les points sont les centres des cellules d'une
    grille régulière → placement direct par indices. Les trous éventuels
    (plans d'eau) restent à nodata −9999.
    """
    chemin = Path(chemin)
    try:
        with open(chemin, "rb") as fh:
            tete = fh.read(64)
    except OSError:
        return
    if tete[:4] in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
        return  # déjà un GeoTIFF
    premiere = tete.split(b"\n", 1)[0]
    if b";" not in premiere or not premiere[:1].isdigit():
        return  # ni TIFF ni ASC ARSO — laisser le validateur trancher

    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds

    raw = chemin.read_bytes()
    vals = np.array(raw.replace(b";", b" ").split(), dtype=np.float64)
    if vals.size % 3:
        raise ValueError(f"ASC ARSO malformé : {vals.size} valeurs (≠ 3n)")
    pts = vals.reshape(-1, 3)
    xs, ys, zs = pts[:, 0], pts[:, 1], pts[:, 2]

    res = RESOLUTION_M
    x0, x1 = float(xs.min()), float(xs.max())
    y0, y1 = float(ys.min()), float(ys.max())
    nx = int(round((x1 - x0) / res)) + 1
    ny = int(round((y1 - y0) / res)) + 1
    grid = np.full((ny, nx), -9999.0, dtype=np.float32)
    ci = np.rint((xs - x0) / res).astype(np.int64)
    ri = np.rint((y1 - ys) / res).astype(np.int64)   # origine haut-gauche
    grid[ri, ci] = zs

    # Coordonnées ASC = centres de cellules → bornes décalées d'un demi-pixel
    transform = from_bounds(x0 - res / 2, y0 - res / 2,
                            x1 + res / 2, y1 + res / 2, nx, ny)
    tmp = chemin.with_suffix(".tif_tmp")
    with rasterio.open(str(tmp), "w",
                       driver="GTiff", height=ny, width=nx,
                       count=1, dtype="float32",
                       crs=rasterio.CRS.from_epsg(3794),
                       transform=transform, nodata=-9999,
                       compress="deflate", predictor=2, tiled=True) as dst:
        dst.write(grid, 1)
    tmp.replace(chemin)
