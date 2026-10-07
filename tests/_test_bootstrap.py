"""Contrats hors reseau du bootstrap precoce de lidar2map.

Le module principal execute son bootstrap des l'import. Le runner impose le
mode ``none`` pour cet import, puis chaque test appelle explicitement la
fonction visee avec ses effets externes simules (pip, venv, exec et sorties).
"""

from __future__ import annotations

import ast
import contextlib
import inspect
import io
import os
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
# Jamais les vrais dossiers d'état et de sorties de l'utilisateur (voir
# _dossiers.py) : run_tests.py en fournit un, sinon un dossier temporaire.
if not os.environ.get("LIDAR2MAP_HOME"):
    os.environ["LIDAR2MAP_HOME"] = tempfile.mkdtemp(prefix="lidar2map-tests-")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lidar2map as L  # noqa: E402
import _amorcage  # noqa: E402
import _installation as installation  # noqa: E402
import _bootstrap_tls as bootstrap_tls  # noqa: E402
import _smoketest as smoketest  # noqa: E402
import _logging_helpers as logging_helpers  # noqa: E402
import _log_activation as log_activation  # noqa: E402
import _runtime_paths as runtime_paths  # noqa: E402
import _disk_guard as disk_guard  # noqa: E402


class BootstrapControlModuleTests(unittest.TestCase):
    def test_early_bootstrap_modules_parse_with_python_39_grammar(self):
        for name in (
            "_amorcage.py",
            "_installation.py",
            "_bootstrap_tls.py",
        ):
            with self.subTest(module=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                ast.parse(source, filename=name, feature_version=(3, 9))


class BootstrapTlsTests(unittest.TestCase):
    @staticmethod
    def _fake_ssl():
        contexts = []

        def create_default_context(*, cafile=None):
            context = SimpleNamespace(
                cafile=cafile,
                verify_mode="CERT_REQUIRED",
                check_hostname=True,
            )
            contexts.append(context)
            return context

        return SimpleNamespace(
            contexts=contexts,
            create_default_context=mock.Mock(side_effect=create_default_context),
            _create_default_https_context=object(),
            _create_unverified_context=object(),
        )

    @staticmethod
    def _certifi(path="C:/ca/certifi.pem"):
        return SimpleNamespace(where=mock.Mock(return_value=path))

    def test_certifi_loader_only_translates_the_package_own_absence(self):
        absent = ModuleNotFoundError("certifi absent", name="certifi")
        with mock.patch("builtins.__import__", side_effect=absent), \
             self.assertRaises(bootstrap_tls.CertifiIndisponible):
            bootstrap_tls._charger_certifi()

        internal_errors = (
            ModuleNotFoundError("dépendance absente", name="certifi.core"),
            ImportError("certifi cassé"),
        )
        for error in internal_errors:
            with self.subTest(error=type(error).__name__), mock.patch(
                "builtins.__import__",
                side_effect=error,
            ), self.assertRaises(type(error)) as raised:
                bootstrap_tls._charger_certifi()
            self.assertIs(raised.exception, error)

    def test_tls_module_and_historical_facade_are_stable(self):
        self.assertIs(L._bootstrap_tls_impl, bootstrap_tls)
        self.assertEqual(str(inspect.signature(L._restaurer_tls_strict)), "()")
        self.assertEqual(
            L._restaurer_tls_strict.__doc__,
            bootstrap_tls.restaurer_tls_strict.__doc__,
        )

        previous = L._SSL_CTX_CERTIFI
        replacement = object()
        try:
            with mock.patch.object(
                bootstrap_tls,
                "restaurer_tls_strict",
                return_value=replacement,
            ) as restore:
                L._restaurer_tls_strict()
            self.assertIs(L._SSL_CTX_CERTIFI, replacement)
            restore.assert_called_once_with(
                environnement=L.os.environ,
                module_ssl=L.ssl,
            )
        finally:
            L._SSL_CTX_CERTIFI = previous

    def test_initial_tls_uses_certifi_and_publishes_only_strict_state(self):
        fake_ssl = self._fake_ssl()
        certifi = self._certifi()
        environnement = {}

        context = bootstrap_tls.initialiser_tls(
            environnement=environnement,
            module_ssl=fake_ssl,
            charger_certifi=mock.Mock(return_value=certifi),
        )

        certifi.where.assert_called_once_with()
        fake_ssl.create_default_context.assert_called_once_with(
            cafile="C:/ca/certifi.pem"
        )
        self.assertEqual(
            environnement,
            {
                "SSL_CERT_FILE": "C:/ca/certifi.pem",
                "REQUESTS_CA_BUNDLE": "C:/ca/certifi.pem",
            },
        )
        self.assertEqual(context.verify_mode, "CERT_REQUIRED")
        self.assertTrue(context.check_hostname)
        self.assertIs(fake_ssl._create_default_https_context(), context)
        self.assertIs(fake_ssl._create_default_https_context(), context)

    def test_initial_tls_without_certifi_never_installs_unverified_context(self):
        fake_ssl = self._fake_ssl()
        environnement = {}
        missing = mock.Mock(side_effect=bootstrap_tls.CertifiIndisponible())

        context = bootstrap_tls.initialiser_tls(
            environnement=environnement,
            module_ssl=fake_ssl,
            charger_certifi=missing,
        )

        self.assertIsNone(context)
        self.assertEqual(environnement, {})
        self.assertIs(
            fake_ssl._create_default_https_context,
            fake_ssl.create_default_context,
        )
        self.assertIsNot(
            fake_ssl._create_default_https_context,
            fake_ssl._create_unverified_context,
        )
        strict = fake_ssl._create_default_https_context()
        self.assertEqual(strict.verify_mode, "CERT_REQUIRED")
        self.assertTrue(strict.check_hostname)

    def test_user_ca_has_priority_and_is_never_overwritten(self):
        cases = (
            (
                {"SSL_CERT_FILE": "C:/enterprise.pem"},
                "C:/enterprise.pem",
                {
                    "SSL_CERT_FILE": "C:/enterprise.pem",
                    "REQUESTS_CA_BUNDLE": "C:/enterprise.pem",
                },
            ),
            (
                {"REQUESTS_CA_BUNDLE": "C:/requests.pem"},
                "C:/requests.pem",
                {
                    "SSL_CERT_FILE": "C:/requests.pem",
                    "REQUESTS_CA_BUNDLE": "C:/requests.pem",
                },
            ),
            (
                {
                    "SSL_CERT_FILE": "C:/ssl.pem",
                    "REQUESTS_CA_BUNDLE": "C:/requests.pem",
                },
                "C:/ssl.pem",
                {
                    "SSL_CERT_FILE": "C:/ssl.pem",
                    "REQUESTS_CA_BUNDLE": "C:/requests.pem",
                },
            ),
        )
        for initial, expected_cafile, expected_environment in cases:
            with self.subTest(environment=initial):
                fake_ssl = self._fake_ssl()
                environnement = dict(initial)
                loader = mock.Mock(side_effect=AssertionError("certifi lu"))
                bootstrap_tls.initialiser_tls(
                    environnement=environnement,
                    module_ssl=fake_ssl,
                    charger_certifi=loader,
                )
                loader.assert_not_called()
                fake_ssl.create_default_context.assert_called_once_with(
                    cafile=expected_cafile
                )
                self.assertEqual(environnement, expected_environment)

    def test_tls_publication_is_transactional_when_context_creation_fails(self):
        fake_ssl = self._fake_ssl()
        previous_factory = fake_ssl._create_default_https_context
        fake_ssl.create_default_context.side_effect = OSError("CA illisible")
        environnement = {"AUTRE": "valeur"}

        with self.assertRaisesRegex(OSError, "CA illisible"):
            bootstrap_tls.initialiser_tls(
                environnement=environnement,
                module_ssl=fake_ssl,
                charger_certifi=mock.Mock(return_value=self._certifi()),
            )

        self.assertEqual(environnement, {"AUTRE": "valeur"})
        self.assertIs(fake_ssl._create_default_https_context, previous_factory)

    def test_broken_certifi_is_not_misclassified_as_an_absent_package(self):
        fake_ssl = self._fake_ssl()
        previous_factory = fake_ssl._create_default_https_context
        certifi = self._certifi()
        certifi.where.side_effect = ImportError("certifi cassé")
        environnement = {"AUTRE": "valeur"}

        with self.assertRaisesRegex(ImportError, "certifi cassé"):
            bootstrap_tls.initialiser_tls(
                environnement=environnement,
                module_ssl=fake_ssl,
                charger_certifi=mock.Mock(return_value=certifi),
            )

        fake_ssl.create_default_context.assert_not_called()
        self.assertEqual(environnement, {"AUTRE": "valeur"})
        self.assertIs(fake_ssl._create_default_https_context, previous_factory)

    def test_restore_switches_from_system_to_certifi_and_is_repeatable(self):
        fake_ssl = self._fake_ssl()
        environnement = {}
        missing = mock.Mock(side_effect=bootstrap_tls.CertifiIndisponible())
        self.assertIsNone(
            bootstrap_tls.initialiser_tls(
                environnement=environnement,
                module_ssl=fake_ssl,
                charger_certifi=missing,
            )
        )

        certifi = self._certifi()
        first = bootstrap_tls.restaurer_tls_strict(
            environnement=environnement,
            module_ssl=fake_ssl,
            charger_certifi=mock.Mock(return_value=certifi),
        )
        second = bootstrap_tls.restaurer_tls_strict(
            environnement=environnement,
            module_ssl=fake_ssl,
            charger_certifi=mock.Mock(return_value=certifi),
        )

        self.assertIsNot(first, second)
        self.assertEqual(first.verify_mode, "CERT_REQUIRED")
        self.assertEqual(second.verify_mode, "CERT_REQUIRED")
        self.assertTrue(first.check_hostname and second.check_hostname)
        self.assertIs(fake_ssl._create_default_https_context(), second)
        self.assertEqual(
            environnement["SSL_CERT_FILE"],
            "C:/ca/certifi.pem",
        )


class BootstrapDependencyTests(unittest.TestCase):
    def test_main_import_by_spec_works_from_isolated_cwd(self):
        app_literal = repr(str(ROOT / "lidar2map.py"))
        code = (
            "import importlib.util, os, pathlib\n"
            "os.environ['LIDAR2MAP_BOOTSTRAP'] = 'none'\n"
            f"spec = importlib.util.spec_from_file_location('isolated_lidar2map', {app_literal})\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            # Sonde de fumée : exercer un appel qui traverse vers
            # _bootstrap_runtime (module frère) confirme que l'auto-fixup de
            # sys.path a fonctionne depuis ce cwd isole, et que le module
            # retrouve requirements.in a cote de lui, pas dans ce cwd.
            "assert 'rasterio' in module._amorcage.dependances_directes(pathlib.Path(module.__file__).parent / 'requirements.in')\n"
        )
        with self.subTest(mode="spec_from_file_location"):
            with tempfile.TemporaryDirectory() as directory:
                completed = subprocess.run(
                    [sys.executable, "-I", "-c", code],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_spec_import_prioritizes_its_bootstrap_modules_on_sys_path(self):
        with tempfile.TemporaryDirectory() as directory:
            hostile = Path(directory)
            (hostile / "_bootstrap_tls.py").write_text(
                "raise RuntimeError('module TLS hostile chargé')\n",
                encoding="utf-8",
            )
            (hostile / "_amorcage.py").write_text(
                "raise RuntimeError('module d amorçage hostile chargé')\n",
                encoding="utf-8",
            )
            app_literal = repr(str(ROOT / "lidar2map.py"))
            root_literal = repr(str(ROOT))
            hostile_literal = repr(str(hostile))
            code = (
                "import importlib.util, os, pathlib, sys\n"
                "os.environ['LIDAR2MAP_BOOTSTRAP'] = 'none'\n"
                f"sys.path.insert(0, {hostile_literal})\n"
                f"sys.path.append({root_literal})\n"
                f"spec = importlib.util.spec_from_file_location('isolated_secure', {app_literal})\n"
                "module = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(module)\n"
                f"expected = pathlib.Path({root_literal}, '_bootstrap_tls.py').resolve()\n"
                "assert pathlib.Path(module._bootstrap_tls_impl.__file__).resolve() == expected\n"
                f"engine = pathlib.Path({root_literal}, '_amorcage.py').resolve()\n"
                "assert pathlib.Path(module._amorcage.__file__).resolve() == engine\n"
            )
            completed = subprocess.run(
                [sys.executable, "-I", "-c", code],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )


class VerrouTests(unittest.TestCase):
    """Dépendances déclarées une fois (requirements.in), verrouillées pour
    les trois systèmes (requirements.txt), plus PyInstaller pour construire
    (requirements-build.txt)."""

    @staticmethod
    def _pins(fichier):
        pins = {}
        for ligne in (ROOT / fichier).read_text(encoding="utf-8").splitlines():
            if ligne[:1].isalnum() and "==" in ligne:
                nom, reste = ligne.split("==", 1)
                version, _, marqueur = reste.partition(";")
                pins[(_amorcage.nom_normalise(nom),
                      marqueur.replace("\\", "").strip())] = version.strip()
        return pins

    def test_direct_dependencies_are_read_without_versions_or_markers(self):
        noms = _amorcage.dependances_directes(ROOT / "requirements.in", conditionnelles=True)
        for attendu in ("Pillow", "rasterio", "pystray", "platformdirs",
                        "nico579-commons", "numba", "cloth-simulation-filter"):
            self.assertIn(attendu, noms)
        for nom in noms:
            self.assertRegex(nom, r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

    def test_conditional_dependencies_are_not_required_at_startup(self):
        # numba porte un marqueur (pas de roue pour Python 3.13 sur les Mac
        # Intel) : absent à bon droit de certains systèmes, le contrôle au
        # démarrage ne l'exige pas, sans quoi pip serait relancé à chaque
        # démarrage. Le filtre CSF, compilé depuis ses sources sur Mac
        # Intel, est inconditionnel et donc exigé partout.
        requises = _amorcage.dependances_directes(ROOT / "requirements.in")
        self.assertIn("rasterio", requises)
        self.assertNotIn("numba", requises)
        self.assertIn("cloth-simulation-filter", requises)
        with tempfile.TemporaryDirectory() as dossier:
            fichier = Path(dossier) / "requirements.in"
            fichier.write_text("# commentaire\n-c contraintes.txt\nPillow>=10  # image\n"
                               "numba ; sys_platform != 'darwin'\nlaspy[lazrs]\n",
                               encoding="utf-8")
            self.assertEqual(_amorcage.dependances_directes(fichier),
                             ["Pillow", "laspy"])
            self.assertEqual(
                _amorcage.dependances_directes(fichier, conditionnelles=True),
                ["Pillow", "numba", "laspy"])

    def test_every_direct_dependency_is_in_both_locks(self):
        for fichier in ("requirements.txt", "requirements-build.txt"):
            verrouilles = {nom for nom, _ in self._pins(fichier)}
            with self.subTest(verrou=fichier):
                for nom in _amorcage.dependances_directes(ROOT / "requirements.in", conditionnelles=True):
                    self.assertIn(_amorcage.nom_normalise(nom), verrouilles)

    def test_build_lock_adds_pyinstaller_at_the_same_versions(self):
        execution = self._pins("requirements.txt")
        construction = self._pins("requirements-build.txt")
        self.assertEqual({k: construction.get(k) for k in execution}, execution)
        self.assertIn("pyinstaller", {nom for nom, _ in construction})
        self.assertNotIn("pyinstaller", {nom for nom, _ in execution})

    def test_every_locked_package_carries_its_hashes(self):
        # Chaque entrée commence par son nom en début de ligne ; les lignes
        # d'empreintes et de commentaires qui la suivent sont indentées.
        for fichier in ("requirements.txt", "requirements-build.txt"):
            texte = (ROOT / fichier).read_text(encoding="utf-8")
            entrees = [e for e in re.split(r"\n(?=[A-Za-z0-9])", texte)
                       if e[:1].isalnum()]
            self.assertGreater(len(entrees), 20)
            for entree in entrees:
                with self.subTest(verrou=fichier, paquet=entree.split("==", 1)[0]):
                    self.assertIn("--hash=sha256:", entree)


class BootstrapUninstallPlanningTests(unittest.TestCase):
    def test_windows_targets_use_localappdata(self):
        targets = installation.chemins_desinstallation(
            systeme="Windows", home=Path("/home/test"), localappdata=Path("/local")
        )
        self.assertEqual(targets[0][0], Path("/local/lidar2map"))
        self.assertEqual(targets[1][0], Path("/home/test/.lidar2map/venv"))

    def test_macos_and_linux_targets_are_deterministic(self):
        mac = installation.chemins_desinstallation(
            systeme="Darwin", home=Path("/home/test")
        )
        linux = installation.chemins_desinstallation(
            systeme="Linux", home=Path("/home/test")
        )
        self.assertEqual(mac[0][0], Path("/home/test/Library/Application Support/lidar2map"))
        self.assertEqual(linux[0][0], Path("/home/test/.local/share/lidar2map"))

    def test_planning_does_not_touch_filesystem(self):
        targets = installation.chemins_desinstallation(
            systeme="Other", home=Path("/path/that/need/not/exist")
        )
        self.assertEqual(len(targets), 4)
        self.assertFalse(any(path.exists() for path, _label in targets))

    def test_uninstall_removes_only_planned_temporary_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            outside = root / "outside.txt"
            outside.write_bytes(b"preserve")
            targets = installation.chemins_desinstallation(
                systeme="Linux", home=home
            )
            for index, (path, _label) in enumerate(targets):
                path.mkdir(parents=True)
                (path / f"file-{index}.bin").write_bytes(b"data")
            messages = []
            ok = installation.desinstaller_lidar2map(
                systeme="Linux", home=home, ecrire=messages.append
            )
            self.assertTrue(ok)
            self.assertTrue(outside.is_file())
            self.assertTrue(all(not path.exists() for path, _label in targets))
            self.assertEqual(messages.count("    ✓ removed"), 4)

    def test_uninstall_reports_partial_failure_and_continues(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            targets = installation.chemins_desinstallation(
                systeme="Linux", home=home
            )
            for path, _label in targets[:2]:
                path.mkdir(parents=True)
            failed = targets[0][0]
            removed = []

            def remover(path):
                if path == failed:
                    raise PermissionError("locked")
                removed.append(path)
                path.rmdir()

            messages = []
            ok = installation.desinstaller_lidar2map(
                systeme="Linux",
                home=home,
                supprimer_arbre=remover,
                ecrire=messages.append,
            )
            self.assertFalse(ok)
            self.assertTrue(failed.exists())
            self.assertEqual(removed, [targets[1][0]])
            self.assertTrue(any("partial (locked)" in line for line in messages))

    def test_historical_uninstall_facade_reads_environment_late(self):
        with mock.patch.object(L.platform, "system", return_value="Windows"), \
             mock.patch.object(L.Path, "home", return_value=Path("/home/test")), \
             mock.patch.dict(L.os.environ, {"LOCALAPPDATA": "/local"}, clear=True), \
             mock.patch.object(
                 L._installation_impl,
                 "desinstaller_lidar2map",
                 return_value=True,
             ) as uninstall:
            self.assertTrue(L._desinstaller_installation())
        uninstall.assert_called_once_with(
            systeme="Windows",
            home=Path("/home/test"),
            localappdata="/local",
            executable=None,
        )

    def test_frozen_uninstall_facade_names_the_running_program(self):
        with mock.patch.object(L.sys, "frozen", True, create=True), \
             mock.patch.object(L.sys, "executable", "/opt/lidar2map/lidar2map"), \
             mock.patch.object(
                 L._installation_impl,
                 "desinstaller_lidar2map",
                 return_value=True,
             ) as uninstall:
            self.assertTrue(L._desinstaller_installation())
        self.assertEqual(uninstall.call_args.kwargs["executable"],
                         "/opt/lidar2map/lidar2map")

    def test_uninstall_keeps_the_folder_the_program_runs_from(self):
        # Depuis la 1.55, rien n'empêche d'installer le programme là où le
        # lanceur d'une version <= 1.54 extrayait le sien.
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            targets = installation.chemins_desinstallation(
                systeme="Linux", home=home
            )
            for path, _label in targets:
                path.mkdir(parents=True)
            extraction = targets[0][0]
            programme = extraction / "lidar2map"
            programme.write_bytes(b"")
            messages = []
            ok = installation.desinstaller_lidar2map(
                systeme="Linux", home=home, executable=str(programme),
                ecrire=messages.append,
            )
            self.assertTrue(ok)
            self.assertTrue(programme.is_file())
            self.assertTrue(all(not path.exists() for path, _label in targets[1:]))
            self.assertTrue(any("kept, the running program lives there" in line
                                for line in messages))

    def test_frozen_uninstall_ignores_a_former_bundle_and_relaunches_nothing(self):
        # Un lidar2map_bundle.zip resté d'une version <= 1.54 (archive
        # décompressée par-dessus) ne doit ni être ouvert ni rien relancer.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake_executable = root / "lidar2map.exe"
            (root / "lidar2map_bundle.zip").write_bytes(b"not-opened")
            localappdata = root / "local"
            with mock.patch.object(sys, "frozen", True, create=True), \
                 mock.patch.object(sys, "executable", str(fake_executable)), \
                 mock.patch.object(sys, "argv", [str(fake_executable), "--desinstaller"]), \
                 mock.patch("platform.system", return_value="Windows"), \
                 mock.patch.dict(os.environ, {"LOCALAPPDATA": str(localappdata)}), \
                 mock.patch.object(
                     installation,
                     "desinstaller_lidar2map",
                     return_value=True,
                 ) as uninstall, \
                 mock.patch("zipfile.ZipFile") as zip_file, \
                 mock.patch("subprocess.Popen") as popen:
                with self.assertRaises(SystemExit) as raised:
                    runpy.run_path(str(ROOT / "lidar2map.py"), run_name="__launcher_test__")
            self.assertEqual(raised.exception.code, 0)
            uninstall.assert_called_once()
            self.assertEqual(uninstall.call_args.kwargs["systeme"], "Windows")
            self.assertEqual(
                uninstall.call_args.kwargs["localappdata"], str(localappdata)
            )
            zip_file.assert_not_called()
            popen.assert_not_called()


class FormerLauncherCleanupTests(unittest.TestCase):
    """Depuis la 1.55, le programme est livré tel quel : ce que le lanceur
    d'une version <= 1.54 a laissé est retiré au lancement."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.programme = self.root / "Programs" / "lidar2map"
        self.programme.mkdir(parents=True)
        self.exe = self.programme / "lidar2map.exe"
        self.exe.write_bytes(b"")
        self.extraction = self.root / "local" / "lidar2map"
        (self.extraction / "_internal").mkdir(parents=True)
        (self.extraction / ".bundle_sha").write_text("abc\n1", encoding="utf-8")

    def nettoyer(self, executable=None):
        return installation.nettoyer_ancienne_extraction(
            systeme="Windows", home=self.root / "home",
            localappdata=str(self.root / "local"),
            executable=executable or self.exe)

    def test_extraction_and_leftover_bundle_are_removed(self):
        zip_voisin = self.programme / "lidar2map_bundle.zip"
        zip_voisin.write_bytes(b"ancien bundle")
        corbeille = self.root / "local" / "lidar2map.ancienne-extraction"
        corbeille.mkdir()   # reste d'un nettoyage interrompu

        self.assertEqual(self.nettoyer(), [zip_voisin, self.extraction])

        self.assertFalse(zip_voisin.exists())
        self.assertFalse(self.extraction.exists())
        self.assertFalse(corbeille.exists())
        self.assertTrue(self.exe.exists())

    def test_folder_without_the_launcher_mark_is_left_alone(self):
        (self.extraction / ".bundle_sha").unlink()
        self.assertEqual(self.nettoyer(), [])
        self.assertTrue((self.extraction / "_internal").is_dir())

    def test_extraction_in_use_waits_for_the_next_launch(self):
        # Sous Windows, renommer un dossier dont un programme tourne encore
        # échoue : rien n'est retiré, le lancement suivant retentera.
        with mock.patch.object(installation.os, "rename",
                               side_effect=PermissionError(13, "in use")):
            self.assertEqual(self.nettoyer(), [])
        self.assertTrue((self.extraction / ".bundle_sha").is_file())

    def test_program_running_from_the_extraction_is_left_alone(self):
        interne = self.extraction / "lidar2map.exe"
        interne.write_bytes(b"")
        self.assertEqual(self.nettoyer(executable=interne), [])
        self.assertTrue((self.extraction / ".bundle_sha").is_file())


class IntegratedSmoketestTests(unittest.TestCase):
    def test_source_smoketest_runs_all_modes_and_validates_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "lidar2map.py"
            # Depuis la 1.54, la racine des sorties n'est plus le dossier du
            # script : les livrables sont cherchés sous celle qu'on transmet.
            sorties = root / "Documents" / "lidar2map"
            projects = sorties / "Projets" / "smoke"
            calls = []

            def run(command, **kwargs):
                calls.append((command, kwargs))
                if "--ignlidar" in command:
                    outputs = ["ign_lidar/smoke_multi_ombrage_z10-13.mbtiles"]
                elif "--ignraster" in command:
                    outputs = ["raster/smoke_planign_z12-14.mbtiles"]
                elif "--ignvecteur" in command:
                    outputs = ["ign_vecteur/smoke_ign_troncon_de_route.geojson.gz"]
                elif "--osm" in command:
                    outputs = ["osm_vecteur/smoke.map",
                               "osm_vecteur/smoke_osm_highway.geojson.gz"]
                else:
                    outputs = ["fusion/smoke_fusion.geojson.gz"]
                for relative in outputs:
                    output = projects / relative
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(b"ok")
                return SimpleNamespace(returncode=0)

            messages = []
            ok = smoketest.executer_smoketest(
                frozen=False,
                executable="python-test",
                script_path=script,
                environnement={"KEPT": "yes"},
                sorties=sorties,
                lancer=run,
                maintenant=lambda: 0.0,
                ecrire=messages.append,
            )
            self.assertTrue(ok)
            self.assertEqual(len(calls), 5)
            self.assertEqual(calls[0][0][:2], ["python-test", str(script.resolve())])
            self.assertTrue(all(call[1]["env"]["LIDAR2MAP_SKIP_HIST"] == "1"
                                for call in calls))
            self.assertIn("\n5/5 OK", messages)

    def test_smoketest_missing_outputs_and_fusion_skip_fail_the_run(self):
        with tempfile.TemporaryDirectory() as temp:
            messages = []
            ok = smoketest.executer_smoketest(
                frozen=False,
                executable="python-test",
                script_path=Path(temp) / "lidar2map.py",
                environnement={},
                sorties=Path(temp),
                lancer=lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
                maintenant=lambda: 0.0,
                ecrire=messages.append,
            )
            self.assertFalse(ok)
            self.assertTrue(any("(4 failed)" in line for line in messages))
            self.assertTrue(any("(1 skipped)" in line for line in messages))

    def test_smoketest_refuses_to_use_stale_outputs_after_failed_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            projects = work / "Projets" / "smoke"
            projects.mkdir(parents=True)
            launcher = mock.Mock()
            ok = smoketest.executer_smoketest(
                frozen=True,
                executable=str(work / "lidar2map.exe"),
                script_path=work / "lidar2map.py",
                environnement={"LIDAR2MAP_WORK_DIR": str(work)},
                sorties=work,
                lancer=launcher,
                supprimer_arbre=lambda *_args, **_kwargs: None,
                ecrire=lambda _message: None,
            )
            self.assertFalse(ok)
            launcher.assert_not_called()

    def test_smoketest_timeout_is_aggregated_and_other_modes_continue(self):
        with tempfile.TemporaryDirectory() as temp:
            calls = []

            def run(*_args, **_kwargs):
                calls.append(1)
                if len(calls) == 1:
                    raise subprocess.TimeoutExpired("smoke", 600)
                return SimpleNamespace(returncode=2)

            messages = []
            ok = smoketest.executer_smoketest(
                frozen=False,
                executable="python-test",
                script_path=Path(temp) / "lidar2map.py",
                environnement={},
                sorties=Path(temp),
                lancer=run,
                maintenant=lambda: 0.0,
                ecrire=messages.append,
            )
            self.assertFalse(ok)
            self.assertEqual(len(calls), 4)
            self.assertIn("  ✗ TIMEOUT (> 600s)", messages)

    def test_smoketest_facade_keeps_historical_signature(self):
        self.assertEqual(str(inspect.signature(L._executer_smoketest)), "()")
        with mock.patch.object(
            L._smoketest_impl, "executer_smoketest", return_value=True
        ) as execute:
            self.assertTrue(L._executer_smoketest())
        self.assertEqual(execute.call_args.kwargs["script_path"], L.__file__)
        # Les modes lancés écrivent sous la racine des sorties, que le
        # diagnostic doit donc connaître (Projets/smoke, voir _dossiers.py).
        self.assertEqual(execute.call_args.kwargs["sorties"],
                         L._dossiers_impl.DOSSIERS.dossier_sorties())


class LoggingHelpersTests(unittest.TestCase):
    def test_secret_redaction_covers_both_flags_and_cli_forms(self):
        command = "run --api-key secret-a --apikey=secret-b --zone-name public"
        self.assertEqual(
            logging_helpers.rediger_secrets(command),
            "run --api-key *** --apikey=*** --zone-name public",
        )
        self.assertEqual(logging_helpers.rediger_secrets(""), "")

    def test_duration_boundaries_keep_historical_format(self):
        self.assertEqual(logging_helpers.formater_duree(59.9), "59s")
        self.assertEqual(logging_helpers.formater_duree(60), "1m00s")
        self.assertEqual(logging_helpers.formater_duree(3661), "1h01m01s")

    def test_external_request_formatting(self):
        self.assertEqual(
            logging_helpers.formater_requete(["/tools/gdal.exe", "-of", "GTiff"]),
            "  $ gdal.exe -of GTiff",
        )
        self.assertEqual(
            logging_helpers.formater_requete("https://example.test", "GET"),
            "  → GET https://example.test",
        )

    def test_historical_logging_facades_keep_signatures_and_output(self):
        signature = inspect.signature(L._rediger_secrets)
        self.assertEqual(tuple(signature.parameters), ("texte",))
        self.assertIs(signature.parameters["texte"].annotation, str)
        self.assertIs(signature.return_annotation, str)
        self.assertEqual(str(inspect.signature(L._hms)), "(seconds)")
        self.assertEqual(str(inspect.signature(L._log_req)), "(url_or_cmd, label='')")
        with mock.patch("builtins.print") as printer:
            L._log_req("url", "GET")
        printer.assert_called_once_with("  → GET url", flush=True)


class LogActivationTests(unittest.TestCase):
    class FakeLogger:
        def __init__(self, path):
            self.path = Path(path)
            self._log = io.StringIO()
            self.closed = False

        def close(self):
            self.closed = True

    def _activate(self, *, frozen=False, dossier="/etat/lidar2map-data",
                  verifier=lambda _path: None):
        fake_sys = SimpleNamespace(
            frozen=frozen,
            executable="/bundle/lidar2map.exe",
            argv=["lidar2map.py", "--api-key", "secret"],
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            excepthook=None,
        )
        registered = []
        messages = []
        logger = log_activation.activer_log(
            sys_module=fake_sys,
            dossier=dossier,
            classe_logger=self.FakeLogger,
            rediger_secrets=logging_helpers.rediger_secrets,
            enregistrer_atexit=registered.append,
            verifier_dossier=verifier,
            ecrire=messages.append,
        )
        return logger, fake_sys, registered, messages

    def test_source_activation_installs_streams_header_hook_and_atexit(self):
        logger, fake_sys, registered, messages = self._activate()
        self.assertIs(fake_sys.stdout, logger)
        self.assertIs(fake_sys.stderr, logger)
        self.assertEqual(logger.path.parent, Path("/etat/lidar2map-data") / "logs")
        self.assertIn("Commande : lidar2map.py --api-key ***", logger._log.getvalue())
        self.assertEqual(len(registered), 1)
        registered[0]()
        self.assertTrue(logger.closed)
        fake_sys.excepthook(ValueError, ValueError("boom"), None)
        self.assertTrue(any("UNHANDLED EXCEPTION" in line for line in messages))

    def test_frozen_activation_logs_to_the_state_folder_too(self):
        # Jusqu'à la 1.53, l'exe figé journalisait à côté du lanceur
        # (LIDAR2MAP_WORK_DIR) : c'est désormais le dossier d'état, comme
        # depuis les sources.
        with mock.patch.dict(os.environ, {"LIDAR2MAP_WORK_DIR": "/work"}):
            logger, _fake_sys, _registered, _messages = self._activate(
                frozen=True, dossier="/autre/etat")
        self.assertEqual(logger.path.parent, Path("/autre/etat") / "logs")

    def test_inaccessible_directory_keeps_original_streams(self):
        logger, fake_sys, registered, messages = self._activate(
            verifier=lambda _path: (_ for _ in ()).throw(PermissionError("denied"))
        )
        self.assertIsNone(logger)
        self.assertIsInstance(fake_sys.stdout, io.StringIO)
        self.assertEqual(registered, [])
        self.assertEqual(
            messages, ["  WARNING: logs/ folder inaccessible, console log only."]
        )

    def test_activation_facade_keeps_empty_signature_and_dynamic_dependencies(self):
        self.assertEqual(str(inspect.signature(L._activer_log)), "()")
        with mock.patch.object(
            L._log_activation_impl, "activer_log", return_value="logger"
        ) as activate:
            self.assertEqual(L._activer_log(), "logger")
        self.assertIs(activate.call_args.kwargs["classe_logger"], L._TeeLogger)
        self.assertIs(activate.call_args.kwargs["rediger_secrets"], L._rediger_secrets)
        self.assertEqual(activate.call_args.kwargs["dossier"],
                         L._dossiers_impl.DOSSIERS.dossier_etat())

    def test_import_does_not_activate_the_file_log(self):
        # Chargé comme module (tests, outils), lidar2map ne détourne pas
        # sys.stdout et n'écrit aucun journal : seul le programme lancé le fait.
        self.assertNotIsInstance(sys.stdout, L._TeeLogger)


class RuntimePathTests(unittest.TestCase):
    def test_source_paths_are_derived_from_script_and_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "application" / "lidar2map.py"
            home = root / "profile"
            paths = runtime_paths.calculer_chemins(
                frozen=False,
                environnement={"LIDAR2MAP_WORK_DIR": str(root / "ignored")},
                executable=root / "python" / "python.exe",
                script_path=script,
                meipass=root / "ignored-bundle",
                home=home,
            )

        work, bundle, lidar_home, cache, production = paths
        self.assertEqual(work, script.resolve().parent)
        self.assertEqual(bundle, work)
        self.assertEqual(lidar_home, home / ".lidar2map")
        self.assertEqual(cache, work / "cache")
        self.assertEqual(production, work / "production")

    def test_frozen_paths_follow_the_program_and_meipass(self):
        # Depuis la 1.55, plus de lanceur : un LIDAR2MAP_WORK_DIR resté dans
        # l'environnement ne compte plus, seul le dossier du programme.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            paths = runtime_paths.calculer_chemins(
                frozen=True,
                environnement={"LIDAR2MAP_WORK_DIR": str(root / "ancien-lanceur")},
                executable=root / "bin" / "lidar2map.exe",
                script_path=root / "ignored.py",
                meipass=bundle,
                home=root / "home",
            )
            work = (root / "bin").resolve()

        self.assertEqual(paths[0], work)
        self.assertEqual(paths[1], bundle)
        self.assertEqual(paths[3], work / "cache")
        self.assertEqual(paths[4], work / "production")

    def test_frozen_paths_fall_back_to_executable_without_creating_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "missing" / "lidar2map.exe"
            paths = runtime_paths.calculer_chemins(
                frozen=True,
                environnement={},
                executable=executable,
                script_path=root / "ignored.py",
                home=root / "missing-home",
            )

            expected = executable.resolve().parent
            self.assertEqual(paths[0], expected)
            self.assertEqual(paths[1], expected)
            self.assertFalse(expected.exists())
            self.assertFalse(paths[2].exists())

    def test_explicit_output_root_replaces_the_program_folder(self):
        # Depuis la 1.54, la racine des sorties vient de _dossiers.py : le
        # bundle reste celui du programme, cache et production la suivent.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sorties = root / "Documents" / "lidar2map"
            work, bundle, tools, cache, production = runtime_paths.calculer_chemins(
                frozen=True,
                environnement={"LIDAR2MAP_WORK_DIR": str(root / "launcher")},
                executable=root / "bin" / "lidar2map.exe",
                script_path=root / "ignored.py",
                meipass=root / "bundle",
                home=root / "home",
                dossier_travail=sorties,
            )
        self.assertEqual(work, sorties)
        self.assertEqual(bundle, root / "bundle")
        self.assertEqual(tools, root / "home" / ".lidar2map")
        self.assertEqual(cache, sorties / "cache")
        self.assertEqual(production, sorties / "production")

    def test_program_folder_is_where_versions_before_1_54_kept_everything(self):
        # Le programme est livré tel quel depuis la 1.55 : un reste de
        # LIDAR2MAP_WORK_DIR (posé par le lanceur d'avant) est ignoré.
        self.assertEqual(
            runtime_paths.dossier_programme(
                frozen=True, environnement={"LIDAR2MAP_WORK_DIR": "/launcher"},
                executable="/Programs/lidar2map/lidar2map.exe", script_path="/ignored.py"),
            Path("/Programs/lidar2map/lidar2map.exe").resolve().parent)
        # Sous macOS, le dossier qui contient le .app, pas Contents/MacOS.
        self.assertEqual(
            runtime_paths.dossier_programme(
                frozen=True, environnement={},
                executable="/Applications/LIDAR2MAP.app/Contents/MacOS/lidar2map",
                script_path="/ignored.py"),
            Path("/Applications").resolve())
        self.assertEqual(
            runtime_paths.dossier_programme(
                frozen=False, environnement={"LIDAR2MAP_WORK_DIR": "/ignored"},
                executable="/python/python.exe", script_path=ROOT / "lidar2map.py"),
            ROOT)

    def test_state_preparation_takes_the_program_folder_and_never_blocks(self):
        with mock.patch.object(L._dossiers_impl.DOSSIERS, "preparer_etat",
                               return_value=[]) as preparer:
            L._preparer_etat()
        self.assertEqual(preparer.call_args.args[0], ROOT)
        # Verrou tenu trop longtemps, disque refusé : le lancement continue,
        # la reprise sera retentée au suivant.
        sortie = io.StringIO()
        with mock.patch.object(L._dossiers_impl.DOSSIERS, "preparer_etat",
                               side_effect=TimeoutError("verrou occupé")), \
                contextlib.redirect_stdout(sortie):
            L._preparer_etat()
        self.assertIn("postponed", sortie.getvalue())

    def test_platform_indicators_are_exact_and_exclusive(self):
        self.assertEqual(
            runtime_paths.indicateurs_plateforme("Windows"), (True, False, False)
        )
        self.assertEqual(
            runtime_paths.indicateurs_plateforme("Linux"), (False, True, False)
        )
        self.assertEqual(
            runtime_paths.indicateurs_plateforme("Darwin"), (False, False, True)
        )
        self.assertEqual(
            runtime_paths.indicateurs_plateforme("FreeBSD"), (False, False, False)
        )

    def test_main_source_constants_use_the_extracted_policy(self):
        # Les suites tournent avec un LIDAR2MAP_HOME temporaire (en tête de
        # ce fichier) : état et sorties y sont regroupés, jamais dans les
        # dossiers réels de l'utilisateur ni dans les sources.
        home = Path(os.environ["LIDAR2MAP_HOME"]).resolve()
        self.assertEqual(L.DOSSIER_ETAT, home)
        self.assertEqual(L.DOSSIER_TRAVAIL, home)
        self.assertEqual(L.BUNDLE_DIR, ROOT)
        self.assertEqual(L.DOSSIER_OUTILS, Path.home() / ".lidar2map")
        self.assertEqual(L.DOSSIER_CACHE, home / "cache")
        self.assertEqual(L.DOSSIER_PRODUCTION, home / "production")
        self.assertEqual(L._PREFS_PATH, home / "preferences.json")
        self.assertEqual(L._HISTORIQUE_PATH, home / "historique.json")
        self.assertEqual(L._apikey_env_path, home / "lidar2map.env")
        self.assertEqual(
            (L.WINDOWS, L.LINUX, L.MACOS),
            runtime_paths.indicateurs_plateforme(L.platform.system()),
        )


class DiskGuardTests(unittest.TestCase):
    def test_probe_uses_first_existing_parent_and_converts_bytes_to_gib(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "future" / "chunk"
            usage = SimpleNamespace(free=7 * 1024 ** 3)
            with mock.patch.object(L.shutil, "disk_usage", return_value=usage) as probe:
                self.assertEqual(L._espace_libre_go(target), 7.0)
        probe.assert_called_once_with(root)

    def test_probe_failure_is_non_blocking(self):
        with mock.patch.object(L.shutil, "disk_usage", side_effect=OSError("probe")):
            self.assertEqual(L._espace_libre_go(Path.cwd()), float("inf"))

    def test_disabled_guard_does_not_probe_or_exit(self):
        probe = mock.Mock(side_effect=AssertionError("sonde interdite"))
        writer = mock.Mock()
        quitter = mock.Mock()
        disk_guard.garder_disque(
            "unused", 0, "001x001", 0, 4,
            sonde=probe, exit_code=3, ecrire=writer, quitter=quitter,
        )
        probe.assert_not_called()
        writer.assert_not_called()
        quitter.assert_not_called()

    def test_sufficient_space_continues_silently(self):
        writer = mock.Mock()
        quitter = mock.Mock()
        disk_guard.garder_disque(
            "target", 5, "001x001", 1, 4,
            sonde=lambda _path: 5.0,
            exit_code=3,
            ecrire=writer,
            quitter=quitter,
        )
        writer.assert_not_called()
        quitter.assert_not_called()

    def test_historical_guard_facade_reports_progress_and_exits_three(self):
        self.assertEqual(str(inspect.signature(L._espace_libre_go)), "(chemin) -> float")
        self.assertEqual(
            str(inspect.signature(L._garde_disque)),
            "(chemin, seuil_go: float, cle: str, nb_ok: int, n_total: int)",
        )
        with mock.patch.object(L, "_espace_libre_go", return_value=2.25) as probe, \
             mock.patch("builtins.print") as writer, \
             mock.patch.object(L.sys, "exit", side_effect=SystemExit(3)) as quitter, \
             self.assertRaises(SystemExit) as raised:
            L._garde_disque("target", 5.0, "002x003", 4, 9)

        self.assertEqual(raised.exception.code, L.EXIT_DISK_LOW)
        probe.assert_called_once_with("target")
        quitter.assert_called_once_with(L.EXIT_DISK_LOW)
        messages = [call.args[0] for call in writer.call_args_list]
        self.assertIn("2.2 GB free < 5 GB threshold", messages[0])
        self.assertIn("chunk 002x003: 4/9 chunks done", messages[1])


class SystemEnvironmentRestoreTests(unittest.TestCase):
    """Programmes du système lancés depuis le binaire Linux (systemctl,
    xdg-open) : LD_LIBRARY_PATH d'origine, pas celui que préfixe PyInstaller.
    La fonction est celle de nico579_commons.environnement, et ses
    comportements y sont éprouvés ; il ne reste à vérifier ici que le câblage
    de lidar2map.py. tests/exe_smoke.py le vérifie aussi sur le vrai binaire."""

    def test_called_before_any_process_is_launched(self):
        # Tout processus lancé ensuite (exécution distante en tête, dès le
        # dispatch précoce) doit hériter d'un environnement déjà rétabli, sans
        # le préfixe que PyInstaller pose sur LD_LIBRARY_PATH.
        source = (ROOT / "lidar2map.py").read_text(encoding="utf-8")
        appel = source.index("environnement.retablir_environnement_systeme()")
        self.assertLess(appel, source.index("# EXÉCUTION DISTANTE (rlidar2map_CLI"))

    def test_only_in_the_executable_where_the_library_is_embedded(self):
        # Depuis les sources, la bibliothèque peut ne pas être installée avant
        # le bootstrap, et la fonction n'y fait rien : l'import est gardé.
        source = (ROOT / "lidar2map.py").read_text(encoding="utf-8")
        appel = source.index("environnement.retablir_environnement_systeme()")
        garde = source.rindex('if getattr(sys, "frozen", False):', 0, appel)
        self.assertLess(appel - garde, 400)

    def test_the_local_copy_no_longer_exists(self):
        self.assertFalse(hasattr(installation, "retablir_environnement_systeme"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
