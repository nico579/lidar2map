# providers/gb_england.py — Royaume-Uni (Angleterre), LIDAR Composite DTM 1m (EA)
#
# Source : Environment Agency, National LIDAR Programme — "LIDAR Composite DTM 1m"
#   https://environment.data.gov.uk/dataset/13787b9a-26a4-4775-8523-806d13af58fc
#
# Couvre ~99 % de l'Angleterre à 1 m, ouvert (Open Government Licence v3).
#
# Paradigme : WCS (comme at_tirol), mais en WCS 2.0.1 (subsets par axe nommé
# au lieu du BBOX de la 1.0.0). Un GetCoverage par dalle 1 km se mappe sur le
# pattern "une requête par dalle" — validé end-to-end (Peak District, 301-375 m).
#   - CRS natif EPSG:27700 (British National Grid, OSGB36).
#   - axisLabels du coverage = "E N" → subset=E(...)&subset=N(...).
#   - DTM 1 m → dalle 1 km = 1000×1000 px. Format image/tiff.
#   - Nommage par coin SW (Emin, Nmin), synthétique. Découverte = grille clippée
#     à l'étendue du coverage (pas d'index réseau, le WCS est continu).
#
# NB : c'est l'ANGLETERRE seule. Écosse (remotesensingdata.gov.scot) et Pays de
# Galles (DataMapWales) ont leurs propres services — providers séparés à ajouter.
#
# Self-contained : stdlib uniquement.

from pathlib import Path


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Royaume-Uni (Angleterre) — LIDAR Composite DTM 1 m (EA)"
CODE       = "gb-england"
COUNTRY    = "gb"          # ISO 3166-1 alpha-2 — utilisé pour cache/lidar/<country>/
LICENSE    = "Open Government Licence v3 — © Environment Agency"
DOC_URL    = "https://environment.data.gov.uk/dataset/13787b9a-26a4-4775-8523-806d13af58fc"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:27700"         # British National Grid (OSGB36)
RESOLUTION_M       = 1.0                  # DTM 1 m
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 1000 px
SEUIL_DALLE_VALIDE = 500_000              # octets


# ── Endpoints WCS ────────────────────────────────────────────────────────────
WCS_URL  = ("https://environment.data.gov.uk/spatialdata/"
            "lidar-composite-digital-terrain-model-dtm-1m/wcs")
COVERAGE = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"
# Étendue du coverage en EPSG:27700 (depuis DescribeCoverage) — clippe la grille.
COVERAGE_EXTENT = (80000, 4000, 656000, 665000)   # (E_min, N_min, E_max, N_max)


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    """Nom synthétique de la dalle (coin SW (E_km, N_km) en km EPSG:27700)."""
    return f"dtm_england_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"dtm_england_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL : WCS 2.0.1 GetCoverage par dalle ───────────────────────
def dalle_url(x_km, y_km):
    """URL WCS 2.0.1 GetCoverage : GeoTIFF 1000×1000 sur la dalle [E,N]→[E+1,N+1]
    km en EPSG:27700. Subsets E()/N() non encodés (parenthèses/virgules brutes,
    forme vérifiée fonctionnelle contre le serveur EA)."""
    step = DALLE_KM * 1000
    e0 = x_km * step
    n0 = y_km * step
    return (f"{WCS_URL}?service=WCS&version=2.0.1&request=GetCoverage"
            f"&coverageId={COVERAGE}"
            f"&subset=E({e0},{e0 + step})&subset=N({n0},{n0 + step})"
            f"&format=image/tiff")


# ── Calcul de la liste des dalles couvrant une bbox ──────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    """Liste (E_km, N_km) des coins SW couvrant la bbox EPSG:27700.
    Borne haute demi-ouverte sur ligne de grille (cf. at_tirol / de_bayern)."""
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
    """{nom: url_wcs} pour les dalles de bbox_natif (EPSG:27700) dans l'étendue
    du coverage EA. Pas d'index réseau (WCS continu) : on synthétise la grille
    et on clippe à COVERAGE_EXTENT."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  England : bbox hors de l'étendue du coverage EA")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
