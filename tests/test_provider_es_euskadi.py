"""providers/es_euskadi.py : le service WCS d'Euskadi n'accepte plus l'index de couverture
(« COVERAGE=2 » : parameter COVERAGE is invalid, constaté le 2026-10-07), il veut le nom de la
couverture. Le test de fumée réseau (tests/smoke_providers.py) joue le vrai service ; ici, ce qui
se vérifie sans réseau : la requête porte le nom et non l'index."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
# Jamais les vrais dossiers d'état et de sorties de l'utilisateur (voir
# _dossiers.py) : run_tests.py en fournit un, sinon un dossier temporaire.
if not os.environ.get("LIDAR2MAP_HOME"):
    os.environ["LIDAR2MAP_HOME"] = tempfile.mkdtemp(prefix="lidar2map-tests-")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from providers import es_euskadi  # noqa: E402


class Couverture(unittest.TestCase):
    def test_la_couverture_est_un_nom_pas_un_index(self):
        self.assertFalse(es_euskadi.COVERAGE.isdigit(), es_euskadi.COVERAGE)
        self.assertEqual(es_euskadi.COVERAGE, "MDT_LIDAR_1M_EGUNERATUENA_MAS_ACTUALIZADA")

    def test_la_requete_de_dalle_porte_ce_nom(self):
        requete = parse_qs(urlparse(es_euskadi.dalle_url(505, 4789)).query)
        self.assertEqual(requete["COVERAGE"], [es_euskadi.COVERAGE])
        self.assertEqual(requete["REQUEST"], ["GetCoverage"])
        self.assertEqual(requete["CRS"], ["EPSG:25830"])
        self.assertEqual(requete["BBOX"], ["505000,4789000,506000,4790000"])


if __name__ == "__main__":
    unittest.main()
