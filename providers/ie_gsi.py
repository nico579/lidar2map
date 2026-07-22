# providers/ie_gsi.py — Irlande, LiDAR DTM 1m via GSI ArcGIS FeatureServer
#
# Source : Geological Survey Ireland (GSI)
#   https://data.gov.ie/dataset/open-topographic-lidar-data
#   https://gsi.geodata.gov.ie/server/rest/services/Lidar
#
# Paradigme : ArcGIS FeatureServer → URL directe GeoTIFF par tuile 2×2 km.
#   - Les services imagehost (ImageServer) sont des HILLSHADES U8 — inutilisables
#     pour le pipeline lidar2map (besoin d'élévations float32).
#   - Le vrai accès DTM passe par le FeatureServer "Coverage" :
#     chaque feature = polygone 2×2 km avec attribut contenant l'URL GeoTIFF.
#   - CRS natif EPSG:2157 (ITM — Irish Transverse Mercator)
#   - Résolution 1m (Phase2, DCHG) ou 2m (TII, OPW)
#   - Grille 2×2 km (pas 1×1 km comme les autres providers)
#   - Couverture ~60% du territoire (7 organisations, 2006–2021)
#
# Self-contained : stdlib uniquement.

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Irlande — LiDAR DTM (GSI FeatureServer)"
CODE       = "ie-gsi"
COUNTRY    = "ie"
LICENSE    = "CC BY 4.0 — © Geological Survey Ireland"
DOC_URL    = "https://data.gov.ie/dataset/open-topographic-lidar-data"

HTTP_UA    = "lidar2map/1.0 (GSI Ireland)"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2157"
RESOLUTION_M       = 1.0
DALLE_KM           = 2                    # tuiles 2×2 km (grille GSI)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 2000
SEUIL_DALLE_VALIDE = 200_000


# ── Services FeatureServer Coverage (contiennent les URL download) ────────────
SERVER   = "https://gsi.geodata.gov.ie/server/rest/services/Lidar"
# Services Coverage avec URLs directes (champ dtm_url ou download_url)
# Noms confirmés via REST API (log 06/06/2026)
COVERAGE_SERVICES = [
    "IE_GSI_LiDAR_Coverage_GSI_DCHG_DP_IE26_ITM",  # Multi-org (plus large)
    "IE_GSI_LiDAR_Coverage_GSI_Phase2_IE26_ITM",    # Phase2 SE Ireland
    "IE_GSI_LiDAR_Coverage_NYU_Dublin_IE26_ITM",    # NYU Dublin
    "IE_GSI_LiDAR_Coverage_OPW_IE26_ITM",           # OPW
]
# Étendue Irlande en EPSG:2157
COVERAGE_EXTENT = (480000, 505000, 780000, 960000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"ie_dtm1m_{x_km:04d}_{y_km:05d}.tif"


def subdir_from_name(nom):
    m = re.match(r"ie_dtm1m_(\d+)_", nom)
    return m.group(1) if m else None


# ── Découverte via FeatureServer ──────────────────────────────────────────────
def _query_feature_service(service_name, bbox_natif, max_records=500):
    """Interroge le FeatureServer (ou MapServer) d'un service Coverage GSI.
    Essaie FeatureServer/0 puis MapServer/0 puis MapServer layers 1..4."""
    x1, y1, x2, y2 = bbox_natif
    params = {
        "where":         "1=1",
        "geometry":      f"{x1},{y1},{x2},{y2}",
        "geometryType":  "esriGeometryEnvelope",
        "inSR":          "2157",
        "spatialRel":    "esriSpatialRelIntersects",
        "outFields":     "*",
        "returnGeometry":"false",
        "resultRecordCount": max_records,
        "f":             "json",
    }
    qs = urllib.parse.urlencode(params)
    # Essayer FeatureServer puis MapServer (Phase2 n'a pas de FeatureServer)
    candidates = (
        [f"{SERVER}/{service_name}/FeatureServer/{i}/query" for i in range(3)] +
        [f"{SERVER}/{service_name}/MapServer/{i}/query" for i in range(5)]
    )
    for url in candidates:
        try:
            req = urllib.request.Request(url + "?" + qs,
                                         headers={"User-Agent": HTTP_UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
            if data.get("features"):
                return data["features"]
            if data.get("error"):
                continue
        except Exception:
            continue
    return []


def _extract_download_url(attrs):
    """Extrait l'URL de téléchargement depuis les attributs d'un feature.
    Champ confirmé : DATA_URL (contient un ZIP avec GeoTIFF à l'intérieur).
    Le post_fetch se charge du dézip."""
    # Champ confirmé par inspection live (06/06/2026)
    for field in ["DATA_URL", "dtm_url", "dtm_link", "download_url", "url",
                  "DTM_URL", "GeoTIFF_URL", "geotiff_url", "file_url"]:
        val = attrs.get(field)
        if val and isinstance(val, str) and val.startswith("http"):
            return val
    # Fallback : toute valeur URL dans les attributs
    for v in attrs.values():
        if isinstance(v, str) and v.startswith("http") and (
                ".zip" in v.lower() or ".tif" in v.lower()):
            return v
    return None


def _coords_from_attrs(attrs):
    """Tente d'extraire (x_km, y_km) depuis les attributs du feature."""
    for field in ["tile_name", "TILE_NAME", "name", "NAME", "tilename"]:
        val = attrs.get(field, "")
        if val:
            m = re.search(r"(\d{3,4})_(\d{4,6})", str(val))
            if m:
                return int(m.group(1)), int(m.group(2))
    # Fallback depuis champs X/Y
    for xf, yf in [("x_km", "y_km"), ("X_KM", "Y_KM"),
                   ("easting", "northing"), ("EASTING", "NORTHING")]:
        if attrs.get(xf) and attrs.get(yf):
            return int(attrs[xf] / 1000), int(attrs[yf] / 1000)
    return None, None


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Interroge les FeatureServer GSI et retourne {nom: url_geotiff}."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  GSI Ireland: bbox outside ITM extent")
        return {}

    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    dalles = {}
    n_services_ok = 0

    for svc in COVERAGE_SERVICES:
        print(f"  GSI Ireland : query {svc.split('_')[5]}...", flush=True)
        features = _query_feature_service(svc, (ix1, iy1, ix2, iy2))
        if not features:
            continue
        n_services_ok += 1
        for feat in features:
            attrs = feat.get("attributes", {}) or {}
            url = _extract_download_url(attrs)
            if not url:
                continue
            # Nommage : depuis le nom de tuile dans les attrs ou depuis l'URL
            x_km, y_km = _coords_from_attrs(attrs)
            if x_km is None:
                # Extraire depuis l'URL
                m = re.search(r"[/_](\d{3,4})[/_](\d{4,6})[._]", url)
                if m:
                    x_km, y_km = int(m.group(1)), int(m.group(2))
            if x_km is None:
                # Fallback : hash de l'URL pour nommage unique
                import hashlib
                h = hashlib.md5(url.encode()).hexdigest()[:8]
                nom = f"ie_dtm_{h}.tif"
            else:
                nom = dalle_filename(x_km, y_km)
            dalles.setdefault(nom, url)  # premier service = priorité

    if n_services_ok == 0:
        print("  GSI Ireland: no FeatureServer responded, "
              "check connectivity to gsi.geodata.gov.ie/server")
        return None

    print(f"  GSI Ireland: {n_services_ok} service(s) → {len(dalles)} tile(s)")
    return dalles


# ── Hook post_fetch (dézip ZIP → GeoTIFF) ────────────────────────────────────
# Les tuiles GSI Ireland sont distribuées en ZIP contenant un GeoTIFF.
# Nécessite le mécanisme post_fetch dans lidar2map.py (comme be_flanders).
def post_fetch(chemin):
    """Dézip la tuile ZIP → GeoTIFF, supprime le ZIP.
    Le fichier peut avoir une extension .tif mais contenir du ZIP (quand l'URL
    est un .zip mais que le pipeline l'a sauvegardé sous le nom .tif du provider).
    On détecte le format par magic bytes pour être robuste.
    """
    import zipfile
    from pathlib import Path
    chemin = Path(chemin)

    # Détecter si le fichier est un ZIP par magic bytes (PK)
    try:
        with open(chemin, "rb") as fh:
            magic = fh.read(4)
        if magic[:2] != b"PK":
            return  # pas un ZIP → déjà un GeoTIFF ou autre, rien à faire
    except OSError:
        return

    dossier = chemin.parent
    target = chemin.with_suffix(".tif") if chemin.suffix.lower() != ".tif" else chemin

    from providers import common as _common
    extracted = None
    with zipfile.ZipFile(chemin) as z:
        # Chercher le premier GeoTIFF dans le ZIP
        members_tif = [m for m in z.namelist() if m.lower().endswith(".tif")]
        if not members_tif:
            raise ValueError(f"Aucun .tif dans {chemin.name}")
        # Extraction anti zip-slip (membre venu d'une archive distante) —
        # cf. providers/common.py.
        extracted = _common.extraire_membre(z, members_tif[0], dossier)

    # Supprimer le ZIP (maintenant que le contenu est extrait)
    if chemin != extracted:
        chemin.unlink(missing_ok=True)

    # Renommer vers le chemin attendu par le pipeline
    if extracted != target:
        target.unlink(missing_ok=True)
        extracted.rename(target)
