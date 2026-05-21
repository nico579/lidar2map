# providers/no_kartverket.py — Norvège, Nasjonal Høydemodell (Kartverket)
#
# Source : Kartverket (Norvegian Mapping Authority) via hoydedata.no.
# Distribution : ArcGIS ImageServer (exportImage) → GeoTIFF rendu à la demande.
# Pas d'index de dalles : on construit une grille km synthétique et chaque
# "dalle" est une requête exportImage pour une bbox 1×1 km.
#
# Différence vs FR (WMS GetMap) : ArcGIS ImageServer au lieu de WMS, mais
# le pattern d'accès est identique — bbox → raster. Validé live sur Oslo
# (élévation 0-35m réelle, 4 Mo Float32 par dalle).

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Norvège — Nasjonal Høydemodell (Kartverket)"
CODE       = "no-kartverket"
COUNTRY    = "no"
LICENSE    = "CC BY 4.0 (Kartverket)"
DOC_URL    = "https://hoydedata.no/"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25833"       # ETRS89 / UTM zone 33N (extended for all Norway)
RESOLUTION_M       = 1.0                # 1m natif
DALLE_KM           = 1                  # tuiles synthétiques 1×1 km
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 1000 px
SEUIL_DALLE_VALIDE = 100_000            # Float32 1000×1000 compressé : ~2-4 Mo
                                        # mais le seuil bas tolère les zones en mer
                                        # (où exportImage retourne nodata compressible)


# ── Endpoints ────────────────────────────────────────────────────────────────
IMAGESERVER = "https://hoydedata.no/arcgis/rest/services/DTM/ImageServer"
EXPORT_URL  = f"{IMAGESERVER}/exportImage"


# ── Nommage des dalles ───────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    """Convention de nommage interne (pas d'équivalent IGN officiel norvégien).
    Format : nhm_dtm_<X_km>_<Y_km>_25833_1m.tif"""
    return f"nhm_dtm_{x_km:04d}_{y_km:05d}_25833_1m.tif"


def dalle_subdir(x_km):
    """Sous-dossier par colonne X (km) — convention identique à FR."""
    return f"{x_km:04d}"


import re as _re
_SUBDIR_FROM_NAME = _re.compile(r"nhm_dtm_(\d+)_\d+_")


def subdir_from_name(nom):
    m = _SUBDIR_FROM_NAME.match(nom)
    return m.group(1) if m else None


# ── Construction URL pour une dalle ──────────────────────────────────────────
def dalle_url(x_km, y_km):
    """URL ArcGIS ImageServer exportImage pour une dalle 1×1 km."""
    xmin = x_km * DALLE_KM * 1000
    ymin = y_km * DALLE_KM * 1000
    xmax = xmin + DALLE_KM * 1000
    ymax = ymin + DALLE_KM * 1000
    params = {
        "bbox":      f"{xmin},{ymin},{xmax},{ymax}",
        "bboxSR":    "25833",
        "imageSR":   "25833",
        "size":      f"{PX_PAR_DALLE},{PX_PAR_DALLE}",
        "format":    "tiff",
        "f":         "image",
        "pixelType": "F32",
    }
    return EXPORT_URL + "?" + urllib.parse.urlencode(params)


# ── Grille pour une bbox ─────────────────────────────────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    step = DALLE_KM * 1000
    x_start = int(x1 // step)
    x_end   = int(x2 // step)
    y_start = int(y1 // step)
    y_end   = int(y2 // step)
    return [(x_km, y_km)
            for x_km in range(x_start, x_end + 1)
            for y_km in range(y_start, y_end + 1)]


# ── Découverte des dalles ────────────────────────────────────────────────────
# Pas d'API d'index : on synthétise depuis la grille natif. Tous les (x_km, y_km)
# sont théoriquement servables ; les zones hors couverture (en mer notamment)
# retournent du nodata compressé que le validator filtrera.
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Construit {nom: url} depuis la grille km en CRS natif."""
    if bbox_natif is None:
        return {}
    x1, y1, x2, y2 = bbox_natif
    dalles = {}
    for x_km, y_km in dalles_pour_bbox(x1, y1, x2, y2):
        dalles[dalle_filename(x_km, y_km)] = dalle_url(x_km, y_km)
    print(f"  Kartverket : {len(dalles)} dalle(s) générées (grille km UTM33N)")
    return dalles
