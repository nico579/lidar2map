"""Candidat non activé : DGM1 natif GeoSN, ZIP GeoTIFF public de 2 km.

Intégration soumise à la validation explicite de l'utilisateur.

Les URL 1 km du catalogue Mapterhorn 2025 ne fonctionnent plus. La page
officielle publie une configuration JSON (produit, partage public et grille)
utilisée par son bouton de téléchargement par lot. Aucun cookie ni compte
n'est nécessaire. Le partage public est lu dans cette page, jamais figé.
"""

import json
import math
import re
import shutil
import time
import urllib.request
import zipfile
from pathlib import Path

from providers.common import atomic_write_json, part_path

NAME = "Saxe — DGM1 1 m (GeoSN, GeoTIFF natif)"
CODE = "de-sachsen"
COUNTRY = "de"
LICENSE = "dl-de/by-2-0 — © GeoSN"
DOC_URL = "https://www.geodaten.sachsen.de/downloadbereich-digitale-hoehenmodelle-4851.html"
CRS_NATIF = "EPSG:25833"
RESOLUTION_M = 1.0
DALLE_KM = 2
PX_PAR_DALLE = 2000
SEUIL_DALLE_VALIDE = 1000
DISCOVER_EXACT = True
DOWNLOAD_WORKERS_MAX = 3

BATCH_URL = "https://www.geodaten.sachsen.de/batch-download-4719.html"
HTTP_UA = "lidar2map/1.0 (GeoSN DGM1)"
CACHE_MAX_AGE_S = 7 * 86400
_BASE_URL = "https://geocloud.landesvermessung.sachsen.de/public.php/dav/files/"


def dalle_filename(x_km, y_km):
    return f"sn_dgm1_{int(x_km)}_{int(y_km)}.tif"


def subdir_from_name(nom):
    m = re.match(r"sn_dgm1_(\d+)_", nom)
    return m.group(1) if m else None


def _configuration(texte, cle):
    m = re.search(r"\bbatchConfig\." + re.escape(cle) + r"\s*=\s*\{", texte)
    if not m:
        raise ValueError(f"GeoSN : configuration {cle} absente")
    return json.JSONDecoder().raw_decode(texte[m.end() - 1:])[0]


def _decompresser_grille(valeurs, pas=1):
    if len(valeurs) % 2:
        raise ValueError("GeoSN : grille compressée malformée")
    for debut, compte in zip(valeurs[::2], valeurs[1::2]):
        if not isinstance(debut, int) or not isinstance(compte, int) or not 0 <= compte <= 100000:
            raise ValueError("GeoSN : séquence de grille invalide")
        yield from range(debut, debut + compte * pas, pas)


def _index_depuis_page(texte):
    produits = _configuration(texte, "products")
    produit = produits.get("DGM1_TIFF_2km", {})
    partage = produit.get("share_id", "")
    modele = produit.get("filename", "")
    if (produit.get("packagesize") != 2000
            or not re.fullmatch(r"[A-Za-z0-9]+", partage)
            or modele != "dgm1_33$Rechtswert$_$Hochwert$_2_sn_tiff.zip"):
        raise ValueError("GeoSN : produit DGM1 2 km inattendu")
    cellules = set()
    for commune in _configuration(texte, "mapping").values():
        for cellule in _decompresser_grille(commune["grid_id"]):
            x, y = divmod(cellule, 10000)
            cellules.add((x // 2 * 2, y // 2 * 2))
    # Même décompression/agrégation que getSelectedGridCells de la page.
    for cellule in _decompresser_grille(produit.get("computed_not_existing", []), 2):
        cellules.discard(divmod(cellule, 10000))
    for cellule in _decompresser_grille(produit.get("existing_not_computed", []), 2):
        cellules.add(divmod(cellule, 10000))
    if not cellules:
        raise ValueError("GeoSN : index vide")
    return {
        f"{x}_{y}": _BASE_URL + partage + "/" + modele.replace(
            "$Rechtswert$", str(x)).replace("$Hochwert$", str(y))
        for x, y in sorted(cellules)
    }


def _charger_index(cache_path):
    cache_path = Path(cache_path)
    try:
        if time.time() - cache_path.stat().st_mtime < CACHE_MAX_AGE_S:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if data.get("version") == 1 and data.get("tiles"):
                return data["tiles"]
    except (OSError, ValueError, AttributeError):
        pass
    try:
        req = urllib.request.Request(BATCH_URL, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            texte = resp.read(8 * 1024 * 1024 + 1)
        if len(texte) > 8 * 1024 * 1024:
            raise ValueError("GeoSN : page de configuration trop grande")
        index = _index_depuis_page(texte.decode("utf-8"))
    except Exception as exc:
        print(f"  ERROR GeoSN batch index: {type(exc).__name__}: {exc}")
        return None
    try:
        atomic_write_json(cache_path, {"version": 1, "tiles": index})
    except OSError as exc:
        print(f"  WARNING GeoSN index cache: {exc}")
    return index


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = bbox_natif
    if x1 >= x2 or y1 >= y2:
        return {}
    index = _charger_index(cache_path)
    if index is None:
        return None
    dalles = {}
    for x in range(math.floor(x1 / 2000) * 2, math.ceil(x2 / 2000) * 2, 2):
        for y in range(math.floor(y1 / 2000) * 2, math.ceil(y2 / 2000) * 2, 2):
            url = index.get(f"{x}_{y}")
            if url:
                dalles[dalle_filename(x, y)] = url
    print(f"  GeoSN DGM1 (1 m): {len(dalles)} tile(s) in the bbox")
    return dalles


def post_fetch(chemin):
    """Extrait l'unique TIFF dans un staging voisin, puis valide sa grille.

    Recopie d'un membre vers un chemin choisi localement : aucun nom distant
    n'est utilisé comme chemin d'extraction. Le ZIP initial est conservé si
    une validation échoue, et le staging est toujours supprimé.
    """
    import rasterio

    chemin = Path(chemin)
    with chemin.open("rb") as src:
        magic = src.read(4)
    if magic in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
        return
    if magic[:2] != b"PK":
        raise ValueError("GeoSN : réponse attendue ZIP/GeoTIFF")
    m = re.match(r"sn_dgm1_(\d+)_(\d+)\.tif(?:\.|$)", chemin.name)
    if not m:
        raise ValueError("GeoSN : nom de dalle invalide")
    x, y = (int(v) for v in m.groups())
    staging = part_path(chemin)
    try:
        with zipfile.ZipFile(chemin) as zf:
            membres = [i for i in zf.infolist() if i.filename.lower().endswith((".tif", ".tiff"))]
            if len(membres) != 1 or membres[0].file_size > 128 * 1024 * 1024:
                raise ValueError("GeoSN : ZIP sans TIFF unique de taille attendue")
            with zf.open(membres[0]) as src, staging.open("wb") as dst:
                shutil.copyfileobj(src, dst)
        with rasterio.open(staging) as ds:
            attendu = (x * 1000, y * 1000, x * 1000 + 2000, y * 1000 + 2000)
            if (ds.crs is None or ds.crs.to_epsg() != 25833 or ds.count != 1
                    or ds.shape != (2000, 2000) or ds.res != (1.0, 1.0)
                    or any(abs(a - b) > 0.01 for a, b in zip(ds.bounds, attendu))):
                raise ValueError("GeoSN : CRS, résolution ou emprise de dalle inattendus")
        staging.replace(chemin)
    finally:
        staging.unlink(missing_ok=True)
