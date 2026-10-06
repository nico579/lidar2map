"""_dossiers.py : l'état dans le dossier standard de l'OS, les sorties dans
un dossier visible, et la reprise unique de l'état d'une version <= 1.53.

Isolation stricte : dans chaque test, le dossier standard et Documents sont
remplacés par des dossiers temporaires. Changer LOCALAPPDATA ne suffirait
pas : sous Windows, platformdirs interroge le shell, qui l'ignore.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
# Jamais les vrais dossiers d'état et de sorties de l'utilisateur (voir
# _dossiers.py) : run_tests.py en fournit un, sinon un dossier temporaire.
if not os.environ.get("LIDAR2MAP_HOME"):
    os.environ["LIDAR2MAP_HOME"] = tempfile.mkdtemp(prefix="lidar2map-tests-")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import _dossiers  # noqa: E402


class _Isole(unittest.TestCase):
    """Dossier standard, Documents et ancien dossier du programme dans un
    dossier temporaire au nom accentué ; LIDAR2MAP_HOME retiré."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.racine = Path(tmp.name).resolve() / "Données é"
        self.etat = self.racine / "AppData" / "Local" / "lidar2map-data"
        self.documents = self.racine / "Documents"
        self.ancien = self.racine / "Cartes" / "lidar2map-windows-x86_64"
        self.ancien.mkdir(parents=True)
        sans_home = {cle: valeur for cle, valeur in os.environ.items()
                     if cle != "LIDAR2MAP_HOME"}
        for correctif in (
                mock.patch.dict(os.environ, sans_home, clear=True),
                mock.patch.object(_dossiers.DOSSIERS, "dossier_etat_standard",
                                  return_value=self.etat),
                mock.patch.object(_dossiers.DOSSIERS, "documents",
                                  return_value=self.documents)):
            correctif.start()
            self.addCleanup(correctif.stop)

    def ecrire_ancien(self, nom, contenu):
        (self.ancien / nom).write_text(contenu, encoding="utf-8")

    def preferences(self):
        return json.loads((self.etat / "preferences.json").read_text(encoding="utf-8"))


class ConfigurationTests(unittest.TestCase):
    """Les paramètres propres à lidar2map. Les règles (calcul des dossiers,
    reprise unique, repli sans platformdirs) sont celles de
    nico579_commons.dossiers et y sont éprouvées."""

    def test_noms_et_fichiers_de_lidar2map(self):
        d = _dossiers.DOSSIERS
        self.assertEqual((d.application, d.nom_etat, d.nom_sorties, d.variable_home),
                         ("lidar2map", "lidar2map-data", "lidar2map", "LIDAR2MAP_HOME"))
        self.assertEqual((d.preferences, d.cle_sorties, d.marqueur),
                         ("preferences.json", "dossier_sorties",
                          ".lidar2map_etat_migre.json"))
        self.assertEqual(d.fichiers_etat,
                         ("preferences.json", "historique.json", "lidar2map.env"))
        self.assertEqual(d.dossiers_sorties, ("Projets", "cache", "production"))

    def test_la_copie_locale_de_la_logique_n_existe_plus(self):
        for nom in ("dossier_etat", "dossier_sorties", "preparer_etat", "_documents",
                    "_dossier_etat_standard", "_force", "_reprendre",
                    "_copier_si_absent", "_ecrire_json"):
            self.assertFalse(hasattr(_dossiers, nom), nom)


class LancementReelTests(unittest.TestCase):
    """Le vrai programme, lancé en __main__ : son journal va dans le dossier
    d'état, et rien n'est plus écrit à côté des sources."""

    def test_journal_dans_le_dossier_d_etat_pas_dans_les_sources(self):
        journaux_sources = ROOT / "logs"
        avant = set(journaux_sources.iterdir()) if journaux_sources.is_dir() else set()
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, LIDAR2MAP_HOME=tmp, LIDAR2MAP_BOOTSTRAP="none",
                       PYTHONUTF8="1")
            resultat = subprocess.run(
                [sys.executable, str(ROOT / "lidar2map.py"), "--version"],
                cwd=tmp, env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=180)
            self.assertEqual(resultat.returncode, 0, resultat.stdout + resultat.stderr)
            self.assertTrue(list((Path(tmp) / "logs").glob("lidar_*.log")),
                            resultat.stdout + resultat.stderr)
            self.assertFalse((Path(tmp) / _dossiers.DOSSIERS.marqueur).exists())
        apres = set(journaux_sources.iterdir()) if journaux_sources.is_dir() else set()
        self.assertEqual(apres - avant, set())


if __name__ == "__main__":
    unittest.main()
