# providers/fr_ign.py — France, IGN LiDAR HD (geopf.fr)
#
# Source de référence pour le pattern provider. Définit toutes les
# spécificités du téléchargement de dalles LiDAR HD IGN :
#   - URLs WMS / WFS / TMS index
#   - CRS natif (Lambert-93)
#   - Géométrie des dalles (1 km × 1 km, 0.5 m/px)
#   - Format de nommage et organisation sous-dossiers
#   - Construction d'URL GetMap
#   - Découverte des dalles disponibles via TMS vectoriel
#
# Tout le reste du pipeline (SVF, ombrages, warp EPSG:3857, MBTiles) est
# provider-agnostique : il consomme des GeoTIFF en CRS natif et n'a rien
# de spécifique à la France au-delà de ce module.
#
# Self-contained : pour rester indépendant de lidar2map.py, ce module
# importe uniquement la stdlib + mapbox-vector-tile (lazy import).

import json
import math
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "France — IGN LiDAR HD"
CODE       = "fr-ign"
COUNTRY    = "fr"          # ISO 3166-1 alpha-2 — utilisé pour cache/lidar/<country>/
LICENSE    = "Open License Etalab 2.0"
DOC_URL    = "https://geoservices.ign.fr/lidarhd"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2154"          # Lambert-93
RESOLUTION_M       = 0.5                  # résolution native (m/px)
DALLE_KM           = 1                    # côté d'une dalle (km)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 2000 px

# Seuil de validation : dalles plus petites = mer/hors-couverture, ignorées.
# IGN sert ~16 Mo pour une dalle 2000×2000 px GeoTIFF compressé.
SEUIL_DALLE_VALIDE = 2_000_000            # octets


# ── Endpoints ────────────────────────────────────────────────────────────────
WMS_URL   = "https://data.geopf.fr/wms-r"
WFS_URL   = "https://data.geopf.fr/wfs/ows"
TMS_URL   = "https://data.geopf.fr/tms/1.0.0/IGNF_MNT-LIDAR-HD-produit"
WMS_LAYER = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93"


# ── Conventions de nommage des dalles ────────────────────────────────────────
def dalle_filename(x_km, y_km):
    """Nom du fichier .tif pour la dalle (x_km, y_km) en coordonnées Lambert-93.
    Convention IGN : LHD_FXX_XXXX_YYYY_MNT_O_0M50_LAMB93_IGN69.tif"""
    return f"LHD_FXX_{x_km:04d}_{y_km:04d}_MNT_O_0M50_LAMB93_IGN69.tif"


def dalle_subdir(x_km):
    """Sous-dossier où ranger une dalle dans le cache (organisation par
    colonne X pour éviter d'avoir 10000+ fichiers dans un seul dossier).
    Retourne une string vide si on stocke à la racine."""
    return f"{x_km:04d}"


# Pattern pour extraire le sous-dossier depuis un nom de dalle déjà connu
# (utilisé par chemin_dalle pour retrouver l'emplacement d'une dalle quand
# on n'a que son nom, pas ses coordonnées).
import re as _re
_SUBDIR_FROM_NAME = _re.compile(r"LHD_FXX_(\d+)_")


def subdir_from_name(nom):
    """Retourne le sous-dossier d'une dalle à partir de son nom de fichier,
    ou None si le nom ne matche pas le format attendu."""
    m = _SUBDIR_FROM_NAME.match(nom)
    return m.group(1) if m else None


# ── Construction URL WMS pour une dalle ──────────────────────────────────────
def dalle_url(x_km, y_km):
    """URL WMS GetMap pour télécharger la dalle (x_km, y_km).
    Le WMS IGN 1.3.0 retourne les pixels centrés sur la grille dalles.
    L'offset ±0.25 m (demi-pixel à 0.5 m/px) compense la convention
    "coin supérieur gauche" du WMS pour aligner les dalles sans chevauchement."""
    xmin = x_km * DALLE_KM * 1000 - 0.25
    xmax = xmin + DALLE_KM * 1000
    ymin = y_km * DALLE_KM * 1000 + 0.25
    ymax = ymin + DALLE_KM * 1000
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": WMS_LAYER, "FORMAT": "image/geotiff", "STYLES": "",
        "CRS": CRS_NATIF,
        "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
        "WIDTH": PX_PAR_DALLE, "HEIGHT": PX_PAR_DALLE,
        "FILENAME": dalle_filename(x_km, y_km),
    }
    return WMS_URL + "?" + urllib.parse.urlencode(params)


# ── Calcul de la liste des dalles couvrant une bbox ──────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    """Liste (x_km, y_km) des dalles couvrant la bbox Lambert-93.
    Inclusive aux bords : une dalle dont le coin SW = (x2, y2) sera incluse."""
    step = DALLE_KM * 1000
    x_start = int(x1 // step)
    x_end   = int(x2 // step)
    y_start = int(y1 // step)
    y_end   = int(y2 // step)
    return [(x_km, y_km)
            for x_km in range(x_start, x_end + 1)
            for y_km in range(y_start, y_end + 1)]


# ── Découverte des dalles disponibles via TMS vectoriel ──────────────────────
HTTP_UA  = "lidar2map/1.0 (IGN WMTS/WMS)"
TMS_ZOOM = 12         # zoom suffisant pour avoir toutes les dalles 1 km × 1 km


def _deg_to_tile(lat_deg, lon_deg, zoom):
    """WGS84 → tuile XYZ (Google/OSM, y=0 en haut). Pure math."""
    n = 2 ** zoom
    x = int((lon_deg + 180.0) / 360.0 * n)
    lat_r = math.radians(lat_deg)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi)
            / 2.0 * n)
    return x, max(0, min(n - 1, y))


def _write_json_atomic(path, data):
    """Écriture JSON atomique : tmp + os.replace. Best-effort (silent fail)."""
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass


def _import_mvt():
    """Lazy import mapbox-vector-tile, auto-install si absent."""
    try:
        import mapbox_vector_tile as _mvt
        return _mvt
    except ImportError:
        pass
    print("  Installation mapbox-vector-tile...", flush=True)
    r = subprocess.run([sys.executable, "-m", "pip", "install",
                        "mapbox-vector-tile", "-q"], capture_output=True)
    if r.returncode != 0:
        subprocess.run([sys.executable, "-m", "pip", "install",
                        "mapbox-vector-tile", "-q", "--user"], capture_output=True)
    try:
        import mapbox_vector_tile as _mvt
        return _mvt
    except ImportError:
        return None


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=16):
    """Liste les dalles disponibles dans la bbox — entry point unifié.

    Combine deux sources :
      1. **Index TMS vectoriel** (data.geopf.fr/tms/...IGNF_MNT-LIDAR-HD-produit) :
         truth officielle des dalles existantes côté IGN, avec URLs WFS prêtes.
      2. **Fallback grille** : pour chaque (x_km, y_km) déductible de bbox_natif
         et absent du TMS, on synthétise une URL WMS GetMap. Couvre les cas
         où le TMS rate des bordures ou est temporairement indisponible.

    bbox_wgs84 : (lon_min, lat_min, lon_max, lat_max) WGS84 pour le découpage TMS
    bbox_natif : (x_min, y_min, x_max, y_max) en Lambert-93 pour le filtre + grille
    cache_path : JSON où mettre en cache les tuiles TMS brutes
    workers    : threads parallèles pour fetch TMS

    Retourne {nom_dalle: url} (jamais None — la grille garantit au moins
    quelques dalles si bbox_natif est valide).
    """
    _mvt = _import_mvt()
    if _mvt is None:
        print("  ERREUR : mapbox-vector-tile non installable — repli WFS")
        return None

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    tx0, ty0 = _deg_to_tile(lat_max, lon_min, TMS_ZOOM)   # NW
    tx1, ty1 = _deg_to_tile(lat_min, lon_max, TMS_ZOOM)   # SE
    tuiles = [(tx, ty) for tx in range(tx0, tx1 + 1) for ty in range(ty0, ty1 + 1)]
    nb_tuiles = len(tuiles)
    print(f"  TMS : {nb_tuiles} tuiles à interroger (zoom {TMS_ZOOM}, "
          f"x={tx0}..{tx1}, y={ty0}..{ty1})...", flush=True)

    cache_path = Path(cache_path)
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    except Exception:
        cache = {}

    tuiles_a_fetcher = [(tx, ty) for tx, ty in tuiles if f"{tx}/{ty}" not in cache]
    if tuiles_a_fetcher:
        print(f"  TMS cache : {nb_tuiles - len(tuiles_a_fetcher)} tuiles en cache, "
              f"{len(tuiles_a_fetcher)} à télécharger...", flush=True)

    def _fetch_tuile(tx, ty):
        url = f"{TMS_URL}/{TMS_ZOOM}/{tx}/{ty}.pbf"
        req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                pbf_data = resp.read()
            tile = _mvt.decode(pbf_data)
            entries = []
            for layer in tile.values():
                for feat in layer.get("features", []):
                    props = feat.get("properties", {})
                    nom    = props.get("name_download") or props.get("name")
                    url_dl = props.get("url")
                    bbox_s = props.get("bbox")
                    if nom and url_dl:
                        if not nom.endswith(".tif"):
                            nom += ".tif"
                        entries.append((nom, url_dl, bbox_s))
            return (tx, ty, entries, None)
        except Exception as _e:
            return (tx, ty, [], str(_e))

    nb_erreurs = 0
    done_fetch = 0
    if tuiles_a_fetcher:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_fetch_tuile, tx, ty): (tx, ty)
                    for tx, ty in tuiles_a_fetcher}
            for fut in as_completed(futs):
                tx, ty, entries, err = fut.result()
                done_fetch += 1
                if err:
                    nb_erreurs += 1
                    cache[f"{tx}/{ty}"] = []
                else:
                    cache[f"{tx}/{ty}"] = entries
                if done_fetch % 20 == 0 or done_fetch == len(tuiles_a_fetcher):
                    pct = done_fetch * 100 // max(len(tuiles_a_fetcher), 1)
                    print(f"\r  TMS : {pct:3d}%  {done_fetch}/{len(tuiles_a_fetcher)} "
                          f"nouvelles tuiles...", end="", flush=True)
        if tuiles_a_fetcher:
            print()
        _write_json_atomic(cache_path, cache)

    # Filtre bbox L93 sur les résultats
    dalles = {}
    for tx, ty in tuiles:
        for entry in cache.get(f"{tx}/{ty}", []):
            nom, url_dl, bbox_s = entry if len(entry) == 3 else (*entry, None)
            if bbox_natif is not None and bbox_s:
                try:
                    _fx0, _fy0, _fx1, _fy1 = map(float, str(bbox_s).split(","))
                    _zx0, _zy0, _zx1, _zy1 = bbox_natif
                    if _fx1 < _zx0 or _fx0 > _zx1 or _fy1 < _zy0 or _fy0 > _zy1:
                        continue
                except Exception:
                    pass
            dalles[nom] = url_dl

    if nb_erreurs == nb_tuiles:
        print("  ERREUR TMS : toutes les tuiles ont échoué — repli sur grille pure WMS")
        dalles = {}   # repli total : aucune dalle TMS, on construit tout depuis la grille
    elif nb_erreurs:
        print(f"  TMS : {nb_erreurs}/{nb_tuiles} tuiles en erreur (ignorées)")
    print(f"  TMS : {len(dalles)} dalle(s) trouvée(s)", flush=True)

    # ── Fallback grille : ajouter les dalles (x_km, y_km) absentes du TMS ────
    # Utile quand TMS rate des bordures ou n'indexe pas certaines dalles.
    if bbox_natif is not None:
        x1, y1, x2, y2 = bbox_natif
        ajoutes = 0
        for x_km, y_km in dalles_pour_bbox(x1, y1, x2, y2):
            nom = dalle_filename(x_km, y_km)
            if nom not in dalles:
                dalles[nom] = dalle_url(x_km, y_km)
                ajoutes += 1
        if ajoutes:
            print(f"  Grille : +{ajoutes} dalle(s) complémentaires (WMS direct)")

    return dalles
