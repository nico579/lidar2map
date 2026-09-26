"""providers/de_sh.py : conversion d'une dalle XYZ de Schleswig-Holstein en
GeoTIFF, telle que le serveur la livre depuis septembre 2026, c'est-à-dire
suivie d'une page HTML (un bouton de retour vers le portail)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
# Jamais les vrais dossiers d'état et de sorties de l'utilisateur (voir
# _dossiers.py) : run_tests.py en fournit un, sinon un dossier temporaire.
if not os.environ.get("LIDAR2MAP_HOME"):
    os.environ["LIDAR2MAP_HOME"] = tempfile.mkdtemp(prefix="lidar2map-tests-")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import rasterio  # noqa: E402

from providers import de_sh  # noqa: E402

# Grille 3 × 2 au pas de 1 m, centres de cellules en .50 comme les vraies
# dalles, puis l'enveloppe HTML que le serveur ajoute désormais.
XYZ = (
    "573000.50 6019999.50 17.40\n"
    "573001.50 6019999.50 17.36\n"
    "573002.50 6019999.50 17.28\n"
    "573000.50 6019998.50 17.34\n"
    "573001.50 6019998.50 17.42\n"
    "573002.50 6019998.50 17.45\n"
)
PAGE = (
    "\n<!DOCTYPE html>\n<html lang=\"de\">\n<head>\n"
    "    <meta charset=\"UTF-8\">\n    <title>OpenGBD_Geobasisdaten</title>\n"
    "</head>\n<body>\n<!-- Button als Link -->\n<br>\n"
    "<a href=\"https://geodaten.schleswig-holstein.de/gaialight-sh/_apps/dladownload/dl-dgm1.html\""
    " class=\"btn-link\">Zurück zum OpenGBD-Downloadportal</a>\n</html>\n"
)


class ConversionXyzTests(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.dalle = Path(dossier.name) / "sh_dgm1_573_6019.tif"

    def test_page_html_apres_les_points_est_ignoree(self):
        self.dalle.write_text(XYZ + PAGE, encoding="utf-8")
        de_sh.post_fetch(self.dalle)
        with rasterio.open(self.dalle) as tif:
            self.assertEqual((tif.height, tif.width), (2, 3))
            self.assertEqual(tif.crs.to_epsg(), 25832)
            valeurs = tif.read(1)
        self.assertAlmostEqual(float(valeurs[0, 0]), 17.40, places=3)
        self.assertAlmostEqual(float(valeurs[1, 2]), 17.45, places=3)

    def test_dalle_sans_page_html_reste_convertie(self):
        self.dalle.write_text(XYZ, encoding="utf-8")
        de_sh.post_fetch(self.dalle)
        with rasterio.open(self.dalle) as tif:
            self.assertEqual((tif.height, tif.width), (2, 3))

    def test_page_d_erreur_sans_points_refusee(self):
        self.dalle.write_text(PAGE, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "malformé"):
            de_sh.post_fetch(self.dalle)


if __name__ == "__main__":
    unittest.main()
