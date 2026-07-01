# providers/cz_cuzk.py — République Tchèque, DMR 5G via ČÚZK (LAZ zippés)
#
# Source : ČÚZK (Zeměměřický úřad / Czech Office for Surveying, Mapping and Cadastre)
#   https://ags.cuzk.cz/geoprohlizec/?atom=dm5g
#   Atom feed : https://atom.cuzk.cz/DMR5G-SJTSK/DMR5G-SJTSK.xml
#
# Paradigme : Atom INSPIRE à DEUX niveaux → URLs directes ZIP (ZIP = 1 .laz).
#   1. Feed dataset (16k entries, 1 par feuille = tuile 2.5km) : chaque entry a
#      un georss:polygon (bornes WGS84) + un lien alternate atom+xml vers le
#      "datasetFeed" de la feuille.
#   2. datasetFeed (1 entry) : lien application/vnd.laszip → l'URL ZIP réelle
#      (https://openzu.cuzk.gov.cz/opendata/DMR5G/epsg-5514/<feuille>.zip).
#   - CRS natif EPSG:5514 (S-JTSK / Krovak East North)
#   - Résolution ~0.5m (densité ~5 pts/m², maillage 1m)
#   - Tuiles 2500×2500 m, nommées par code feuille Krovak (ex. BENE09)
#   - Licence : Open Data (ČÚZK), libre sans restriction
#   - NÉCESSITE post_fetch : dézip + conversion LAZ → GeoTIFF (PDAL ou laspy)
#
# NB : EPSG:5514 a des axes inversés (Krovak East North) par rapport au Krovak
# classique (EPSG:5513). Le CRS est négatif en Y (valeurs ~-600000, ~-1100000).
# GDAL/rasterio gèrent transparentement EPSG:5514.
#
# Self-contained : stdlib uniquement (PDAL / laspy requis au runtime).

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "République Tchèque — DMR 5G (ČÚZK, LAZ)"
CODE       = "cz-cuzk"
COUNTRY    = "cz"
LICENSE    = "Open Data ČÚZK — libre sans restriction"
DOC_URL    = "https://ags.cuzk.cz/geoprohlizec/?atom=dm5g"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:5514"          # S-JTSK / Krovak East North
RESOLUTION_M       = 1.0                  # maillage 1m (densité ~5 pts/m²)
DALLE_KM           = 2.5                  # tuiles 2500×2500 m
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 2500
SEUIL_DALLE_VALIDE = 500_000


# ── Endpoints ────────────────────────────────────────────────────────────────
ATOM_URL = "https://atom.cuzk.cz/DMR5G-SJTSK/DMR5G-SJTSK.xml"
HTTP_UA  = "lidar2map/1.0 (CUZK DMR5G)"
_NS = {"atom": "http://www.w3.org/2005/Atom",
       "georss": "http://www.georss.org/georss"}


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    # Grille non utilisée (découverte par Atom) — conservé pour compat.
    return f"cz_dmr5g_{int(x_km):+07d}_{int(y_km):+08d}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km):+07d}"


def subdir_from_name(nom):
    # Tuiles nommées par code feuille (cz_dmr5g_BENE09.tif) → sous-dossier =
    # préfixe alpha (regroupe les feuilles voisines, évite 16k fichiers à plat).
    m = re.match(r"cz_dmr5g_([A-Za-z]+)", nom)
    return m.group(1)[:4].upper() if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("CZ : URL via Atom feed → utiliser discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("CZ : utiliser discover_dalles()")


# ── Découverte via Atom INSPIRE (2 niveaux) ──────────────────────────────────
def _bbox_from_polygon(text):
    """georss:polygon 'lat lon lat lon ...' → (lat_min, lon_min, lat_max, lon_max)."""
    vals = list(map(float, text.split()))
    if len(vals) < 8:
        return None
    lats, lons = vals[0::2], vals[1::2]
    return (min(lats), min(lons), max(lats), max(lons))


def _construire_index(cache_path):
    """Télécharge et parse le feed top-level → {feuille: {sub, bbox}}.
    Mis en cache sur disque (cache_path) : ~16k feuilles, téléchargé une fois.
    Retourne None en cas d'échec réseau total."""
    if cache_path.exists():
        try:
            idx = json.loads(cache_path.read_text(encoding="utf-8"))
            if idx:
                return idx
        except Exception:
            pass
    print("  ČÚZK: downloading the Atom index (~16k sheets, once)...",
          flush=True)
    try:
        req = urllib.request.Request(ATOM_URL, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            root = ET.parse(r).getroot()
    except Exception as e:
        print(f"  ERROR CZ Atom index: {e}")
        return None
    index = {}
    for entry in root.findall("atom:entry", _NS):
        sub = None
        for link in entry.findall("atom:link", _NS):
            if (link.get("rel") == "alternate"
                    and "atom+xml" in (link.get("type") or "")):
                sub = link.get("href")
                break
        if not sub:
            continue
        poly = entry.find("georss:polygon", _NS)
        if poly is None or not poly.text:
            continue
        bb = _bbox_from_polygon(poly.text)
        if not bb:
            continue
        # code feuille = suffixe du nom de datasetFeed (..._BENE09.xml → BENE09)
        feuille = sub.rsplit("/", 1)[-1].rsplit(".", 1)[0].rsplit("_", 1)[-1]
        index[feuille] = {"sub": sub, "bbox": list(bb)}
    try:
        cache_path.write_text(json.dumps(index), encoding="utf-8")
    except Exception:
        pass
    print(f"  ČÚZK: {len(index)} sheets indexed")
    return index


def _resoudre_zip(sub_url):
    """datasetFeed (niveau 2) → URL ZIP (lien application/vnd.laszip / .zip)."""
    try:
        req = urllib.request.Request(sub_url, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            root = ET.parse(r).getroot()
    except Exception:
        return None
    for entry in root.findall("atom:entry", _NS):
        for link in entry.findall("atom:link", _NS):
            href = link.get("href", "") or ""
            typ = link.get("type", "") or ""
            if "laszip" in typ or "zip" in typ or href.lower().endswith(".zip"):
                return href
    return None


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Retourne {nom_interne.tif: url_zip} pour les tuiles LAZ intersectant la
    bbox. Traversée Atom INSPIRE 2 niveaux ; filtrage par georss:polygon WGS84.

    Les clés finissent en .tif : le contenu téléchargé est un ZIP, converti en
    place en GeoTIFF par post_fetch (détection par magic bytes PK, pas suffixe).
    """
    if bbox_natif is None:
        return {}
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # bbox de requête en WGS84 : le pipeline passe (lon_min, lat_min, lon_max, lat_max)
    if bbox_wgs84 is not None:
        lo1, la1, lo2, la2 = bbox_wgs84
    else:
        # Repli : approximation Krovak EN → WGS84 depuis bbox_natif
        import math
        x1, y1, x2, y2 = bbox_natif
        def _approx(x, y):
            lon = (x + 853000) / (-111000 / math.cos(math.radians(50))) + 15.5
            lat = (y + 1082000) / 111000 + 49.8
            return lon, lat
        lo1, la1 = _approx(x1, y1)
        lo2, la2 = _approx(x2, y2)
    qlon_min, qlon_max = min(lo1, lo2), max(lo1, lo2)
    qlat_min, qlat_max = min(la1, la2), max(la1, la2)

    index = _construire_index(cache_path)
    if index is None:
        return None

    # Intersection bbox (georss:polygon : lat_min, lon_min, lat_max, lon_max)
    matches = []
    for feuille, info in index.items():
        la_min, lo_min, la_max, lo_max = info["bbox"]
        if (lo_max < qlon_min or lo_min > qlon_max
                or la_max < qlat_min or la_min > qlat_max):
            continue
        matches.append((feuille, info))
    if not matches:
        print("  ČÚZK: no sheet in the bbox")
        return {}

    dalles = {}
    for feuille, info in matches:
        url_zip = _resoudre_zip(info["sub"])
        if url_zip:
            dalles[f"cz_dmr5g_{feuille}.tif"] = url_zip
        else:
            print(f"  ČÚZK: datasetFeed {feuille} without ZIP link")
    print(f"  ČÚZK: {len(dalles)} LAZ tile(s) in the bbox")
    return dalles


# ── Hook post_fetch : dézip + conversion LAZ → GeoTIFF ───────────────────────
# Réutilise exactement le même pattern que se_lantmateriet
# (le pipeline LAZ→GeoTIFF est identique, seul le CRS change : EPSG:5514)

RESOLUTION_LAZ = 1.0  # résolution cible de l'interpolation


def post_fetch(chemin):
    """Dézip + conversion LAZ → GeoTIFF DTM (PDAL ou laspy+scipy).
    Détecte le ZIP par magic bytes (PK), pas par suffixe : le pipeline a pu
    nommer le fichier .tif tout en y écrivant le contenu ZIP téléchargé."""
    from pathlib import Path as _Path
    chemin = _Path(chemin)

    # Détecter ZIP par magic bytes
    try:
        with open(chemin, "rb") as fh:
            magic = fh.read(4)
        if magic[:2] != b"PK":
            return  # déjà un GeoTIFF
    except OSError:
        return

    # Dézip → .laz (dans un nom temporaire à côté, suffixe .tif possible)
    import zipfile
    dossier = chemin.parent
    laz_path = None
    with zipfile.ZipFile(chemin) as z:
        members = [m for m in z.namelist() if m.lower().endswith(".laz")]
        if not members:
            raise ValueError(f"Aucun .laz dans {chemin.name}")
        z.extract(members[0], dossier)
        laz_path = dossier / members[0]
    chemin.unlink(missing_ok=True)

    tif_path = chemin.with_suffix(".tif")

    # Conversion LAZ → GeoTIFF
    try:
        _laz_to_tif_pdal(laz_path, tif_path)
    except Exception as e_pdal:
        try:
            _laz_to_tif_laspy(laz_path, tif_path, crs_epsg=5514)
        except Exception as e_laspy:
            raise RuntimeError(
                f"LAZ→GeoTIFF échoué.\n  PDAL: {e_pdal}\n  laspy: {e_laspy}"
            )
    laz_path.unlink(missing_ok=True)


def _laz_to_tif_pdal(laz_path, tif_path):
    import subprocess, json as _json, tempfile
    pipeline = {
        "pipeline": [
            str(laz_path),
            {"type": "filters.range", "limits": "Classification[2:2]"},
            {"type": "writers.gdal", "filename": str(tif_path),
             "resolution": RESOLUTION_LAZ, "output_type": "min",
             "gdaldriver": "GTiff",
             "gdalopts": "COMPRESS=DEFLATE,PREDICTOR=2,TILED=YES",
             "nodata": -9999}
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                     delete=False, encoding="utf-8") as f:
        _json.dump(pipeline, f)
        p = f.name
    try:
        subprocess.check_call(["pdal", "pipeline", p], timeout=300)
    finally:
        Path(p).unlink(missing_ok=True)


def _laz_to_tif_laspy(laz_path, tif_path, crs_epsg=5514):
    """Conversion LAZ → GeoTIFF DTM via laspy + scipy (fallback sans PDAL).

    INTERPOLATION (griddata linéaire), pas binning : les LAZ DMR5G/NH sont des
    nuages de points SOL épars (~0.1–1 pt/m²) — un binning min à 1m laisserait
    la majorité des cellules vides. L'interpolation produit un DTM continu.
    Reste rapide ici (nuages de quelques 10⁵–10⁶ points) ; pour de très gros
    nuages denses, PDAL (chemin principal) est préférable.

    NÉCESSITE un backend LAZ pour laspy (lazrs ou laszip) — sans lui,
    laspy lève 'No LazBackend selected, cannot decompress data'."""
    import laspy
    import numpy as np
    from scipy.interpolate import griddata

    las = laspy.read(str(laz_path))
    mask = las.classification == 2          # points sol (DTM)
    if mask.sum() < 100:
        mask = np.ones(len(las.x), dtype=bool)
    xs = np.asarray(las.x[mask], dtype=np.float64)
    ys = np.asarray(las.y[mask], dtype=np.float64)
    zs = np.asarray(las.z[mask], dtype=np.float64)

    res = RESOLUTION_LAZ
    x_min, x_max = float(xs.min()), float(xs.max())
    y_min, y_max = float(ys.min()), float(ys.max())
    nx = int((x_max - x_min) / res) + 1
    ny = int((y_max - y_min) / res) + 1
    grid_x, grid_y = np.meshgrid(np.linspace(x_min, x_max, nx),
                                 np.linspace(y_min, y_max, ny))
    grid_z = griddata((xs, ys), zs, (grid_x, grid_y), method="linear")
    grid_z = np.flipud(grid_z)              # origine haut-gauche
    # Bords du convex hull → NaN ; on comble par nodata pour cohérence
    grid_z = np.where(np.isfinite(grid_z), grid_z, -9999.0).astype(np.float32)

    import rasterio
    from rasterio.transform import from_bounds
    transform = from_bounds(x_min, y_min, x_max, y_max, nx, ny)
    crs = rasterio.CRS.from_epsg(crs_epsg)
    with rasterio.open(str(tif_path), "w",
                       driver="GTiff", height=ny, width=nx,
                       count=1, dtype="float32", crs=crs,
                       transform=transform, nodata=-9999,
                       compress="deflate", predictor=2, tiled=True) as dst:
        dst.write(grid_z, 1)
