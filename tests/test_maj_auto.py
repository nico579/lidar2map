"""Installation automatique de lidar2map : ce qui lui est propre.

Le protocole (préparation, assistant, retour arrière) est testé dans
nico579_commons (maj_install) ; ici, la description de lidar2map (noms
d'archive, service systemd et agent launchd du démarrage automatique,
arguments de relance), l'auto-test que passe un bundle téléchargé, l'entrée
du menu de l'icône et la page, qui n'a plus son propre bandeau.
"""
import importlib.util
import os
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
_SPEC = importlib.util.spec_from_file_location("l2m_maj_auto", ROOT / "lidar2map.py")
L2M = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = L2M
_SPEC.loader.exec_module(L2M)

from nico579_commons import maj_archive, maj_install  # noqa: E402


def _systeme_onedir():
    """Un dossier PyInstaller « onedir » (Windows, Linux) quel que soit le système
    des tests : sous macOS, le bundle publié est une .app, autre disposition."""
    nom = "Windows" if sys.platform == "win32" else "Linux"
    return mock.patch.multiple(maj_install.platform, system=lambda: nom,
                               machine=lambda: "x86_64")


class AutoTest(unittest.TestCase):
    def lancer(self, *argv):
        return L2M._auto_test_version(list(argv))

    def test_accepte_sa_version_avec_ou_sans_v(self):
        self.assertEqual(self.lancer("--self-test-version", L2M.VERSION), 0)
        self.assertEqual(self.lancer("--self-test-version", "v" + L2M.VERSION), 0)

    def test_refuse_une_autre_version(self):
        self.assertEqual(self.lancer("--self-test-version", "0.0.1"), 1)

    def test_sans_valeur(self):
        self.assertEqual(self.lancer("--self-test-version"), 2)

    def test_refuse_un_bundle_sans_les_fichiers_communs(self):
        # Un exécutable dont le .spec oublie les données de nico579_commons : refusé par
        # la CI, et par la mise à jour automatique avant de remplacer quoi que ce soit.
        from nico579_commons import serveweb
        with mock.patch.object(serveweb, "fichiers_manquants", return_value=["reglages.js"]):
            self.assertEqual(self.lancer("--self-test-version", L2M.VERSION), 1)

    def test_refuse_si_l_interface_est_introuvable(self):
        with mock.patch.object(L2M, "_resoudre_gui_dir", side_effect=RuntimeError("absente")):
            self.assertEqual(self.lancer("--self-test-version", L2M.VERSION), 1)

    def test_le_point_d_entree_court_circuite_tout_le_reste(self):
        source = (ROOT / "lidar2map.py").read_text(encoding="utf-8")
        entree = source[source.index('if __name__ == "__main__":\n    try:'):]
        self.assertLess(entree.index("--self-test-version"),
                        entree.index("_normaliser_argv_valeurs_negatives()"))


class Description(unittest.TestCase):
    def test_service_et_agent_du_demarrage_automatique(self):
        with mock.patch.object(sys, "argv", ["lidar2map", "--port", "9000"]):
            app = L2M._application_installation()
        self.assertEqual(app.nom, "lidar2map")
        self.assertEqual(app.unite_systemd, "lidar2map.service")
        self.assertEqual(app.label_launchd, "com.nico.lidar2map")
        self.assertEqual(app.arguments_relance, ("--port", "9000"))
        self.assertEqual(app.donnees_preservees, ())

    def test_noms_d_archive_des_systemes_publies(self):
        for systeme, machine, attendu, racine in (
                ("Windows", "AMD64", "lidar2map-windows-x86_64.zip", "lidar2map-windows-x86_64"),
                ("Linux", "x86_64", "lidar2map-linux-x86_64.tar.gz", "lidar2map-linux-x86_64"),
                ("Darwin", "arm64", "lidar2map-macos-arm64.zip", "LIDAR2MAP.app"),
                ("Darwin", "x86_64", "lidar2map-macos-x86_64.zip", "LIDAR2MAP.app")):
            with self.subTest(systeme=systeme, machine=machine):
                fichier, _, dossier = maj_install.archive_standard(
                    "lidar2map", racine_macos="LIDAR2MAP.app", systeme=systeme, machine=machine)
                self.assertEqual((fichier, dossier), (attendu, racine))

    def test_depuis_les_sources_pas_d_installation_automatique(self):
        with self.assertRaises(maj_archive.ErreurMiseAJour) as c:
            L2M._disposition_installation()
        self.assertEqual(c.exception.code, "source_mode")

    def test_bundle_fige_dedie_accepte_et_dossier_general_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            nom_exe = "lidar2map.exe" if sys.platform == "win32" else "lidar2map"
            ok = Path(tmp).resolve() / "lidar2map"
            (ok / "_internal").mkdir(parents=True)
            (ok / nom_exe).write_bytes(b"x")
            general = Path(tmp).resolve() / "Telechargements"
            (general / "_internal").mkdir(parents=True)
            (general / nom_exe).write_bytes(b"x")
            (general / "photo.jpg").write_bytes(b"x")
            with mock.patch.object(sys, "frozen", True, create=True), _systeme_onedir():
                with mock.patch.object(sys, "executable", str(ok / nom_exe)):
                    disposition = L2M._disposition_installation()
                with mock.patch.object(sys, "executable", str(general / nom_exe)):
                    with self.assertRaises(maj_archive.ErreurMiseAJour) as c:
                        L2M._disposition_installation()
        self.assertEqual(disposition.install_root, ok)
        self.assertTrue(disposition.asset_name.startswith("lidar2map-"))
        self.assertEqual(c.exception.code, "unsafe_install")


class FauxVerificateur:
    page_des_releases = "https://github.com/nico579/lidar2map/releases/latest"

    def __init__(self, version="9.9.9"):
        self.info = {"version": version, "page": "https://x/r", "assets": []} if version else None

    def disponible(self):
        return self.info


class FauxInstallateur:
    def __init__(self, possible=True):
        self._possible = possible
        self.demarre = 0

    def possible(self):
        return (self._possible, "" if self._possible else "source_mode")

    def demarrer(self):
        self.demarre += 1
        return True


class MenuIcone(unittest.TestCase):
    def actions(self, installateur):
        return L2M._actions_tray("http://127.0.0.1:8765/", ROOT / "gui", lambda: None,
                                 FauxVerificateur(), installateur)

    def test_mise_a_jour_installe_quand_c_est_possible(self):
        installateur = FauxInstallateur(True)
        with mock.patch("webbrowser.open") as ouvrir:
            self.actions(installateur).mettre_a_jour()
        self.assertEqual(installateur.demarre, 1)
        ouvrir.assert_not_called()

    def test_mise_a_jour_ouvre_la_page_sinon(self):
        installateur = FauxInstallateur(False)
        with mock.patch("webbrowser.open") as ouvrir:
            self.actions(installateur).mettre_a_jour()
        self.assertEqual(installateur.demarre, 0)
        ouvrir.assert_called_once_with("https://x/r")

    def test_sans_installateur_comme_avant(self):
        with mock.patch("webbrowser.open") as ouvrir:
            self.actions(None).mettre_a_jour()
        ouvrir.assert_called_once_with("https://x/r")

    def test_l_icone_ne_se_ferme_pas_pendant_le_telechargement(self):
        self.assertFalse(self.actions(FauxInstallateur()).mettre_a_jour_referme)


class Page(unittest.TestCase):
    def test_la_page_charge_le_bandeau_commun_apres_app_js(self):
        html = (ROOT / "gui" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<script src="/nico579-maj.js"></script>', html)
        self.assertLess(html.index("/app.js"), html.index("/nico579-maj.js"))

    def test_la_page_place_le_bouton_reglages_avant_le_choix_de_langue(self):
        html = (ROOT / "gui" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<script src="/nico579-reglages.js"></script>', html)
        self.assertLess(html.index("/app.js"), html.index("/nico579-reglages.js"))
        # L'emplacement du bouton : juste avant FR / EN, comme dans blink2video.
        self.assertLess(html.index('id="nico579-reglages"'), html.index('data-lang-btn="fr"'))

    def test_les_executables_embarquent_les_fichiers_communs(self):
        # PyInstaller n'embarque les donnees d'un paquet que si le .spec le demande ;
        # sans cela la page reclame /nico579-maj.js et /nico579-reglages.js en 404.
        for spec in ("lidar2map_win.spec", "lidar2map_mac.spec"):
            texte = (ROOT / spec).read_text(encoding="utf-8")
            self.assertIn('collect_data_files("nico579_commons")', texte, spec)

    def test_l_ancien_bandeau_et_sa_route_ont_disparu(self):
        for nom in ("app.js", "web_bridge.js"):
            texte = (ROOT / "gui" / nom).read_text(encoding="utf-8")
            for ancien in ("check_update", "afficherBandeauUpdate", "update-banner", "update.dispo"):
                self.assertNotIn(ancien, texte, f"{nom} : {ancien}")
        self.assertFalse(hasattr(L2M.Api, "check_update"))


if __name__ == "__main__":
    unittest.main()
