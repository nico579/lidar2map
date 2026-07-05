# providers/es_cnig.py — Espagne, MDT 5m via WCS INSPIRE IGN/CNIG
#
# Source : Instituto Geográfico Nacional (IGN) / CNIG — service WCS INSPIRE MDT
#   GetCapabilities : https://servicios.idee.es/wcs-inspire/mdt?request=GetCapabilities&service=WCS
#
# Paradigme : WCS 2.0.1 GetCoverage par bbox (calque at_tirol / be_flanders).
#   - CRS natif EPSG:25830 (ETRS89 / UTM 30N) — péninsule ibérique
#   - Coverage "Elevacion25830_5" = MDT 5 m (la meilleure résolution servie par
#     le WCS ; 25 m / 200 m / 1000 m aussi disponibles, plus grossiers)
#   - axisLabels="x y" (minuscules, comme MapServer Vlaanderen) → WCS_AXIS_LABELS
#   - GetCoverage renvoie un GeoTIFF brut (pas de multipart)
#   - Licence : CC BY 4.0 — © IGN España
#
# NB RÉSOLUTION : ce provider sert le MDT 5 m (échelle paysage : terrasses,
# enceintes, voies, hydrologie). Le LiDAR brut espagnol (PNOA-LiDAR 1-2 m,
# micro-relief) n'est distribué que via le portail à session du Centro de
# Descargas (recherche spatiale → ID fichier → descargaDir avec cookie/CSRF),
# qui demanderait un scraper fragile non-documenté → écarté. Le WCS 5 m est
# l'accès propre et maintenable au prix d'une résolution moindre.
#
# Self-contained : stdlib uniquement.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Espagne — MDT (IGN/CNIG, WCS)"
CODE       = "es-cnig"
COUNTRY    = "es"
LICENSE    = "CC BY 4.0 — © IGN España / CNIG"
DOC_URL    = "https://servicios.idee.es/wcs-inspire/mdt?request=GetCapabilities&service=WCS"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25830"         # ETRS89 / UTM 30N (péninsule)
RESOLUTION_M       = 5.0                  # MDT 5 m
DALLE_KM           = 5                     # tuile 5×5 km → 1000×1000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000
SEUIL_DALLE_VALIDE = 100_000              # Float32 1000×1000 compressé


# ── Endpoints ────────────────────────────────────────────────────────────────
WCS_URL  = "https://servicios.idee.es/wcs-inspire/mdt"
COVERAGE = "Elevacion25830_5"
# axisLabels="x y" (depuis DescribeCoverage) — PAS E/N
WCS_AXIS_LABELS = ("x", "y")
# Étendue du coverage en EPSG:25830 (depuis DescribeCoverage)
COVERAGE_EXTENT = (-19452, 3901197, 1140352, 4865682)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"es_mdt5m_{x_km}_{y_km}.tif"


def dalle_subdir(x_km):
    return f"{x_km}"


def subdir_from_name(nom):
    import re
    m = re.match(r"es_mdt5m_(\d+)_", nom)
    return m.group(1) if m else None


# ── Construction URL WCS 2.0.1 GetCoverage ───────────────────────────────────
def dalle_url(x_km, y_km):
    """WCS 2.0.1 GetCoverage, subsets x/y en EPSG:25830 → GeoTIFF."""
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
        print("  Spain: bbox out of the MDT extent (UTM 30N peninsula)")
        return {}
    grille = dalles_pour_bbox(ix1, iy1, ix2, iy2)
    print(f"  ES IGN (MDT 5m): {len(grille)} tile(s) generated")
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in grille}
