# providers/it_sardegna.py — Italie (Sardaigne), DTM 1 m via WCS
#
# Source : Regione Autonoma della Sardegna — Geoportale, mosaïque « DTM 1 m
#   ALTIMETRIA » (LiDAR : côtes + centres urbains par la Région, zones critiques
#   + bandes fluviales + Gallura par le Ministère de l'Environnement).
#   GetCapabilities : https://webgis.regione.sardegna.it/geoserverraster/ows?service=WCS&version=2.0.1&request=GetCapabilities
#   Produit : https://www.sardegnageoportale.it/webgis/  (sezione Cartografia di base)
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque de_hessen / es_cnig), servi
#   par un GeoServer standard.
#   - CRS natif EPSG:7791 (RDN2008 / UTM 32N) — même datum que it-emilia-romagna.
#   - Coverage "raster__DTM_1M_MOSAICO_ALTIMETRIA" = DTM 1 m (offsetVector 1,
#     confirmé). Le pendant "..._OMBRE" est l'ombrage rendu → pas utilisé.
#   - axisLabels="E N" ; E=Est, N=Nord.
#   - GetCoverage renvoie un GeoTIFF float32 AVEC tag CRS embarqué (EPSG:7791) :
#     PAS de post_fetch de réétiquetage nécessaire (contrairement à
#     it-emilia-romagna dont le WCS régional omet le tag CRS).
#   - Couverture PARTIELLE (mosaïque à trous) : hors zone relevée, GetCoverage
#     renvoie du nodata=-9999 PROPRE (pas des zéros — c'est ce qui rendait le
#     0,5 m d'Émilie-Romagne inexploitable). Les tuiles hors-couverture sont donc
#     transparentes en aval, pas des plans plats parasites.
#   - Licence : CC BY 4.0 (dati aperti Regione Sardegna).
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Italie (Sardaigne) — DTM 1 m (RAS, WCS)"
CODE       = "it-sardegna"
COUNTRY    = "it"
LICENSE    = "CC BY 4.0 — © Regione Autonoma della Sardegna"
DOC_URL    = "https://www.sardegnageoportale.it/webgis/"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:7791"          # RDN2008 / UTM 32N
RESOLUTION_M       = 1.0                   # DTM 1 m (offsetVector du WCS)
DALLE_KM           = 1                     # tuile 1×1 km → 1000×1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000              # Float32 1000×1000 (>> erreur XML)


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://webgis.regione.sardegna.it/geoserverraster/ows"
COVERAGE = "raster__DTM_1M_MOSAICO_ALTIMETRIA"
# axisLabels="E N" (depuis DescribeCoverage) — E=Est, N=Nord
WCS_AXIS_LABELS = ("E", "N")
# Étendue du coverage en EPSG:7791 (depuis DescribeCoverage)
COVERAGE_EXTENT = (426609, 4301307, 570196, 4573593)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"it_sar_dtm1_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"it_sar_dtm1_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0.1 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 2.0.1 GetCoverage, subsets E/N en EPSG:7791 → GeoTIFF."""
    step = DALLE_KM * 1000
    xmin = x_km * step
    ymin = y_km * step
    ax1, ax2 = WCS_AXIS_LABELS
    params = urllib.parse.urlencode({
        "service":    "WCS",
        "version":    "2.0.1",
        "request":    "GetCoverage",
        "coverageId": COVERAGE,
        "format":     "image/tiff",
        "subset":     f"{ax1}({xmin},{xmin + step})",
    })
    # 2e subset ajouté manuellement (urllib ne gère pas les clés dupliquées)
    return f"{WCS_URL}?{params}&subset={ax2}({ymin},{ymin + step})"


# ── Grille de dalles ─────────────────────────────────────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
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


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Grille synthétique clippée à l'étendue du coverage. WCS continu → pas d'index."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  Sardegna: bbox out of the DTM extent (UTM 32N / RDN2008)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  IT Sardegna (DTM 1m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
