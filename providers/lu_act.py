# providers/lu_act.py — Luxembourg, MNT 0,5 m (LiDAR 2024) via ACT / data.public.lu
#
# Source : ACT (Administration du Cadastre et de la Topographie) — BD-L-Lidar 2024
#   Données : https://data.public.lu/fr/datasets/dados-... (dataset DTM 2024)
#   Géoportail : https://g-o.lu/lidar2024mn
#
# Paradigme : UN SEUL COG national en lecture fenêtrée /vsicurl (comme ca_nrcan).
#   Le MNT 2024 est un unique GeoTIFF Cloud-Optimized de ~40 Go (114617×163687
#   px à 0,5 m, EPSG:2169). Le télécharger en entier pour une petite zone est
#   prohibitif ; un COG supporte les requêtes HTTP par plage (range) + le
#   tuilage interne (blocs 128², overviews) → rasterio/GDAL lisent UNIQUEMENT la
#   fenêtre bbox. Le pipeline gère ça via COG_WINDOWED=True (telecharger_cog_fenetre).
#
#   - CRS natif EPSG:2169 (LUREF / Luxembourg TM)
#   - Couverture nationale complète (2 586 km²), levé 2024, 30 pts/m²
#   - GeoTIFF déjà prêt (pas de post_fetch) ; nodata −9999, dtype float64
#   - Pas de clé, pas de compte. URL directe stable (data.public.lu → resources).
#   - Licence : Open Data ACT (CC0).
#
# NB : un provider « COG unique » n'a pas de grille de dalles. discover_dalles
# renvoie UNE entrée par zone, dont le NOM encode la bbox zone : deux zones
# différentes → noms différents → pas de réutilisation d'une fenêtre périmée
# (telecharger_cog_fenetre fait « skip » si le fichier existe déjà).
#
# Self-contained : stdlib uniquement.

import re


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Luxembourg — MNT (ACT, LiDAR 2024)"
CODE       = "lu-act"
COUNTRY    = "lu"
LICENSE    = "Open Data ACT Luxembourg — CC0"
DOC_URL    = "https://data.public.lu/fr/datasets/r/507842e4-0272-48ab-84b4-33f06ccfe2ea"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2169"          # LUREF / Luxembourg TM
RESOLUTION_M       = 0.5
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000 (nominal)
SEUIL_DALLE_VALIDE = 50_000
COG_WINDOWED       = True                 # lecture fenêtrée /vsicurl

# Étendue du COG en EPSG:2169 (lue dans l'en-tête, 2026-06-15) — clippe la zone.
COVERAGE_EXTENT = (48880, 56965, 106189, 138809)   # (E_min, N_min, E_max, N_max)


# ── Endpoint ─────────────────────────────────────────────────────────────────
# URL directe du COG (résolution stable de data.public.lu/.../r/<id> →
# download.data.public.lu/resources/...). Accept-Ranges: bytes confirmé.
COG_URL = ("https://download.data.public.lu/resources/"
           "bd-l-lidar2024-releve-3d-du-territoire-luxembourgeois/"
           "20241223-093912/MNT_Lidar2024.tif")


# ── Nommage ──────────────────────────────────────────────────────────────────
def _nom_fenetre(x1, y1, x2, y2):
    """Nom encodant la bbox zone (EPSG:2169, entiers) → 1 fichier par zone."""
    return f"lu_mnt2024_{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}.tif"


def subdir_from_name(nom):
    # Regrouper par bande 10 km de l'easting de la zone (évite tout à plat).
    m = re.match(r"lu_mnt2024_(\d+)_", nom)
    return f"{int(m.group(1)) // 10000}" if m else None


def dalle_filename(x_km, y_km):
    raise NotImplementedError("LU : COG unique fenêtré → noms via discover_dalles()")


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """UNE entrée {nom_fenetre: COG_URL} si la bbox intersecte le Luxembourg.
    Pas de réseau (COG + étendue connus) ; la lecture fenêtrée réelle est faite
    par telecharger_cog_fenetre (COG_WINDOWED=True)."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  LU-ACT: bbox outside Luxembourg extent")
        return {}
    nom = _nom_fenetre(ix1, iy1, ix2, iy2)
    print("  LU-ACT (MNT 0.5 m): 1 COG window in the bbox")
    return {nom: COG_URL}
