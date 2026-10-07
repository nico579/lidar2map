"""Le moteur d'amorçage de lidar2map est celui des quatre applications.

``_amorcage.py`` est une copie octet pour octet de ``nico579_commons.amorcage`` :
il tourne avant l'installation de la bibliothèque commune, qu'il ne peut donc
pas importer. Ces tests vérifient que la copie n'a pas dérivé du paquet
installé et que lidar2map l'appelle comme il faut. Le moteur lui-même (modes,
venv, pip, relance) est testé dans nico579-commons (tests/test_amorcage.py).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import _amorcage  # noqa: E402


def _lignes(chemin):
    """Le texte sans égard aux fins de ligne : un dépôt récupéré sous Windows
    peut les convertir, sans que la copie ait dérivé."""
    return Path(chemin).read_bytes().decode("utf-8").splitlines()


class CopieDuCommun(unittest.TestCase):
    def test_la_copie_est_identique_au_module_du_paquet(self):
        from nico579_commons import amorcage
        self.assertEqual(
            _lignes(ROOT / "_amorcage.py"), _lignes(amorcage.__file__),
            "_amorcage.py a dérivé de nico579_commons.amorcage : recopier le "
            "fichier du paquet (et monter l'épingle de nico579-commons).")


class Branchement(unittest.TestCase):
    def test_lidar2map_declare_son_amorcage(self):
        source = (ROOT / "lidar2map.py").read_text(encoding="utf-8")
        self.assertIn('_amorcage.Amorcage("lidar2map"', source)
        self.assertIn("apres_installation=_restaurer_tls_strict", source)
        self.assertNotIn("reutiliser_environnement", source)

    def test_le_verrou_et_ses_dependances_sont_lus_au_bon_endroit(self):
        moteur = _amorcage.Amorcage("lidar2map", ROOT)
        self.assertEqual(moteur.fichier_verrou, ROOT / "requirements.txt")
        self.assertEqual(moteur.fichier_dependances, ROOT / "requirements.in")
        self.assertEqual(moteur.variable, "LIDAR2MAP_BOOTSTRAP")
        self.assertEqual(moteur.marque, "lidar2map-verrou.sha256")
        self.assertIn("rasterio", _amorcage.dependances_directes(moteur.fichier_dependances))

    def _lancer(self, *arguments):
        return subprocess.run([sys.executable, str(ROOT / "lidar2map.py"), *arguments],
                              capture_output=True, text=True, encoding="utf-8", timeout=120,
                              cwd=tempfile.gettempdir())

    def test_aide_du_mode_sans_rien_installer(self):
        resultat = self._lancer("--help-bootstrap")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        for attendu in ("--bootstrap=auto", "--bootstrap=force", "LIDAR2MAP_BOOTSTRAP",
                        "~/.lidar2map/venv"):
            self.assertIn(attendu, resultat.stdout)

    def test_un_mode_invalide_sort_en_2(self):
        resultat = self._lancer("--bootstrap=oups")
        self.assertEqual(resultat.returncode, 2)
        self.assertIn("--bootstrap", resultat.stderr)


if __name__ == "__main__":
    unittest.main()
