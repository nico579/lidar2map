# providers/ca_quebec.py — Québec, MNT LiDAR 1 m (COG) via le GeoServer RGQ
#
# Source : Gouvernement du Québec — Ressources naturelles et Forêts (MRNF),
#   Réseau géodésique / diffusion RGQ. Le MNT 1 m est DÉRIVÉ du LiDAR provincial
#   (gratuit, CC BY 4.0, sans compte). https://www.donneesquebec.ca/recherche/dataset/produits-derives-de-base-du-lidar
#
# Paradigme : WFS d'index de téléchargement + COG (comme ca-nrcan HRDEM).
#   - Découverte : couche WFS `IndexTelechargementMNT` (GeoServer RGQ) ; chaque
#     feuille 15 km porte son URL GeoTIFF directe (TELECHARGEMENT_TUILE) et son
#     CODE_EPSG. common.quebec_wfs_features (partagé avec ca-quebec-laz).
#   - Tuiles = COG 15 km × 15 km à 1 m (~600 Mo/feuille, tiled 256 + overviews) →
#     on NE rapatrie PAS le fichier : lecture FENÊTRÉE bbox via /vsicurl
#     (COG_WINDOWED, cf. telecharger_cog_fenetre).
#   - CRS UNIQUE province-wide : EPSG:6622 (NAD83(CSRS) / Québec Lambert). Pas de
#     multi-zone ici (c'est le NUAGE LAZ qui est en MTM par fuseau, cf. le jumeau).
#   - Millésime : plusieurs acquisitions (2013/2017/2025…) couvrent la même
#     feuille 15 km ; pas de couche « PlusRecent » côté MNT → on DÉDUPLIQUE par
#     emprise (grille du nom) en gardant l'année la plus récente (inutile de
#     composer plusieurs COG d'emprise identique).
#   - Les URLs sont en `.TIF` (majuscule) : gdal_env_options() autorise cette
#     extension à /vsicurl (le filtre CPL_VSIL_CURL_ALLOWED_EXTENSIONS du cœur est
#     sensible à la casse).
#
# Ce provider est aussi le PARENT du mode LAZ (providers/ca_quebec_laz.py) : la
# case « Mode LAZ » de la GUI et le remap --laz s'y rattachent.
#
# Self-contained : stdlib uniquement (rasterio/GDAL au runtime pour le COG).

import re

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Québec — MNT LiDAR 1 m (MRNF, dérivé du LiDAR provincial)"
CODE       = "ca-quebec"
COUNTRY    = "ca"
LICENSE    = "Creative Commons Attribution 4.0 (CC BY 4.0) — Gouvernement du Québec"
DOC_URL    = "https://www.donneesquebec.ca/recherche/dataset/produits-derives-de-base-du-lidar"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:6622"          # NAD83(CSRS) / Québec Lambert (unique)
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000
SEUIL_DALLE_VALIDE = 200_000
# MNT = COG 15 km/feuille : lecture fenêtrée bbox via /vsicurl au lieu du fichier.
COG_WINDOWED       = True


# ── Index WFS (GeoServer RGQ) ────────────────────────────────────────────────
_WS    = "Index_Telechargement_Mnt_Pub"
_LAYER = "IndexTelechargementMNT"


# ── Nommage (grille d'emprise du NOM_TUILE : MNT<année>_<gx>_<gy>_…) ──────────
def dalle_filename(gx, gy):
    return f"qc_mnt1m_{int(gx)}_{int(gy)}.tif"


_SUBDIR_FROM_NAME = re.compile(r"qc_mnt1m_(\d+)_\d+\.tif$")


def subdir_from_name(nom):
    m = _SUBDIR_FROM_NAME.match(nom)
    return m.group(1) if m else None


def dalle_url(gx, gy):
    raise NotImplementedError("ca-quebec : URL via WFS index → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("ca-quebec : WFS index → discover_dalles()")


# ── Options GDAL : autoriser l'extension .TIF (majuscule) à /vsicurl ──────────
def gdal_env_options():
    return {"CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff,.TIF"}


# ── Hook post-download : estampiller le code EPSG:6622 ────────────────────────
def post_download(path):
    """Le COG source porte un WKT « Quebec Lambert_SCRS » COMPLET (lat_origin 44,
    méridien -68.5, parallèles 60/46, NAD83(CSRS)/GRS80) mais SANS code EPSG
    (to_epsg()->None), ce qui laisserait la dalle fenêtrée sans EPSG canonique.
    Cette projection EST EPSG:6622 (paramètres identiques, vérifié) → on estampille
    le code (ASSIGNATION du tag, PAS une reprojection : mêmes coordonnées) pour une
    géoréf propre en aval (VRT/warp 3857) et le garde résolution du smoke. Idempotent."""
    import rasterio
    from rasterio.crs import CRS
    with rasterio.open(str(path), "r+") as s:
        if s.crs is None or s.crs.to_epsg() != 6622:
            s.crs = CRS.from_epsg(6622)


# ── Découverte (WFS IndexTelechargementMNT, dédup emprise → millésime récent) ─
_NOM_RE = re.compile(r"MNT[^_]*_(\d+)_(\d+)_", re.IGNORECASE)
_YEAR_RE = re.compile(r"MNT(\d{4})")


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """WFS IndexTelechargementMNT par bbox → COG DTM 1 m (EPSG:6622). Dédup par
    emprise (grille gx_gy du NOM_TUILE) en gardant l'année la plus récente. Le
    cœur en lit la fenêtre bbox via /vsicurl. None sur échec réseau."""
    feats = common.quebec_wfs_features(_WS, _LAYER, bbox_wgs84)
    if feats is None:
        return None
    best = {}          # (gx, gy) -> (year, url)
    for f in feats:
        p = f.get("properties", {})
        url = p.get("TELECHARGEMENT_TUILE")
        nom = str(p.get("NOM_TUILE") or "")
        m = _NOM_RE.search(nom)
        if not url or not m:
            continue
        gx, gy = int(m.group(1)), int(m.group(2))
        ym = _YEAR_RE.search(nom)
        year = int(ym.group(1)) if ym else 0
        cur = best.get((gx, gy))
        if cur is None or year > cur[0]:
            best[(gx, gy)] = (year, str(url))
    dalles = {dalle_filename(gx, gy): url for (gx, gy), (_y, url) in best.items()}
    if dalles:
        print(f"  QC MNT 1m (COG): {len(dalles)} tile(s) in the bbox "
              f"(windowed read via /vsicurl)")
    else:
        print("  QC MNT: no tile here (coverage gap)")
    return dalles
