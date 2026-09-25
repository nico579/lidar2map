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
import threading
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
                mock.patch.object(_dossiers, "_dossier_etat_standard",
                                  return_value=self.etat),
                mock.patch.object(_dossiers, "_documents",
                                  return_value=self.documents)):
            correctif.start()
            self.addCleanup(correctif.stop)

    def ecrire_ancien(self, nom, contenu):
        (self.ancien / nom).write_text(contenu, encoding="utf-8")

    def preferences(self):
        return json.loads((self.etat / "preferences.json").read_text(encoding="utf-8"))


class DossiersTests(_Isole):
    def test_etat_dans_le_dossier_standard(self):
        self.assertEqual(_dossiers.dossier_etat(), self.etat)

    def test_sorties_dans_documents_par_defaut(self):
        self.assertEqual(_dossiers.dossier_sorties(), self.documents / "lidar2map")

    def test_simple_calcul_rien_n_est_cree(self):
        _dossiers.dossier_etat()
        _dossiers.dossier_sorties()
        self.assertFalse(self.etat.exists())
        self.assertFalse(self.documents.exists())

    def test_lidar2map_home_regroupe_etat_et_sorties(self):
        portable = self.racine / "portable"
        with mock.patch.dict(os.environ, {"LIDAR2MAP_HOME": str(portable)}):
            self.assertEqual(_dossiers.dossier_etat(), portable)
            self.assertEqual(_dossiers.dossier_sorties(), portable)

    def test_reglage_dossier_sorties_prioritaire(self):
        self.etat.mkdir(parents=True)
        cartes = self.racine / "D" / "Cartes"
        (self.etat / "preferences.json").write_text(
            json.dumps({"lang": "fr", "dossier_sorties": str(cartes)}), encoding="utf-8")
        self.assertEqual(_dossiers.dossier_sorties(), cartes)


class RepliSansPlatformdirsTests(unittest.TestCase):
    def test_repli_identique_a_platformdirs(self):
        # Calcul pur : rien n'est écrit, le vrai dossier peut être comparé.
        try:
            import platformdirs  # noqa: F401
        except ImportError:
            self.skipTest("platformdirs absent : rien à comparer")
        reel = _dossiers._dossier_etat_standard()
        with mock.patch.dict(sys.modules, {"platformdirs": None}):
            repli = _dossiers._dossier_etat_standard()
        self.assertEqual(repli, reel)
        self.assertEqual(reel.name, "lidar2map-data")


class RepriseTests(_Isole):
    def test_etat_copie_et_sorties_laissees_en_place(self):
        self.ecrire_ancien("preferences.json", json.dumps({"lang": "fr"}))
        self.ecrire_ancien("historique.json", "[]")
        self.ecrire_ancien("lidar2map.env", "IGN_APIKEY=secret\n")
        (self.ancien / "Projets" / "Gareoult").mkdir(parents=True)

        repris = _dossiers.preparer_etat(self.ancien)

        self.assertEqual(repris, ["preferences.json", "historique.json",
                                  "lidar2map.env", "dossier_sorties"])
        self.assertEqual(self.preferences(),
                         {"lang": "fr", "dossier_sorties": str(self.ancien)})
        self.assertEqual((self.etat / "lidar2map.env").read_text(encoding="utf-8"),
                         "IGN_APIKEY=secret\n")
        self.assertEqual(_dossiers.dossier_sorties(), self.ancien)
        # Copiés, jamais déplacés : revenir à la 1.53 reste possible.
        for nom in ("preferences.json", "historique.json", "lidar2map.env"):
            self.assertTrue((self.ancien / nom).is_file(), nom)
        self.assertTrue((self.ancien / "Projets" / "Gareoult").is_dir())
        marqueur = json.loads((self.etat / _dossiers.MARQUEUR).read_text(encoding="utf-8"))
        self.assertEqual(marqueur["depuis"], str(self.ancien))
        self.assertEqual(marqueur["dossier_sorties"], str(self.ancien))

    def test_une_seule_reprise(self):
        self.ecrire_ancien("historique.json", "[]")
        self.assertEqual(_dossiers.preparer_etat(self.ancien), ["historique.json"])
        self.ecrire_ancien("preferences.json", "{}")
        self.assertEqual(_dossiers.preparer_etat(self.ancien), [])
        self.assertFalse((self.etat / "preferences.json").exists())

    def test_rien_a_reprendre_ni_marqueur_ni_reglage(self):
        self.assertEqual(_dossiers.preparer_etat(self.ancien), [])
        self.assertFalse((self.etat / _dossiers.MARQUEUR).exists())
        self.assertFalse((self.etat / "preferences.json").exists())
        # Sans marqueur, la version installée pourra encore reprendre.
        self.ecrire_ancien("historique.json", "[]")
        self.assertEqual(_dossiers.preparer_etat(self.ancien), ["historique.json"])

    def test_n_ecrase_jamais_l_etat_ni_le_reglage_existants(self):
        self.etat.mkdir(parents=True)
        (self.etat / "historique.json").write_text("[1]", encoding="utf-8")
        (self.etat / "preferences.json").write_text(
            json.dumps({"dossier_sorties": "D:/Cartes"}), encoding="utf-8")
        self.ecrire_ancien("historique.json", "[]")
        self.ecrire_ancien("preferences.json", "{}")
        (self.ancien / "cache").mkdir()

        self.assertEqual(_dossiers.preparer_etat(self.ancien), [])
        self.assertEqual((self.etat / "historique.json").read_text(encoding="utf-8"), "[1]")
        self.assertEqual(self.preferences(), {"dossier_sorties": "D:/Cartes"})

    def test_sans_effet_avec_lidar2map_home(self):
        self.ecrire_ancien("historique.json", "[]")
        with mock.patch.dict(os.environ, {"LIDAR2MAP_HOME": str(self.racine / "portable")}):
            self.assertEqual(_dossiers.preparer_etat(self.ancien), [])
        self.assertFalse(self.etat.exists())

    def test_ancien_dossier_deja_dossier_d_etat(self):
        self.etat.mkdir(parents=True)
        (self.etat / "historique.json").write_text("[]", encoding="utf-8")
        self.assertEqual(_dossiers.preparer_etat(self.etat), [])
        self.assertFalse((self.etat / _dossiers.MARQUEUR).exists())

    def test_lancements_simultanes_une_seule_reprise(self):
        # Démarrage automatique et lancement manuel au même instant : le
        # verrou exclut aussi deux fils d'un même processus.
        self.ecrire_ancien("historique.json", "[]")
        (self.ancien / "Projets").mkdir()
        resultats = []
        depart = threading.Barrier(4)

        def lancer():
            depart.wait()
            resultats.append(_dossiers.preparer_etat(self.ancien))

        fils = [threading.Thread(target=lancer) for _ in range(4)]
        for f in fils:
            f.start()
        for f in fils:
            f.join()
        self.assertEqual(sorted(bool(r) for r in resultats), [False, False, False, True])
        self.assertEqual(self.preferences(), {"dossier_sorties": str(self.ancien)})


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
            self.assertFalse((Path(tmp) / _dossiers.MARQUEUR).exists())
        apres = set(journaux_sources.iterdir()) if journaux_sources.is_dir() else set()
        self.assertEqual(apres - avant, set())


if __name__ == "__main__":
    unittest.main()
