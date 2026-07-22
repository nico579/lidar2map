# providers/lv_lgia.py — Lettonie, DTM 1 m depuis le LiDAR national (LĢIA, LAS)
#
# Source : Latvijas Ģeotelpiskās informācijas aģentūra (LĢIA), open data
#   https://www.lgia.gov.lv/en/atvertie-dati
#   Liste des LAS : https://s3.storage.pub.lvdc.gov.lv/lgia-opendata/las/LGIA_OpenData_las_saites.txt
#
# Paradigme : index statique (S3) de ~66 000 nuages LAS 1 km² classifiés →
#   téléchargement du LAS → binning classe 2 (sol) → GeoTIFF (schéma cz_cuzk,
#   conversion mutualisée dans providers/common.py::las_to_dtm).
#   - CRS natif EPSG:3059 (LKS-92 / Latvia TM).
#   - LAS 1.2, format point 1, classifiés (classe 2 = sol présente, densité sol
#     >= 1,5 pt/m²). Fichiers ~50-100 Mo (nuages denses) → binning min-z (pas
#     d'interpolation Delaunay, qui exploserait à ~7 M points/tuile).
#   - Résolution cible 1 m, dalle 1×1 km.
#   - Licence : CC BY 4.0 (LĢIA open data).
#   - NÉCESSITE laspy (+ scipy/rasterio) au runtime pour post_fetch.
#
# La DÉCOUVERTE (index S3 + mesure TKS-93 des origines de feuille depuis les
#   en-têtes LAS) vit dans common.lgia_dalles, partagée avec le jumeau lv-lgia-laz
#   (mode LAZ DFM/CSF sur le nuage complet, même index).
#
# Self-contained : stdlib uniquement (laspy/scipy/rasterio requis au runtime).

import re
from pathlib import Path

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Lettonie — DTM 1 m (LĢIA, LiDAR LAS)"
CODE       = "lv-lgia"
COUNTRY    = "lv"
LICENSE    = "CC BY 4.0 — © Latvijas Ģeotelpiskās informācijas aģentūra (LĢIA)"
DOC_URL    = "https://www.lgia.gov.lv/en/atvertie-dati"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3059"          # LKS-92 / Latvia TM
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000
SEUIL_DALLE_VALIDE = 100_000              # GeoTIFF 1000×1000 compressé

# Exemple réel pour le test de disjonction intra-pays (nommage non-formule).
SAMPLE_DALLE = "lv_dtm1_649_176.tif"


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"lv_dtm1_{int(x_km)}_{int(y_km)}.tif"


def subdir_from_name(nom):
    m = re.match(r"lv_dtm1_(\d+)_", nom)
    return m.group(1) if m else None


# ── Découverte (index S3 + mesure TKS-93, mutualisée common.lgia_dalles) ──────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=8):
    """{lv_dtm1_<x>_<y>.tif: url_las} pour les tuiles 1 km intersectant bbox_natif
    (EPSG:3059). Le contenu téléchargé est un .las → GeoTIFF par post_fetch."""
    dalles = common.lgia_dalles(bbox_natif, dalle_filename, Path(cache_path), workers)
    if dalles is None:
        return None
    print(f"  LV Latvia (DTM 1m, LiDAR): {len(dalles)} tile(s) in the bbox")
    return dalles


# ── Hook post_fetch : LAS → GeoTIFF DTM (binning classe sol) ──────────────────
def post_fetch(chemin):
    """Le téléchargement est un .las brut (magic LASF), écrit sous un nom .tif par
    le cœur. On convertit en GeoTIFF DTM (binning min-z classe 2) via
    common.las_to_dtm. Détection par magic LASF (pas suffixe)."""
    chemin = Path(chemin)
    try:
        with open(chemin, "rb") as fh:
            magic = fh.read(4)
    except OSError:
        return
    if magic != b"LASF":
        return  # déjà un GeoTIFF (ou réponse d'erreur → le validateur tranchera)

    las_tmp = chemin.with_suffix(".las")
    chemin.replace(las_tmp)
    # Bornes nominales de la tuile 1 km (le nom porte le coin SW en km) →
    # grille alignée au km entre tuiles voisines (pas de couture au VRT).
    m = re.match(r"lv_dtm1_(\d+)_(\d+)\.tif$", chemin.name)
    bounds = ((int(m.group(1)) * 1000, int(m.group(2)) * 1000,
               (int(m.group(1)) + 1) * 1000, (int(m.group(2)) + 1) * 1000)
              if m else None)
    try:
        common.las_to_dtm(las_tmp, chemin, crs_epsg=3059,
                          resolution=RESOLUTION_M, classes=(2,), bounds=bounds)
    finally:
        las_tmp.unlink(missing_ok=True)
