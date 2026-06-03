# providers/at_osttirol.py — Autriche (Osttirol), DGM 0.5 m via WCS tiris
#
# JUMEAU de at_tirol.py (même service WCS tiris, même pattern GetCoverage par
# dalle). Ne diffère QUE par le fuseau Gauss-Krüger : l'Osttirol est dans M31
# (EPSG:31255, MGI Austria GK Central), pas M28. Si tu touches l'un, vérifie
# l'autre (drift jumeau). Pas d'abstraction partagée pour seulement 2 fuseaux —
# si un 3e Land tiris-WCS arrive, factoriser un helper commun à ce moment-là.
#
# Couvre l'Osttirol (Lienz, Hohe Tauern sud, Großglockner côté tyrolien).
# Étendue + CRS vérifiés via DescribeCoverage ; GetCoverage validé end-to-end.
#
# Self-contained : stdlib uniquement.

import urllib.parse
from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Autriche (Osttirol) — DGM 0.5 m (tiris)"
CODE       = "at-osttirol"
COUNTRY    = "at"          # ISO 3166-1 alpha-2 — utilisé pour cache/lidar/<country>/
LICENSE    = "CC BY 4.0 — © Land Tirol / tiris (attribution requise)"
DOC_URL    = "https://www.tirol.gv.at/sicherheit/geoinformation/geodaten-tiris/laserscandaten/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:31255"         # MGI / Austria GK Central (fuseau M31)
RESOLUTION_M       = 0.5                  # DTM 0.5 m
DALLE_KM           = 1                    # côté d'une dalle (km)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 2000 px

SEUIL_DALLE_VALIDE = 2_000_000            # octets


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL   = "https://gis.tirol.gv.at/arcgis/services/Service_Public/terrain/MapServer/WCSServer"
COVERAGE  = "Gelaendemodell_50cm_M31"     # MNT 0.5 m, fuseau M31
# Étendue du coverage en EPSG:31255 (depuis DescribeCoverage). Eastings négatifs
# (l'Osttirol est à l'ouest du méridien central M31).
COVERAGE_EXTENT = (-120000, 167000, -27500, 291000)   # (x_min, y_min, x_max, y_max)


# ── Conventions de nommage des dalles ────────────────────────────────────────
def dalle_filename(x_km, y_km):
    """Nom synthétique (coin SW (x_km, y_km) en km EPSG:31255). x_km est
    typiquement négatif (eastings négatifs en M31 côté Osttirol)."""
    return f"dgm_osttirol_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    """Sous-dossier par colonne Est."""
    return f"{x_km}"


def subdir_from_name(nom):
    """Sous-dossier (colonne Est) déduit du nom, ou None."""
    import re
    m = re.match(r"dgm_osttirol_(-?\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL : WCS GetCoverage par dalle ─────────────────────────────
def dalle_url(x_km, y_km):
    """URL WCS 1.0.0 GetCoverage : GeoTIFF 2000×2000 sur la bbox [x,y]→[x+1,y+1]
    km en EPSG:31255. Déterministe."""
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
    """Liste (x_km, y_km) des coins SW couvrant la bbox EPSG:31255.
    Borne haute demi-ouverte sur ligne de grille (cf. at_tirol)."""
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
    """{nom: url_wcs} pour les dalles de bbox_natif (EPSG:31255) dans l'étendue
    du coverage Osttirol M31. Pas d'index réseau (WCS continu)."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  Osttirol : bbox hors de l'étendue du coverage M31")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
