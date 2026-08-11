"""Caracterisation hors reseau du pipeline GeoJSON IGN -> Mapsforge."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lidar2map as L  # noqa: E402


class GeojsonMapsforgeCharacterizationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source = self.root / "source.geojson"
        self.source.write_text('{"type":"FeatureCollection","features":[]}',
                               encoding="utf-8")
        self.bbox = (6.1, 43.1, 6.2, 43.2)

    def tearDown(self):
        self._tmp.cleanup()

    def _paths(self, name="zone"):
        return (
            self.root / f"{name}_ign.map",
            self.root / f"{name}_ign.osm",
        )

    def _invoke(self, name="zone", **kwargs):
        options = {
            "geojson_src": self.source,
            "dossier_ville": self.root,
            "nom_zone": name,
            "bbox_wgs84": self.bbox,
            "ecraser": True,
            "epsilon": 0.00015,
        }
        options.update(kwargs)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), \
             contextlib.redirect_stderr(stderr):
            result = L.generer_map_depuis_geojson_ign(**options)
        return result, stdout.getvalue(), stderr.getvalue()

    @staticmethod
    def _converter(calls, result=True):
        def convert(source, osm_path, epsilon=None):
            source = Path(source)
            osm_path = Path(osm_path)
            calls.append((source, osm_path, epsilon))
            if result:
                osm_path.write_bytes(b"<osm/>")
            return result

        return convert

    @staticmethod
    def _map_part_from_command(command):
        if not isinstance(command, list):
            raise AssertionError("list command expected for this scenario")
        index = command.index("--mapfile-writer")
        value = str(command[index + 1])
        if not value.startswith("file="):
            raise AssertionError(value)
        return Path(value.split("=", 1)[1])

    def _assert_no_part(self):
        self.assertEqual(list(self.root.rglob("*.part")), [])

    def test_cache_hit_migrates_missing_signature_and_skips_pipeline(self):
        final, _osm = self._paths()
        previous = b"cached-map"
        final.write_bytes(previous)
        expected_mtime = round(self.source.stat().st_mtime, 1)
        bbox = (6.12345678, 43.12345678, 6.23456789, 43.23456789)
        converter = mock.Mock()
        prepare = mock.Mock()
        runner = mock.Mock()

        with mock.patch.object(
            L,
            "_hash_config",
            return_value="sig-current",
        ) as hash_config, mock.patch.object(
            L,
            "_sig_sidecar_stale",
            return_value=False,
        ) as stale, mock.patch.object(
            L,
            "_sig_sidecar_ecrire",
        ) as write_signature, mock.patch.object(
            L,
            "geojson_ign_vers_osm_xml",
            converter,
        ), mock.patch.object(
            L,
            "_preparer_osmosis",
            prepare,
        ), mock.patch.object(
            L,
            "_run_osmosis_streaming",
            runner,
        ):
            result, _stdout, _stderr = self._invoke(
                bbox_wgs84=bbox,
                ecraser=False,
                epsilon=0.012345,
            )

        self.assertEqual(result, final)
        self.assertEqual(final.read_bytes(), previous)
        hash_config.assert_called_once_with({
            "src": self.source.name,
            "src_mtime": expected_mtime,
            "bbox": [round(float(value), 6) for value in bbox],
            "eps": 0.012345,
        })
        stale.assert_called_once_with(final, "sig-current")
        write_signature.assert_called_once_with(final, "sig-current")
        converter.assert_not_called()
        prepare.assert_not_called()
        runner.assert_not_called()
        self._assert_no_part()

    def test_stale_cache_runs_one_osmosis_pass_and_publishes_atomically(self):
        final, osm_xml = self._paths()
        final.write_bytes(b"old-map")
        converter_calls = []
        runner_call = {}
        seen_parts = []
        original_chemin_part = L._chemin_part

        def record_part(path):
            target = Path(path)
            part = original_chemin_part(target)
            seen_parts.append((target, part))
            return part

        def runner(command, **kwargs):
            runner_call.update(command=command, **kwargs)
            part = self._map_part_from_command(command)
            part.write_bytes(b"new-map")
            return 0, ""

        with mock.patch.object(
            L,
            "_hash_config",
            return_value="sig-new",
        ), mock.patch.object(
            L,
            "_sig_sidecar_stale",
            return_value=True,
        ) as stale, mock.patch.object(
            L,
            "_sig_sidecar_ecrire",
        ) as write_signature, mock.patch.object(
            L,
            "geojson_ign_vers_osm_xml",
            side_effect=self._converter(converter_calls),
        ) as converter, mock.patch.object(
            L,
            "_preparer_osmosis",
            return_value=("osmosis", "java-home"),
        ) as prepare, mock.patch.object(
            L,
            "_java_opts_extra",
            return_value=' "-Dtest=true"',
        ) as java_extra, mock.patch.object(
            L,
            "_chemin_part",
            side_effect=record_part,
        ), mock.patch.object(
            L,
            "_run_osmosis_streaming",
            side_effect=runner,
        ) as run_osmosis, mock.patch.object(
            L,
            "_log_req",
        ) as log_req, mock.patch.object(
            L,
            "WINDOWS",
            False,
        ), mock.patch.object(
            L.os,
            "environ",
            {"KEEP": "yes"},
        ):
            result, _stdout, _stderr = self._invoke(ecraser=False)

        self.assertEqual(result, final)
        self.assertEqual(final.read_bytes(), b"new-map")
        self.assertFalse(osm_xml.exists())
        self.assertEqual(converter_calls, [(self.source, osm_xml, 0.00015)])
        converter.assert_called_once()
        prepare.assert_called_once_with()
        java_extra.assert_called_once_with()
        stale.assert_called_once_with(final, "sig-new")
        write_signature.assert_called_once_with(final, "sig-new")
        run_osmosis.assert_called_once()

        command = runner_call["command"]
        self.assertIsInstance(command, list)
        self.assertEqual(command[0], "osmosis")
        self.assertEqual(
            command[command.index("--read-xml") + 1],
            f"file={osm_xml}",
        )
        map_part = self._map_part_from_command(command)
        self.assertEqual(seen_parts, [(final, map_part)])
        self.assertEqual(map_part.suffix, ".part")
        self.assertIn(
            "bbox=43.100000,6.100000,43.200000,6.200000",
            command,
        )
        for option in (
            "zoom-interval-conf=7,0,7,11,8,11,14,12,21",
            "tag-values=true",
            "polygon-clipping=true",
            "way-clipping=true",
            "label-position=true",
        ):
            self.assertIn(option, command)
        self.assertFalse(runner_call["shell"])
        self.assertEqual(runner_call["env"]["KEEP"], "yes")
        self.assertEqual(runner_call["env"]["JAVA_HOME"], "java-home")
        self.assertEqual(
            runner_call["env"]["JAVA_OPTS"],
            '-Xmx4g "-Dtest=true"',
        )
        log_req.assert_called_once_with(command)
        self._assert_no_part()

    def test_conversion_failure_keeps_previous_and_never_prepares_osmosis(self):
        final, osm_xml = self._paths()
        previous = b"old-map"
        final.write_bytes(previous)
        converter = mock.Mock(return_value=False)
        prepare = mock.Mock()
        runner = mock.Mock()

        with mock.patch.object(
            L,
            "geojson_ign_vers_osm_xml",
            converter,
        ), mock.patch.object(
            L,
            "_preparer_osmosis",
            prepare,
        ), mock.patch.object(
            L,
            "_run_osmosis_streaming",
            runner,
        ):
            result, _stdout, _stderr = self._invoke()

        self.assertIsNone(result)
        self.assertEqual(final.read_bytes(), previous)
        converter.assert_called_once_with(
            self.source,
            osm_xml,
            epsilon=0.00015,
        )
        prepare.assert_not_called()
        runner.assert_not_called()
        self.assertFalse(osm_xml.exists())
        self._assert_no_part()

    def test_missing_osmosis_removes_intermediate_xml_and_keeps_previous(self):
        final, osm_xml = self._paths()
        previous = b"old-map"
        final.write_bytes(previous)
        converter_calls = []
        runner = mock.Mock()

        with mock.patch.object(
            L,
            "geojson_ign_vers_osm_xml",
            side_effect=self._converter(converter_calls),
        ), mock.patch.object(
            L,
            "_preparer_osmosis",
            return_value=(None, None),
        ) as prepare, mock.patch.object(
            L,
            "_run_osmosis_streaming",
            runner,
        ):
            result, _stdout, _stderr = self._invoke()

        self.assertIsNone(result)
        self.assertEqual(final.read_bytes(), previous)
        self.assertEqual(converter_calls, [(self.source, osm_xml, 0.00015)])
        prepare.assert_called_once_with()
        runner.assert_not_called()
        self.assertFalse(osm_xml.exists())
        self._assert_no_part()

    def test_three_unsuccessful_osmosis_outcomes_keep_xml_for_diagnostics(self):
        cases = (
            ("nonzero", b"partial-map", 7, "forced diagnostic"),
            ("empty", b"", 0, ""),
            ("missing", None, 0, ""),
        )
        for name, staged_bytes, returncode, diagnostic in cases:
            with self.subTest(case=name):
                final, osm_xml = self._paths(name)
                previous = f"old-{name}".encode()
                final.write_bytes(previous)
                converter_calls = []

                def runner(command, **_kwargs):
                    part = self._map_part_from_command(command)
                    if staged_bytes is not None:
                        part.write_bytes(staged_bytes)
                    return returncode, diagnostic

                with mock.patch.object(
                    L,
                    "geojson_ign_vers_osm_xml",
                    side_effect=self._converter(converter_calls),
                ), mock.patch.object(
                    L,
                    "_preparer_osmosis",
                    return_value=("osmosis", "java-home"),
                ), mock.patch.object(
                    L,
                    "_java_opts_extra",
                    return_value="",
                ), mock.patch.object(
                    L,
                    "_run_osmosis_streaming",
                    side_effect=runner,
                ), mock.patch.object(
                    L,
                    "_sig_sidecar_ecrire",
                ) as write_signature, mock.patch.object(
                    L,
                    "_log_req",
                ), mock.patch.object(
                    L,
                    "WINDOWS",
                    False,
                ), mock.patch.object(L.os, "environ", {}):
                    result, stdout, _stderr = self._invoke(name=name)

                self.assertIsNone(result)
                self.assertEqual(final.read_bytes(), previous)
                self.assertTrue(osm_xml.exists())
                write_signature.assert_not_called()
                if diagnostic:
                    self.assertIn(diagnostic, stdout)
                if name == "empty":
                    self.assertIn("created but empty", stdout)
                self._assert_no_part()

    def test_runner_base_exceptions_clean_part_and_keep_xml_and_previous_map(self):
        cases = (
            ("runtime", RuntimeError("forced runner exception")),
            ("keyboard", KeyboardInterrupt("forced ctrl-c")),
        )
        for name, error in cases:
            with self.subTest(case=name):
                final, osm_xml = self._paths(name)
                previous = f"old-{name}".encode()
                final.write_bytes(previous)

                def runner(command, **_kwargs):
                    self._map_part_from_command(command).write_bytes(b"partial")
                    raise error

                with mock.patch.object(
                    L,
                    "geojson_ign_vers_osm_xml",
                    side_effect=self._converter([]),
                ), mock.patch.object(
                    L,
                    "_preparer_osmosis",
                    return_value=("osmosis", "java-home"),
                ), mock.patch.object(
                    L,
                    "_java_opts_extra",
                    return_value="",
                ), mock.patch.object(
                    L,
                    "_run_osmosis_streaming",
                    side_effect=runner,
                ), mock.patch.object(
                    L,
                    "_log_req",
                ), mock.patch.object(
                    L,
                    "WINDOWS",
                    False,
                ), mock.patch.object(L.os, "environ", {}):
                    with self.assertRaises(type(error)):
                        self._invoke(name=name)

                self.assertEqual(final.read_bytes(), previous)
                self.assertTrue(osm_xml.exists())
                self._assert_no_part()

    def test_windows_batch_command_preserves_existing_java_opts(self):
        final, osm_xml = self._paths("windows")
        previous = b"old-windows"
        final.write_bytes(previous)
        captured = {}

        def runner(command, **kwargs):
            captured.update(command=command, **kwargs)
            return 9, "windows diagnostic"

        java_extra = mock.Mock(return_value=" should-not-be-used")
        with mock.patch.object(
            L,
            "geojson_ign_vers_osm_xml",
            side_effect=self._converter([]),
        ), mock.patch.object(
            L,
            "_preparer_osmosis",
            return_value=(
                r"C:\Program Files\osmosis\bin\osmosis.bat",
                r"C:\Java Home",
            ),
        ), mock.patch.object(
            L,
            "_java_opts_extra",
            java_extra,
        ), mock.patch.object(
            L,
            "_run_osmosis_streaming",
            side_effect=runner,
        ), mock.patch.object(
            L,
            "_log_req",
        ) as log_req, mock.patch.object(
            L,
            "WINDOWS",
            True,
        ), mock.patch.object(
            L.os,
            "environ",
            {"JAVA_OPTS": "-Xmx2g", "KEEP": "yes"},
        ):
            result, stdout, _stderr = self._invoke(name="windows")

        self.assertIsNone(result)
        self.assertEqual(final.read_bytes(), previous)
        self.assertTrue(osm_xml.exists())
        self.assertTrue(captured["shell"])
        self.assertIsInstance(captured["command"], str)
        self.assertIn('"C:\\Program Files\\osmosis\\bin\\osmosis.bat"',
                      captured["command"])
        self.assertIn('"file=', captured["command"])
        self.assertIn('"bbox=43.100000,6.100000,43.200000,6.200000"',
                      captured["command"])
        self.assertEqual(captured["env"]["JAVA_HOME"], r"C:\Java Home")
        self.assertEqual(captured["env"]["JAVA_OPTS"], "-Xmx2g")
        self.assertEqual(captured["env"]["KEEP"], "yes")
        java_extra.assert_not_called()
        logged_command = log_req.call_args.args[0]
        self.assertIsInstance(logged_command, list)
        self.assertIn("windows diagnostic", stdout)
        self._assert_no_part()

    def test_publication_replace_failure_keeps_previous_but_must_clean_part(self):
        """Un echec de publication conserve l'ancien map sans staging."""
        final, osm_xml = self._paths("replace")
        previous = b"old-map"
        final.write_bytes(previous)

        def runner(command, **_kwargs):
            self._map_part_from_command(command).write_bytes(b"new-map")
            return 0, ""

        with mock.patch.object(
            L,
            "geojson_ign_vers_osm_xml",
            side_effect=self._converter([]),
        ), mock.patch.object(
            L,
            "_preparer_osmosis",
            return_value=("osmosis", "java-home"),
        ), mock.patch.object(
            L,
            "_java_opts_extra",
            return_value="",
        ), mock.patch.object(
            L,
            "_run_osmosis_streaming",
            side_effect=runner,
        ), mock.patch.object(
            L,
            "_sig_sidecar_ecrire",
        ) as write_signature, mock.patch.object(
            L,
            "_log_req",
        ), mock.patch.object(
            L,
            "WINDOWS",
            False,
        ), mock.patch.object(
            L.os,
            "environ",
            {},
        ), mock.patch.object(
            Path,
            "replace",
            side_effect=OSError("forced publication failure"),
        ):
            with self.assertRaises(OSError):
                self._invoke(name="replace")

        self.assertEqual(final.read_bytes(), previous)
        self.assertTrue(osm_xml.exists())
        write_signature.assert_not_called()
        self._assert_no_part()


if __name__ == "__main__":
    unittest.main(verbosity=2)
