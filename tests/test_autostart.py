"""_autostart.py : lancement automatique du serveur web à l'ouverture de
session. Isolation stricte : jamais écrire dans le VRAI dossier Démarrage
Windows (%APPDATA%\\...\\Startup) pendant un test - os.environ["APPDATA"]
est toujours mocké vers un dossier temporaire, comme pour un dossier
systemd/launchd réel sur les deux autres OS.

Depuis la 1.54.0 : un raccourci .lnk sous Windows (comme blink2video et
watch2notif), qui lance le LANCEUR visible plutôt que l'exe interne, sans
aucune variable d'environnement à transmettre.
"""
import importlib.util
import os
import platform
import plistlib
import subprocess
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


class _DossierIsole(unittest.TestCase):
    """APPDATA et le dossier personnel dans un dossier temporaire au nom
    accentué, avec un faux lanceur, et le programme vu comme figé."""

    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        # Forme longue : sur les runners GitHub, le dossier temporaire passe
        # par un nom court 8.3 (RUNNER~1), et Windows enregistre puis relit la
        # cible d'un raccourci sous sa forme longue (runneradmin).
        self.tmp = Path(self.tmp_ctx.name).resolve() / "Données é"
        self.tmp.mkdir()
        suffixe = ".exe" if platform.system() == "Windows" else ""
        self.lanceur = self.tmp / "Mes Cartes" / f"lidar2map{suffixe}"
        self.lanceur.parent.mkdir()
        self.lanceur.write_bytes(b"")
        for correctif in (
                mock.patch.object(_autostart.sys, "frozen", True, create=True),
                mock.patch.dict("os.environ", {"APPDATA": str(self.tmp),
                                               "LIDAR2MAP_LANCEUR": str(self.lanceur)}),
                mock.patch.object(_autostart.Path, "home", return_value=self.tmp)):
            correctif.start()
            self.addCleanup(correctif.stop)
        self.lnk = _autostart._windows_startup_file()
        self.vbs = _autostart._windows_legacy_file()


@unittest.skipUnless(platform.system() == "Windows", "raccourci .lnk : Windows seulement")
class AutostartWindowsTests(_DossierIsole):
    def lire_raccourci(self) -> list:
        # Sortie en UTF-8 : sinon PowerShell écrit dans la page de code de la
        # console, et le « é » du dossier de test revient déformé.
        script = ("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
                  " $s = (New-Object -ComObject WScript.Shell).CreateShortcut("
                  + _autostart._chaine_ps(str(self.lnk))
                  + "); Write-Output $s.TargetPath; Write-Output $s.Arguments;"
                  " Write-Output $s.WorkingDirectory")
        sortie = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                                 "-Command", script], capture_output=True,
                                encoding="utf-8", check=True).stdout
        return [ligne.strip() for ligne in sortie.splitlines()]

    def test_desactive_par_defaut(self):
        self.assertFalse(_autostart.is_enabled())

    def test_raccourci_lance_le_lanceur_en_mode_serveur(self):
        _autostart.enable()
        self.assertTrue(self.lnk.is_file())
        self.assertTrue(_autostart.is_enabled())
        cible, arguments, dossier = self.lire_raccourci()
        self.assertEqual(Path(cible), self.lanceur)
        self.assertEqual(arguments, "--serve-gui --no-browser")
        self.assertEqual(Path(dossier), self.lanceur.parent)

    def test_disable_supprime_raccourci_et_ancien_vbs(self):
        _autostart.enable()
        self.vbs.write_text("ancien", encoding="utf-8")
        _autostart.disable()
        self.assertFalse(self.lnk.exists())
        self.assertFalse(self.vbs.exists())
        self.assertFalse(_autostart.is_enabled())

    def test_disable_sans_avoir_active_ne_leve_pas(self):
        _autostart.disable()
        self.assertFalse(_autostart.is_enabled())

    def test_enable_deux_fois_reste_actif_sans_erreur(self):
        _autostart.enable()
        _autostart.enable()
        self.assertTrue(_autostart.is_enabled())

    def test_migration_remplace_l_ancien_vbs(self):
        self.vbs.parent.mkdir(parents=True, exist_ok=True)
        self.vbs.write_text("ancien", encoding="utf-8")
        self.assertTrue(_autostart.is_enabled())
        self.assertTrue(_autostart.migrer_ancien_demarrage())
        self.assertTrue(self.lnk.is_file())
        self.assertFalse(self.vbs.exists())

    def test_migration_sans_vbs_n_active_rien(self):
        self.assertFalse(_autostart.migrer_ancien_demarrage())
        self.assertFalse(self.lnk.exists())


class AutostartLanceurTests(_DossierIsole):
    """Générateurs appelés directement (fichiers en dossier temporaire,
    systemctl/launchctl mockés) : valables sur les 3 OS."""

    def test_commande_lance_le_lanceur(self):
        self.assertEqual(_autostart._lidar2map_command(),
                         [str(self.lanceur), "--serve-gui", "--no-browser"])
        self.assertEqual(_autostart._dossier_lancement(), self.lanceur.parent)

    def test_lanceur_d_avant_1_54_retrouve_par_son_dossier(self):
        # Un lanceur <= 1.53 ne donnait que LIDAR2MAP_WORK_DIR.
        with mock.patch.dict("os.environ", {"LIDAR2MAP_WORK_DIR": str(self.lanceur.parent)}), \
                mock.patch.object(_autostart.platform, "system", return_value="Windows"):
            os.environ.pop("LIDAR2MAP_LANCEUR")
            lanceur = self.lanceur.with_suffix(".exe")
            lanceur.write_bytes(b"")
            self.assertEqual(_autostart._lanceur(), lanceur)

    def test_sans_lanceur_connu_l_exe_courant(self):
        os.environ.pop("LIDAR2MAP_LANCEUR")
        self.assertIsNone(_autostart._lanceur())
        self.assertEqual(_autostart._lidar2map_command()[0], sys.executable)

    def test_service_systemd_lance_le_lanceur_sans_environnement(self):
        with mock.patch.object(_autostart.subprocess, "run"):
            _autostart._enable_linux()
        contenu = _autostart._linux_service_file().read_text(encoding="utf-8")
        self.assertNotIn("Environment=", contenu)
        exec_start = next(ligne for ligne in contenu.splitlines()
                          if ligne.startswith("ExecStart="))
        self.assertEqual(exec_start, "ExecStart=" + " ".join(
            _autostart._systemd_quote(part) for part in _autostart._lidar2map_command()))
        self.assertIn(f"WorkingDirectory={self.lanceur.parent}\n", contenu)

    def test_plist_launchd_lance_le_lanceur_sans_environnement(self):
        with mock.patch.object(_autostart.subprocess, "run"):
            _autostart._enable_mac()
        donnees = plistlib.loads(_autostart._mac_plist_file().read_bytes())
        self.assertEqual(donnees["ProgramArguments"],
                         [str(self.lanceur), "--serve-gui", "--no-browser"])
        self.assertNotIn("EnvironmentVariables", donnees)
        self.assertEqual(donnees["WorkingDirectory"], str(self.lanceur.parent))
        self.assertEqual(donnees["KeepAlive"], {"SuccessfulExit": False})


class AutostartWindowsLogiqueTests(_DossierIsole):
    """Logique Windows sur tout OS : PowerShell remplacé par un faux qui
    écrit le raccourci comme le ferait Save()."""

    def powershell(self, reussi=True):
        def lancer(commande, **options):
            if reussi:
                self.lnk.write_bytes(b"raccourci")
            return subprocess.CompletedProcess(commande, 0 if reussi else 1, stderr="refus")
        return mock.patch.object(_autostart.subprocess, "run", side_effect=lancer)

    def setUp(self):
        super().setUp()
        correctif = mock.patch.object(_autostart.platform, "system", return_value="Windows")
        correctif.start()
        self.addCleanup(correctif.stop)
        self.vbs.parent.mkdir(parents=True, exist_ok=True)

    def test_enable_retire_l_ancien_vbs_et_cache_powershell(self):
        self.vbs.write_text("ancien", encoding="utf-8")
        with self.powershell() as lancer:
            _autostart.enable()
        self.assertTrue(self.lnk.exists())
        self.assertFalse(self.vbs.exists())
        self.assertEqual(lancer.call_args.kwargs["creationflags"],
                         getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def test_echec_signale_sans_perdre_l_ancien_demarrage(self):
        self.vbs.write_text("ancien", encoding="utf-8")
        with self.powershell(reussi=False):
            with self.assertRaisesRegex(RuntimeError, "refus"):
                _autostart.enable()
        self.assertTrue(self.vbs.exists())

    def test_migration_ignoree_depuis_les_sources(self):
        # Un lancement depuis les sources a cote d'une installation ne doit
        # pas repointer le demarrage automatique de celle-ci vers python.
        self.vbs.write_text("ancien", encoding="utf-8")
        with mock.patch.object(_autostart.sys, "frozen", False), \
                self.powershell() as lancer:
            self.assertFalse(_autostart.migrer_ancien_demarrage())
        lancer.assert_not_called()
        self.assertTrue(self.vbs.exists())
        self.assertFalse(self.lnk.exists())


if __name__ == "__main__":
    unittest.main()
