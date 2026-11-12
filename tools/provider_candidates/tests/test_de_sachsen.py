"""Configuration batch GeoSN, bornes demi-ouvertes et extraction ZIP sûre."""

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402
from tools.provider_candidates import de_sachsen as P  # noqa: E402


def page():
    produits = {"DGM1_TIFF_2km": {
        "packagesize": 2000, "share_id": "PublicShare",
        "filename": "dgm1_33$Rechtswert$_$Hochwert$_2_sn_tiff.zip",
        "computed_not_existing": [4125656, 1],
    }}
    mapping = {"commune": {"grid_id": [4115656, 2, 4125656, 1]}}
    return "batchConfig.products=" + json.dumps(produits) + "\nbatchConfig.mapping=" + json.dumps(mapping)


class GeoSNTests(unittest.TestCase):
    def test_index_2km_depuis_grille_compressee_1km(self):
        index = P._index_depuis_page(page())
        self.assertEqual(list(index), ["410_5656"])
        self.assertTrue(index["410_5656"].endswith(
            "/PublicShare/dgm1_33410_5656_2_sn_tiff.zip"))

    def test_configuration_absente_refusee(self):
        with self.assertRaisesRegex(ValueError, "configuration"):
            P._index_depuis_page("<html>error</html>")

    def test_borne_alignee_decouvre_une_seule_dalle(self):
        index = {"410_5656": "url", "412_5656": "autre"}
        with mock.patch.object(P, "_charger_index", return_value=index):
            self.assertEqual(P.discover_dalles(
                None, (410000, 5656000, 412000, 5658000), "unused.json"),
                {"sn_dgm1_410_5656.tif": "url"})

    def test_reseau_indisponible_ne_devient_pas_hors_couverture(self):
        with mock.patch.object(P, "_charger_index", return_value=None):
            self.assertIsNone(P.discover_dalles(
                None, (410000, 5656000, 412000, 5658000), "unused.json"))

    def test_zip_natif_converti_et_georeference_valide(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.tif"
            with rasterio.open(source, "w", driver="GTiff", width=2000,
                               height=2000, count=1, dtype="float32",
                               crs="EPSG:25833", nodata=-9999,
                               transform=from_origin(410000, 5658000, 1, 1),
                               compress="deflate") as dst:
                dst.write(np.full((2000, 2000), 120.25, dtype=np.float32), 1)
            target = root / "sn_dgm1_410_5656.tif.123.abcdef.part"
            with zipfile.ZipFile(target, "w") as zf:
                # Le membre est recopié vers le staging local choisi, jamais
                # extrait vers ce chemin distant (pas de zip-slip).
                zf.write(source, "../escaped.tif")
            P.post_fetch(target)
            with rasterio.open(target) as ds:
                self.assertEqual(ds.crs.to_epsg(), 25833)
                self.assertEqual(float(ds.read(1)[0, 0]), 120.25)
            self.assertFalse((root.parent / "escaped.tif").exists())

    def test_mauvaise_emprise_refusee_et_zip_initial_preserve(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.tif"
            with rasterio.open(source, "w", driver="GTiff", width=2,
                               height=2, count=1, dtype="float32", crs="EPSG:25833",
                               transform=from_origin(0, 2, 1, 1)) as dst:
                dst.write(np.ones((2, 2), dtype=np.float32), 1)
            target = root / "sn_dgm1_410_5656.tif"
            with zipfile.ZipFile(target, "w") as zf:
                zf.write(source, "wrong.tif")
            original = target.read_bytes()
            with self.assertRaisesRegex(ValueError, "emprise"):
                P.post_fetch(target)
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(list(root.glob("*.part")), [])


if __name__ == "__main__":
    unittest.main()
