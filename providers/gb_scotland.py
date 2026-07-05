# providers/gb_scotland.py : Royaume-Uni (Écosse), DTM via Scottish Remote
# Sensing Portal (JNCC / Scottish Government).
#
# Source : Scottish Public Sector LiDAR, bucket S3 Open Data `srsp-open-data`.
#   Portail : https://remotesensingdata.gov.scot/
#   Registre AWS : https://registry.opendata.aws/scottish-lidar/
#
# Paradigme : index par LISTING S3 + lecture FENÊTRÉE des GeoTIFF (COG_WINDOWED).
#   La donnée vit dans un bucket public, le nom de fichier ENCODE la position
#   (référence OS National Grid), donc le préfixe de clé S3 sert de filtre
#   spatial. C'est l'équivalent AWS du fishnet ArcGIS slovène (si_arso).
#   Les dalles sont des GeoTIFF tuilés en interne (blocs 256), donc on lit via
#   /vsicurl/ uniquement la fenêtre bbox au lieu de rapatrier le fichier entier
#   (range requests HTTP, le principe du Cloud-Optimized GeoTIFF, comme lu_act /
#   es_icgc). Crucial ici : les dalles phase font 20 à 60 Mo chacune.
#
# Couverture = PLUSIEURS collections fusionnées par priorité (la 1re qui couvre
# une cellule 1 km gagne). Trois grilles OS coexistent dans le bucket :
#   - national-lidar-programme, orkney-islands-council-23 : dalles 1 km à 50 cm,
#     réf OS `NR5807` (2 lettres + 2 chiffres easting km + 2 chiffres northing km).
#   - phase-3..6 : dalles 5 km à 50 cm, réf `NS16NE` (cellule 10 km + quadrant
#     N/S puis E/O). C'est là qu'est l'essentiel de la couverture (central belt
#     Glasgow/Édimbourg), absente du national-lidar-programme clairsemé.
#   - phase-1, phase-2 : dalles 10 km à 1 m, réf `HY20` (cellule 10 km).
#   Priorité : national/orkney (50 cm, récent) > phase-6..3 (50 cm) > phase-2..1
#   (1 m). RESOLUTION_M=0.5 est la cible de sortie ; les dalles 1 m sont
#   ré-échantillonnées par le pipeline (pas de détail inventé).
#
# Inclus aussi : `hes` (Historic Environment Scotland, 7 sous-jeux de scans archéo
#   de sites, 25/50 cm, lidar/hes/<sous-jeu>/) et `outer-hebrides/2019` (Hébrides
#   extérieures, 25 cm en grille 1 km + 50 cm en grille 5 km). Toutes en
#   EPSG:27700, mêmes grilles OS que ci-dessus. Les 25 cm passent en tête (plus
#   fins ; sortie ré-échantillonnée à RESOLUTION_M=0.5). Tout l'open LiDAR
#   écossais du portail est désormais couvert.
#
#   - CRS natif EPSG:27700 (British National Grid, OSGB36), MÊME grille que
#     gb_england / gb_wales (réutilisation de l'encodage OS, cf. _os_cell).
#   - Licence Open Government v3.
#
# Self-contained : stdlib uniquement (urllib + xml.etree).

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Royaume-Uni (Écosse) — DTM (Scottish Remote Sensing Portal)"
CODE       = "gb-scotland"
COUNTRY    = "gb"
LICENSE    = "Open Government Licence v3 — © Scottish Government / JNCC"
DOC_URL    = "https://remotesensingdata.gov.scot/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:27700"         # British National Grid (OSGB36)
RESOLUTION_M       = 0.5                  # cible de sortie (national + phase 50 cm)
DALLE_KM           = 1                    # grille d'énumération des cellules
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000 px (nominal)
COG_WINDOWED       = True                 # lecture fenêtrée /vsicurl (cf. lu_act)
# Lecture fenêtrée : la sortie est clippée à (bbox ∩ dalle), souvent < dalle
# pleine. Seuil bas pour ne pas rejeter un sliver côtier valide, tout en
# écartant les pages d'erreur S3.
SEUIL_DALLE_VALIDE = 50_000

# Étendue Écosse en EPSG:27700 (mainland + Hébrides + Orcades + Shetland) :
# clippe la grille théorique ; les cellules sans dalle sont de toute façon
# écartées par le listing S3.
COVERAGE_EXTENT = (0, 520000, 470000, 1220000)   # (E_min, N_min, E_max, N_max)


# ── Endpoints S3 ─────────────────────────────────────────────────────────────
S3_BASE  = "https://srsp-open-data.s3.eu-west-2.amazonaws.com"
HTTP_UA  = "lidar2map/1.0 (Scottish Remote Sensing Portal)"


def _gp(coll):
    """Chemin gridded standard (layout le plus courant)."""
    return f"lidar/{coll}/dtm/27700/gridded/"


# (label, chemin S3 gridded complet, grille) par ordre de PRIORITÉ : la 1re
# collection qui couvre une cellule 1 km gagne. Grille : "1km" (réf AAeennn),
# "5km" (réf AAenQ quadrant), "10km" (réf AAen). Ordre = résolution décroissante
# (la plus fine d'abord). Le chemin est stocké en entier car les layouts varient
# (hes ajoute un sous-jeu ; outer-hebrides intercale la résolution avant le CRS).
COLLECTIONS = (
    # 25 cm, grille 1 km : scans archéo HES (sites ponctuels) + Hébrides extérieures
    ("hes-2016-2017", _gp("hes/hes-2016-2017"), "1km"),
    ("hes-2016",      _gp("hes/hes-2016"),      "1km"),
    ("hes-2017",      _gp("hes/hes-2017"),      "1km"),
    ("outer-hebrides-25cm",
     "lidar/outer-hebrides/2019/dtm/25cm/27700/gridded/", "1km"),
    # 50 cm, grille 1 km : national, Orcades, puis les autres jeux HES
    ("national-lidar-programme",  _gp("national-lidar-programme"),  "1km"),
    ("orkney-islands-council-23", _gp("orkney-islands-council-23"), "1km"),
    ("hes-2010s10", _gp("hes/hes-2010s10"), "1km"),
    ("hes-2017sp3", _gp("hes/hes-2017sp3"), "1km"),
    ("hes_2010",    _gp("hes/hes_2010"),    "1km"),
    ("luing",       _gp("hes/luing"),       "1km"),
    # 50 cm, grille 5 km : Hébrides extérieures puis phases 3-6
    ("outer-hebrides-50cm",
     "lidar/outer-hebrides/2019/dtm/50cm/27700/gridded/", "5km"),
    ("phase-6", _gp("phase-6"), "5km"), ("phase-5", _gp("phase-5"), "5km"),
    ("phase-4", _gp("phase-4"), "5km"), ("phase-3", _gp("phase-3"), "5km"),
    # 1 m, grille 10 km : phases 1-2
    ("phase-2", _gp("phase-2"), "10km"), ("phase-1", _gp("phase-1"), "10km"),
)

_S3_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
_CACHE_VERSION = 3


# ── OS National Grid : (E, N) mètres → référence de dalle ─────────────────────
_OS_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"   # 25 lettres, 'I' exclue


def _os_cell(e, n):
    """(E, N) m EPSG:27700 → ('NR', e_km, n_km) où e_km/n_km = 0..99 km dans le
    carré 100 km. Algorithme OS standard (Ordnance Survey, 1936). Validé sur
    NR5807 (E158000/N607000) et HY20 (E320000/N1000000)."""
    e, n = int(e), int(n)
    e100, n100 = e // 100000, n // 100000
    l1 = _OS_LETTERS[(19 - n100) - (19 - n100) % 5 + (e100 + 10) // 5]
    l2 = _OS_LETTERS[(19 - n100) % 5 * 5 + (e100 + 10) % 5]
    return l1 + l2, (e % 100000) // 1000, (n % 100000) // 1000


def _ref_pour_grille(e, n, grille):
    """Réf OS de la dalle qui contient (e, n) dans la grille donnée."""
    aa, ek, nk = _os_cell(e, n)
    if grille == "1km":
        return f"{aa}{ek:02d}{nk:02d}"          # ex. NR5807
    if grille == "10km":
        return f"{aa}{ek // 10}{nk // 10}"      # ex. HY20
    ns = "N" if (nk % 10) >= 5 else "S"         # 5 km : quadrant N/S puis E/O
    ew = "E" if (ek % 10) >= 5 else "W"
    return f"{aa}{ek // 10}{nk // 10}{ns}{ew}"  # ex. NS16NE


def _prefixe_listing(e, n, grille):
    """Préfixe S3 à lister pour trouver la dalle couvrant (e, n)."""
    aa, ek, nk = _os_cell(e, n)
    if grille == "1km":
        return f"{aa}{ek:02d}"                  # colonne easting (≤100 dalles 1 km)
    return f"{aa}{ek // 10}{nk // 10}"          # cellule 10 km (1 dalle 10 km ou 4 quadrants)


# ── API provider (surface commune ; non utilisées par le mode discover) ───────
def dalle_filename(x_km, y_km):
    return _ref_pour_grille(int(x_km) * 1000, int(y_km) * 1000, "1km") + ".tif"


def subdir_from_name(nom):
    """Regroupe les dalles par carré OS 100 km (2 lettres en tête du nom)."""
    m = re.match(r"([A-Za-z]{2})", nom)
    return m.group(1).upper() if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("GB-Scotland : URL via listing S3 → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    """Grille 1 km EPSG:27700, borne haute demi-ouverte (cf. gb_england)."""
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
    """clé S3 …/gridded/NS16NE_50CM_DTM_….tif → 'NS16NE' (1er token du nom)."""
    return key.rsplit("/", 1)[-1].split("_", 1)[0]


# ── Découverte multi-collection via listing S3 (cache cumulatif disque) ───────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{nom_dalle: url_s3} pour la bbox. Chaque cellule 1 km est affectée à la
    collection la PLUS PRIORITAIRE qui la couvre (national 50 cm > phase 50 cm >
    phase 1 m) ; les dalles 5/10 km déduplent naturellement (clé = nom de
    fichier). Les listings S3 sont mis en cache cumulatif sur disque."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  GB-Scotland: bbox outside Scotland extent")
        return {}

    cellules = dalles_pour_bbox(ix1, iy1, ix2, iy2)   # [(x_km, y_km)] = sortie 1 km

    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if data.get("v") == _CACHE_VERSION:
                cache = data.get("listings", {})
        except Exception:
            cache = {}

    etat = {"reseau_ok": False, "nouveaux": False}

    def _availabilite(label, base, grille, cells):
        """{ref_token: url} pour `cells` dans cette collection ; liste S3 par
        préfixe (mémoïsé dans `cache`). Ne liste que les préfixes manquants."""
        prefixes = sorted({_prefixe_listing(x * 1000, y * 1000, grille)
                           for x, y in cells})
        avail = {}
        for pfx in prefixes:
            ck = f"{label}|{pfx}"
            if ck in cache:
                avail.update(cache[ck]); etat["reseau_ok"] = True; continue
            try:
                keys = _list_prefix(base + pfx)
                etat["reseau_ok"] = True
            except Exception as e:
                print(f"  GB-Scotland listing {label}/{pfx} : {type(e).__name__}: {e}")
                continue
            trouve = {_osref_depuis_cle(k): f"{S3_BASE}/{k}" for k in keys}
            cache[ck] = trouve
            etat["nouveaux"] = True
            avail.update(trouve)
        return avail

    dalles = {}
    par_collection = {}
    restantes = set(cellules)
    for label, base, grille in COLLECTIONS:
        if not restantes:
            break
        avail = _availabilite(label, base, grille, restantes)
        if not avail:
            continue
        couvertes = set()
        for (x, y) in restantes:
            url = avail.get(_ref_pour_grille(x * 1000, y * 1000, grille))
            if url:
                dalles[url.rsplit("/", 1)[-1]] = url
                couvertes.add((x, y))
        if couvertes:
            par_collection[label] = len(couvertes)
        restantes -= couvertes

    if etat["nouveaux"] and etat["reseau_ok"]:
        try:
            cache_path.write_text(
                json.dumps({"v": _CACHE_VERSION, "listings": cache}),
                encoding="utf-8")
        except Exception:
            pass
    if not etat["reseau_ok"] and not dalles:
        return None   # réseau KO et rien en cache

    detail = ", ".join(f"{c}:{n}" for c, n in par_collection.items())
    hors = len(restantes)
    print(f"  GB-Scotland (multi-collection): {len(dalles)} COG tile(s) for "
          f"{len(cellules)} 1 km cell(s)"
          + (f" [{detail}]" if detail else "")
          + (f" ({hors} hors couverture)" if hors else ""))
    return dalles
