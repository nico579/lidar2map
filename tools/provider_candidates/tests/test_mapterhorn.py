"""Altitudes Terrarium signées, masque de source et publication atomique."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image  # noqa: E402
from tools.provider_candidates._mapterhorn import MapterhornProvider, tile_bounds  # noqa: E402


class TerrariumTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.provider = MapterhornProvider(prefix="test_v1", source="lidar",
                                          zoom=14, extent=(-180, -85, 180, 85))
        self.x, self.y = 8000, 6000
        self.path = self.root / self.provider.dalle_filename(14, self.x, self.y)
        self.provider._layers[(self.x, self.y)] = {
            "extent": 4096,
            "features": [{"properties": {"source": "lidar"}, "geometry": {
                "type": "Polygon", "coordinates": [
                    [[0, 0], [4096, 0], [4096, 2048], [0, 2048], [0, 0]]]}},
                {"properties": {"source": "glo30"}, "geometry": {
                    "type": "Polygon", "coordinates": [
                        [[0, 0], [4096, 0], [4096, 4096], [0, 4096], [0, 0]]]}}],
        }

    def _webp(self, path=None):
        elevation = np.full((512, 512), 123.25, dtype=np.float64)
        elevation[:128] = -12.5
        elevation[128:256] = 0
        offset = elevation + 32768
        rgb = np.stack((offset // 256, offset % 256,
                        (offset - np.floor(offset)) * 256), axis=-1).astype(np.uint8)
        Image.fromarray(rgb).save(path or self.path, format="WEBP", lossless=True)

    def test_altitudes_negatives_zero_et_masque_y_vers_le_bas(self):
        self._webp()
        self.provider.post_fetch(self.path)
        with rasterio.open(self.path) as ds:
            dem = ds.read(1)
            self.assertEqual(ds.crs.to_epsg(), 3857)
            self.assertEqual(ds.count, 1)
            self.assertEqual(ds.dtypes, ("float32",))
            self.assertEqual(tuple(ds.bounds), tile_bounds(14, self.x, self.y))
            self.assertAlmostEqual(ds.res[0], self.provider.resolution)
            self.assertTrue(np.all(dem[:128] == -12.5))
            self.assertTrue(np.all(dem[128:256] == 0))
            self.assertTrue(np.all(dem[256:] == ds.nodata))
            self.assertEqual(ds.tags()["source"], "lidar")

    def test_nom_de_staging_du_telechargeur_est_accepte(self):
        staging = self.path.with_name(self.path.name + ".123.abcdef.part")
        self._webp(staging)
        self.provider.post_fetch(staging)
        with rasterio.open(staging) as ds:
            self.assertEqual(ds.crs.to_epsg(), 3857)
        self.assertEqual(list(self.root.glob("*.part")), [staging])

    def test_reprojection_sur_grille_metrique_alignee(self):
        self.provider.crs = "EPSG:2154"
        self.provider.resolution = 5.0
        self._webp()
        self.provider.post_fetch(self.path)
        with rasterio.open(self.path) as ds:
            self.assertEqual(ds.crs.to_epsg(), 2154)
            self.assertEqual(ds.res, (5.0, 5.0))
            self.assertAlmostEqual(ds.bounds.left % 5, 0)
            self.assertAlmostEqual(ds.bounds.top % 5, 0)
            dem = ds.read(1, masked=True)
            self.assertGreater(dem.count(), 0)
            self.assertAlmostEqual(float(dem.min()), -12.5)
            self.assertAlmostEqual(float(dem.max()), 0)

    def test_image_rendue_png_refusee_sans_modifier_la_source(self):
        Image.new("RGB", (512, 512)).save(self.path, format="PNG")
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "WebP RGB"):
            self.provider.post_fetch(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_echec_ecriture_garde_le_webp_et_nettoie_le_staging(self):
        self._webp()
        original = self.path.read_bytes()
        with mock.patch("rasterio.open", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.provider.post_fetch(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.root.glob("*.part")), [])

    def test_source_satellite_seule_ne_decouvre_aucune_dalle(self):
        self.provider._layers[(self.x, self.y)]["features"] = [
            self.provider._layers[(self.x, self.y)]["features"][1]]
        bounds = tile_bounds(14, self.x, self.y)
        self.assertEqual(self.provider.discover_dalles(
            (-1, 40, 1, 41), bounds, self.root / "cache.json"), {})

    def test_borne_haute_alignee_ne_prend_pas_la_tuile_voisine(self):
        dalles = self.provider.discover_dalles(
            (-1, 40, 1, 41), tile_bounds(14, self.x, self.y), self.root / "cache.json")
        self.assertEqual(list(dalles), [self.path.name])

    def test_erreur_couverture_reste_une_erreur_de_decouverte(self):
        self.provider._layers.clear()
        with mock.patch("urllib.request.urlopen", side_effect=OSError("network")):
            self.assertIsNone(self.provider.discover_dalles(
                (-1, 40, 1, 41), tile_bounds(14, self.x, self.y), self.root / "cache.json"))

    def test_bbox_hors_region_ne_contacte_pas_le_service(self):
        regional = MapterhornProvider(prefix="be_test", source="bewallonie",
                                     zoom=17, extent=(2.8, 49.45, 6.5, 50.9))
        with mock.patch("urllib.request.urlopen") as urlopen:
            self.assertEqual(regional.discover_dalles(
                (20, 0, 21, 1), (0, 0, 100, 100), self.root / "cache.json"), {})
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
