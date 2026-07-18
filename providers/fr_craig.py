# providers/fr_craig.py — France (Auvergne-Rhône-Alpes), CRAIG MNT LiDAR 0,5 m
#
# Source : CRAIG (Centre Régional Auvergne-Rhône-Alpes de l'Information
#   Géographique), programme LiDARAURA. Partage Nextcloud PUBLIC
#   (drive.opendata.craig.fr/s/opendata), download `/s/<token>/download` sans auth.
#   MNT = ESRI ASCII Grid `.asc` 0,5 m EPSG:2154 (converti en GeoTIFF au post_fetch).
#   Doc : https://www.craig.fr/contenu/nuages-de-points-lidar
#
# RÔLE : ce provider raster est surtout le PARENT du jumeau fr-craig-dfm (le
#   « mode LAZ » haute densité, la vraie valeur CRAIG). Son raster (MNT) est
#   secondaire : l'IGN couvre déjà la France. Découverte par index shapefile
#   (common.craig_dalles), campagne 2019 (seule avec un index MNT propre).
#
# Self-contained : rasterio au post_fetch (déjà dépendance du pipeline).

import re

from providers import common

# ── Identification ───────────────────────────────────────────────────────────
NAME       = "France — CRAIG MNT LiDAR 0,5 m (Auvergne-Rhône-Alpes)"
CODE       = "fr-craig"
COUNTRY    = "fr"
LICENSE    = "Licence Ouverte 2.0 (Etalab) — © CRAIG"
DOC_URL    = "https://www.craig.fr/contenu/nuages-de-points-lidar"

# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2154"          # Lambert-93 (le .asc n'embarque pas le CRS)
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 50_000               # tuiles CRAIG petites (200-500 m)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x, y):
    return f"fr_craig_dtm05_{int(x)}_{int(y)}.tif"


def dalle_subdir(x):
    return f"{int(x)}"


def subdir_from_name(nom):
    m = re.match(r"fr_craig_dtm05_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x, y):
    raise NotImplementedError("fr-craig : URL via index TA → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("fr-craig : index shapefile → discover_dalles()")


# ── Découverte (index shapefile CRAIG, mutualisée) ───────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    # Le raster n'a pas besoin des bornes par tuile (le .asc est auto-géoréférencé) :
    # sink jetable.
    dalles = common.craig_dalles(bbox_natif, dalle_filename, {}, cache_path,
                                 campaigns=common.CRAIG_MNT_CAMPAIGNS)
    if dalles:
        print(f"  FR CRAIG MNT: {len(dalles)} tile(s) in the bbox (0,5 m)")
    else:
        print("  FR CRAIG MNT: no CRAIG tile here (coverage = named survey zones)")
    return dalles


# ── post_fetch : ESRI ASCII Grid (.asc) → GeoTIFF EPSG:2154 ───────────────────
def post_fetch(chemin):
    """La dalle téléchargée est un `.asc` (ESRI ASCII Grid) SANS CRS embarqué,
    écrite sous un nom .tif par le cœur. On la relit (driver AAIGrid, détecté au
    contenu) et on la réécrit en GeoTIFF EPSG:2154 : sinon _valider_tif_dalle la
    rejette (pas un magic GeoTIFF) et le CRS serait absent."""
    from pathlib import Path

    import rasterio
    chemin = Path(chemin)
    try:
        with open(chemin, "rb") as fh:
            head = fh.read(2)
    except OSError:
        return
    if head in (b"II", b"MM"):
        return                          # déjà un GeoTIFF (rien à faire)
    with rasterio.open(str(chemin)) as src:      # AAIGrid détecté au contenu
        data = src.read(1)
        profile = src.profile
    # GeoTIFF strippé (pas de tiled : la source .asc porte un blocksize non
    # multiple de 16 qui casse un GTiff tuilé, et les tuiles CRAIG sont petites).
    profile.pop("blockxsize", None); profile.pop("blockysize", None)
    profile.update(driver="GTiff", crs=rasterio.CRS.from_epsg(2154),
                   compress="deflate", predictor=3, tiled=False)
    tmp = Path(str(chemin) + ".gtif.tmp")
    with rasterio.open(str(tmp), "w", **profile) as dst:
        dst.write(data, 1)
    tmp.replace(chemin)
