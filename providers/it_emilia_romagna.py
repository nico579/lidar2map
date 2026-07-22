# providers/it_emilia_romagna.py — Italie (Émilie-Romagne), DTM 5 m via WCS
#
# Source : Regione Emilia-Romagna — Geoportale, « DTM 5x5 ultima edizione »
#   (mosaïque LiDAR 2022-2024 + cartographie legacy, COUVERTURE RÉGIONALE COMPLÈTE).
#   GetCapabilities : https://servizigis.regione.emilia-romagna.it/wcs/dtm5x5?service=WCS&version=2.0.1&request=GetCapabilities
#   Produit : https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/altimetria/layer-2
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque es_cnig / de_hessen).
#   - CRS natif EPSG:7791 (RDN2008 / UTM 32N) — datum italien moderne.
#   - Coverage "DTM5X5_RDN32_RMD" = DTM 5 m (offsetVector 5, confirmé).
#   - axisLabels="x y" (minuscules, comme es_cnig) ; x=Est, y=Nord.
#   - GetCoverage renvoie un multipart/related WCS 2.0 (partie GML + GeoTIFF) : le
#     cœur désencapsule via _extraire_tiff_multipart. Le GeoTIFF a une géoréf
#     correcte mais SANS tag CRS → post_fetch réétiquette EPSG:7791.
#   - Licence : CC BY 4.0 (dati aperti Regione Emilia-Romagna).
#   - NB TLS : la chaîne du serveur régional a un CA « self-signed » rejeté par
#     le magasin Windows mais accepté par certifi ; le cœur force déjà le
#     contexte HTTPS sur le bundle certifi, donc le download passe.
#
# NB RÉSOLUTION : la campagne LiDAR 2023/24 fournit un DTM 0,5 m (WCS
#   dtmrer2023_24) BIEN plus fin, mais sa couverture est encore PARTIELLE (la
#   plupart des tuiles reviennent tout-à-zéro hors zones déjà relevées). On sert
#   donc le 5 m complet et fiable ; repointer vers le 0,5 m quand il couvrira
#   toute la région (même schéma WCS, coverage "Coverage1").
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Italie (Émilie-Romagne) — DTM 5 m (RER, WCS)"
CODE       = "it-emilia-romagna"
COUNTRY    = "it"
LICENSE    = "CC BY 4.0 — © Regione Emilia-Romagna"
DOC_URL    = "https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/altimetria/layer-2"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:7791"          # RDN2008 / UTM 32N
RESOLUTION_M       = 5.0                   # DTM 5 m (offsetVector du WCS)
DALLE_KM           = 5                     # tuile 5×5 km → 1000×1000 px à 5 m
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000              # Float32 1000×1000 compressé (>> erreur XML)


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://servizigis.regione.emilia-romagna.it/wcs/dtm5x5"
COVERAGE = "DTM5X5_RDN32_RMD"
# axisLabels="x y" (depuis DescribeCoverage) — minuscules, x=Est y=Nord
WCS_AXIS_LABELS = ("x", "y")
# Étendue du coverage en EPSG:7791 (depuis DescribeCoverage)
COVERAGE_EXTENT = (508200, 4843000, 802800, 5002000)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"it_er_dtm5_{x_km}_{y_km}.tif"


def subdir_from_name(nom):
    import re
    m = re.match(r"it_er_dtm5_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0.1 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 2.0.1 GetCoverage, subsets x/y en EPSG:7791 → GeoTIFF."""
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
        print("  Emilia-Romagna: bbox out of the DTM extent (UTM 32N / RDN2008)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  IT Emilia-Romagna (DTM 5m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}


# ── Hook post_fetch : réétiqueter le CRS EPSG:7791 ───────────────────────────
def post_fetch(chemin):
    """Le WCS RER renvoie un GeoTIFF à la géoréf correcte mais SANS tag CRS
    (src.crs → None). On réétiquette en EPSG:7791 EN PLACE (métadonnée seule, pas
    de reprojection). S'exécute APRÈS la désencapsulation multipart du cœur ; le
    cœur re-valide ensuite la dalle."""
    from pathlib import Path as _P
    p = _P(chemin)
    try:
        with open(p, "rb") as fh:
            if fh.read(2) not in (b"II", b"MM"):
                return          # pas un TIFF brut (erreur/HTML) → laisser le validateur
    except OSError:
        return
    import rasterio
    with rasterio.open(p, "r+") as src:
        if src.crs is None:
            src.crs = rasterio.CRS.from_epsg(7791)
