"""_autostart.py : lancement automatique du serveur web à l'ouverture de
session. Isolation stricte : jamais écrire dans le VRAI dossier Démarrage
Windows (%APPDATA%\\...\\Startup) pendant un test - os.environ["APPDATA"]
est toujours mocké vers un dossier temporaire, comme pour un dossier
systemd/launchd réel sur les deux autres OS.
"""
import importlib.util
import platform
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("l2m_autostart", ROOT / "_autostart.py")
_autostart = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _autostart
_SPEC.loader.exec_module(_autostart)


@unittest.skipUnless(platform.system() == "Windows", "chemin Windows uniquement")
class AutostartWindowsTests(unittest.TestCase):
    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_ctx.name)
        self.env_patch = mock.patch.dict("os.environ", {"APPDATA": str(self.tmp)})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.tmp_ctx.cleanup()

    def _fichier_attendu(self) -> Path:
        return (self.tmp / "Microsoft" / "Windows" / "Start Menu" /
                "Programs" / "Startup" / "lidar2map.vbs")

    def test_desactive_par_defaut(self):
        self.assertFalse(_autostart.is_enabled())

    def test_enable_cree_le_vbs_et_is_enabled_le_voit(self):
        _autostart.enable()
        fichier = self._fichier_attendu()
        self.assertTrue(fichier.is_file())
        self.assertTrue(_autostart.is_enabled())

    def test_vbs_lance_en_mode_serveur_sans_navigateur(self):
        _autostart.enable()
        contenu = self._fichier_attendu().read_text(encoding="utf-8")
        self.assertIn("--serve-gui", contenu)
        self.assertIn("--no-browser", contenu)
        # Fenêtre cachée (0) et sans attendre la fin (False) : un lancement
        # automatique visible ou bloquant à l'ouverture de session serait
        # exactement le défaut que ce mécanisme doit éviter.
        self.assertIn(", 0, False", contenu)

    def test_disable_supprime_le_fichier(self):
        _autostart.enable()
        self.assertTrue(_autostart.is_enabled())
        _autostart.disable()
        self.assertFalse(_autostart.is_enabled())
        self.assertFalse(self._fichier_attendu().is_file())

    def test_disable_sans_avoir_active_ne_leve_pas(self):
        _autostart.disable()  # ne doit pas lever, rien à supprimer
        self.assertFalse(_autostart.is_enabled())

    def test_enable_deux_fois_reste_actif_sans_erreur(self):
        _autostart.enable()
        _autostart.enable()  # idempotent
        self.assertTrue(_autostart.is_enabled())


if __name__ == "__main__":
    unittest.main()
