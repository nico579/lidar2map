# providers/lv_lgia_laz.py — Lettonie, « mode LAZ » nuage LiDAR national (LĢIA)
#
# CONTEXTE : LĢIA diffuse le nuage LiDAR national en LAS CLASSIFIÉ (sol/végé/bâti),
#   données ouvertes CC BY 4.0. Vérifié bout-en-bout 2026-07-22 : nuage COMPLET
#   (classes 2 sol, 3/4/5 végé, 6 bâti — PAS ground-only, donc apte au DFM/CSF qui
#   ont besoin des retours non-sol pour les murs), ~3,4 pts/m² total (~1,6 sol).
#   Densité MARGINALE pour du micro-relief 0,5 m (comme l'Estonie ee-maaamet-laz) :
#   couverture nationale mais à valider terrain avant d'y croire.
#
# JUMEAU LAZ de lv-lgia (raster DTM 1 m, binning classe 2). Machinerie DFM/CSF
#   dans common.LazProvider ; découverte (index S3 + mesure TKS-93 des origines de
#   feuille depuis les en-têtes LAS) MUTUALISÉE dans common.lgia_dalles, partagée
#   avec le raster (même index caché). CRS EPSG:3059 UNIQUE (national, projeté :
#   pas de wrinkle multi-zone). Défaut ground=csf (schéma de classes ≠ IGN).
#   NB : les fichiers sont des .las NON compressés (~78 Mo/tuile), pas des .laz.
#
# Licence : CC BY 4.0 — LĢIA open data. Self-contained : stdlib + laspy.

from pathlib import Path

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Lettonie — mode LAZ nuage LiDAR ALS 0,5 m (~3,4 pts/m², expérimental)"
CODE       = "lv-lgia-laz"
COUNTRY    = "lv"
LICENSE    = "CC BY 4.0 — © Latvijas Ģeotelpiskās informācijas aģentūra (LĢIA)"
DOC_URL    = "https://www.lgia.gov.lv/en/atvertie-dati"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3059"          # LKS-92 / Latvia TM (national, unique)
RESOLUTION_M       = 0.5
SEUIL_DALLE_VALIDE = 100_000


# ── Bornes nominales (coin SW en km ; tuiles TKS-93 alignées au km) ───────────
def _bounds_nominaux(x_km, y_km):
    """(x_km, y_km) = coin SW en km → bornes 1 km alignées entre tuiles voisines
    (pas de couture au VRT)."""
    x, y = int(x_km) * 1000, int(y_km) * 1000
    return (x, y, x + 1000, y + 1000)


# ── Découverte (index S3 + mesure TKS-93, mutualisée common.lgia_dalles) ──────
def _discover(bbox_wgs84, bbox_natif, cache_path, workers=8):
    dalles = common.lgia_dalles(bbox_natif, dalle_filename, Path(cache_path), workers)
    if dalles is None:
        return None
    if dalles:
        print(f"  LV LĢIA LAZ (LAS classifié): {len(dalles)} tile(s) in the bbox "
              f"(~3,4 pts/m², marginal — validation terrain conseillée)")
    else:
        print("  LV LĢIA LAZ: no tile here")
    return dalles


# ── Machinerie DFM (mutualisée) ──────────────────────────────────────────────
# Préfixe « lv_laz05 » (laz = nuage ; 05 = version de méthode). CRS mono-zone
# 3059. Socle ASPRS (2=sol, 9=eau) ; classes réinjectables 3/4/5/6. Défaut csf.
_P = common.LazProvider(
    prefix="lv_laz05", crs_epsg=3059, resolution=RESOLUTION_M,
    socle_possible=(2, 9),
    defaults=(0.4, 2.5, (2, 3, 4, 5, 6), "csf"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=_bounds_nominaux, discover_fn=_discover,
    zipped=False, tile_mb=80)

DOWNLOAD_WORKERS_MAX = _P.download_workers_max

# Défauts exposés (lus par le cœur pour préremplir la GUI + par les tests)
LAZ_HMIN           = _P.def_hmin
LAZ_HMAX           = _P.def_hmax
LAZ_CLASSES        = _P.def_classes
LAZ_GROUND         = _P.def_ground
LAZ_CSF_THRESHOLD  = _P.def_csf_threshold
LAZ_CSF_RESOLUTION = _P.def_csf_resolution
LAZ_CSF_RIGIDNESS  = _P.def_csf_rigidness

# Contrat provider : delegators vers l'instance partagée
set_laz_params   = _P.set_params
dalle_filename   = _P.dalle_filename
subdir_from_name = _P.subdir_from_name
variant_tag      = _P.variant_tag
method_label     = _P.method_label
discover_dalles  = _P.discover_dalles
pre_download     = _P.pre_download
post_fetch       = _P.post_fetch
set_cloud_cache_dir = _P.set_cloud_cache_dir
# Internes exposés pour les tests
_socle           = _P.socle
_reinjectees     = _P.reinjectees
_laz_filename    = _P.laz_filename


def dalle_url(x_km, y_km):
    raise NotImplementedError("lv-lgia-laz : URL via index LAS S3 → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("lv-lgia-laz : index LAS S3 → discover_dalles()")
