"""Candidat hors catalogue : DMR 5.0 natif ÚGKK par WCS officiel.

Grille officielle ETRS89 / UTM 34N (EPSG:3046), 1 m, altitudes ellipsoïdales
ETRS89. Extraction WCS dans le CRS natif, sans paramètre de mise à l'échelle,
de reprojection ou d'interpolation. Le DMR reste un MNT interpolé à partir
des points sol du LiDAR ; il ne remplace pas un nuage LAZ pour reclassification.

Remplace notre ancien prototype Mapterhorn, toujours hors catalogue actif.
L'intégration au catalogue actif nécessite la validation de l'utilisateur.
"""
from __future__ import annotations

import math
import re
from urllib.parse import urlencode

NAME = "Slovaquie — DMR 5.0 ÚGKK natif 1 m (WCS officiel)"
CODE = "sk-ugkk"
COUNTRY = "sk"
LICENSE = "CC BY 4.0 — attribution : ÚGKK SR"
DOC_URL = "https://www.gku.sk/geoportal/zbgis/lls/1-cyklus/"
SERVICE_DOC_URL = "https://www.gku.sk/geoportal/inspire/ukladacie-sluzby/"
CRS_NATIF = "EPSG:3046"
RESOLUTION_M = SOURCE_RESOLUTION_M = 1.0
VERTICAL_REFERENCE = "ETRS89 ellipsoidal heights (h), metres — not Bpv"
DALLE_KM = 1
PX_PAR_DALLE = 1000
SEUIL_DALLE_VALIDE = 1024
DOWNLOAD_WORKERS_MAX = 2
WCS_URL = "https://inspirews.skgeodesy.sk/geoserver/el/ows"
COVERAGE = "el__EL.GridCoverage"
WCS_AXIS_LABELS = ("E", "N")
COVERAGE_EXTENT = (191148.0, 5289631.0, 614666.0, 5497220.0)
_NAME = re.compile(r"sk_ugkk_dmr5_native_(\d+)_(\d+)\.tif(?:\.|$)")


def dalle_filename(x_km, y_km):
    return f"sk_ugkk_dmr5_native_{int(x_km)}_{int(y_km)}.tif"


def subdir_from_name(nom):
    match = _NAME.search(str(nom))
    return match.group(1) if match else None


def dalle_url(x_km, y_km):
    left, bottom = int(x_km)*1000, int(y_km)*1000
    # Bornes de cellules, pas centres : le serveur testé restitue exactement
    # 1000 × 1000 pixels. Les demi-pixels produisent une fenêtre décalée.
    query = [("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"),
             ("coverageId", COVERAGE), ("format", "image/tiff"),
             ("subset", f"E({left},{left + 1000})"),
             ("subset", f"N({bottom},{bottom + 1000})")]
    return WCS_URL + "?" + urlencode(query)


def dalles_pour_bbox(x1, y1, x2, y2):
    values = (x1, y1, x2, y2)
    if not all(math.isfinite(v) for v in values) or x1 >= x2 or y1 >= y2:
        raise ValueError("BBox native invalide")
    west, south, east, north = COVERAGE_EXTENT
    x1, y1, x2, y2 = max(x1, west), max(y1, south), min(x2, east), min(y2, north)
    if x1 >= x2 or y1 >= y2:
        return []
    return [(x, y) for x in range(math.floor(x1/1000), math.ceil(x2/1000))
            for y in range(math.floor(y1/1000), math.ceil(y2/1000))]


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    if bbox_natif is None:
        return {}
    return {dalle_filename(x, y): dalle_url(x, y) for x, y in dalles_pour_bbox(*bbox_natif)}


def post_fetch(chemin):
    """Refuse les images de visualisation et les grilles rééchantillonnées."""
    import numpy as np
    import rasterio
    from pathlib import Path

    match = _NAME.search(Path(chemin).name)
    if not match:
        raise ValueError("Nom de dalle native ÚGKK invalide")
    x, y = map(int, match.groups())
    with rasterio.open(chemin) as src:
        if src.count != 1 or src.dtypes != ("float32",):
            raise ValueError("MNT Float32 monobande attendu, image de fond refusée")
        if not src.crs or src.crs.to_epsg() != 3046:
            raise ValueError("CRS natif EPSG:3046 attendu")
        if src.res != (1.0, 1.0) or src.transform.b or src.transform.d:
            raise ValueError("Grille native régulière de 1 m attendue")
        west, south, east, north = COVERAGE_EXTENT
        expected = (max(x*1000.0, west), max(y*1000.0, south),
                    min((x+1)*1000.0, east), min((y+1)*1000.0, north))
        expected_shape = (int(expected[3]-expected[1]), int(expected[2]-expected[0]))
        if tuple(src.bounds) != expected or src.shape != expected_shape:
            raise ValueError("Extraction WCS décalée ou incomplète")
        if src.nodata is None or not np.isfinite(src.nodata):
            raise ValueError("NoData natif déclaré attendu")
        data = src.read(1, masked=True)
        if data.count() and (not np.isfinite(data.compressed()).all()
                             or data.min() < -200 or data.max() > 3000):
            raise ValueError("Altitudes natives incohérentes")
