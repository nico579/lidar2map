# providers/gb_scotland.py — Royaume-Uni (Écosse), DTM 50 cm via Scottish
# Remote Sensing Portal (JNCC / Scottish Government).
#
# Source : Scottish Public Sector LiDAR — bucket S3 Open Data `srsp-open-data`
#   Portail : https://remotesensingdata.gov.scot/
#   Registre AWS : https://registry.opendata.aws/scottish-lidar/
#
# Paradigme : index par LISTING S3 + dalles GeoTIFF directes (validé par
#   sondage 2026-06-15). C'est l'équivalent du fishnet ArcGIS slovène
#   (si_arso) mais via l'API AWS S3 ListObjectsV2 : la donnée vit dans un
#   bucket public, et le nom de fichier ENCODE la position (référence OS
#   National Grid), donc le préfixe de clé S3 SERT de filtre spatial.
#
#   1. Le nom d'une dalle 1 km est sa référence OS National Grid :
#        NR5807_50cm_DTM_ScotlandNationalLiDAR.tif
#        = carré 100 km `NR` + easting 58 km + northing 07 km (coin SW).
#      L'OS National Grid (Ordnance Survey, 1936) est LA grille de toute la
#      cartographie britannique → pas une convention maison.
#   2. On calcule les références OS des dalles 1 km couvrant la bbox, puis on
#      LISTE le bucket avec un préfixe `gridded/{NR}{ee}` (colonne de 10 dalles)
#      → on récupère les noms exacts (le token de résolution et le suffixe
#      varient selon la collection, d'où le listing plutôt qu'une URL devinée).
#   3. URL dalle = objet S3 public en HTTPS (GET anonyme, pas de signature).
#
#   - CRS natif EPSG:27700 (British National Grid, OSGB36) — MÊME grille que
#     gb_england / gb_wales (réutilisation de l'encodage OS, cf. _en_vers_osref).
#   - DTM 50 cm → dalle 1 km = 2000×2000 px. GeoTIFF (COG) prêt à l'emploi,
#     aucune conversion (pas de post_fetch).
#   - Licence Open Government v3.
#
# Couverture v1 : collections en 50 cm / dalles 1 km (captures modernes) :
#     national-lidar-programme (national) + orkney-islands-council-23 (Orcades).
#   Les `phase-1..6` historiques sont en dalles 10 km à 1 m
#   (HY20_1M_DTM_PHASE1.tif) → taille de dalle incompatible avec le modèle
#   grille-1 km, donc EXCLUES ici (à traiter dans un provider séparé si besoin).
#
# Self-contained : stdlib uniquement (urllib + xml.etree).

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Royaume-Uni (Écosse) — DTM 50 cm (Scottish Remote Sensing Portal)"
CODE       = "gb-scotland"
COUNTRY    = "gb"
LICENSE    = "Open Government Licence v3 — © Scottish Government / JNCC"
DOC_URL    = "https://remotesensingdata.gov.scot/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:27700"         # British National Grid (OSGB36)
RESOLUTION_M       = 0.5                  # DTM 50 cm
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000 px (nominal)
# Les COG sont rognés à l'emprise réelle des données dans la cellule OS 1 km
# (souvent < 2000² px). Seuil bas (cf. profil 50 cm du fallback inline) pour ne
# pas rejeter un sliver côtier valide, tout en écartant les pages d'erreur S3.
SEUIL_DALLE_VALIDE = 50_000

# Étendue Écosse en EPSG:27700 (mainland + Hébrides + Orcades + Shetland) —
# clippe la grille théorique ; les dalles inexistantes sont de toute façon
# écartées par le listing S3.
COVERAGE_EXTENT = (0, 520000, 470000, 1220000)   # (E_min, N_min, E_max, N_max)


# ── Endpoints S3 ─────────────────────────────────────────────────────────────
S3_BASE  = "https://srsp-open-data.s3.eu-west-2.amazonaws.com"
# Collections retenues, par ordre de priorité (première trouvée gagne).
COLLECTIONS = ("national-lidar-programme", "orkney-islands-council-23")
GRIDDED_TMPL = "lidar/{coll}/dtm/27700/gridded/"
HTTP_UA  = "lidar2map/1.0 (Scottish Remote Sensing Portal)"

_S3_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


# ── OS National Grid : (E, N) mètres → référence de dalle 1 km ────────────────
_OS_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"   # 25 lettres, 'I' exclue


def _en_vers_osref(e, n):
    """Coin SW (E, N) en mètres EPSG:27700 → référence OS 1 km (ex. 'NR5807').
    Algorithme OS standard : 2 lettres (carré 500 km puis 100 km) + 2+2 chiffres
    km. Validé sur NR5807 (E158000/N607000) et HY1700 (E317000/N1000000)."""
    e100, n100 = e // 100000, n // 100000
    l1 = _OS_LETTERS[(19 - n100) - (19 - n100) % 5 + (e100 + 10) // 5]
    l2 = _OS_LETTERS[(19 - n100) % 5 * 5 + (e100 + 10) % 5]
    e_km = (e % 100000) // 1000
    n_km = (n % 100000) // 1000
    return f"{l1}{l2}{e_km:02d}{n_km:02d}"


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"sct_dtm_{_en_vers_osref(int(x_km) * 1000, int(y_km) * 1000)}.tif"


def dalle_subdir(x_km):
    # Non utilisé par le pipeline (le chemin disque passe par subdir_from_name,
    # qui regroupe par carré 100 km lu dans le nom). Présent pour symétrie API.
    return f"{x_km}"


def subdir_from_name(nom):
    m = re.match(r"sct_dtm_([A-Z]{2})", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    # L'URL dépend de la collection qui détient la dalle (et du token de
    # résolution dans le nom) → connue seulement via le listing S3.
    raise NotImplementedError("GB-Scotland : URL via listing S3 → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    """Grille 1 km EPSG:27700 — borne haute demi-ouverte (cf. gb_england)."""
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


# ── Listing S3 (ListObjectsV2) ───────────────────────────────────────────────
def _list_prefix(prefix):
    """Toutes les clés sous `prefix` (pagination via continuation-token)."""
    keys = []
    token = None
    while True:
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        url = f"{S3_BASE}/?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            root = ET.fromstring(r.read())
        for c in root.findall(f"{_S3_NS}Contents"):
            k = c.findtext(f"{_S3_NS}Key")
            if k:
                keys.append(k)
        if root.findtext(f"{_S3_NS}IsTruncated") == "true":
            token = root.findtext(f"{_S3_NS}NextContinuationToken")
            if token:
                continue
        break
    return keys


def _osref_depuis_cle(key):
    """clé S3 …/gridded/NR5807_50cm_DTM_….tif → 'NR5807' (le 1er token)."""
    nom = key.rsplit("/", 1)[-1]
    return nom.split("_", 1)[0]


# ── Découverte via listing S3 (cache cumulatif sur disque) ───────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{sct_dtm_<osref>.tif: url_s3} pour les dalles existantes dans bbox_natif
    (EPSG:27700). Le mapping osref→url est mis en cache cumulatif : les colonnes
    10 km déjà listées ne re-touchent pas le réseau (osref absent mémorisé None).
    """
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  GB-Scotland : bbox hors de l'étendue Écosse")
        return {}

    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    refs = {(x, y): _en_vers_osref(x * 1000, y * 1000) for x, y in grille}

    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    # Préfixes « colonne 10 km » à lister = les 4 premiers car. des refs
    # (lettres + easting km) ; ~10 dalles chacun. On ne liste que ce qui manque.
    manquants = [r for r in refs.values() if r not in cache]
    if manquants:
        prefixes = sorted({r[:4] for r in manquants})
        reseau_ok = False
        for pfx in prefixes:
            trouve = {}
            for coll in COLLECTIONS:
                base = GRIDDED_TMPL.format(coll=coll)
                try:
                    keys = _list_prefix(base + pfx)
                    reseau_ok = True
                except Exception as e:
                    print(f"  GB-Scotland listing {coll}/{pfx} : "
                          f"{type(e).__name__}: {e}")
                    continue
                for k in keys:
                    ref = _osref_depuis_cle(k)
                    trouve.setdefault(ref, f"{S3_BASE}/{k}")   # priorité collection
            # Mémoriser tout le préfixe (présents + absents) si le réseau a répondu.
            if reseau_ok:
                for r in refs.values():
                    if r[:4] == pfx and r not in cache:
                        cache[r] = trouve.get(r)   # None = hors couverture
        if reseau_ok:
            try:
                cache_path.write_text(json.dumps(cache), encoding="utf-8")
            except Exception:
                pass
        elif not any(r in cache for r in refs.values()):
            return None   # réseau KO et rien en cache

    dalles = {}
    hors_couv = 0
    for (x, y), ref in refs.items():
        url = cache.get(ref)
        if url:
            dalles[dalle_filename(x, y)] = url
        else:
            hors_couv += 1
    print(f"  GB-Scotland (DTM 50 cm) : {len(dalles)} dalle(s) dans la bbox"
          + (f" ({hors_couv} hors couverture)" if hors_couv else ""))
    return dalles
