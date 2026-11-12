"""Régressions du candidat natif, sans réseau ni catalogue actif."""
import hashlib
import math
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.provider_candidates import sk_ugkk as p


class NativeSlovakiaTests(unittest.TestCase):
    def test_native_host_and_unscaled_subsets(self):
        url = urlsplit(p.dalle_url(208, 5345))
        self.assertEqual(url.hostname, "inspirews.skgeodesy.sk")
        query = parse_qs(url.query)
        self.assertEqual(query["subset"], ["E(208000,209000)", "N(5345000,5346000)"])
        self.assertEqual(query["coverageId"], ["el__EL.GridCoverage"])
        self.assertFalse(set(query) & {"scaleSize", "scaleFactor", "outputCrs", "subsettingCrs", "width", "height", "interpolation"})

    def test_half_open_tile_grid(self):
        self.assertEqual(p.dalles_pour_bbox(208000, 5345000, 209000, 5346000), [(208, 5345)])
        self.assertEqual(p.dalles_pour_bbox(208999, 5345999, 209001, 5346001),
                         [(208, 5345), (208, 5346), (209, 5345), (209, 5346)])

    def test_outside_country_envelope(self):
        self.assertEqual(p.discover_dalles(None, (0, 0, 1000, 1000), None), {})
        self.assertEqual(p.discover_dalles(None, None, None), {})

    def test_invalid_bbox(self):
        for bbox in ((math.nan, 0, 1, 1), (0, 0, math.inf, 1), (1, 1, 1, 2), (2, 1, 1, 2)):
            with self.subTest(bbox=bbox), self.assertRaises(ValueError):
                p.dalles_pour_bbox(*bbox)

    def write_fixture(self, directory, *, x=208, y=5345, resolution=1, dtype="float32", count=1,
                      crs="EPSG:3046", nodata=3.4e38, shift=0, value=350, clipped=False):
        path = Path(directory) / p.dalle_filename(x, y)
        west, south, east, north = p.COVERAGE_EXTENT
        left, bottom, right, top = (max(x*1000, west), max(y*1000, south),
                                   min((x+1)*1000, east), min((y+1)*1000, north)) if clipped else (x*1000, y*1000, (x+1)*1000, (y+1)*1000)
        width, height = int((right-left)/resolution), int((top-bottom)/resolution)
        data = np.full((count, height, width), value, dtype=dtype)
        with rasterio.open(path, "w", driver="GTiff", width=width, height=height,
                           count=count, dtype=dtype, crs=crs, nodata=nodata,
                           transform=from_origin(left+shift, top, resolution, resolution)) as dst:
            dst.write(data)
        return path

    def test_valid_raster_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_fixture(tmp)
            before = hashlib.sha256(path.read_bytes()).digest()
            p.post_fetch(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)

    def test_native_envelope_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            p.post_fetch(self.write_fixture(tmp, x=191, y=5289, clipped=True))

    def test_rendered_image_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "Float32"):
                p.post_fetch(self.write_fixture(tmp, dtype="uint8", count=3, nodata=0, value=150))

    def test_wrong_resolution_or_crs_rejected(self):
        for kwargs in ({"resolution": 2}, {"crs": "EPSG:3857"}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    p.post_fetch(self.write_fixture(tmp, **kwargs))

    def test_shifted_or_nodata_missing_rejected(self):
        for kwargs in ({"shift": .5}, {"nodata": None}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    p.post_fetch(self.write_fixture(tmp, **kwargs))

    def test_bad_altitudes_rejected(self):
        for value in (math.nan, 4000, -1000):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ValueError, "Altitudes"):
                    p.post_fetch(self.write_fixture(tmp, value=value))

    def test_nodata_remains_masked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_fixture(tmp, value=3.4e38)
            p.post_fetch(path)
            with rasterio.open(path) as src:
                self.assertEqual(src.read(1, masked=True).count(), 0)


if __name__ == "__main__":
    unittest.main()
