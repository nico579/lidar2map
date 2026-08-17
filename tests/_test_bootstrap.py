"""Contrats hors reseau du bootstrap precoce de lidar2map.

Le module principal execute son bootstrap des l'import. Le runner impose le
mode ``none`` pour cet import, puis chaque test appelle explicitement la
fonction visee avec ses effets externes simules (pip, venv, exec et sorties).
"""

from __future__ import annotations

import ast
import builtins
import contextlib
import importlib.util
import inspect
import io
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lidar2map as L  # noqa: E402
import _bootstrap_policy as bootstrap_policy  # noqa: E402
import _bootstrap_runtime as bootstrap_runtime  # noqa: E402
import _bootstrap_tls as bootstrap_tls  # noqa: E402
import _smoketest as smoketest  # noqa: E402
import _logging_helpers as logging_helpers  # noqa: E402
import _log_activation as log_activation  # noqa: E402
import _runtime_paths as runtime_paths  # noqa: E402
import _disk_guard as disk_guard  # noqa: E402


class BootstrapModeTests(unittest.TestCase):
    def _resolve(self, argv, env=None):
        with mock.patch.object(L.sys, "argv", list(argv)), mock.patch.dict(
            L.os.environ,
            env or {},
            clear=True,
        ):
            mode = L._resoudre_mode_bootstrap()
            remaining = list(L.sys.argv)
        return mode, remaining

    def test_default_and_environment_modes(self):
        self.assertEqual(self._resolve(["lidar2map.py"]),
                         ("auto", ["lidar2map.py"]))
        self.assertEqual(
            self._resolve(
                ["lidar2map.py"],
                {"LIDAR2MAP_BOOTSTRAP": " PIP "},
            ),
            ("pip", ["lidar2map.py"]),
        )
        self.assertEqual(
            self._resolve(
                ["lidar2map.py"],
                {"LIDAR2MAP_BOOTSTRAP": "invalide"},
            ),
            ("auto", ["lidar2map.py"]),
        )

    def test_cli_forms_override_environment_and_are_consumed(self):
        mode, argv = self._resolve(
            [
                "lidar2map.py",
                "--bootstrap=auto",
                "--zone-name",
                "zone",
                "--bootstrap",
                "none",
            ],
            {"LIDAR2MAP_BOOTSTRAP": "pip"},
        )
        self.assertEqual(mode, "none")
        self.assertEqual(argv, ["lidar2map.py", "--zone-name", "zone"])

    def test_valid_cli_cleanup_mutates_argv_in_place(self):
        argv = [
            "lidar2map.py",
            "--bootstrap=pip",
            "--zone-name",
            "zone",
            "--no-venv",
            "--lidar",
        ]
        with mock.patch.object(L.sys, "argv", argv), mock.patch.dict(
            L.os.environ,
            {},
            clear=True,
        ):
            original_id = id(L.sys.argv)
            mode = L._resoudre_mode_bootstrap()
            self.assertEqual(id(L.sys.argv), original_id)
        self.assertEqual(mode, "pip")
        self.assertEqual(
            argv,
            ["lidar2map.py", "--zone-name", "zone", "--lidar"],
        )

    def test_invalid_cli_values_fail_without_mutating_argv(self):
        cases = (
            ["lidar2map.py", "--bootstrap=invalide", "--lidar"],
            ["lidar2map.py", "--bootstrap=", "--lidar"],
            ["lidar2map.py", "--bootstrap", "invalide", "--lidar"],
            ["lidar2map.py", "--bootstrap"],
            ["lidar2map.py", "--bootstrap", "--lidar"],
            [
                "lidar2map.py",
                "--bootstrap=none",
                "--lidar",
                "--bootstrap",
                "invalide",
            ],
        )
        for initial in cases:
            with self.subTest(argv=initial):
                argv = list(initial)
                stderr = io.StringIO()
                with mock.patch.object(L.sys, "argv", argv), mock.patch.dict(
                    L.os.environ,
                    {"LIDAR2MAP_BOOTSTRAP": "none"},
                    clear=True,
                ), contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as raised:
                        L._resoudre_mode_bootstrap()
                    self.assertIs(L.sys.argv, argv)
                self.assertEqual(raised.exception.code, 2)
                self.assertEqual(argv, initial)
                self.assertIn("--bootstrap", stderr.getvalue())

    def test_legacy_aliases_are_consumed(self):
        cases = (
            ("--no-bootstrap", "none"),
            ("--venv", "auto"),
            ("--no-venv", "pip"),
        )
        for flag, expected in cases:
            with self.subTest(flag=flag):
                self.assertEqual(
                    self._resolve(["lidar2map.py", flag, "--lidar"]),
                    (expected, ["lidar2map.py", "--lidar"]),
                )

    def test_legacy_alias_precedence_remains_fixed(self):
        for aliases in (
            ["--no-venv", "--venv", "--no-bootstrap"],
            ["--no-bootstrap", "--venv", "--no-venv"],
        ):
            with self.subTest(aliases=aliases):
                self.assertEqual(
                    self._resolve(
                        ["lidar2map.py", "--bootstrap=none", *aliases, "--lidar"]
                    ),
                    ("pip", ["lidar2map.py", "--lidar"]),
                )

    def test_help_prints_bootstrap_documentation_and_exits_zero(self):
        output = io.StringIO()
        argv = ["lidar2map.py", "--help-bootstrap"]
        with mock.patch.object(L.sys, "argv", argv), mock.patch.dict(
            L.os.environ,
            {},
            clear=True,
        ), contextlib.redirect_stdout(output), self.assertRaises(
            SystemExit,
        ) as raised:
            L._resoudre_mode_bootstrap()
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--bootstrap=auto", output.getvalue())

    def test_help_precedes_invalid_cli_and_leaves_argv_untouched(self):
        output = io.StringIO()
        argv = ["lidar2map.py", "--bootstrap=invalide", "--help-bootstrap"]
        with mock.patch.object(L.sys, "argv", argv), mock.patch.dict(
            L.os.environ,
            {},
            clear=True,
        ), contextlib.redirect_stdout(output), self.assertRaises(
            SystemExit,
        ) as raised:
            L._resoudre_mode_bootstrap()
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(
            argv,
            ["lidar2map.py", "--bootstrap=invalide", "--help-bootstrap"],
        )
        self.assertIn("--bootstrap=auto", output.getvalue())


class BootstrapOrchestrationTests(unittest.TestCase):
    def _orchestrate(self, mode):
        events = []
        with mock.patch.object(
            L,
            "_resoudre_mode_bootstrap",
            side_effect=lambda: events.append("resolve") or mode,
        ), mock.patch.object(
            L,
            "_bootstrap_venv_si_besoin_avec_mode",
            side_effect=lambda value: events.append(("venv", value)),
        ), mock.patch.object(
            L,
            "_bootstrap_pip",
            side_effect=lambda: events.append("pip"),
        ), mock.patch.object(
            L,
            "_installer_deps",
            side_effect=lambda: events.append("deps"),
        ), mock.patch.object(
            L,
            "_restaurer_tls_strict",
            side_effect=lambda: events.append("tls"),
        ):
            L._bootstrap_environnement()
        return events

    def test_orchestrator_routes_each_mode_in_order(self):
        self.assertEqual(
            self._orchestrate("auto"),
            ["resolve", ("venv", "auto"), "deps", "tls"],
        )
        self.assertEqual(
            self._orchestrate("pip"),
            ["resolve", ("venv", "pip"), "pip", "deps", "tls"],
        )
        self.assertEqual(
            self._orchestrate("none"),
            ["resolve", ("venv", "none")],
        )

    def test_orchestrator_stops_at_the_first_failed_stage(self):
        expectations = {
            "resolve": ["resolve"],
            "venv": ["resolve", "venv"],
            "pip": ["resolve", "venv", "pip"],
            "deps": ["resolve", "venv", "pip", "deps"],
            "tls": ["resolve", "venv", "pip", "deps", "tls"],
        }
        for failed, expected in expectations.items():
            with self.subTest(failed=failed):
                events = []

                def stage(name, result=None):
                    def run(*_args):
                        events.append(name)
                        if name == failed:
                            raise RuntimeError(name)
                        return result

                    return run

                with mock.patch.object(
                    L,
                    "_resoudre_mode_bootstrap",
                    side_effect=stage("resolve", "pip"),
                ), mock.patch.object(
                    L,
                    "_bootstrap_venv_si_besoin_avec_mode",
                    side_effect=stage("venv"),
                ), mock.patch.object(
                    L,
                    "_bootstrap_pip",
                    side_effect=stage("pip"),
                ), mock.patch.object(
                    L,
                    "_installer_deps",
                    side_effect=stage("deps"),
                ), mock.patch.object(
                    L,
                    "_restaurer_tls_strict",
                    side_effect=stage("tls"),
                ), self.assertRaisesRegex(RuntimeError, failed):
                    L._bootstrap_environnement()
                self.assertEqual(events, expected)

    def test_frozen_bundle_cleans_bootstrap_flags_then_bypasses_runtime(self):
        argv = ["lidar2map.py", "--bootstrap=none", "--lidar"]
        resolver = mock.Mock(wraps=L._resoudre_mode_bootstrap)
        runtime = (
            "_bootstrap_venv_si_besoin_avec_mode",
            "_bootstrap_pip",
            "_installer_deps",
            "_restaurer_tls_strict",
        )
        patches = [mock.patch.object(L, name) for name in runtime]
        with mock.patch.object(L.sys, "frozen", True, create=True), \
             mock.patch.object(L.sys, "argv", argv), \
             mock.patch.dict(L.os.environ, {}, clear=True), \
             mock.patch.object(L, "_resoudre_mode_bootstrap", resolver):
            mocks = [patcher.start() for patcher in patches]
            try:
                L._bootstrap_environnement()
            finally:
                for patcher in reversed(patches):
                    patcher.stop()
        resolver.assert_called_once_with()
        self.assertEqual(argv, ["lidar2map.py", "--lidar"])
        for collaborator in mocks:
            collaborator.assert_not_called()

    def test_frozen_bundle_still_handles_bootstrap_help(self):
        argv = ["lidar2map.py", "--help-bootstrap"]
        output = io.StringIO()
        with mock.patch.object(L.sys, "frozen", True, create=True), \
             mock.patch.object(L.sys, "argv", argv), \
             mock.patch.dict(L.os.environ, {}, clear=True), \
             contextlib.redirect_stdout(output), \
             self.assertRaises(SystemExit) as raised:
            L._bootstrap_environnement()
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--bootstrap=auto", output.getvalue())

    def test_frozen_bundle_rejects_invalid_bootstrap_before_runtime(self):
        argv = ["lidar2map.py", "--bootstrap=invalide", "--lidar"]
        stderr = io.StringIO()
        with mock.patch.object(L.sys, "frozen", True, create=True), \
             mock.patch.object(L.sys, "argv", argv), \
             mock.patch.dict(L.os.environ, {}, clear=True), \
             mock.patch.object(
                 L,
                 "_bootstrap_venv_si_besoin_avec_mode",
             ) as venv, \
             mock.patch.object(L, "_bootstrap_pip") as pip, \
             mock.patch.object(L, "_installer_deps") as deps, \
             mock.patch.object(L, "_restaurer_tls_strict") as tls, \
             contextlib.redirect_stderr(stderr), \
             self.assertRaises(SystemExit) as raised:
            L._bootstrap_environnement()
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(argv, ["lidar2map.py", "--bootstrap=invalide", "--lidar"])
        self.assertIn("--bootstrap", stderr.getvalue())
        for collaborator in (venv, pip, deps, tls):
            collaborator.assert_not_called()

    def test_mode_wrapper_removes_temporary_environment_on_exception(self):
        with mock.patch.dict(L.os.environ, {}, clear=True), mock.patch.object(
            L,
            "_bootstrap_venv_si_besoin",
            side_effect=RuntimeError("boom"),
        ), self.assertRaisesRegex(RuntimeError, "boom"):
            L._bootstrap_venv_si_besoin_avec_mode("pip")
        self.assertNotIn("LIDAR2MAP_BOOTSTRAP", L.os.environ)

    def test_mode_wrapper_exposes_mode_only_during_call(self):
        observed = []

        def probe():
            observed.append(L.os.environ.get("LIDAR2MAP_BOOTSTRAP"))

        with mock.patch.dict(L.os.environ, {}, clear=True), mock.patch.object(
            L,
            "_bootstrap_venv_si_besoin",
            side_effect=probe,
        ):
            L._bootstrap_venv_si_besoin_avec_mode("auto")
            self.assertNotIn("LIDAR2MAP_BOOTSTRAP", L.os.environ)
        self.assertEqual(observed, ["auto"])

    def test_mode_wrapper_intentionally_discards_a_previous_environment_value(self):
        observed = []

        def probe():
            observed.append(L.os.environ.get("LIDAR2MAP_BOOTSTRAP"))

        with mock.patch.dict(
            L.os.environ,
            {"LIDAR2MAP_BOOTSTRAP": "none"},
            clear=True,
        ), mock.patch.object(
            L,
            "_bootstrap_venv_si_besoin",
            side_effect=probe,
        ):
            L._bootstrap_venv_si_besoin_avec_mode("pip")
            self.assertNotIn("LIDAR2MAP_BOOTSTRAP", L.os.environ)
        self.assertEqual(observed, ["pip"])

    def test_mode_wrapper_discards_previous_value_when_the_engine_fails(self):
        with mock.patch.dict(
            L.os.environ,
            {"LIDAR2MAP_BOOTSTRAP": "none"},
            clear=True,
        ), mock.patch.object(
            L,
            "_bootstrap_venv_si_besoin",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                L._bootstrap_venv_si_besoin_avec_mode("auto")
            self.assertNotIn("LIDAR2MAP_BOOTSTRAP", L.os.environ)


class BootstrapControlModuleTests(unittest.TestCase):
    def test_early_bootstrap_modules_parse_with_python_39_grammar(self):
        for name in (
            "_bootstrap_policy.py",
            "_bootstrap_runtime.py",
            "_bootstrap_tls.py",
        ):
            with self.subTest(module=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                ast.parse(source, filename=name, feature_version=(3, 9))

    def test_policy_resolution_does_not_mutate_its_inputs(self):
        argv = [
            "lidar2map.py",
            "--bootstrap",
            "none",
            "--zone-name",
            "zone",
        ]
        environnement = {"LIDAR2MAP_BOOTSTRAP": "pip", "AUTRE": "valeur"}
        argv_initial = list(argv)
        environnement_initial = dict(environnement)

        resolution = bootstrap_policy.resoudre_mode_bootstrap(
            argv,
            environnement,
        )

        self.assertEqual(resolution.mode, "none")
        self.assertEqual(
            resolution.argv,
            ("lidar2map.py", "--zone-name", "zone"),
        )
        self.assertFalse(resolution.aide)
        self.assertEqual(argv, argv_initial)
        self.assertEqual(environnement, environnement_initial)

    def test_policy_rejects_invalid_cli_without_mutating_inputs(self):
        argv = ["lidar2map.py", "--bootstrap", "--lidar"]
        environnement = {"LIDAR2MAP_BOOTSTRAP": "auto"}
        with self.assertRaisesRegex(ValueError, "--bootstrap"):
            bootstrap_policy.resoudre_mode_bootstrap(argv, environnement)
        self.assertEqual(argv, ["lidar2map.py", "--bootstrap", "--lidar"])
        self.assertEqual(environnement, {"LIDAR2MAP_BOOTSTRAP": "auto"})


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


class BootstrapRuntimeFacadeTests(unittest.TestCase):
    def test_runtime_module_and_historical_facade_signatures_are_stable(self):
        self.assertIs(L._bootstrap_policy_impl, bootstrap_policy)
        self.assertIs(L._bootstrap_runtime_impl, bootstrap_runtime)
        expected = {
            L._resoudre_mode_bootstrap: "()",
            L._verifier_venv_linux: "()",
            L._bootstrap_venv_si_besoin: "()",
            L._relancer_dans_venv: "(venv_python, is_windows)",
            L._bootstrap_pip: "()",
            L._installer_deps: "()",
            L._bootstrap_environnement: "()",
            L._bootstrap_venv_si_besoin_avec_mode: "(mode)",
        }
        for facade, signature in expected.items():
            with self.subTest(facade=facade.__name__):
                self.assertEqual(str(inspect.signature(facade)), signature)

    def test_historical_facades_keep_runtime_documentation(self):
        pairs = (
            (L._verifier_venv_linux, bootstrap_runtime.verifier_venv_linux),
            (
                L._bootstrap_venv_si_besoin,
                bootstrap_runtime.bootstrap_venv_si_besoin,
            ),
            (L._relancer_dans_venv, bootstrap_runtime.relancer_dans_venv),
            (L._bootstrap_pip, bootstrap_runtime.bootstrap_pip),
            (L._installer_deps, bootstrap_runtime.installer_deps),
            (
                L._bootstrap_environnement,
                bootstrap_runtime.orchestrer_bootstrap,
            ),
            (
                L._bootstrap_venv_si_besoin_avec_mode,
                bootstrap_runtime.bootstrap_venv_avec_mode,
            ),
        )
        for facade, implementation in pairs:
            with self.subTest(facade=facade.__name__):
                self.assertEqual(facade.__doc__, implementation.__doc__)


class BootstrapRelaunchTests(unittest.TestCase):
    def test_unix_relaunch_replaces_process_with_exact_argv(self):
        executable = Path("/tmp/lidar-venv/bin/python")
        with mock.patch.object(
            L.sys,
            "argv",
            ["lidar2map.py", "--lidar", "--zone-name", "zone"],
        ), mock.patch.object(L.os, "execv") as execv:
            L._relancer_dans_venv(executable, False)
        execv.assert_called_once_with(
            str(executable),
            [str(executable), "lidar2map.py", "--lidar", "--zone-name", "zone"],
        )

    def test_windows_relaunch_waits_for_child_and_propagates_return_code(self):
        executable = Path("C:/venv/Scripts/python.exe")
        stdout = SimpleNamespace(flush=mock.Mock())
        stderr = SimpleNamespace(flush=mock.Mock())
        stdin = object()
        completed = SimpleNamespace(returncode=17)
        with mock.patch.object(L.sys, "argv", ["lidar2map.py", "--lidar"]), \
             mock.patch.object(L.sys, "stdout", stdout), \
             mock.patch.object(L.sys, "stderr", stderr), \
             mock.patch.object(L.sys, "stdin", stdin), \
             mock.patch.object(L.subprocess, "run", return_value=completed) as run, \
             self.assertRaises(SystemExit) as raised:
            L._relancer_dans_venv(executable, True)
        self.assertEqual(raised.exception.code, 17)
        stdout.flush.assert_called_once_with()
        stderr.flush.assert_called_once_with()
        run.assert_called_once_with(
            [str(executable), "lidar2map.py", "--lidar"],
            stdout=stdout,
            stderr=stderr,
            stdin=stdin,
        )

    def test_windows_keyboard_interrupt_maps_to_exit_130(self):
        stream = SimpleNamespace(flush=mock.Mock())
        with mock.patch.object(L.sys, "argv", ["lidar2map.py"]), \
             mock.patch.object(L.sys, "stdout", stream), \
             mock.patch.object(L.sys, "stderr", stream), \
             mock.patch.object(L.subprocess, "run", side_effect=KeyboardInterrupt), \
             self.assertRaises(SystemExit) as raised:
            L._relancer_dans_venv(Path("python.exe"), True)
        self.assertEqual(raised.exception.code, 130)


class BootstrapDependencyTests(unittest.TestCase):
    def test_gui_dependencies_for_each_platform(self):
        expected = {
            "Darwin": (
                [
                    "pyobjc-framework-WebKit",
                    "pyobjc-framework-Cocoa",
                    "PyQt6",
                    "PyQt6-WebEngine",
                    "qtpy",
                ],
                [],
            ),
            "Linux": (["PyQt6", "PyQt6-WebEngine", "qtpy"], []),
            "Windows": (["PyQt6", "PyQt6-WebEngine", "qtpy"], []),
            "Plan9": (["PyQt6", "PyQt6-WebEngine", "qtpy"], []),
        }
        for system_name, dependencies in expected.items():
            with self.subTest(system=system_name), mock.patch.object(
                L.platform,
                "system",
                return_value=system_name,
            ):
                self.assertEqual(L._gui_deps_plateforme(), dependencies)

    def test_gui_policy_returns_fresh_lists_and_facade_reads_platform_late(self):
        self.assertEqual(str(inspect.signature(L._gui_deps_plateforme)), "()")
        self.assertEqual(
            str(inspect.signature(bootstrap_policy.dependances_gui_plateforme)),
            "(systeme: 'str') -> 'tuple[list[str], list[str]]'",
        )
        self.assertIs(
            L._dependances_gui_plateforme,
            bootstrap_policy.dependances_gui_plateforme,
        )
        first = bootstrap_policy.dependances_gui_plateforme("Linux")
        first[0].append("local-only")
        self.assertEqual(
            bootstrap_policy.dependances_gui_plateforme("Linux"),
            (["PyQt6", "PyQt6-WebEngine", "qtpy"], []),
        )
        with mock.patch.object(
            L.platform,
            "system",
            side_effect=RuntimeError("platform probe failed"),
        ), self.assertRaisesRegex(RuntimeError, "platform probe failed"):
            L._gui_deps_plateforme()

    def test_main_import_by_spec_works_from_isolated_cwd(self):
        app_literal = repr(str(ROOT / "lidar2map.py"))
        code = (
            "import importlib.util, os\n"
            "os.environ['LIDAR2MAP_BOOTSTRAP'] = 'none'\n"
            f"spec = importlib.util.spec_from_file_location('isolated_lidar2map', {app_literal})\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "assert module._gui_deps_plateforme()[0]\n"
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

    def test_bootstrap_pip_is_noop_when_pip_exists(self):
        with mock.patch.object(
            L.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0),
        ) as run:
            L._bootstrap_pip()
        run.assert_called_once_with(
            [L.sys.executable, "-m", "pip", "--version"],
            capture_output=True,
        )

    def test_bootstrap_pip_uses_ensurepip_when_missing(self):
        ensurepip = SimpleNamespace(bootstrap=mock.Mock())
        with mock.patch.object(
            L.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=1),
        ), mock.patch.dict(sys.modules, {"ensurepip": ensurepip}):
            L._bootstrap_pip()
        ensurepip.bootstrap.assert_called_once_with(upgrade=True)

    def test_bootstrap_pip_failure_exits_one(self):
        ensurepip = SimpleNamespace(
            bootstrap=mock.Mock(side_effect=RuntimeError("ensurepip failed")),
        )
        with mock.patch.object(
            L.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=1),
        ), mock.patch.dict(sys.modules, {"ensurepip": ensurepip}), \
             contextlib.redirect_stdout(io.StringIO()), \
             self.assertRaises(SystemExit) as raised:
            L._bootstrap_pip()
        self.assertEqual(raised.exception.code, 1)

    def test_install_dependencies_is_noop_when_everything_is_present(self):
        with mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(importlib.util, "find_spec", return_value=object()), \
             mock.patch.object(L.subprocess, "run") as run:
            L._installer_deps()
        run.assert_not_called()

    def test_linux_venv_guard_exits_when_module_and_command_are_missing(self):
        real_import = builtins.__import__

        def importing(name, *args, **kwargs):
            if name == "venv":
                raise ImportError("forced missing venv")
            return real_import(name, *args, **kwargs)

        output = io.StringIO()
        with mock.patch.object(L.platform, "system", return_value="Linux"), \
             mock.patch.object(
                 L.subprocess,
                 "run",
                 return_value=SimpleNamespace(returncode=1),
             ) as run, mock.patch.object(
                 builtins,
                 "__import__",
                 side_effect=importing,
             ), contextlib.redirect_stdout(output), self.assertRaises(
                 SystemExit,
             ) as raised:
            L._verifier_venv_linux()
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("python3-venv", output.getvalue())
        run.assert_called_once()

    def test_venv_guard_is_noop_outside_linux(self):
        with mock.patch.object(L.platform, "system", return_value="Windows"), \
             mock.patch.object(L.subprocess, "run") as run:
            L._verifier_venv_linux()
        run.assert_not_called()

    def test_linux_venv_guard_accepts_working_command_fallback(self):
        real_import = builtins.__import__

        def importing(name, *args, **kwargs):
            if name == "venv":
                raise ImportError("forced missing import")
            return real_import(name, *args, **kwargs)

        with mock.patch.object(L.platform, "system", return_value="Linux"), \
             mock.patch.object(
                 L.subprocess,
                 "run",
                 return_value=SimpleNamespace(returncode=0),
             ) as run, mock.patch.object(
                 builtins,
                 "__import__",
                 side_effect=importing,
             ):
            L._verifier_venv_linux()
        run.assert_called_once_with(
            [L.sys.executable, "-m", "venv", "--help"],
            capture_output=True,
        )

    def test_install_dependencies_uses_standard_strategy_first(self):
        def find_spec(name):
            return None if name == "PIL" else object()

        completed = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(importlib.util, "find_spec", side_effect=find_spec), \
             mock.patch.object(L.sys, "prefix", "system"), \
             mock.patch.object(L.sys, "base_prefix", "system"), \
             mock.patch.object(L.subprocess, "run", return_value=completed) as run:
            L._installer_deps()
        command = run.call_args.args[0]
        self.assertEqual(command[-1], "Pillow")
        self.assertNotIn("--user", command)
        self.assertNotIn("--break-system-packages", command)
        self.assertEqual(run.call_count, 1)

    def test_install_dependencies_tries_three_system_strategies(self):
        def find_spec(name):
            return None if name == "PIL" else object()

        completed = SimpleNamespace(returncode=1, stdout="", stderr="denied")
        with mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(importlib.util, "find_spec", side_effect=find_spec), \
             mock.patch.object(L.sys, "prefix", "system"), \
             mock.patch.object(L.sys, "base_prefix", "system"), \
             mock.patch.object(L.subprocess, "run", return_value=completed) as run, \
             contextlib.redirect_stdout(io.StringIO()), \
             self.assertRaises(SystemExit) as raised:
            L._installer_deps()
        self.assertEqual(raised.exception.code, 1)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(commands), 3)
        self.assertNotIn("--break-system-packages", commands[0])
        self.assertIn("--break-system-packages", commands[1])
        self.assertIn("--user", commands[2])

    def test_optional_dependency_failure_is_non_fatal(self):
        def find_spec(name):
            return None if name == "osmium" else object()

        completed = SimpleNamespace(returncode=1, stdout="", stderr="denied")
        with mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(importlib.util, "find_spec", side_effect=find_spec), \
             mock.patch.object(L.sys, "prefix", "system"), \
             mock.patch.object(L.sys, "base_prefix", "system"), \
             mock.patch.object(L.subprocess, "run", return_value=completed) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            L._installer_deps()
        self.assertEqual(run.call_count, 3)

    def test_system_retry_installs_critical_dependencies_without_optionals(self):
        def find_spec(name):
            return None if name in {"PIL", "osmium"} else object()

        real_import = builtins.__import__

        def importing(name, *args, **kwargs):
            if name == "PIL":
                return object()
            return real_import(name, *args, **kwargs)

        failed = SimpleNamespace(returncode=1, stdout="", stderr="denied")
        succeeded = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(importlib.util, "find_spec", side_effect=find_spec), \
             mock.patch.object(builtins, "__import__", side_effect=importing), \
             mock.patch.object(L.sys, "prefix", "system"), \
             mock.patch.object(L.sys, "base_prefix", "system"), \
             mock.patch.object(
                 L.subprocess,
                 "run",
                 side_effect=[failed, failed, failed, succeeded],
             ) as run, contextlib.redirect_stdout(io.StringIO()):
            L._installer_deps()
        self.assertEqual(run.call_count, 4)
        commands = [call.args[0] for call in run.call_args_list]
        for command in commands[:3]:
            self.assertIn("Pillow", command)
            self.assertIn("osmium", command)
        self.assertIn("Pillow", commands[3])
        self.assertNotIn("osmium", commands[3])

    def test_system_critical_retry_keeps_pep668_strategies(self):
        def find_spec(name):
            return None if name in {"PIL", "osmium"} else object()

        real_import = builtins.__import__

        def importing(name, *args, **kwargs):
            if name == "PIL":
                return object()
            return real_import(name, *args, **kwargs)

        failed = SimpleNamespace(returncode=1, stdout="", stderr="denied")
        succeeded = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(importlib.util, "find_spec", side_effect=find_spec), \
             mock.patch.object(builtins, "__import__", side_effect=importing), \
             mock.patch.object(L.sys, "prefix", "system"), \
             mock.patch.object(L.sys, "base_prefix", "system"), \
             mock.patch.object(
                 L.subprocess,
                 "run",
                 side_effect=[failed, failed, failed, failed, succeeded],
             ) as run, contextlib.redirect_stdout(io.StringIO()):
            L._installer_deps()
        self.assertEqual(run.call_count, 5)
        retry_standard = run.call_args_list[3].args[0]
        retry_pep668 = run.call_args_list[4].args[0]
        self.assertNotIn("osmium", retry_standard)
        self.assertNotIn("--break-system-packages", retry_standard)
        self.assertNotIn("osmium", retry_pep668)
        self.assertIn("--break-system-packages", retry_pep668)

    def test_system_critical_retry_reaches_user_strategy(self):
        def find_spec(name):
            return None if name in {"PIL", "osmium"} else object()

        real_import = builtins.__import__

        def importing(name, *args, **kwargs):
            if name == "PIL":
                return object()
            return real_import(name, *args, **kwargs)

        failed = SimpleNamespace(returncode=1, stdout="", stderr="denied")
        succeeded = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(importlib.util, "find_spec", side_effect=find_spec), \
             mock.patch.object(builtins, "__import__", side_effect=importing), \
             mock.patch.object(L.sys, "prefix", "system"), \
             mock.patch.object(L.sys, "base_prefix", "system"), \
             mock.patch.object(
                 L.subprocess,
                 "run",
                 side_effect=[failed, failed, failed, failed, failed, succeeded],
             ) as run, contextlib.redirect_stdout(io.StringIO()):
            L._installer_deps()
        self.assertEqual(run.call_count, 6)
        retry_user = run.call_args_list[5].args[0]
        self.assertNotIn("osmium", retry_user)
        self.assertIn("Pillow", retry_user)
        self.assertIn("--user", retry_user)

    def test_post_install_validates_pywebview_module_name(self):
        def find_spec(name):
            return None if name == "webview" else object()

        real_import = builtins.__import__
        imported = []

        def importing(name, *args, **kwargs):
            if name == "webview":
                imported.append(name)
                return object()
            if name == "pywebview":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        succeeded = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(importlib.util, "find_spec", side_effect=find_spec), \
             mock.patch.object(builtins, "__import__", side_effect=importing), \
             mock.patch.object(L.sys, "prefix", "venv"), \
             mock.patch.object(L.sys, "base_prefix", "system"), \
             mock.patch.object(
                 L.subprocess,
                 "run",
                 return_value=succeeded,
             ) as run, contextlib.redirect_stdout(io.StringIO()):
            L._installer_deps()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(imported, ["webview"])

    def test_darwin_post_install_validates_pyobjc_module_names(self):
        packages = ["pyobjc-framework-WebKit", "pyobjc-framework-Cocoa"]

        def find_spec(name):
            return None if name in {"WebKit", "Cocoa"} else object()

        real_import = builtins.__import__
        imported = []

        def importing(name, *args, **kwargs):
            if name in {"WebKit", "Cocoa"}:
                imported.append(name)
                return object()
            if name.startswith("pyobjc-framework-"):
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        succeeded = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(
            L,
            "_gui_deps_plateforme",
            return_value=(packages, []),
        ), mock.patch.object(
            importlib.util,
            "find_spec",
            side_effect=find_spec,
        ), mock.patch.object(
            builtins,
            "__import__",
            side_effect=importing,
        ), mock.patch.object(
            L.sys,
            "prefix",
            "venv",
        ), mock.patch.object(
            L.sys,
            "base_prefix",
            "system",
        ), mock.patch.object(
            L.subprocess,
            "run",
            return_value=succeeded,
        ) as run, contextlib.redirect_stdout(io.StringIO()):
            L._installer_deps()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(imported, ["WebKit", "Cocoa"])

    def test_critical_retry_revalidates_pyobjc_modules(self):
        packages = ["pyobjc-framework-WebKit", "pyobjc-framework-Cocoa"]

        def find_spec(name):
            return None if name in {"WebKit", "Cocoa", "osmium"} else object()

        real_import = builtins.__import__
        imported = []

        def importing(name, *args, **kwargs):
            if name in {"WebKit", "Cocoa"}:
                imported.append(name)
                return object()
            return real_import(name, *args, **kwargs)

        failed = SimpleNamespace(returncode=1, stdout="", stderr="optional failed")
        succeeded = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(
            L,
            "_gui_deps_plateforme",
            return_value=(packages, []),
        ), mock.patch.object(
            importlib.util,
            "find_spec",
            side_effect=find_spec,
        ), mock.patch.object(
            builtins,
            "__import__",
            side_effect=importing,
        ), mock.patch.object(
            L.sys,
            "prefix",
            "venv",
        ), mock.patch.object(
            L.sys,
            "base_prefix",
            "system",
        ), mock.patch.object(
            L.subprocess,
            "run",
            side_effect=[failed, succeeded],
        ) as run, contextlib.redirect_stdout(io.StringIO()):
            L._installer_deps()
        self.assertEqual(run.call_count, 2)
        self.assertEqual(imported, ["WebKit", "Cocoa"])


class BootstrapFullInstallTests(unittest.TestCase):
    def _run(self, *, missing=(), returncode=0):
        missing = set(missing)
        imports = []
        commands = []
        messages = []

        def importer(module):
            imports.append(module)
            if module in missing:
                raise ImportError(module)

        def lancer(command, **kwargs):
            commands.append((command, kwargs))
            return SimpleNamespace(returncode=returncode)

        ok = bootstrap_runtime.installer_toutes_dependances(
            gui_deps_plateforme=lambda: ([], []),
            importer=importer,
            lancer=lancer,
            executable="python-test",
            ecrire=messages.append,
        )
        return ok, imports, commands, messages

    def test_full_install_uses_the_shared_package_catalog(self):
        self.assertEqual(bootstrap_runtime.MODULE_PAR_PAQUET["Pillow"], "PIL")
        self.assertEqual(bootstrap_runtime.MODULE_PAR_PAQUET["pywebview"], "webview")
        self.assertEqual(
            bootstrap_runtime.MODULE_PAR_PAQUET["mapbox-vector-tile"],
            "mapbox_vector_tile",
        )
        self.assertEqual(
            bootstrap_runtime.MODULE_PAR_PAQUET["cloth-simulation-filter"], "CSF"
        )

    def test_full_install_does_not_call_pip_for_importable_packages(self):
        ok, _imports, commands, messages = self._run()
        self.assertTrue(ok)
        self.assertEqual(commands, [])
        self.assertIn("  All dependencies installed.", messages)

    def test_full_install_fails_for_a_missing_critical_dependency(self):
        ok, _imports, commands, messages = self._run(missing={"PIL"}, returncode=1)
        self.assertFalse(ok)
        self.assertEqual(commands[0][0], ["python-test", "-m", "pip", "install", "-q", "Pillow"])
        self.assertEqual(len(commands), 1)
        self.assertIn("    ERROR Pillow (critical dependency unavailable)", messages)

    def test_full_install_keeps_an_optional_failure_non_fatal(self):
        ok, _imports, commands, messages = self._run(missing={"osmium"}, returncode=1)
        self.assertTrue(ok)
        self.assertEqual(commands[0][0][-1], "osmium")
        self.assertEqual(len(commands), 1)
        self.assertIn("    ⚠ osmium (optional - skipped)", messages)


class BootstrapUninstallPlanningTests(unittest.TestCase):
    def test_windows_targets_use_localappdata(self):
        targets = bootstrap_runtime.chemins_desinstallation(
            systeme="Windows", home=Path("/home/test"), localappdata=Path("/local")
        )
        self.assertEqual(targets[0][0], Path("/local/lidar2map"))
        self.assertEqual(targets[1][0], Path("/home/test/.lidar2map/venv"))

    def test_macos_and_linux_targets_are_deterministic(self):
        mac = bootstrap_runtime.chemins_desinstallation(
            systeme="Darwin", home=Path("/home/test")
        )
        linux = bootstrap_runtime.chemins_desinstallation(
            systeme="Linux", home=Path("/home/test")
        )
        self.assertEqual(mac[0][0], Path("/home/test/Library/Application Support/lidar2map"))
        self.assertEqual(linux[0][0], Path("/home/test/.local/share/lidar2map"))

    def test_planning_does_not_touch_filesystem(self):
        targets = bootstrap_runtime.chemins_desinstallation(
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
            targets = bootstrap_runtime.chemins_desinstallation(
                systeme="Linux", home=home
            )
            for index, (path, _label) in enumerate(targets):
                path.mkdir(parents=True)
                (path / f"file-{index}.bin").write_bytes(b"data")
            messages = []
            ok = bootstrap_runtime.desinstaller_lidar2map(
                systeme="Linux", home=home, ecrire=messages.append
            )
            self.assertTrue(ok)
            self.assertTrue(outside.is_file())
            self.assertTrue(all(not path.exists() for path, _label in targets))
            self.assertEqual(messages.count("    ✓ removed"), 4)

    def test_uninstall_reports_partial_failure_and_continues(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            targets = bootstrap_runtime.chemins_desinstallation(
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
            ok = bootstrap_runtime.desinstaller_lidar2map(
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
                 L._bootstrap_runtime_impl,
                 "desinstaller_lidar2map",
                 return_value=True,
             ) as uninstall:
            self.assertTrue(L._desinstaller_installation())
        uninstall.assert_called_once_with(
            systeme="Windows",
            home=Path("/home/test"),
            localappdata="/local",
        )

    def test_frozen_launcher_uninstalls_before_extraction_or_relaunch(self):
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
                     bootstrap_runtime,
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


class IntegratedSmoketestTests(unittest.TestCase):
    def test_source_smoketest_runs_all_modes_and_validates_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "lidar2map.py"
            projects = root / "Projets" / "smoke"
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

    def _activate(self, *, frozen=False, env=None, verifier=lambda _path: None):
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
            environnement=env or {},
            script_path="/source/lidar2map.py",
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
        self.assertEqual(logger.path.parent.name, "logs")
        self.assertEqual(logger.path.parent.parent.name, "source")
        self.assertIn("Commande : lidar2map.py --api-key ***", logger._log.getvalue())
        self.assertEqual(len(registered), 1)
        registered[0]()
        self.assertTrue(logger.closed)
        fake_sys.excepthook(ValueError, ValueError("boom"), None)
        self.assertTrue(any("UNHANDLED EXCEPTION" in line for line in messages))

    def test_frozen_activation_prefers_explicit_work_directory(self):
        logger, _fake_sys, _registered, _messages = self._activate(
            frozen=True, env={"LIDAR2MAP_WORK_DIR": "/work"}
        )
        self.assertEqual(logger.path.parent.name, "logs")
        self.assertEqual(logger.path.parent.parent.name, "work")

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

    def test_frozen_paths_prefer_launcher_work_dir_and_meipass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / "portable"
            bundle = root / "bundle"
            paths = runtime_paths.calculer_chemins(
                frozen=True,
                environnement={"LIDAR2MAP_WORK_DIR": str(work)},
                executable=root / "bin" / "lidar2map.exe",
                script_path=root / "ignored.py",
                meipass=bundle,
                home=root / "home",
            )

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
        self.assertEqual(L.DOSSIER_TRAVAIL, ROOT)
        self.assertEqual(L.BUNDLE_DIR, ROOT)
        self.assertEqual(L.LIDAR2MAP_HOME, Path.home() / ".lidar2map")
        self.assertEqual(L.DOSSIER_CACHE, ROOT / "cache")
        self.assertEqual(L.DOSSIER_PRODUCTION, ROOT / "production")
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


class BootstrapVenvEngineTests(unittest.TestCase):
    CRITICAL_IMPORTS = {
        "PIL",
        "pyproj",
        "numpy",
        "scipy",
        "ijson",
        "rasterio",
        "fiona",
        "certifi",
    }

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _venv_paths(self, system_name="Linux"):
        root = self.root / ".lidar2map" / "venv"
        if system_name == "Windows":
            return root, root / "Scripts" / "python.exe", root / "Scripts" / "pip.exe"
        return root, root / "bin" / "python", root / "bin" / "pip"

    @staticmethod
    def _completed(returncode=0, stderr="", stdout=""):
        return SimpleNamespace(returncode=returncode, stderr=stderr, stdout=stdout)

    def test_none_mode_with_all_imports_present_has_no_external_effect(self):
        real_import = builtins.__import__

        def importing(name, *args, **kwargs):
            if name in self.CRITICAL_IMPORTS:
                return object()
            return real_import(name, *args, **kwargs)

        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="none"), \
             mock.patch.object(builtins, "__import__", side_effect=importing), \
             mock.patch.object(
                 L.subprocess,
                 "run",
                 side_effect=AssertionError("subprocess interdit en mode none"),
             ) as run:
            L._bootstrap_venv_si_besoin()
        run.assert_not_called()

    def test_none_mode_reports_every_missing_import_and_exits_one(self):
        real_import = builtins.__import__
        missing = {"ijson", "rasterio"}

        def importing(name, *args, **kwargs):
            if name in missing:
                raise ImportError(f"forced missing {name}")
            if name in self.CRITICAL_IMPORTS:
                return object()
            return real_import(name, *args, **kwargs)

        output = io.StringIO()
        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="none"), \
             mock.patch.object(builtins, "__import__", side_effect=importing), \
             mock.patch.object(L.subprocess, "run") as run, \
             contextlib.redirect_stdout(output), \
             self.assertRaises(SystemExit) as raised:
            L._bootstrap_venv_si_besoin()
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("Missing Python modules: ijson, rasterio", output.getvalue())
        self.assertIn("pip install Pillow", output.getvalue())
        run.assert_not_called()

    def test_pip_mode_delegates_without_touching_venv_or_subprocess(self):
        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="pip"), \
             mock.patch.object(Path, "home") as home, \
             mock.patch.object(L.subprocess, "run") as run:
            L._bootstrap_venv_si_besoin()
        home.assert_not_called()
        run.assert_not_called()

    def test_auto_mode_returns_when_already_inside_managed_venv(self):
        venv_path, _python, _pip = self._venv_paths()
        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="auto"), \
             mock.patch.object(L.platform, "system", return_value="Linux"), \
             mock.patch.object(Path, "home", return_value=self.root), \
             mock.patch.object(L.sys, "prefix", str(venv_path)), \
             mock.patch.dict(
                 L.os.environ,
                 {
                     "CONDA_PREFIX": str(self.root / "conda-parent"),
                     "VIRTUAL_ENV": str(self.root / "other-venv"),
                 },
                 clear=True,
             ), \
             mock.patch.object(L.subprocess, "run") as run:
            L._bootstrap_venv_si_besoin()
        run.assert_not_called()

    def test_auto_mode_rejects_an_external_active_environment(self):
        cases = (
            ({"CONDA_PREFIX": str(self.root / "conda")}, self.root / "conda"),
            ({"VIRTUAL_ENV": str(self.root / "venv")}, self.root / "venv"),
            (
                {
                    "CONDA_PREFIX": str(self.root / "conda-first"),
                    "VIRTUAL_ENV": str(self.root / "venv-second"),
                },
                self.root / "conda-first",
            ),
        )
        for environment, expected in cases:
            with self.subTest(environment=environment):
                output = io.StringIO()
                with mock.patch.object(
                    L,
                    "_resoudre_mode_bootstrap",
                    return_value="auto",
                ), mock.patch.object(
                    L.platform,
                    "system",
                    return_value="Linux",
                ), mock.patch.object(
                    Path,
                    "home",
                    return_value=self.root,
                ), mock.patch.object(
                    L.sys,
                    "prefix",
                    str(self.root / "system"),
                ), mock.patch.dict(
                    L.os.environ,
                    environment,
                    clear=True,
                ), mock.patch.object(
                    L.subprocess,
                    "run",
                ) as run, contextlib.redirect_stdout(
                    output,
                ), self.assertRaises(SystemExit) as raised:
                    L._bootstrap_venv_si_besoin()
                self.assertEqual(raised.exception.code, 1)
                self.assertIn("Active Python environment detected", output.getvalue())
                self.assertIn(str(expected), output.getvalue())
                run.assert_not_called()

    def test_existing_healthy_venv_is_relaunched_without_install(self):
        venv_path, venv_python, _venv_pip = self._venv_paths()
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()
        completed = self._completed(returncode=0)
        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="auto"), \
             mock.patch.object(L.platform, "system", return_value="Linux"), \
             mock.patch.object(Path, "home", return_value=self.root), \
             mock.patch.object(L.sys, "prefix", str(self.root / "system")), \
             mock.patch.dict(L.os.environ, {}, clear=True), \
             mock.patch.object(L.subprocess, "run", return_value=completed) as run, \
             mock.patch.object(
                 L,
                 "_relancer_dans_venv",
                 side_effect=RuntimeError("relaunch sentinel"),
             ) as relaunch, \
             mock.patch.object(L, "_verifier_venv_linux") as guard, \
             mock.patch.object(L, "_gui_deps_plateforme") as gui, \
             self.assertRaisesRegex(RuntimeError, "relaunch sentinel"):
            L._bootstrap_venv_si_besoin()
        run.assert_called_once_with(
            [
                str(venv_python),
                "-c",
                "import PIL, pyproj, numpy, scipy, ijson, rasterio, fiona, certifi",
            ],
            capture_output=True,
        )
        relaunch.assert_called_once_with(venv_python, False)
        guard.assert_not_called()
        gui.assert_not_called()
        self.assertEqual(venv_path, self.root / ".lidar2map" / "venv")

    def test_new_venv_is_created_installed_and_relaunched(self):
        venv_path, venv_python, venv_pip = self._venv_paths()
        completed = self._completed(returncode=0)
        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="auto"), \
             mock.patch.object(L.platform, "system", return_value="Linux"), \
             mock.patch.object(Path, "home", return_value=self.root), \
             mock.patch.object(L.sys, "prefix", str(self.root / "system")), \
             mock.patch.object(L.sys, "executable", str(self.root / "python")), \
             mock.patch.dict(L.os.environ, {}, clear=True), \
             mock.patch.object(L.subprocess, "run", return_value=completed) as run, \
             mock.patch.object(L, "_verifier_venv_linux") as guard, \
             mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(L, "_relancer_dans_venv") as relaunch, \
             contextlib.redirect_stdout(io.StringIO()):
            L._bootstrap_venv_si_besoin()
        self.assertEqual(run.call_count, 2)
        run.assert_any_call(
            [str(self.root / "python"), "-m", "venv", str(venv_path)],
            check=True,
        )
        install_command = run.call_args_list[1].args[0]
        self.assertEqual(install_command[:4], [str(venv_pip), "install", "-q", "--disable-pip-version-check"])
        self.assertIn("Pillow", install_command)
        self.assertIn("osmium", install_command)
        relaunch.assert_called_once_with(venv_python, False)
        guard.assert_called_once_with()

    def test_windows_new_venv_uses_scripts_executables(self):
        venv_path, venv_python, venv_pip = self._venv_paths("Windows")
        completed = self._completed(returncode=0)
        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="auto"), \
             mock.patch.object(L.platform, "system", return_value="Windows"), \
             mock.patch.object(Path, "home", return_value=self.root), \
             mock.patch.object(L.sys, "prefix", str(self.root / "system")), \
             mock.patch.object(L.sys, "executable", str(self.root / "python.exe")), \
             mock.patch.dict(L.os.environ, {}, clear=True), \
             mock.patch.object(L.subprocess, "run", return_value=completed) as run, \
             mock.patch.object(L, "_verifier_venv_linux") as guard, \
             mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(L, "_relancer_dans_venv") as relaunch, \
             contextlib.redirect_stdout(io.StringIO()):
            L._bootstrap_venv_si_besoin()
        run.assert_any_call(
            [str(self.root / "python.exe"), "-m", "venv", str(venv_path)],
            check=True,
        )
        self.assertEqual(run.call_args_list[1].args[0][0], str(venv_pip))
        relaunch.assert_called_once_with(venv_python, True)
        guard.assert_called_once_with()

    def test_venv_creation_failure_exits_one_without_install_or_relaunch(self):
        venv_path, _venv_python, _venv_pip = self._venv_paths()
        error = subprocess.CalledProcessError(2, ["python", "-m", "venv"])
        output = io.StringIO()
        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="auto"), \
             mock.patch.object(L.platform, "system", return_value="Linux"), \
             mock.patch.object(Path, "home", return_value=self.root), \
             mock.patch.object(L.sys, "prefix", str(self.root / "system")), \
             mock.patch.dict(L.os.environ, {}, clear=True), \
             mock.patch.object(L.subprocess, "run", side_effect=error) as run, \
             mock.patch.object(L, "_verifier_venv_linux"), \
             mock.patch.object(L, "_gui_deps_plateforme") as gui, \
             mock.patch.object(L, "_relancer_dans_venv") as relaunch, \
             contextlib.redirect_stdout(output), \
             self.assertRaises(SystemExit) as raised:
            L._bootstrap_venv_si_besoin()
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("ERROR creating venv", output.getvalue())
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-1], str(venv_path))
        gui.assert_not_called()
        relaunch.assert_not_called()

    def test_failed_bulk_install_retries_critical_then_each_optional(self):
        _venv_path, venv_python, venv_pip = self._venv_paths()
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()
        results = [
            self._completed(returncode=1, stderr="broken existing env"),
            self._completed(returncode=1, stderr="optional wheel failed"),
            self._completed(returncode=0),
            self._completed(returncode=1, stderr="osmium unavailable"),
            self._completed(returncode=0),
        ]
        output = io.StringIO()
        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="auto"), \
             mock.patch.object(L.platform, "system", return_value="Linux"), \
             mock.patch.object(Path, "home", return_value=self.root), \
             mock.patch.object(L.sys, "prefix", str(self.root / "system")), \
             mock.patch.dict(L.os.environ, {}, clear=True), \
             mock.patch.object(L.subprocess, "run", side_effect=results) as run, \
             mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(L, "_relancer_dans_venv") as relaunch, \
             contextlib.redirect_stdout(output):
            L._bootstrap_venv_si_besoin()
        self.assertEqual(run.call_count, 5)
        commands = [call.args[0] for call in run.call_args_list[1:]]
        self.assertIn("osmium", commands[0])
        self.assertNotIn("osmium", commands[1])
        self.assertEqual(commands[2], [str(venv_pip), "install", "-q", "--disable-pip-version-check", "osmium"])
        self.assertEqual(commands[3], [str(venv_pip), "install", "-q", "--disable-pip-version-check", "numba"])
        self.assertIn("Optional deps not installed: osmium", output.getvalue())
        relaunch.assert_called_once_with(venv_python, False)

    def test_failed_critical_install_exits_one_without_relaunch(self):
        _venv_path, venv_python, _venv_pip = self._venv_paths()
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()
        results = [
            self._completed(returncode=1, stderr="broken existing env"),
            self._completed(returncode=1, stderr="bulk failed"),
            self._completed(returncode=1, stderr="critical failed"),
        ]
        with mock.patch.object(L, "_resoudre_mode_bootstrap", return_value="auto"), \
             mock.patch.object(L.platform, "system", return_value="Linux"), \
             mock.patch.object(Path, "home", return_value=self.root), \
             mock.patch.object(L.sys, "prefix", str(self.root / "system")), \
             mock.patch.dict(L.os.environ, {}, clear=True), \
             mock.patch.object(L.subprocess, "run", side_effect=results) as run, \
             mock.patch.object(L, "_gui_deps_plateforme", return_value=([], [])), \
             mock.patch.object(L, "_relancer_dans_venv") as relaunch, \
             contextlib.redirect_stdout(io.StringIO()), \
             self.assertRaises(SystemExit) as raised:
            L._bootstrap_venv_si_besoin()
        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(run.call_count, 3)
        relaunch.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
