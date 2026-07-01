# providers/ee_maaamet.py — Estonie, DTM 1m (LiDAR national) via Maa-amet
#
# Source : Maa-amet (Estonian Land and Spatial Development Board)
#   https://geoportaal.maaamet.ee/ (kõrgusandmed, page_id=614)
#
# Paradigme : grille synthétique + URLs directes (validé par sondage 2026-06-11).
#   - Feuilles 1:10000 de 5×5 km, numérotées ABCDQ (formule dérivée
#     empiriquement de 6 feuilles téléchargées, voir _ruut_depuis_sw) :
#       A = y//100000 − 59          (bloc 100 km nord)
#       B = x//100000 − 2           (bloc 100 km est)
#       C = (y % 100000) // 10000   (ligne 10 km dans le bloc)
#       D = (x % 100000) // 10000   (colonne 10 km dans le bloc)
#       Q = quart 5 km : 1=SO, 2=SE, 3=NO, 4=NE
#   - Téléchargement direct (doc officielle « mass download » Maa-amet) :
#       index.php?lang_id=1&plugin_act=otsing&page_id=614
#         &andmetyyp=dem_1m_geotiff&kaardiruut={n}&dl=1&f={n}_dtm_1m.tif
#     → GeoTIFF 5000×5000 Float32, EPSG:3301, nodata −9999.
#     {n}_dtm_1m.tif = DTM courant (ALS 2021-2024) ; un produit plus ancien
#     {n}_dem_1m_2017-2020.tif existe aussi (non utilisé ici).
#   - CRS natif EPSG:3301 (L-EST97), couverture nationale, pas de clé.
#   - Licence : données ouvertes Maa-amet (utilisation libre, perso et
#     commerciale, sans enregistrement).
#
# Self-contained : stdlib uniquement.

import re


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Estonie — DTM 1m (Maa-amet, LiDAR national)"
CODE       = "ee-maaamet"
COUNTRY    = "ee"
LICENSE    = "Maa-amet open data — utilisation libre"
DOC_URL    = "https://geoportaal.maaamet.ee/eng/Maps-and-Data/Elevation-data-p308.html"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3301"          # L-EST97 / Estonian Coordinate System 1997
RESOLUTION_M       = 1.0
DALLE_KM           = 5                    # feuille 1:10000 = 5×5 km
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 5000 px
SEUIL_DALLE_VALIDE = 2_000_000            # Float32 5000×5000 deflate ≈ 30-60 Mo

# Étendue Estonie en L-EST97 (numéros de feuille 44744–74331 d'après Maa-amet,
# soit y 6 375 000–6 640 000 / x 300 000–800 000 ; resserré sur le territoire).
COVERAGE_EXTENT = (369000, 6377000, 740000, 6635000)   # (x_min, y_min, x_max, y_max)

DL_TMPL = ("https://geoportaal.maaamet.ee/index.php?lang_id=1&plugin_act=otsing"
           "&page_id=614&andmetyyp=dem_1m_geotiff&kaardiruut={ruut}"
           "&dl=1&f={ruut}_dtm_1m.tif")


# ── Numérotation des feuilles ────────────────────────────────────────────────
def _ruut_depuis_sw(x_sw, y_sw):
    """Coin SW (multiples de 5000 m, L-EST97) → numéro de feuille 1:10000."""
    a = y_sw // 100000 - 59
    b = x_sw // 100000 - 2
    c = (y_sw % 100000) // 10000
    d = (x_sw % 100000) // 10000
    q = 1 + (1 if (x_sw % 10000) >= 5000 else 0) + (2 if (y_sw % 10000) >= 5000 else 0)
    return f"{a}{b}{c}{d}{q}"


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    # x_km/y_km = indices de grille 5 km (convention pipeline : unités DALLE_KM)
    return f"ee_dtm1m_{_ruut_depuis_sw(int(x_km) * 5000, int(y_km) * 5000)}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    # ee_dtm1m_63544.tif → regrouper par bloc 1:20000 (4 premiers chiffres)
    m = re.match(r"ee_dtm1m_(\d{4})\d", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    return DL_TMPL.format(ruut=_ruut_depuis_sw(int(x_km) * 5000, int(y_km) * 5000))


# ── Grille de dalles ─────────────────────────────────────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
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


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Grille synthétique 5 km clippée à l'étendue Estonie — la numérotation
    des feuilles est une formule pure, aucun index réseau requis. Les feuilles
    en mer / hors couverture renvoient une page HTML que le validateur TIFF
    rejette (dalle simplement absente du résultat)."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  EE Maa-amet: bbox outside Estonia extent")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  EE Maa-amet (dem_1m_geotiff): {len(grille)} 5 km sheet(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
