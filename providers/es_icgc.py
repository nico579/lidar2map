# providers/es_icgc.py — Catalogne (Espagne), MET 50 cm (LiDAR) via ICGC datacloud
#
# Source : Institut Cartogràfic i Geològic de Catalunya (ICGC) —
#   Model d'Elevacions del Terreny LiDAR 50 cm (couverture 2021-2023).
#   Doc : https://www.icgc.cat/en/Geoinformation-and-Maps/Data-and-products/Digital-twins-Elevations
#   Endpoint exposé par le plugin officiel OpenICGC (github.com/OpenICGC/QgisPlugin).
#
# Paradigme : UN SEUL COG national en lecture fenêtrée /vsicurl (comme lu_act /
#   ca_nrcan). Le MET 50 cm est un unique GeoTIFF Cloud-Optimized de ~433 Go
#   (538000×526000 px à 0,5 m, EPSG:25831, overviews + tuilage 512²). On lit
#   seulement la fenêtre bbox par requêtes HTTP range (COG_WINDOWED=True) ;
#   jamais de download complet.
#
#   - CRS natif EPSG:25831 (ETRS89 / UTM 31N) — CRS du COG, aucune reprojection.
#   - 50 cm → bien plus fin que es_cnig (MDT national 5 m). Catalogne très fouillée
#     (ibères, voie romaine, terrasses).
#   - GeoTIFF Float32, nodata −9999. Pas de post_fetch.
#   - CC BY 4.0 — ICGC. Pas de clé, pas de compte.
#
# NB : variantes ICGC disponibles au même endroit (datacloud …/model-elevacions-
#   terreny/tif_unzip/) : 25cm (AMB Barcelone seulement), 2m (2008-2011), 5m. On
#   cible le 50 cm pleine-Catalogne ; changer COG_URL pour une autre résolution.
#
# Self-contained : stdlib uniquement.

import re


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Catalogne (Espagne) — MET (ICGC, LiDAR 2021-2023)"
CODE       = "es-icgc"
COUNTRY    = "es"
LICENSE    = "CC BY 4.0 — Institut Cartogràfic i Geològic de Catalunya (ICGC)"
DOC_URL    = "https://www.icgc.cat/en/Geoinformation-and-Maps/Data-and-products/Digital-twins-Elevations"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:25831"         # ETRS89 / UTM 31N
RESOLUTION_M       = 0.5
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000 (nominal)
SEUIL_DALLE_VALIDE = 50_000
COG_WINDOWED       = True                 # lecture fenêtrée /vsicurl

# Étendue du COG en EPSG:25831 (lue dans l'en-tête, 2026-06-15).
COVERAGE_EXTENT = (259000, 4487000, 528000, 4750000)   # (E_min, N_min, E_max, N_max)


# ── Endpoint ─────────────────────────────────────────────────────────────────
# COG unique pleine-Catalogne 50 cm (Accept-Ranges: bytes confirmé, ~433 Go).
COG_URL = ("https://datacloud.icgc.cat/datacloud/model-elevacions-terreny/"
           "tif_unzip/model-elevacions-terreny-lidar-catalunya-50cm-2021-2023.tif")


# ── Nommage ──────────────────────────────────────────────────────────────────
def _nom_fenetre(x1, y1, x2, y2):
    """Nom encodant la bbox zone (EPSG:25831, entiers) → 1 fichier par zone
    (sinon telecharger_cog_fenetre ferait « skip » sur une fenêtre périmée)."""
    return f"icgc_met50cm_{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}.tif"


def subdir_from_name(nom):
    # Regrouper par bande 10 km de l'easting de la zone.
    m = re.match(r"icgc_met50cm_(\d+)_", nom)
    return f"{int(m.group(1)) // 10000}" if m else None


# Exemple réel pour le test de disjonction intra-pays (nommage non-formule).
SAMPLE_DALLE = "icgc_met50cm_400000_4600000_401000_4601000.tif"


def dalle_filename(x_km, y_km):
    raise NotImplementedError("ES-ICGC : COG unique fenêtré → discover_dalles()")


def dalle_url(x_km, y_km):
    raise NotImplementedError("ES-ICGC : COG unique fenêtré → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("ES-ICGC : COG unique fenêtré → discover_dalles()")


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """UNE entrée {nom_fenetre: COG_URL} si la bbox intersecte la Catalogne.
    Pas de réseau ; la lecture fenêtrée réelle est faite par telecharger_cog_fenetre
    (COG_WINDOWED=True)."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  ES-ICGC: bbox outside Catalonia extent")
        return {}
    nom = _nom_fenetre(ix1, iy1, ix2, iy2)
    print("  ES-ICGC (MET 50 cm): 1 COG window in the bbox")
    return {nom: COG_URL}
