"""_autostart.py : lancement automatique du serveur web à l'ouverture de
session. Isolation stricte : jamais écrire dans le VRAI dossier Démarrage
Windows (%APPDATA%\\...\\Startup) pendant un test - os.environ["APPDATA"]
est toujours mocké vers un dossier temporaire, comme pour un dossier
systemd/launchd réel sur les deux autres OS.

Depuis la 1.54.0 : un raccourci .lnk sous Windows (comme blink2video et
watch2notif), sans aucune variable d'environnement à transmettre. Depuis la
1.55.0, il lance le programme en cours lui-même : l'archive le livre tel
quel, sans lanceur qui l'extrairait ailleurs.
"""
import importlib.util
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

from nico579_commons import demarrage  # noqa: E402


class _DossierIsole(unittest.TestCase):
    """APPDATA et le dossier personnel dans un dossier temporaire au nom
    accentué, avec un faux programme, vu comme figé."""

    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        # Forme longue : sur les runners GitHub, le dossier temporaire passe
        # par un nom court 8.3 (RUNNER~1), et Windows enregistre puis relit la
        # cible d'un raccourci sous sa forme longue (runneradmin).
        self.tmp = Path(self.tmp_ctx.name).resolve() / "Données é"
        self.tmp.mkdir()
        suffixe = ".exe" if platform.system() == "Windows" else ""
        self.programme = self.tmp / "Mes Cartes" / f"lidar2map{suffixe}"
        self.programme.parent.mkdir()
        self.programme.write_bytes(b"")
        # Variables posées par un lanceur <= 1.54 : une instance 1.54 encore
        # en marche les transmet au programme 1.55 qu'elle relance après une
        # mise à jour décompressée par-dessus. Il doit les ignorer.
        ancien = self.tmp / "ancienne extraction" / f"lidar2map{suffixe}"
        for correctif in (
                mock.patch.object(_autostart.sys, "frozen", True, create=True),
                mock.patch.object(_autostart.sys, "executable", str(self.programme)),
                mock.patch.dict("os.environ", {"APPDATA": str(self.tmp),
                                               "LIDAR2MAP_LANCEUR": str(ancien),
                                               "LIDAR2MAP_WORK_DIR": str(ancien.parent)}),
                mock.patch.object(_autostart.Path, "home", return_value=self.tmp),
                # Jamais le vrai dossier Démarrage (nico579_commons.demarrage).
                mock.patch.object(demarrage, "dossier_demarrage",
                                  return_value=self.tmp / "Startup")):
            correctif.start()
            self.addCleanup(correctif.stop)
        self.startup = self.tmp / "Startup"
        self.lnk = self.startup / "lidar2map.lnk"
        self.vbs = self.startup / "lidar2map.vbs"


@unittest.skipUnless(platform.system() == "Windows", "raccourci .lnk : Windows seulement")
class AutostartWindowsTests(_DossierIsole):
    def lire_raccourci(self) -> list:
        # Sortie en UTF-8 : sinon PowerShell écrit dans la page de code de la
        # console, et le « é » du dossier de test revient déformé.
        script = ("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
                  " $s = (New-Object -ComObject WScript.Shell).CreateShortcut("
                  + "'" + str(self.lnk).replace("'", "''") + "'"
                  + "); Write-Output $s.TargetPath; Write-Output $s.Arguments;"
                  " Write-Output $s.WorkingDirectory")
        sortie = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                                 "-Command", script], capture_output=True,
                                encoding="utf-8", check=True).stdout
        return [ligne.strip() for ligne in sortie.splitlines()]

    def test_desactive_par_defaut(self):
        self.assertFalse(_autostart.is_enabled())

    def test_raccourci_lance_le_programme_en_mode_serveur(self):
        _autostart.enable()
        self.assertTrue(self.lnk.is_file())
        self.assertTrue(_autostart.is_enabled())
        cible, arguments, dossier = self.lire_raccourci()
        self.assertEqual(Path(cible), self.programme)
        self.assertEqual(arguments, "--serve-gui --no-browser")
        self.assertEqual(Path(dossier), self.programme.parent)

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


class AutostartCommandeTests(_DossierIsole):
    """Générateurs appelés directement (fichiers en dossier temporaire,
    systemctl/launchctl mockés) : valables sur les 3 OS."""

    def test_commande_lance_le_programme_en_cours(self):
        # Les variables d'un lanceur <= 1.54, présentes dans l'environnement
        # (voir _DossierIsole), ne détournent pas la commande.
        self.assertEqual(_autostart._lidar2map_command(),
                         [str(self.programme), "--serve-gui", "--no-browser"])
        self.assertEqual(_autostart._dossier_lancement(), self.programme.parent)

    def test_raccourci_bureau_ouvre_le_navigateur(self):
        # Même programme que le démarrage automatique, mais on le clique pour
        # ouvrir lidar2map : sans --no-browser.
        self.assertEqual(_autostart.raccourci_bureau(),
                         ([str(self.programme), "--serve-gui"], self.programme.parent))

    def test_service_systemd_lance_le_programme_sans_environnement(self):
        demarrage.activer(_autostart._entree(), plateforme="linux", accueil=self.tmp,
                          lancer=mock.Mock(return_value=subprocess.CompletedProcess([], 0)),
                          env={"XDG_RUNTIME_DIR": "/run/user/1"})
        contenu = (self.tmp / ".config" / "systemd" / "user" / "lidar2map.service"
                   ).read_text(encoding="utf-8")
        self.assertNotIn("Environment=", contenu)
        exec_start = next(ligne for ligne in contenu.splitlines()
                          if ligne.startswith("ExecStart="))
        self.assertEqual(exec_start, "ExecStart=" + " ".join(
            demarrage.argument_systemd(part) for part in _autostart._lidar2map_command()))
        self.assertIn(f"WorkingDirectory={self.programme.parent}\n", contenu)
        # Une application à icône : après la session graphique.
        self.assertIn("After=graphical-session.target", contenu)

    def test_plist_launchd_lance_le_programme_sans_environnement(self):
        demarrage.activer(_autostart._entree(), plateforme="darwin", accueil=self.tmp,
                          lancer=mock.Mock(return_value=subprocess.CompletedProcess([], 0)))
        fichier = self.tmp / "Library" / "LaunchAgents" / "com.nico.lidar2map.plist"
        donnees = plistlib.loads(fichier.read_bytes())
        self.assertEqual(donnees["Label"], _autostart.MAC_LABEL)
        self.assertEqual(donnees["ProgramArguments"],
                         [str(self.programme), "--serve-gui", "--no-browser"])
        self.assertNotIn("EnvironmentVariables", donnees)
        self.assertEqual(donnees["WorkingDirectory"], str(self.programme.parent))
        self.assertEqual(donnees["KeepAlive"], {"SuccessfulExit": False})

    def test_noms_connus_du_reste_de_lidar2map(self):
        # maj_install relance le service par son nom (lidar2map.py).
        self.assertEqual(_autostart.LINUX_SERVICE_NAME, f"{_autostart._entree().nom}.service")


class AutostartWindowsLogiqueTests(_DossierIsole):
    """Logique Windows sur tout OS : PowerShell remplacé par un faux qui
    écrit le raccourci comme le ferait Save()."""

    def powershell(self, reussi=True):
        def lancer(commande, **options):
            if reussi:
                self.lnk.write_bytes(b"raccourci")
            return subprocess.CompletedProcess(commande, 0 if reussi else 1, stderr="refus")
        return mock.Mock(side_effect=lancer)

    def activer(self, lancer):
        demarrage.activer(_autostart._entree(), plateforme="win32", dossier=self.startup,
                          lancer=lancer)

    def test_enable_retire_l_ancien_vbs(self):
        self.startup.mkdir(parents=True, exist_ok=True)
        self.vbs.write_text("ancien", encoding="utf-8")
        self.activer(self.powershell())
        self.assertTrue(self.lnk.exists())
        self.assertFalse(self.vbs.exists())

    def test_echec_signale_sans_perdre_l_ancien_demarrage(self):
        self.startup.mkdir(parents=True, exist_ok=True)
        self.vbs.write_text("ancien", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "refus"):
            self.activer(self.powershell(reussi=False))
        self.assertTrue(self.vbs.exists())

    def test_migration_ignoree_depuis_les_sources(self):
        # Un lancement depuis les sources a cote d'une installation ne doit
        # pas repointer le demarrage automatique de celle-ci vers python.
        self.startup.mkdir(parents=True, exist_ok=True)
        self.vbs.write_text("ancien", encoding="utf-8")
        with mock.patch.object(_autostart.sys, "frozen", False), \
                mock.patch.object(demarrage, "_activer_windows") as activer:
            self.assertFalse(_autostart.migrer_ancien_demarrage())
        activer.assert_not_called()
        self.assertTrue(self.vbs.exists())
        self.assertFalse(self.lnk.exists())


if __name__ == "__main__":
    unittest.main()
