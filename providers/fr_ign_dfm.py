# providers/fr_ign_dfm.py — France, DFM « ruines/structures debout » 0,5 m
# depuis le nuage classé LiDAR HD IGN (COPC LAZ)
#
# POURQUOI : le MNT IGN (fr-ign) efface PAR CONSTRUCTION les murs encore debout
#   au-delà d'environ 1 m : la chaîne IGN_AUTO les classe « végétation » (4) ou
#   « non classé » (1), et le MNT (classes 2/9/66 + TIN) interpole au travers.
#   Paradoxe documenté (spec DC_LiDAR_HD) : un muret de 40 cm survit, une ruine
#   de 1,5 m disparaît. Ce provider reconstruit un **DFM** (Digital Feature
#   Model, Štular et al. 2021) : le terrain + les structures debout, en
#   réinjectant les retours bas non-sol (0,4-2,5 m, classes 1/3/4) dans les
#   trous de la classe sol. Tous les ombrages (LRM, VAT…) fonctionnent ensuite
#   tels quels. Le maquis revient aussi (mouchetis) : murs = lignes continues,
#   buissons = tavelures — l'œil discrimine (Kokalj & Hesse).
#
# COÛT (à savoir avant de lancer) : une dalle COPC = ~205 Mo (vs 16 Mo de MNT),
#   ~34 M de points, conversion ~20-30 s/dalle, ~1 Go de RAM. Outil de
#   PROSPECTION CIBLÉE (quelques km²), pas de grandes cartes. Pour l'analyse
#   fine d'un site : tools/dfm_ruines.py (GeoTIFF à draper dans QGIS).
#
# Paradigme : index WFS `IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle` (chaque dalle
#   1 km porte son `url` de download direct, comme fr-reunion/fr-guadeloupe ;
#   découverte mutualisée common.ign_lidar_hd_dalles) → COPC LAZ → post_fetch
#   common.las_to_dfm → GeoTIFF 0,5 m EPSG:2154.
#   Licence : Licence Ouverte 2.0 (Etalab) — © IGN.
#
# Self-contained : stdlib uniquement (laspy/lazrs/rasterio requis au runtime).

import re


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "France — DFM ruines/structures 0,5 m (LiDAR HD LAZ, ~205 Mo/km²)"
CODE       = "fr-ign-dfm"
COUNTRY    = "fr"
LICENSE    = "Licence Ouverte 2.0 (Etalab) — © IGN"
DOC_URL    = "https://geoservices.ign.fr/lidarhd"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2154"          # Lambert-93
RESOLUTION_M       = 0.5
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000
SEUIL_DALLE_VALIDE = 500_000              # GeoTIFF 2000² DEFLATE après conversion

# Tranche de hauteur réintroduite (au-dessus du sol local) et classes LAS
# concernées. Défauts éprouvés sur ruines du Var (murs ~1,5 m) : 0,4-2,5 m,
# classes 1 (non classé), 3/4 (végétation basse/moyenne).
DFM_HMIN, DFM_HMAX = 0.4, 2.5
DFM_CLASSES        = (1, 3, 4)


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(x_km, y_km):
    return f"fr_dfm05_{int(x_km)}_{int(y_km)}.tif"


def dalle_subdir(x_km):
    return f"{int(x_km)}"


def subdir_from_name(nom):
    m = re.match(r"fr_dfm05_(\d+)_", nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("fr-ign-dfm : URL via WFS dalle → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("fr-ign-dfm : index WFS → discover_dalles()")


# ── Découverte (WFS IGN LiDAR HD, mutualisée — typename NUAGES-DE-POINTS) ────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    from providers import common
    dalles = common.ign_lidar_hd_dalles(
        bbox_natif, 2154, dalle_filename,
        typename="IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle")
    if dalles is None:
        return None
    if dalles:
        print(f"  FR DFM (LiDAR HD LAZ): {len(dalles)} tile(s) in the bbox "
              f"(~{len(dalles) * 205} MB of point cloud to download!)")
    else:
        print("  FR DFM: no LiDAR HD point-cloud tile here (not flown yet?)")
    return dalles


# ── Hook post_fetch : COPC LAZ → GeoTIFF DFM ─────────────────────────────────
def post_fetch(chemin):
    """Le download est un COPC LAZ (magic LASF), écrit sous un nom .tif par le
    cœur. Conversion DFM via common.las_to_dfm (binning sol + réinjection des
    retours bas non-sol dans les trous). ~1-2 min/dalle, ~1 Go RAM."""
    from pathlib import Path as _P
    chemin = _P(chemin)
    try:
        with open(chemin, "rb") as fh:
            magic = fh.read(4)
    except OSError:
        return
    if magic != b"LASF":
        return  # déjà un GeoTIFF (ou erreur → validateur)

    from providers import common
    laz_tmp = chemin.with_suffix(".laz")
    chemin.replace(laz_tmp)
    try:
        print(f"  DFM {chemin.name}: converting ~34M-pt cloud (~20-30 s)...",
              flush=True)
        common.las_to_dfm(laz_tmp, chemin, crs_epsg=2154,
                          resolution=RESOLUTION_M,
                          hmin=DFM_HMIN, hmax=DFM_HMAX,
                          classes_low=DFM_CLASSES)
    finally:
        laz_tmp.unlink(missing_ok=True)
