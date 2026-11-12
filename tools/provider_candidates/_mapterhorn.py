"""Adaptateur expérimental Mapterhorn, exclu des providers actifs.

Les tests fonctionnels ne qualifient pas la conservation du microrelief.

On ne propose pas le fond mondial GLO-30 comme LiDAR fin. Le catalogue de
couverture Mapterhorn filtre les seules régions de la source choisie et
masque le reste en NoData. Ce masque vectoriel est généralisé : près des
raccords, les altitudes restent le produit transformé de Mapterhorn.
"""

import math
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from providers.common import part_path

HALF_WORLD = 20037508.342789244
TILE_PX = 512
COVERAGE_ZOOM = 14
CACHE_MAX_AGE_S = 30 * 86400
TILES_URL = "https://tiles.mapterhorn.com/{z}/{x}/{y}.webp"
COVERAGE_URL = "https://single-archive-tiles.mapterhorn.com/coverage/{z}/{x}/{y}.mvt"


def tile_bounds(z, x, y):
    step = 2 * HALF_WORLD / (2 ** z)
    left, top = -HALF_WORLD + x * step, HALF_WORLD - y * step
    return left, top - step, left + step, top


class MapterhornProvider:
    def __init__(self, *, prefix, source, zoom, extent, crs="EPSG:3857", resolution=None):
        self.prefix = prefix
        self.source = source
        self.zoom = zoom
        self.extent = extent  # WGS84, enveloppe seulement ; le MVT fait le masque.
        self.grid_resolution = 2 * HALF_WORLD / (2 ** zoom * TILE_PX)
        self.crs = crs
        self.resolution = self.grid_resolution if resolution is None else resolution
        self._cache_dir = None
        self._layers = {}
        self._lock = threading.Lock()

    def dalle_filename(self, z, x, y):
        return f"{self.prefix}_z{z}_{x}_{y}.tif"

    def subdir_from_name(self, nom):
        m = re.match(re.escape(self.prefix) + r"_z\d+_(\d+)_", nom)
        return str(int(m.group(1)) // 64) if m else None

    def _coverage_layer(self, x, y):
        import mapbox_vector_tile

        key = (x, y)
        with self._lock:
            if key in self._layers:
                return self._layers[key]
            path = (self._cache_dir / f"z14_{x}_{y}.mvt") if self._cache_dir else None
            payload = None
            layer = None
            fetched = False
            if path and path.exists() and time.time() - path.stat().st_mtime < CACHE_MAX_AGE_S:
                try:
                    payload = path.read_bytes()
                    layer = mapbox_vector_tile.decode(
                        payload, default_options={"y_coord_down": True}).get("coverage")
                except Exception:
                    payload = None  # Cache incomplet/corrompu : récupérer à nouveau.
            if payload is None:
                fetched = True
                url = COVERAGE_URL.format(z=COVERAGE_ZOOM, x=x, y=y)
                req = urllib.request.Request(url, headers={"User-Agent": "lidar2map/1.0"})
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        payload = resp.read(8 * 1024 * 1024 + 1)
                except urllib.error.HTTPError as exc:
                    if exc.code != 404:
                        raise
                    return {"extent": 4096, "features": []}
                if len(payload) > 8 * 1024 * 1024:
                    raise ValueError("Mapterhorn : couverture MVT trop grande")
            if layer is None:
                layer = mapbox_vector_tile.decode(
                    payload, default_options={"y_coord_down": True}).get("coverage")
            if not layer or layer.get("extent", 0) <= 0:
                raise ValueError("Mapterhorn : couche de couverture absente/invalide")
            if path and fetched:
                path.parent.mkdir(parents=True, exist_ok=True)
                staging = part_path(path)
                try:
                    staging.write_bytes(payload)
                    staging.replace(path)
                except OSError as exc:
                    print(f"  WARNING Mapterhorn coverage cache: {exc}")
                finally:
                    staging.unlink(missing_ok=True)
            self._layers[key] = layer
            return layer

    def _source_geometries(self, z, x, y):
        factor = 2 ** (z - COVERAGE_ZOOM)
        layer = self._coverage_layer(x // factor, y // factor)
        geometries = [f["geometry"] for f in layer["features"]
                      if f.get("properties", {}).get("source") == self.source
                      and f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
        return geometries, layer["extent"], factor

    def _mask(self, z, x, y):
        import numpy as np
        from affine import Affine
        from rasterio.features import geometry_mask

        geometries, extent, factor = self._source_geometries(z, x, y)
        if not geometries:
            return np.zeros((TILE_PX, TILE_PX), dtype=bool)
        span = extent / factor
        # Géométrie MVT en coordonnées écran (Y vers le bas). Cette affine
        # exprime les pixels du WebP dans le repère de sa tuile de couverture.
        transform = Affine(span / TILE_PX, 0, (x % factor) * span,
                           0, span / TILE_PX, (y % factor) * span)
        return geometry_mask(geometries, out_shape=(TILE_PX, TILE_PX),
                             transform=transform, invert=True)

    def discover_dalles(self, bbox_wgs84, bbox_natif, cache_path, workers=1):
        if bbox_natif is None or bbox_wgs84 is None:
            return {}
        west, south, east, north = self.extent
        bw, bs, be, bn = bbox_wgs84
        if be <= west or bw >= east or bn <= south or bs >= north:
            return {}
        x1, y1, x2, y2 = bbox_natif
        if not all(math.isfinite(v) for v in bbox_natif) or x1 >= x2 or y1 >= y2:
            return {}
        if self.crs != "EPSG:3857":
            from rasterio.warp import transform_bounds
            x1, y1, x2, y2 = transform_bounds(
                self.crs, "EPSG:3857", x1, y1, x2, y2, densify_pts=21)
        # Une bbox de continent doit seulement parcourir l'enveloppe de la
        # région choisie, jamais la pyramide XYZ du monde entier.
        r = HALF_WORLD / math.pi
        ex1, ex2 = r * math.radians(west), r * math.radians(east)
        ey1 = r * math.asinh(math.tan(math.radians(south)))
        ey2 = r * math.asinh(math.tan(math.radians(north)))
        x1, y1, x2, y2 = max(x1, ex1), max(y1, ey1), min(x2, ex2), min(y2, ey2)
        if x1 >= x2 or y1 >= y2:
            return {}
        self._cache_dir = Path(cache_path).parent / "mapterhorn-coverage-v1"
        step = 2 * HALF_WORLD / 2 ** self.zoom
        n = 2 ** self.zoom
        tx0 = max(0, math.floor((x1 + HALF_WORLD) / step))
        tx1 = min(n, math.ceil((x2 + HALF_WORLD) / step))
        ty0 = max(0, math.floor((HALF_WORLD - y2) / step))
        ty1 = min(n, math.ceil((HALF_WORLD - y1) / step))
        dalles = {}
        try:
            for x in range(tx0, tx1):
                for y in range(ty0, ty1):
                    if self._mask(self.zoom, x, y).any():
                        dalles[self.dalle_filename(self.zoom, x, y)] = TILES_URL.format(
                            z=self.zoom, x=x, y=y)
        except Exception as exc:
            print(f"  ERROR Mapterhorn coverage: {type(exc).__name__}: {exc}")
            return None
        print(f"  Mapterhorn {self.source}: {len(dalles)} z{self.zoom} tile(s), "
              f"working grid {self.resolution:g} m in {self.crs} (source mask)")
        return dalles

    def post_fetch(self, chemin):
        import numpy as np
        import rasterio
        from PIL import Image
        from rasterio.transform import from_bounds, from_origin
        from rasterio.warp import reproject, transform_bounds, Resampling

        chemin = Path(chemin)
        with chemin.open("rb") as src:
            magic = src.read(4)
        if magic in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
            return
        m = re.match(re.escape(self.prefix) + r"_z(\d+)_(\d+)_(\d+)\.tif(?:\.|$)", chemin.name)
        if not m:
            raise ValueError("Mapterhorn : nom de tuile invalide")
        z, x, y = (int(v) for v in m.groups())
        if z != self.zoom or not (0 <= x < 2 ** z and 0 <= y < 2 ** z):
            raise ValueError("Mapterhorn : zoom/coordonnées de tuile inattendus")
        with Image.open(chemin) as im:
            if im.format != "WEBP" or im.size != (TILE_PX, TILE_PX) or im.mode != "RGB":
                raise ValueError("Mapterhorn : WebP RGB 512×512 attendu")
            rgb = np.asarray(im, dtype=np.float32)
        dem = rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768
        dem[~self._mask(z, x, y)] = -9999.0
        bounds = tile_bounds(z, x, y)
        transform = from_bounds(*bounds, TILE_PX, TILE_PX)
        if self.crs != "EPSG:3857":
            # Calculer LRM/SVF dans le CRS métrique local : les mètres de
            # Mercator sont dilatés par 1/cos(latitude) et faussent les rayons
            # et les pentes si on les assimile à des distances au sol.
            left, bottom, right, top = transform_bounds(
                "EPSG:3857", self.crs, *bounds, densify_pts=21)
            res = self.resolution
            x0, x1 = math.floor(left / res), math.ceil(right / res)
            y0, y1 = math.floor(bottom / res), math.ceil(top / res)
            target_transform = from_origin(x0 * res, y1 * res, res, res)
            target = np.full((y1 - y0, x1 - x0), -9999.0, dtype=np.float32)
            reproject(dem, target, src_transform=transform, src_crs="EPSG:3857",
                      dst_transform=target_transform, dst_crs=self.crs,
                      src_nodata=-9999.0, dst_nodata=-9999.0,
                      resampling=Resampling.bilinear)
            dem, transform = target, target_transform
        staging = part_path(chemin)
        try:
            with rasterio.open(staging, "w", driver="GTiff", width=dem.shape[1],
                               height=dem.shape[0], count=1, dtype="float32",
                               crs=self.crs, nodata=-9999.0, transform=transform,
                               tiled=True, compress="deflate", predictor=3) as dst:
                dst.write(dem, 1)
                dst.update_tags(source=self.source, distributor="Mapterhorn",
                                encoding="Terrarium", zoom=str(z),
                                source_grid_crs="EPSG:3857",
                                source_grid_resolution=str(self.grid_resolution),
                                attribution_url="https://mapterhorn.com/attribution/",
                                coverage_mask="Mapterhorn MVT z14 (generalized)")
            staging.replace(chemin)
        finally:
            staging.unlink(missing_ok=True)
