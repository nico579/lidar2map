"""Constantes et règles pures du domaine raster WMTS.

Ce module ne lit ni l'environnement ni le réseau. Le chargement de la clé API,
les exceptions métier et les dépendances patchables restent dans la façade
``lidar2map``.
"""


SEUIL_ERR_CONSEC = 30
SEUIL_HORS_COUVERTURE = 300
BATCH_MBTILES_INSERT = 2000

WMTS_URL = "https://data.geopf.fr/private/wmts"
WMTS_URL_PUB = "https://data.geopf.fr/wmts"
WMTS_HEADERS = {"User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/49.0"}


# Couches WMTS IGN — (identifiant_layer, style, format, clé_privée_requise)
COUCHES = {
    # Cartes topographiques publiques
    "planign":       ("GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2",         "normal", "image/png",  False),
    "etatmajor40":   ("GEOGRAPHICALGRIDSYSTEMS.ETATMAJOR40",       "normal", "image/jpeg", False),
    "etatmajor10":   ("GEOGRAPHICALGRIDSYSTEMS.ETATMAJOR10",       "normal", "image/jpeg", False),
    "pentes":        ("GEOGRAPHICALGRIDSYSTEMS.SLOPES.MOUNTAIN",   "normal", "image/png",  False),
    # Imagerie publique
    "ortho":         ("ORTHOIMAGERY.ORTHOPHOTOS",                  "normal", "image/jpeg", False),
    "ortho_1950":    ("ORTHOIMAGERY.ORTHOPHOTOS.1950-1965",        "normal", "image/png",  False),
    "ortho_1965":    ("ORTHOIMAGERY.ORTHOPHOTOS.1965-1980",        "normal", "image/png",  False),
    "ortho_1980":    ("ORTHOIMAGERY.ORTHOPHOTOS.1980-1995",        "normal", "image/png",  False),
    "ortho_irc":     ("ORTHOIMAGERY.ORTHOPHOTOS.IRC",              "normal", "image/jpeg", False),
    "pleiades":      ("ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2024",      "normal", "image/jpeg", False),
    "spot":          ("ORTHOIMAGERY.ORTHO-SAT.SPOT.2024",          "normal", "image/jpeg", False),
    # Orthophotographies EDUGEO PACA, à couverture locale
    "edugeo_marseille_1969": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1969", "normal", "image/png", False),
    "edugeo_marseille_1980": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1980", "normal", "image/png", False),
    "edugeo_marseille_1987": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1987", "normal", "image/png", False),
    "edugeo_marseille_1988": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1988", "normal", "image/png", False),
    "edugeo_marseille_2010": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES2010", "normal", "image/png", False),
    "edugeo_toulon_1972":    ("ORTHOIMAGERY.EDUGEO.TOULON-HYERES1972",      "normal", "image/png", False),
    # Données thématiques publiques
    "cadastre":      ("CADASTRALPARCELS.PARCELLAIRE_EXPRESS",      "normal", "image/png",  False),
    "ombrage":       ("ELEVATION.ELEVATIONGRIDCOVERAGE.SHADOW",    "normal", "image/png",  False),
    # Imagerie XYZ ArcGIS hors France
    "naip":          ("XYZ:https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}", "normal", "image/jpeg", False),
    # Cartes topographiques réservées aux professionnels
    "scan25":        ("GEOGRAPHICALGRIDSYSTEMS.MAPS",              "normal", "image/jpeg", True),
    "scan25tour":    ("GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN25TOUR",   "normal", "image/jpeg", True),
    "scan100":       ("GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN100",      "normal", "image/jpeg", True),
    "scanoaci":      ("GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN-OACI",    "normal", "image/jpeg", True),
}


def jpeg_quality_sortie(img_fmt, formats_image, qualite_image):
    """Retourne la qualité PNG→JPEG, ou ``None`` sans réencodage."""
    native_png = img_fmt.lower() in ("image/png", "png")
    return qualite_image if (native_png and formats_image != "png") else None


def nom_mbtiles_wmts(nom, couche, zoom_min, zoom_max, jpeg_q):
    """Construit le nom de base déterministe du MBTiles WMTS."""
    suffixe_qualite = f"_q{int(jpeg_q)}" if jpeg_q is not None else ""
    return f"{nom}_{couche}_z{zoom_min}-{zoom_max}{suffixe_qualite}"
