# providers/fr_ign.py — France, IGN LiDAR HD (geopf.fr)
#
# Source de référence pour le pattern provider. Définit toutes les
# spécificités du téléchargement de dalles LiDAR HD IGN :
#   - URLs WMS / WFS / TMS index
#   - CRS natif (Lambert-93)
#   - Géométrie des dalles (1 km × 1 km, 0.5 m/px)
#   - Format de nommage et organisation sous-dossiers
#   - Construction d'URL GetMap
#
# Tout le reste du pipeline (SVF, ombrages, warp EPSG:3857, MBTiles) est
# provider-agnostique : il consomme des GeoTIFF en CRS natif et n'a rien
# de spécifique à la France au-delà de ce module.

import urllib.parse


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "France — IGN LiDAR HD"
CODE       = "fr-ign"
LICENSE    = "Open License Etalab 2.0"
DOC_URL    = "https://geoservices.ign.fr/lidarhd"


# ── Géométrie des dalles ─────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2154"          # Lambert-93
RESOLUTION_M       = 0.5                  # résolution native (m/px)
DALLE_KM           = 1                    # côté d'une dalle (km)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 2000 px

# Seuil de validation : dalles plus petites = mer/hors-couverture, ignorées.
# IGN sert ~16 Mo pour une dalle 2000×2000 px GeoTIFF compressé.
SEUIL_DALLE_VALIDE = 2_000_000            # octets


# ── Endpoints ────────────────────────────────────────────────────────────────
WMS_URL   = "https://data.geopf.fr/wms-r"
WFS_URL   = "https://data.geopf.fr/wfs/ows"
TMS_URL   = "https://data.geopf.fr/tms/1.0.0/IGNF_MNT-LIDAR-HD-produit"
WMS_LAYER = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93"


# ── Conventions de nommage des dalles ────────────────────────────────────────
def dalle_filename(x_km, y_km):
    """Nom du fichier .tif pour la dalle (x_km, y_km) en coordonnées Lambert-93.
    Convention IGN : LHD_FXX_XXXX_YYYY_MNT_O_0M50_LAMB93_IGN69.tif"""
    return f"LHD_FXX_{x_km:04d}_{y_km:04d}_MNT_O_0M50_LAMB93_IGN69.tif"


def dalle_subdir(x_km):
    """Sous-dossier où ranger une dalle dans le cache (organisation par
    colonne X pour éviter d'avoir 10000+ fichiers dans un seul dossier).
    Retourne une string vide si on stocke à la racine."""
    return f"{x_km:04d}"


# Pattern pour extraire le sous-dossier depuis un nom de dalle déjà connu
# (utilisé par chemin_dalle pour retrouver l'emplacement d'une dalle quand
# on n'a que son nom, pas ses coordonnées).
import re as _re
_SUBDIR_FROM_NAME = _re.compile(r"LHD_FXX_(\d+)_")


def subdir_from_name(nom):
    """Retourne le sous-dossier d'une dalle à partir de son nom de fichier,
    ou None si le nom ne matche pas le format attendu."""
    m = _SUBDIR_FROM_NAME.match(nom)
    return m.group(1) if m else None


# ── Construction URL WMS pour une dalle ──────────────────────────────────────
def dalle_url(x_km, y_km):
    """URL WMS GetMap pour télécharger la dalle (x_km, y_km).
    Le WMS IGN 1.3.0 retourne les pixels centrés sur la grille dalles.
    L'offset ±0.25 m (demi-pixel à 0.5 m/px) compense la convention
    "coin supérieur gauche" du WMS pour aligner les dalles sans chevauchement."""
    xmin = x_km * DALLE_KM * 1000 - 0.25
    xmax = xmin + DALLE_KM * 1000
    ymin = y_km * DALLE_KM * 1000 + 0.25
    ymax = ymin + DALLE_KM * 1000
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": WMS_LAYER, "FORMAT": "image/geotiff", "STYLES": "",
        "CRS": CRS_NATIF,
        "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
        "WIDTH": PX_PAR_DALLE, "HEIGHT": PX_PAR_DALLE,
        "FILENAME": dalle_filename(x_km, y_km),
    }
    return WMS_URL + "?" + urllib.parse.urlencode(params)


# ── Calcul de la liste des dalles couvrant une bbox ──────────────────────────
def dalles_pour_bbox(x1, y1, x2, y2):
    """Liste (x_km, y_km) des dalles couvrant la bbox Lambert-93.
    Inclusive aux bords : une dalle dont le coin SW = (x2, y2) sera incluse."""
    step = DALLE_KM * 1000
    x_start = int(x1 // step)
    x_end   = int(x2 // step)
    y_start = int(y1 // step)
    y_end   = int(y2 // step)
    return [(x_km, y_km)
            for x_km in range(x_start, x_end + 1)
            for y_km in range(y_start, y_end + 1)]
