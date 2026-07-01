# providers/at_tirol.py — Autriche (Tyrol), DGM 0.5 m via WCS tiris
#
# Source : Land Tirol / tiris (Tiroler Rauminformationssystem), service WCS
#   https://gis.tirol.gv.at/arcgis/services/Service_Public/terrain/MapServer/WCSServer
#
# L'Autriche n'a pas de source LiDAR nationale exploitable (le DGM national du
# BEV est servi en tuiles 50×50 km via portail). L'accès fin est par Land. Le
# Tyrol expose son MNT par WCS ArcGIS — pratique, car un GetCoverage par bbox
# se mappe exactement sur le pattern "une requête par dalle" de fr_ign (qui fait
# un WMS GetMap par dalle). Couvre le cœur des Alpes tyroliennes (Innsbruck,
# Ötztal, Stubai, Zillertal, Karwendel…).
#
# Paradigme :
#   - CRS natif EPSG:31254 (MGI / Austria GK West, fuseau M28).
#   - DTM 0.5 m → dalle 1 km = 2000×2000 px (comme l'IGN).
#   - Pas de fichiers pré-tuilés : dalle_url construit une requête WCS 1.0.0
#     GetCoverage sur la bbox de la dalle → GeoTIFF. Déterministe, pas d'index.
#   - Découverte = grille clippée à l'étendue du coverage (pas de metalink).
#   - Nommage par coin SW (Xmin, Ymin), synthétique (on maîtrise le nom).
#
# Le Tyrol est à cheval sur deux fuseaux Gauss-Krüger : M28 (ce provider,
# Nordtirol) et M31 (Osttirol). Pour couvrir l'Osttirol : même code avec
# COVERAGE=...M31, CRS_NATIF=EPSG:31255 et l'étendue correspondante.
#
# Self-contained : stdlib uniquement.

import urllib.parse
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Autriche (Tyrol/Nordtirol) — DGM 0.5 m (tiris)"
CODE       = "at-tirol"
COUNTRY    = "at"          # ISO 3166-1 alpha-2 — utilisé pour cache/lidar/<country>/
LICENSE    = "CC BY 4.0 — © Land Tirol / tiris (attribution requise)"
DOC_URL    = "https://www.tirol.gv.at/sicherheit/geoinformation/geodaten-tiris/laserscandaten/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:31254"         # MGI / Austria GK West (fuseau M28)
RESOLUTION_M       = 0.5                  # DTM 0.5 m
DALLE_KM           = 1                    # côté d'une dalle (km)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 2000 px

# Une dalle 2000×2000 GeoTIFF pèse ~16 Mo. En dessous de 2 Mo = hors-coverage /
# erreur → ignorée.
SEUIL_DALLE_VALIDE = 2_000_000            # octets


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL   = "https://gis.tirol.gv.at/arcgis/services/Service_Public/terrain/MapServer/WCSServer"
COVERAGE  = "Gelaendemodell_50cm_M28"     # MNT 0.5 m, fuseau M28
# Étendue du coverage en EPSG:31254 (depuis DescribeCoverage) — sert à clipper
# la grille pour ne pas requêter hors zone : easting/northing en mètres.
COVERAGE_EXTENT = (-18750, 180000, 110000, 275000)   # (x_min, y_min, x_max, y_max)


# ── Conventions de nommage des dalles ────────────────────────────────────────
def dalle_filename(x_km, y_km):
    """Nom synthétique de la dalle (coin SW (x_km, y_km) en km EPSG:31254).
    Le nommage est interne (pas de convention externe à respecter) : on nomme
    par le coin SW (Xmin, Ymin). x_km peut être négatif (le fuseau M28 a des
    eastings négatifs à l'ouest)."""
    return f"dgm_tirol_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    """Sous-dossier par colonne Est."""
    return f"{x_km}"


def subdir_from_name(nom):
    """Sous-dossier (colonne Est) déduit du nom, ou None."""
    import re
    m = re.match(r"dgm_tirol_(-?\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL : WCS GetCoverage par dalle (comme WMS GetMap fr_ign) ────
def dalle_url(x_km, y_km):
    """URL WCS 1.0.0 GetCoverage pour la dalle (x_km, y_km) : renvoie un GeoTIFF
    2000×2000 sur la bbox [x,y]→[x+1,y+1] km en EPSG:31254. Déterministe."""
    step = DALLE_KM * 1000
    xmin = x_km * step
    ymin = y_km * step
    params = {
        "SERVICE": "WCS", "VERSION": "1.0.0", "REQUEST": "GetCoverage",
        "COVERAGE": COVERAGE,
        "CRS": CRS_NATIF,
        "BBOX": f"{xmin},{ymin},{xmin + step},{ymin + step}",
        "WIDTH": PX_PAR_DALLE, "HEIGHT": PX_PAR_DALLE,
        "FORMAT": "GeoTIFF",
    }
    return WCS_URL + "?" + urllib.parse.urlencode(params)


# ── Calcul de la liste des dalles couvrant une bbox ──────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    """Liste (x_km, y_km) des coins SW des dalles couvrant la bbox EPSG:31254.
    Borne haute demi-ouverte sur ligne de grille (cf. fr_ign / de_bayern)."""
    step = DALLE_KM * 1000
    x_start = int(x1 // step)
    x_end   = int(x2 // step)
    if x2 % step == 0 and x_end > x_start:
        x_end -= 1
    y_start = int(y1 // step)
    y_end   = int(y2 // step)
    if y2 % step == 0 and y_end > y_start:
        y_end -= 1
    return [(x_km, y_km)
            for x_km in range(x_start, x_end + 1)
            for y_km in range(y_start, y_end + 1)]


# ── Découverte : grille clippée à l'étendue du coverage ──────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Retourne {nom_dalle: url_wcs} pour les dalles de bbox_natif (EPSG:31254)
    qui tombent dans l'étendue du coverage Tyrol M28. Pas d'index réseau : le
    WCS est continu, on synthétise la grille et on clippe à COVERAGE_EXTENT
    (les dalles hors étendue ne sont pas requêtées)."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    # Intersecter la bbox demandée avec l'étendue du coverage
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  Tyrol: bbox out of the M28 coverage extent (Nordtirol)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
