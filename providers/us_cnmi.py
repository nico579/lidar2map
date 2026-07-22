# providers/us_cnmi.py — Îles Mariannes du Nord (CNMI, territoire US), DEM 1 m (NOAA)
#
# Source : NOAA Office for Coastal Management — CNMI Topobathymetric DEM 2019
#   InPort : https://www.fisheries.noaa.gov/inport/item/66821
#   Index S3 : https://noaa-nos-coastal-lidar-pds.s3.us-east-1.amazonaws.com/dem/CNMI_Topobathy_DEM_2019_9474/index.html
#
# Paradigme : UNE mosaïque VRT en lecture fenêtrée /vsicurl (comme es_icgc /
#   lu_act). Le bucket public NOAA expose ~59 tuiles COG 1 m par île (aguijan,
#   saipan, tinian, rota…) + un VRT mosaïque qui les référence ; on lit seulement
#   la fenêtre bbox via HTTP range (COG_WINDOWED=True), sans download complet.
#   - CRS natif EPSG:8693 (NAD83(MA11) / UTM 55N). Le VRT porte un CRS COMPOSÉ
#     (8693 + hauteur NMVD03, to_epsg()=None) → post_download réétiquette en 8693
#     pur (comme de_rlp), pour un warp 3857 propre et le contrôle CRS du smoke.
#   - DEM TOPOBATHYMÉTRIQUE issu des classes sol : la TERRE est du bare-earth
#     (z > 0) ; l'eau porte la bathymétrie (z < 0), inoffensive pour l'archéo
#     terrestre (rendue comme du bas-relief).
#   - GeoTIFF Float32, nodata −999999. Domaine public (NOAA / U.S. Government).
#   - NÉCESSITE d'autoriser l'extension .vrt à /vsicurl → gdal_env_options().
#
# NB LEVIER : le bucket `noaa-nos-coastal-lidar-pds` héberge des dizaines de DEM
#   côtiers US (Guam, Samoa américaines, USVI, Porto Rico…). Ce provider est le
#   patron d'un futur « noaa générique » (paramétré par dataset + étendue).
#
# Self-contained : stdlib uniquement.

import re


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Îles Mariannes du Nord (CNMI) — Topobathy DEM 1 m (NOAA)"
CODE       = "us-cnmi"
COUNTRY    = "us"
LICENSE    = "Public domain — NOAA / U.S. Government"
DOC_URL    = "https://www.fisheries.noaa.gov/inport/item/66821"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:8693"          # NAD83(MA11) / UTM 55N
RESOLUTION_M       = 1.0
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 1000 (nominal)
SEUIL_DALLE_VALIDE = 50_000
COG_WINDOWED       = True

# Étendue de la mosaïque VRT en EPSG:8693 (lue dans l'en-tête).
COVERAGE_EXTENT = (297075, 1560405, 374940, 1691197)   # (E_min, N_min, E_max, N_max)


# ── Endpoint ─────────────────────────────────────────────────────────────────
# VRT mosaïque (référence les ~59 COG tuiles ; lu fenêtré via /vsicurl).
COG_URL = ("https://noaa-nos-coastal-lidar-pds.s3.us-east-1.amazonaws.com/dem/"
           "CNMI_Topobathy_DEM_2019_9474/CNMI_Topobathy_DEM_2019_m9474_EPSG-8693.vrt")


# ── Nommage ──────────────────────────────────────────────────────────────────
def _nom_fenetre(x1, y1, x2, y2):
    return f"cnmi_dtm1_{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}.tif"


def subdir_from_name(nom):
    m = re.match(r"cnmi_dtm1_(\d+)_", nom)
    return f"{int(m.group(1)) // 10000}" if m else None


# Exemple réel pour le test de disjonction intra-pays (nommage non-formule).
SAMPLE_DALLE = "cnmi_dtm1_365000_1679000_366000_1680000.tif"


def dalle_filename(x_km, y_km):
    raise NotImplementedError("US-CNMI : VRT fenêtré → discover_dalles()")


def dalle_url(x_km, y_km):
    raise NotImplementedError("US-CNMI : VRT fenêtré → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("US-CNMI : VRT fenêtré → discover_dalles()")


# ── Hook GDAL : autoriser le VRT (et ses .tif) à /vsicurl ─────────────────────
def gdal_env_options():
    """Options GDAL (scopées) injectées dans l'Env de lecture du cœur : autoriser
    l'extension .vrt (source mosaïque) et ses .tif référencés, et éviter un
    listing S3 coûteux à l'ouverture."""
    return {"CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff,.vrt"}


# ── Découverte ───────────────────────────────────────────────────────────────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """UNE entrée {nom_fenetre: COG_URL} si la bbox intersecte l'étendue CNMI.
    Pas de réseau ; la lecture fenêtrée réelle est faite par telecharger_cog_fenetre."""
    if bbox_natif is None:
        return {}
    cx0, cy0, cx1, cy1 = COVERAGE_EXTENT
    x1, y1, x2, y2 = bbox_natif
    ix1, iy1 = max(x1, cx0), max(y1, cy0)
    ix2, iy2 = min(x2, cx1), min(y2, cy1)
    if ix1 >= ix2 or iy1 >= iy2:
        print("  US-CNMI: bbox outside the CNMI DEM extent")
        return {}
    nom = _nom_fenetre(ix1, iy1, ix2, iy2)
    print("  US-CNMI (Topobathy 1 m): 1 VRT window in the bbox")
    return {nom: COG_URL}


# ── Hook post_download : CRS composé → EPSG:8693 pur ─────────────────────────
def post_download(chemin):
    """La fenêtre lue hérite du CRS COMPOSÉ du VRT (8693 + hauteur NMVD03,
    to_epsg()=None). On réétiquette en EPSG:8693 pur EN PLACE (retire la
    composante verticale ; pas de reprojection) → warp 3857 propre."""
    from pathlib import Path as _P
    p = _P(chemin)
    try:
        with open(p, "rb") as fh:
            if fh.read(2) not in (b"II", b"MM"):
                return
    except OSError:
        return
    import rasterio
    with rasterio.open(p, "r+") as src:
        if src.crs is None or src.crs.to_epsg() != 8693:
            src.crs = rasterio.CRS.from_epsg(8693)
