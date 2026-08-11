"""Régressions hors réseau des traitements découpés et de leur historique."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lidar2map as L  # noqa: E402


class NoopPrefetch:
    """Préchargement neutralisé : les régressions split restent hors réseau."""

    def lancer(self, *_args, **_kwargs):
        return None

    def recuperer(self, _cle):
        return None

    def purger(self):
        return None


class HistoryFixture(unittest.TestCase):
    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_ctx.name)
        self.old_history_path = L._HISTORIQUE_PATH
        self.old_run_id = L._HIST_RUN_ID
        self.old_started = L._HIST_T_DEBUT
        self.old_finalized = L._HIST_FINALIZED
        self.old_argv = sys.argv[:]
        self.old_hist_env = os.environ.get("LIDAR2MAP_HIST_RUN_ID")
        self.old_skip_env = os.environ.get("LIDAR2MAP_SKIP_HIST")
        L._HISTORIQUE_PATH = self.tmp / "historique.json"
        os.environ["LIDAR2MAP_HIST_RUN_ID"] = "split-history-test"
        os.environ.pop("LIDAR2MAP_SKIP_HIST", None)

    def tearDown(self):
        L._HISTORIQUE_PATH = self.old_history_path
        L._HIST_RUN_ID = self.old_run_id
        L._HIST_T_DEBUT = self.old_started
        L._HIST_FINALIZED = self.old_finalized
        sys.argv = self.old_argv
        if self.old_hist_env is None:
            os.environ.pop("LIDAR2MAP_HIST_RUN_ID", None)
        else:
            os.environ["LIDAR2MAP_HIST_RUN_ID"] = self.old_hist_env
        if self.old_skip_env is None:
            os.environ.pop("LIDAR2MAP_SKIP_HIST", None)
        else:
            os.environ["LIDAR2MAP_SKIP_HIST"] = self.old_skip_env
        self.tmp_ctx.cleanup()

    def _reset_history(self, argv):
        sys.argv = list(argv)
        L._HIST_RUN_ID = ""
        L._HIST_T_DEBUT = 0.0
        L._HIST_FINALIZED = False

    def _entry(self):
        entries = json.loads(L._HISTORIQUE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        return entries[0]


class SplitHistoryFinalizationTests(HistoryFixture):
    def _start(self):
        self._reset_history([
            "lidar2map.py", "--lidar", "--zone-bbox", "6,43,6.1,43.1",
            "--split-cols", "2", "--split-rows", "1",
        ])
        L._historique_debut()

    def test_split_success_finalizes_history_with_result_directory(self):
        self._start()
        result_dir = self.tmp / "result"
        completed = L._executer_split_historise(
            lambda: True, time.time() - 3, result_dir)

        self.assertTrue(completed)
        entry = self._entry()
        self.assertEqual(entry["statut"], "ok")
        self.assertEqual(entry["resultat"], str(result_dir))
        self.assertTrue(L._HIST_FINALIZED)

    def test_split_incomplete_finalizes_history_and_raises(self):
        self._start()
        result_dir = self.tmp / "incomplete"
        with self.assertRaisesRegex(RuntimeError, "Split processing incomplete"):
            L._executer_split_historise(
                lambda: False, time.time() - 2, result_dir)

        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(result_dir))

    def test_gui_history_keeps_partial_result_directory_on_failure(self):
        result_dir = self.tmp / "partial"

        status, result = L._bilan_historique_processus(1, result_dir)

        self.assertEqual(status, "ko")
        self.assertEqual(result, str(result_dir))

    def test_batch_failure_overrides_a_later_success(self):
        self._start()
        result_dir = self.tmp / "last-success"
        L._historique_depuis_argv(1, str(result_dir), statut="ok")

        L._historique_fin_batch_ko(time.time() - 4)

        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(result_dir))

    def test_split_exception_finalizes_history_then_reraises(self):
        self._start()
        result_dir = self.tmp / "failed"

        def fail():
            raise RuntimeError("forced split failure")

        with self.assertRaisesRegex(RuntimeError, "forced split failure"):
            L._executer_split_historise(fail, time.time() - 1, result_dir)

        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(result_dir))
        self.assertTrue(L._HIST_FINALIZED)


class SplitEntryPointHistoryTests(HistoryFixture):
    ZONES = [
        (0, 0, 0.0, 0.0, 1000.0, 1000.0),
        (0, 1, 1000.0, 0.0, 2000.0, 1000.0),
    ]

    def _lidar_argv(self, *, block=False):
        argv = [
            "lidar2map.py", "--lidar",
            "--zone-bbox", "6.0,43.0,6.1,43.1",
            "--split-cols", "2", "--split-rows", "1",
            "--output-dir", str(self.tmp / "lidar-result"),
            "--no-download", "--shadings", "none",
            "--file-formats", "mbtiles",
        ]
        if block:
            argv += ["--block", "1/2"]
        return argv

    def _lidar_patches(self, split_mock, split_side_effect):
        return (
            mock.patch.object(L, "_PROVIDER_CLI_EXPLICIT", True),
            mock.patch.object(L, "_appliquer_cache_dir"),
            mock.patch.object(L, "_appliquer_production_dir"),
            mock.patch.object(L, "_configurer_cloud_cache"),
            mock.patch.object(
                L, "_bbox_enveloppe_transform",
                return_value=(0.0, 0.0, 2000.0, 1000.0),
            ),
            mock.patch.object(
                L, "calculer_grille_bbox",
                return_value=(0.0, 0.0, 2000.0, 1000.0),
            ),
            mock.patch.object(
                L, "_calculer_sous_zones_priori",
                side_effect=split_side_effect,
            ),
            split_mock,
        )

    def test_lidar_sliding_split_marks_incomplete_run_ko(self):
        argv = self._lidar_argv()
        self._reset_history(argv)
        sliding = mock.patch.object(
            L, "_run_split_priori_lidar_glissant", return_value=False)
        patches = self._lidar_patches(sliding, [(self.ZONES, "2x1")])
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7] as runner, \
             self.assertRaisesRegex(RuntimeError, "Split processing incomplete"):
            L.main()

        runner.assert_called_once()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(
            Path(entry["resultat"]).resolve(),
            (self.tmp / "lidar-result").resolve(),
        )

    def test_lidar_block_split_marks_successful_run_ok(self):
        argv = self._lidar_argv(block=True)
        self._reset_history(argv)
        blocks = [
            (0, 0, 0.0, 0.0, 2000.0, 1000.0),
            (0, 1, 2000.0, 0.0, 4000.0, 1000.0),
        ]
        classic = mock.patch.object(L, "_run_split_priori", return_value=True)
        patches = self._lidar_patches(
            classic, [(blocks, "block 1/2"), (self.ZONES, "2x1")])
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7] as runner:
            L.main()

        runner.assert_called_once()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ok")
        self.assertEqual(
            Path(entry["resultat"]).resolve(),
            (self.tmp / "lidar-result").resolve(),
        )

    def test_wmts_split_marks_successful_run_ok(self):
        result_dir = self.tmp / "wmts-result"
        argv = [
            "lidar2map.py", "--raster",
            "--zone-bbox", "6.0,43.0,6.1,43.1",
            "--split-cols", "2", "--split-rows", "1",
            "--output-dir", str(result_dir),
            "--file-formats", "mbtiles",
        ]
        self._reset_history(argv)
        with mock.patch.object(L, "_appliquer_cache_dir"), \
             mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=None), \
             mock.patch.object(
                 L, "_resoudre_zone_wgs84",
                 return_value=(6.0, 43.0, 6.1, 43.1, "zone")), \
             mock.patch.object(
                 L, "_calculer_sous_zones_priori",
                 return_value=(self.ZONES, "2x1")), \
             mock.patch.object(L, "_run_split_priori", return_value=True) as runner:
            L.main_wmts()

        runner.assert_called_once()
        self.assertFalse(
            runner.call_args.kwargs["vide_sans_couverture_ok"])
        entry = self._entry()
        self.assertEqual(entry["statut"], "ok")
        self.assertEqual(
            Path(entry["resultat"]).resolve(),
            result_dir.resolve(),
        )


class MonolithicConversionHistoryTests(HistoryFixture):
    _DISCOVER_EMPTY = object()

    def _lidar_argv(self, output, *extra):
        return [
            "lidar2map.py", "--lidar", "--provider", "fr-ign",
            "--zone-bbox", "6.0,43.0,6.01,43.01",
            "--zone-name", "zone",
            "--output-dir", str(output),
            "--no-download", "--shadings", "none",
            "--file-formats", "rmap", *extra,
        ]

    def _lidar_patches(
            self, *, download=False, discover_result=_DISCOVER_EMPTY):
        def defaults(args):
            args.telechargement = download
            args.ombrages = None

        if discover_result is self._DISCOVER_EMPTY:
            discover_result = {}

        return (
            mock.patch.object(L, "_PROVIDER_CLI_EXPLICIT", True),
            mock.patch.object(
                L, "_appliquer_defauts_cli_lidar", side_effect=defaults),
            mock.patch.object(L, "_appliquer_cache_dir"),
            mock.patch.object(L, "_appliquer_production_dir"),
            mock.patch.object(L, "_configurer_cloud_cache"),
            mock.patch.object(
                L, "_bbox_enveloppe_transform",
                return_value=(0.0, 0.0, 1000.0, 1000.0)),
            mock.patch.object(
                L, "calculer_grille_bbox",
                return_value=(0.0, 0.0, 1000.0, 1000.0)),
            mock.patch.object(
                L.PROVIDER, "discover_dalles", return_value=discover_result),
            mock.patch.object(
                L, "_dossier_dalles_actif",
                return_value=self.tmp / "absent-tile-cache"),
            mock.patch.object(L, "_garde_disque"),
            mock.patch.object(L, "_planche_depuis_dossier"),
        )

    def _wmts_argv(self, output):
        return [
            "lidar2map.py", "--raster",
            "--zone-bbox", "6.0,43.0,6.01,43.01",
            "--zone-name", "zone",
            "--zoom-min", "10", "--zoom-max", "10",
            "--output-dir", str(output),
            "--file-formats", "rmap",
        ]

    def test_lidar_shading_conversion_failure_marks_run_ko(self):
        output = self.tmp / "lidar-shadings"
        output.mkdir()
        (output / "zone_lrm_ombrage.tif").write_bytes(b"shade")
        self._reset_history(self._lidar_argv(output))
        patches = self._lidar_patches()

        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7], patches[8], patches[9], \
             patches[10], \
             mock.patch.object(
                 L, "_tuiler_tifs_ombrages", return_value=False) as tile, \
             self.assertRaisesRegex(RuntimeError, "conversion"):
            L.main()

        tile.assert_called_once()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(output.resolve()))
        self.assertTrue(L._HIST_FINALIZED)

    def test_lidar_explicit_tif_conversion_failure_marks_run_ko(self):
        output = self.tmp / "lidar-source"
        source = self.tmp / "source.tif"
        source.write_bytes(b"fake tif")
        argv = self._lidar_argv(output)
        source_index = argv.index("--shadings")
        argv[source_index:source_index + 2] = ["--source", str(source)]
        self._reset_history(argv)
        patches = self._lidar_patches()
        expected_mbt = output / "zone_source.tif_z13-17.mbtiles"

        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7], patches[8], patches[9], \
             patches[10], \
             mock.patch.object(L, "_mbtiles_a_regenerer", return_value=True), \
             mock.patch.object(
                 L, "generer_mbtiles_lidar", return_value=expected_mbt), \
             mock.patch.object(
                 L, "_convertir_formats", return_value=False) as convert, \
             self.assertRaisesRegex(RuntimeError, "conversion"):
            L.main()

        convert.assert_called_once()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(output.resolve()))

    def test_lidar_requested_format_without_shading_marks_run_ko(self):
        output = self.tmp / "lidar-no-shading"
        self._reset_history(self._lidar_argv(output))
        patches = self._lidar_patches()

        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7], patches[8], patches[9], \
             patches[10], \
             mock.patch.object(L, "_tuiler_tifs_ombrages") as tile, \
             self.assertRaisesRegex(RuntimeError, "conversion"):
            L.main()

        tile.assert_not_called()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(output.resolve()))

    def test_lidar_successful_shading_conversion_keeps_run_ok(self):
        output = self.tmp / "lidar-success"
        output.mkdir()
        (output / "zone_lrm_ombrage.tif").write_bytes(b"shade")
        self._reset_history(self._lidar_argv(output))
        patches = self._lidar_patches()

        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7], patches[8], patches[9], \
             patches[10], \
             mock.patch.object(
                 L, "_tuiler_tifs_ombrages", return_value=True) as tile:
            L.main()

        tile.assert_called_once()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ok")
        self.assertEqual(entry["resultat"], str(output.resolve()))

    def test_lidar_no_coverage_finalizes_successful_run(self):
        output = self.tmp / "lidar-no-coverage"
        argv = self._lidar_argv(output)
        argv.remove("--no-download")
        self._reset_history(argv)
        patches = self._lidar_patches(download=True)

        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7], patches[8], patches[9], \
             patches[10], \
             mock.patch.object(L, "_tuiler_tifs_ombrages") as tile:
            L.main()

        tile.assert_not_called()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ok")
        self.assertEqual(entry["resultat"], str(output.resolve()))
        self.assertTrue(L._HIST_FINALIZED)

    def test_lidar_unavailable_discovery_finalizes_failed_run(self):
        output = self.tmp / "lidar-discovery-unavailable"
        argv = self._lidar_argv(output)
        argv.remove("--no-download")
        self._reset_history(argv)
        patches = self._lidar_patches(
            download=True, discover_result=None)

        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7], patches[8], patches[9], \
             patches[10], \
             mock.patch.object(L, "_tuiler_tifs_ombrages") as tile, \
             self.assertRaises(SystemExit) as raised:
            L.main()

        self.assertEqual(raised.exception.code, 1)
        tile.assert_not_called()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(output.resolve()))
        self.assertTrue(L._HIST_FINALIZED)

    def test_wmts_conversion_failure_marks_run_ko(self):
        output = self.tmp / "wmts"
        self._reset_history(self._wmts_argv(output))

        def generate(**kwargs):
            kwargs["chemin"].parent.mkdir(parents=True, exist_ok=True)
            kwargs["chemin"].write_bytes(b"mbtiles")
            return kwargs["chemin"]

        with mock.patch.object(L, "_appliquer_cache_dir"), \
             mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=None), \
             mock.patch.object(
                 L, "_resoudre_zone_wgs84",
                 return_value=(6.0, 43.0, 6.01, 43.01, "zone")), \
             mock.patch.object(L, "DOSSIER_CACHE", self.tmp / "cache"), \
             mock.patch.object(L, "_garde_disque"), \
             mock.patch.object(
                 L, "generer_mbtiles_wmts", side_effect=generate), \
             mock.patch.object(
                 L, "_convertir_formats", return_value=False) as convert, \
             mock.patch.object(L, "_planche_depuis_dossier"), \
             self.assertRaisesRegex(RuntimeError, "conversion"):
            L.main_wmts()

        convert.assert_called_once()
        self.assertTrue(convert.call_args.kwargs["mbtiles_neuf"])
        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(output.resolve()))
        self.assertTrue(L._HIST_FINALIZED)

    def test_wmts_missing_generated_mbtiles_marks_run_ko(self):
        output = self.tmp / "wmts-missing"
        self._reset_history(self._wmts_argv(output))

        with mock.patch.object(L, "_appliquer_cache_dir"), \
             mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=None), \
             mock.patch.object(
                 L, "_resoudre_zone_wgs84",
                 return_value=(6.0, 43.0, 6.01, 43.01, "zone")), \
             mock.patch.object(L, "DOSSIER_CACHE", self.tmp / "cache"), \
             mock.patch.object(L, "_garde_disque"), \
             mock.patch.object(L, "generer_mbtiles_wmts"), \
             mock.patch.object(L, "_convertir_formats") as convert, \
             mock.patch.object(L, "_planche_depuis_dossier"), \
             self.assertRaisesRegex(RuntimeError, "conversion"):
            L.main_wmts()

        convert.assert_not_called()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(output.resolve()))

    def test_wmts_successful_conversion_keeps_run_ok(self):
        output = self.tmp / "wmts-success"
        self._reset_history(self._wmts_argv(output))

        def generate(**kwargs):
            kwargs["chemin"].parent.mkdir(parents=True, exist_ok=True)
            kwargs["chemin"].write_bytes(b"mbtiles")

        with mock.patch.object(L, "_appliquer_cache_dir"), \
             mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=None), \
             mock.patch.object(
                 L, "_resoudre_zone_wgs84",
                 return_value=(6.0, 43.0, 6.01, 43.01, "zone")), \
             mock.patch.object(L, "DOSSIER_CACHE", self.tmp / "cache"), \
             mock.patch.object(L, "_garde_disque"), \
             mock.patch.object(
                 L, "generer_mbtiles_wmts", side_effect=generate), \
             mock.patch.object(
                 L, "_convertir_formats", return_value=True) as convert, \
             mock.patch.object(L, "_planche_depuis_dossier"):
            L.main_wmts()

        convert.assert_called_once()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ok")
        self.assertEqual(entry["resultat"], str(output.resolve()))


class PosterioriSplitHistoryTests(HistoryFixture):
    def _argv(self, source, *extra):
        return [
            "lidar2map.py", "--split", "--source", str(source),
            "--cols", "2", "--rows", "1", *extra,
        ]

    def test_posteriori_split_marks_successful_run_ok(self):
        source = self.tmp / "source.mbtiles"
        source.touch()
        piece = self.tmp / "source_001x001.mbtiles"
        self._reset_history(self._argv(source))

        with mock.patch.object(L, "decouper_mbtiles", return_value=[piece]):
            L.main_decouper()

        entry = self._entry()
        self.assertEqual(entry["statut"], "ok")
        self.assertEqual(entry["resultat"], str(self.tmp.resolve()))

    def test_posteriori_split_conversion_failure_marks_run_ko(self):
        source = self.tmp / "source.mbtiles"
        source.touch()
        piece = self.tmp / "source_001x001.mbtiles"
        self._reset_history(self._argv(source, "--file-formats", "sqlitedb"))

        with mock.patch.object(L, "decouper_mbtiles", return_value=[piece]), \
             mock.patch.object(
                 L, "generer_sqlitedb_depuis_mbtiles", return_value=None), \
             self.assertRaises(SystemExit) as raised:
            L.main_decouper()

        self.assertEqual(raised.exception.code, 1)
        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(self.tmp.resolve()))

    def test_posteriori_split_without_output_marks_run_ko(self):
        source = self.tmp / "source.mbtiles"
        source.touch()
        self._reset_history(self._argv(
            source, "--file-formats", "rmap", "sqlitedb"))

        with mock.patch.object(L, "decouper_mbtiles", return_value=[]), \
             mock.patch.object(L, "generer_rmap_depuis_mbtiles") as rmap, \
             mock.patch.object(L, "generer_sqlitedb_depuis_mbtiles") as db, \
             self.assertRaises(SystemExit) as raised:
            L.main_decouper()

        self.assertEqual(raised.exception.code, 1)
        rmap.assert_not_called()
        db.assert_not_called()
        entry = self._entry()
        self.assertEqual(entry["statut"], "ko")
        self.assertEqual(entry["resultat"], str(self.tmp.resolve()))


class TeeLoggerChunkPrefixTests(unittest.TestCase):
    def test_terminal_prefixes_chunk_details_and_progress_without_duplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "chunk.log"
            terminal = io.StringIO()
            logger = L._TeeLogger(log_path)
            logger._terminal = terminal
            try:
                logger.definir_chunk("001x001:tuilage")
                logger.write("  ── Tuilage [001x001]  (1/4) ──\n")
                # Forme réelle de print : texte et saut de ligne séparés.
                logger.write("  Base tile format: JPEG")
                logger.write("\n")
                logger.write("\r  z10-18  10%")
                logger.write("\r  z10-18  100%\n")
                logger.write("  [001x001] tuilage done in 23s\n")
                logger.definir_chunk(None)
                logger.write("  Total time: 3m36s\n")
            finally:
                logger.close()

            output = terminal.getvalue()
            self.assertIn("  ── Tuilage [001x001]  (1/4) ──", output)
            self.assertNotIn(
                "[001x001:tuilage] ── Tuilage [001x001]", output
            )
            self.assertIn(
                "  [001x001:tuilage] Base tile format: JPEG\n", output
            )
            self.assertIn("\r  [001x001:tuilage] z10-18  10%", output)
            self.assertIn("\r  [001x001:tuilage] z10-18  100%\n", output)
            self.assertEqual(output.count("[001x001] tuilage done in 23s"), 1)
            self.assertIn("  Total time: 3m36s\n", output)
            self.assertNotIn("[001x001:tuilage] Total time", output)

            persisted = log_path.read_text(encoding="utf-8")
            self.assertIn(
                "[001x001:tuilage] Base tile format: JPEG", persisted
            )
            self.assertIn("Total time: 3m36s", persisted)
            self.assertNotIn(
                "[001x001:tuilage] Total time: 3m36s", persisted
            )


class SplitRunnerSignalTests(unittest.TestCase):
    ZONES = [
        (0, 0, 0.0, 0.0, 1000.0, 1000.0),
        (0, 1, 1000.0, 0.0, 2000.0, 1000.0),
    ]

    def setUp(self):
        self.prefetch_patch = mock.patch.object(
            L, "_PrefetchDalles", NoopPrefetch)
        self.lookahead_patch = mock.patch.object(
            L, "_dalles_zone_lookahead", return_value=None)
        self.prefetch_patch.start()
        self.lookahead_patch.start()

    def tearDown(self):
        self.lookahead_patch.stop()
        self.prefetch_patch.stop()

    def _args(self, root, **overrides):
        args = SimpleNamespace(
            dossier=str(root),
            min_free_gb=0.0,
            nettoyage=False,
            nettoyage_garder_dalles=False,
            mbtiles=True,
            rmap=False,
            sqlitedb=False,
            tuiles_ecraser=False,
            ombrages_ecraser=False,
            index_map=False,
        )
        for key, value in overrides.items():
            setattr(args, key, value)
        return args

    def test_classic_log_context_covers_header_and_excludes_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)
            events = []

            def record_context(value):
                events.append(("context", value))

            def record_print(*values, **_kwargs):
                events.append(("print", " ".join(map(str, values))))

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(
                     L, "_definir_chunk_log", side_effect=record_context
                 ), \
                 mock.patch.object(
                     L, "_chunk_livrable_complet", return_value=False
                 ), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch("builtins.print", side_effect=record_print):
                completed = L._run_split_priori(
                    args,
                    [self.ZONES[0]],
                    "1x1",
                    "zone",
                    root,
                    False,
                    lambda _coords: "bbox",
                    lambda *_args: None,
                    time.time(),
                )

            self.assertIs(completed, True)
            header = next(
                index for index, event in enumerate(events)
                if event[0] == "print" and "── Chunk 001x001" in event[1]
            )
            summary = next(
                index for index, event in enumerate(events)
                if event[0] == "print" and "A-priori splitting done" in event[1]
            )
            final_reset = max(
                index for index, event in enumerate(events)
                if event == ("context", None)
            )
            self.assertLess(events.index(("context", "001x001")), header)
            self.assertLess(header, final_reset)
            self.assertLess(final_reset, summary)

    def test_sliding_log_headers_identify_shading_and_tiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)
            zone = self.ZONES[0]
            events = []

            def record_context(value):
                events.append(("context", value))

            def record_print(*values, **_kwargs):
                events.append(("print", " ".join(map(str, values))))

            def shading(
                    _args, _coords, _name, _base, manifest, key, **_kwargs):
                print("shading-detail")
                manifest.enregistrer_fichier(root / f"{key}.tif", key)

            def tiling(*_args, **_kwargs):
                print("tiling-detail")
                return True

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(
                     L, "_definir_chunk_log", side_effect=record_context
                 ), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage", side_effect=shading
                 ), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage", side_effect=tiling
                 ), \
                 mock.patch.object(
                     L, "_chunk_livrable_complet", return_value=True
                 ), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch("builtins.print", side_effect=record_print):
                completed = L._run_split_priori_lidar_glissant(
                    args,
                    [zone],
                    "zone",
                    root,
                    False,
                    lambda _coords: "bbox",
                    time.time(),
                )

            self.assertIs(completed, True)

            def event_index(kind, fragment):
                return next(
                    index for index, event in enumerate(events)
                    if event[0] == kind and fragment in str(event[1])
                )

            shading_header = event_index(
                "print", "── Ombrage [001x001]  (1/1)"
            )
            tiling_header = event_index(
                "print", "── Tuilage [001x001]  (1/1)"
            )
            self.assertLess(shading_header, event_index("print", "shading-detail"))
            self.assertLess(tiling_header, event_index("print", "tiling-detail"))
            self.assertLess(
                event_index("context", "001x001:ombrage"), shading_header
            )
            self.assertLess(
                event_index("context", "001x001:tuilage"), tiling_header
            )
            final_reset = max(
                index for index, event in enumerate(events)
                if event == ("context", None)
            )
            self.assertLess(tiling_header, final_reset)
            self.assertLess(
                final_reset,
                event_index("print", "A-priori splitting done"),
            )

    def test_classic_runner_honors_explicit_chunk_failure_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_chunk_livrable_complet", return_value=True), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori(
                    args, self.ZONES, "2x1", "zone", root,
                    False, lambda _coords: "bbox",
                    lambda _coords, _name, _key, _manifest: False,
                    time.time())

            self.assertIs(completed, False)

    def test_classic_runner_passes_exact_expected_products_to_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)
            expected = root / "zone_001x001" / "current.mbtiles"
            seen = []

            def validate(_folder, _args, mbtiles_attendus):
                seen.append(tuple(mbtiles_attendus))
                return True

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(
                     L, "_chunk_livrable_complet", side_effect=validate), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori(
                    args, [self.ZONES[0]], "1x1", "zone", root,
                    False, lambda _coords: "bbox",
                    lambda *_args: L._ResultatChunk(True, [expected]),
                    time.time())

            self.assertIs(completed, True)
            self.assertEqual(seen, [(expected,)])

    def test_classic_resume_replays_only_chunk_with_missing_expected_derivative(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(
                root, mbtiles=False, rmap=True, sqlitedb=True)
            processed = []

            def produce(_coords, name, key, _manifest):
                processed.append(key)
                folder = root / name
                folder.mkdir(parents=True, exist_ok=True)
                expected = folder / "current.mbtiles"
                expected.with_suffix(".rmap").write_bytes(b"rmap")
                expected.with_suffix(".sqlitedb").write_bytes(b"db")
                # Une ancienne famille complete ne doit jamais masquer la
                # disparition d'un produit attendu du run courant.
                (folder / "stale.rmap").write_bytes(b"old")
                (folder / "stale.sqlitedb").write_bytes(b"old")
                return L._ResultatChunk(True, [expected])

            common = (
                mock.patch.object(L, "_garde_disque"),
                mock.patch.object(L, "_definir_chunk_log"),
                mock.patch.object(L, "_planche_depuis_dossier"),
            )
            with common[0], common[1], common[2]:
                first = L._run_split_priori(
                    args, self.ZONES, "2x1", "zone", root,
                    False, lambda _coords: "bbox", produce, time.time())

            self.assertIs(first, True)
            manifest = L.Manifeste(root / "zone" / "manifeste.json")
            expected_first = root / "zone_001x001" / "current.mbtiles"
            self.assertEqual(
                manifest.mbtiles_attendus_morceau("001x001"),
                (expected_first.resolve(),))
            expected_first.with_suffix(".sqlitedb").unlink()
            processed.clear()

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                second = L._run_split_priori(
                    args, self.ZONES, "2x1", "zone", root,
                    False, lambda _coords: "bbox", produce, time.time())

            self.assertIs(second, True)
            self.assertEqual(processed, ["001x001"])
            self.assertTrue(expected_first.with_suffix(".sqlitedb").is_file())

    def test_classic_resume_replays_legacy_done_chunk_without_output_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root, mbtiles=False, rmap=True)
            zones = [self.ZONES[0]]
            manifest = L.Manifeste(root / "zone" / "manifeste.json")
            manifest.verifier_signature(L._signature_config(args, zones))
            manifest.debut_morceau("001x001", "zone_001x001")
            manifest.fin_morceau("001x001", 1)
            expected = root / "zone_001x001" / "current.mbtiles"

            def produce(*_args):
                expected.parent.mkdir(parents=True, exist_ok=True)
                expected.with_suffix(".rmap").write_bytes(b"rmap")
                return L._ResultatChunk(True, [expected])

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori(
                    args, zones, "1x1", "zone", root,
                    False, lambda _coords: "bbox", produce, time.time())

            self.assertIs(completed, True)
            self.assertTrue(expected.with_suffix(".rmap").is_file())

    def test_classic_resume_replays_corrupt_expected_mbtiles_not_valid_stale_one(self):
        import sqlite3

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)
            zones = [self.ZONES[0]]
            expected = root / "zone_001x001" / "current.mbtiles"
            stale = root / "zone_001x001" / "stale.mbtiles"
            processed = []

            def valid_mbtiles(path):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.unlink(missing_ok=True)
                con = sqlite3.connect(path)
                try:
                    con.execute(
                        "CREATE TABLE tiles (zoom_level INTEGER, "
                        "tile_column INTEGER, tile_row INTEGER, "
                        "tile_data BLOB)")
                    con.execute(
                        "INSERT INTO tiles VALUES (0, 0, 0, ?)",
                        (sqlite3.Binary(b"tile"),))
                    con.commit()
                finally:
                    con.close()

            def produce(*_args):
                processed.append("001x001")
                valid_mbtiles(expected)
                if not stale.exists():
                    valid_mbtiles(stale)
                return L._ResultatChunk(True, [expected])

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                first = L._run_split_priori(
                    args, zones, "1x1", "zone", root,
                    False, lambda _coords: "bbox", produce, time.time())

            self.assertIs(first, True)
            expected.write_bytes(b"not a sqlite database")
            processed.clear()

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                second = L._run_split_priori(
                    args, zones, "1x1", "zone", root,
                    False, lambda _coords: "bbox", produce, time.time())

            self.assertIs(second, True)
            self.assertEqual(processed, ["001x001"])
            self.assertTrue(L._mbtiles_est_complete(expected))

    def test_classic_runner_returns_false_for_covered_incomplete_chunk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)

            def covered_without_output(_coords, _name, key, manifest):
                manifest.enregistrer_fichier(root / f"{key}.tif", key)

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori(
                    args, self.ZONES, "2x1", "zone", root,
                    False, lambda _coords: "bbox", covered_without_output,
                    time.time())

            self.assertIs(completed, False)

    def test_classic_runner_returns_true_for_chunks_without_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori(
                    args, self.ZONES, "2x1", "zone", root,
                    False, lambda _coords: "bbox",
                    lambda _coords, _name, _key, _manifest: None,
                    time.time())

            self.assertIs(completed, True)

    def test_classic_runner_treats_normal_empty_wmts_chunk_as_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori(
                    args, self.ZONES, "2x1", "zone", root,
                    False, lambda _coords: "bbox",
                    lambda _coords, _name, _key, _manifest: None,
                    time.time(), vide_sans_couverture_ok=False)

            self.assertIs(completed, False)

    def test_classic_runner_accepts_explicit_wmts_no_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)

            def outside_layer(_coords, _name, _key, _manifest):
                raise L.ZoneHorsCouvertureWMTS("outside layer")

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori(
                    args, self.ZONES, "2x1", "zone", root,
                    False, lambda _coords: "bbox", outside_layer,
                    time.time(), vide_sans_couverture_ok=False)

            self.assertIs(completed, True)

    def test_sliding_runner_returns_false_for_incomplete_tiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)
            zones = [
                (0, 0, 0.0, 0.0, 1000.0, 1000.0),
                (1, 0, 0.0, 1000.0, 1000.0, 2000.0),
            ]

            def shading_with_coverage(
                    _args, _coords, _name, _base, manifest, key, **_kwargs):
                manifest.enregistrer_fichier(root / f"{key}.tif", key)

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage",
                     side_effect=shading_with_coverage), \
                 mock.patch.object(L, "_traiter_bbox_lidar_tuilage"), \
                 mock.patch.object(L, "_chunk_livrable_complet", return_value=False), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori_lidar_glissant(
                    args, zones, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(completed, False)

    def test_sliding_runner_returns_true_for_chunks_without_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_traiter_bbox_lidar_ombrage"), \
                 mock.patch.object(L, "_traiter_bbox_lidar_tuilage"), \
                 mock.patch.object(L, "_chunk_livrable_complet", return_value=False), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori_lidar_glissant(
                    args, self.ZONES, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(completed, True)
            manifest = L.Manifeste(root / "zone" / "manifeste.json")
            self.assertTrue(manifest.deja_traite("001x001_t"))
            self.assertTrue(manifest.deja_traite("001x002_t"))
            self.assertEqual(
                manifest.mbtiles_attendus_morceau("001x001_t"), ())

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_traiter_bbox_lidar_ombrage") as shading, \
                 mock.patch.object(L, "_traiter_bbox_lidar_tuilage") as tiling, \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                resumed = L._run_split_priori_lidar_glissant(
                    args, self.ZONES, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(resumed, True)
            shading.assert_not_called()
            tiling.assert_not_called()

    def test_sliding_runner_honors_tiling_failure_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)

            def shading_with_coverage(
                    _args, _coords, _name, _base, manifest, key, **_kwargs):
                tif = root / f"{key}.tif"
                tif.write_bytes(b"shade")
                manifest.enregistrer_fichier(tif, key)

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage",
                     side_effect=shading_with_coverage), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage", return_value=False), \
                 mock.patch.object(L, "_chunk_livrable_complet", return_value=True), \
                 mock.patch.object(L, "_planche_depuis_dossier"):
                completed = L._run_split_priori_lidar_glissant(
                    args, self.ZONES, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(completed, False)

    def test_sliding_resume_recomputes_tracked_shading_that_disappeared(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)
            zones = [self.ZONES[0]]
            manifest = L.Manifeste(root / "zone" / "manifeste.json")
            manifest.verifier_signature(L._signature_config(args, zones))
            missing = root / "zone_001x001" / "old_shading.tif"
            manifest.debut_morceau("001x001", "zone_001x001")
            manifest.enregistrer_fichier(missing, "001x001")
            manifest.fin_morceau("001x001", 1)
            manifest.debut_morceau("001x001_t", "zone_001x001")

            def recreate(
                    _args, _coords, _name, _base, current, key, **_kwargs):
                replacement = root / "zone_001x001" / "new_shading.tif"
                replacement.parent.mkdir(parents=True, exist_ok=True)
                replacement.write_bytes(b"shade")
                current.enregistrer_fichier(replacement, key)

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage",
                     side_effect=recreate) as shading, \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage", return_value=True), \
                 mock.patch.object(
                     L, "_chunk_livrable_complet", return_value=True):
                completed = L._run_split_priori_lidar_glissant(
                    args, zones, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(completed, True)
            shading.assert_called_once()
            resumed = L.Manifeste(root / "zone" / "manifeste.json")
            self.assertNotIn(str(missing.resolve()),
                             resumed.fichiers_morceau("001x001"))
            self.assertTrue(resumed.deja_traite("001x001_t"))

    def test_sliding_resume_guards_disk_before_replayed_tiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root, min_free_gb=5.0)
            zones = [self.ZONES[0]]
            manifest = L.Manifeste(root / "zone" / "manifeste.json")
            manifest.verifier_signature(L._signature_config(args, zones))
            shading_path = root / "zone_001x001" / "shade.tif"
            shading_path.parent.mkdir(parents=True, exist_ok=True)
            shading_path.write_bytes(b"shade")
            manifest.debut_morceau("001x001", "zone_001x001")
            manifest.enregistrer_fichier(shading_path, "001x001")
            manifest.fin_morceau("001x001", 1)
            manifest.debut_morceau("001x001_t", "zone_001x001")
            events = []

            def guard(*_args):
                events.append("guard")

            def tile(*_args):
                events.append("tile")
                return True

            with mock.patch.object(L, "_garde_disque", side_effect=guard), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch.object(L, "_traiter_bbox_lidar_ombrage") as shading, \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage", side_effect=tile), \
                 mock.patch.object(
                     L, "_chunk_livrable_complet", return_value=True):
                completed = L._run_split_priori_lidar_glissant(
                    args, zones, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(completed, True)
            shading.assert_not_called()
            self.assertEqual(events, ["guard", "tile"])

    def test_sliding_resume_keeps_cleaned_shading_when_deliverable_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(
                root, nettoyage=True, mbtiles=False, rmap=True)
            zones = [self.ZONES[0]]
            expected = root / "zone_001x001" / "current.mbtiles"

            def shade(
                    _args, _coords, _name, _base, manifest, key, **_kwargs):
                tif = root / "zone_001x001" / "shade.tif"
                tif.parent.mkdir(parents=True, exist_ok=True)
                tif.write_bytes(b"shade")
                manifest.enregistrer_fichier(tif, key)

            def tile(*_args):
                expected.with_suffix(".rmap").write_bytes(b"rmap")
                return L._ResultatChunk(True, [expected])

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage", side_effect=shade), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage", side_effect=tile):
                first = L._run_split_priori_lidar_glissant(
                    args, zones, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(first, True)
            self.assertFalse((root / "zone_001x001" / "shade.tif").exists())

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch.object(L, "_traiter_bbox_lidar_ombrage") as shading, \
                 mock.patch.object(L, "_traiter_bbox_lidar_tuilage") as tiling:
                second = L._run_split_priori_lidar_glissant(
                    args, zones, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(second, True)
            shading.assert_not_called()
            tiling.assert_not_called()

    def test_sliding_resume_rebuilds_neighbor_shadings_for_missing_deliverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(
                root, nettoyage=True, mbtiles=False, rmap=True, sqlitedb=True)
            shaded = []
            tiled = []

            def shade(
                    _args, _coords, name, _base, manifest, key, **_kwargs):
                shaded.append(key)
                tif = root / name / "shade.tif"
                tif.parent.mkdir(parents=True, exist_ok=True)
                tif.write_bytes(b"shade")
                manifest.enregistrer_fichier(tif, key)

            def tile(_args, _coords, name, _base, _manifest, key, *_indices):
                tiled.append(key)
                expected = root / name / "current.mbtiles"
                expected.with_suffix(".rmap").write_bytes(b"rmap")
                expected.with_suffix(".sqlitedb").write_bytes(b"db")
                (root / name / "stale.rmap").write_bytes(b"old")
                (root / name / "stale.sqlitedb").write_bytes(b"old")
                return L._ResultatChunk(True, [expected])

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage", side_effect=shade), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage", side_effect=tile):
                first = L._run_split_priori_lidar_glissant(
                    args, self.ZONES, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(first, True)
            missing = root / "zone_001x001" / "current.sqlitedb"
            missing.unlink()
            shaded.clear()
            tiled.clear()

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage", side_effect=shade), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage", side_effect=tile):
                second = L._run_split_priori_lidar_glissant(
                    args, self.ZONES, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(second, True)
            self.assertEqual(shaded, ["001x001", "001x002"])
            self.assertEqual(tiled, ["001x001"])
            self.assertTrue(missing.is_file())

    def test_sliding_cleanup_preserves_incomplete_shading_until_retry_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root, nettoyage=True)
            shades = {}

            def create_shading(
                    _args, _coords, _name, _base, manifest, key, **_kwargs):
                tif = root / f"zone_{key}" / "shade.tif"
                tif.parent.mkdir(parents=True, exist_ok=True)
                tif.write_bytes(b"shade")
                manifest.enregistrer_fichier(tif, key)
                shades[key] = tif

            def tile_with_expected(
                    _args, _coords, name, _base, _manifest, _key, *_indices):
                return L._ResultatChunk(
                    True, [root / name / "current.mbtiles"])

            def first_completeness(folder, _args, _expected=None):
                return Path(folder).name != "zone_001x001"

            common = (
                mock.patch.object(L, "_garde_disque"),
                mock.patch.object(L, "_definir_chunk_log"),
                mock.patch.object(L, "_planche_depuis_dossier"),
            )
            with common[0], common[1], common[2], \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage",
                     side_effect=create_shading), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage",
                     side_effect=tile_with_expected), \
                 mock.patch.object(
                     L, "_chunk_livrable_complet",
                     side_effect=first_completeness):
                first = L._run_split_priori_lidar_glissant(
                    args, self.ZONES, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(first, False)
            self.assertEqual(set(shades), {"001x001", "001x002"})
            self.assertTrue(all(path.exists() for path in shades.values()))

            retried = []

            def tile_from_preserved_shading(
                    _args, _coords, name, _base, _manifest, key, *_indices):
                self.assertTrue(shades[key].exists())
                retried.append(key)
                return L._ResultatChunk(
                    True, [root / name / "current.mbtiles"])

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch.object(L, "_traiter_bbox_lidar_ombrage") as shading, \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage",
                     side_effect=tile_from_preserved_shading), \
                 mock.patch.object(L, "_chunk_livrable_complet", return_value=True):
                second = L._run_split_priori_lidar_glissant(
                    args, self.ZONES, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(second, True)
            shading.assert_not_called()
            self.assertEqual(retried, ["001x001"])
            self.assertTrue(all(not path.exists() for path in shades.values()))

    def test_sliding_cleanup_preserves_neighbor_rows_needed_by_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root, nettoyage=True)
            zones = [
                (row, 0, 0.0, row * 1000.0, 1000.0, (row + 1) * 1000.0)
                for row in range(4)
            ]
            shades = {}

            def create_shading(
                    _args, _coords, _name, _base, manifest, key, **_kwargs):
                tif = root / f"zone_{key}" / "shade.tif"
                tif.parent.mkdir(parents=True, exist_ok=True)
                tif.write_bytes(b"shade")
                manifest.enregistrer_fichier(tif, key)
                shades[key] = tif

            def tile_with_expected(
                    _args, _coords, name, _base, _manifest, _key, *_indices):
                return L._ResultatChunk(
                    True, [root / name / "current.mbtiles"])

            def first_completeness(folder, _args, _expected=None):
                return Path(folder).name != "zone_002x001"

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage",
                     side_effect=create_shading), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage",
                     side_effect=tile_with_expected), \
                 mock.patch.object(
                     L, "_chunk_livrable_complet",
                     side_effect=first_completeness):
                first = L._run_split_priori_lidar_glissant(
                    args, zones, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(first, False)
            self.assertTrue(shades["001x001"].exists())
            self.assertTrue(shades["002x001"].exists())
            self.assertTrue(shades["003x001"].exists())
            self.assertFalse(shades["004x001"].exists())

            retried = []

            def retry_tiling(
                    _args, _coords, name, _base, _manifest, key, *_indices):
                retried.append(key)
                for neighbor in ("001x001", "002x001", "003x001"):
                    self.assertTrue(shades[neighbor].exists())
                return L._ResultatChunk(
                    True, [root / name / "current.mbtiles"])

            with mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(L, "_planche_depuis_dossier"), \
                 mock.patch.object(L, "_traiter_bbox_lidar_ombrage") as shading, \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_tuilage",
                     side_effect=retry_tiling), \
                 mock.patch.object(L, "_chunk_livrable_complet", return_value=True):
                second = L._run_split_priori_lidar_glissant(
                    args, zones, "zone", root, False,
                    lambda _coords: "bbox", time.time())

            self.assertIs(second, True)
            shading.assert_not_called()
            self.assertEqual(retried, ["002x001"])
            self.assertTrue(all(not path.exists() for path in shades.values()))

    def test_sliding_runner_purges_prefetch_after_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)

            class PrefetchProbe:
                instance = None

                def __init__(self):
                    self.purged = False
                    PrefetchProbe.instance = self

                def lancer(self, *_args, **_kwargs):
                    return None

                def recuperer(self, _key):
                    return None

                def purger(self):
                    self.purged = True

            with mock.patch.object(L, "_PrefetchDalles", PrefetchProbe), \
                 mock.patch.object(L, "_garde_disque"), \
                 mock.patch.object(L, "_definir_chunk_log"), \
                 mock.patch.object(
                     L, "_traiter_bbox_lidar_ombrage",
                     side_effect=RuntimeError("forced shading failure")):
                with self.assertRaisesRegex(RuntimeError, "forced shading failure"):
                    L._run_split_priori_lidar_glissant(
                        args, self.ZONES, "zone", root, False,
                        lambda _coords: "bbox", time.time())

            self.assertIsNotNone(PrefetchProbe.instance)
            self.assertTrue(PrefetchProbe.instance.purged)


class ChunkDeliverableContractTests(unittest.TestCase):
    @staticmethod
    def _args(**values):
        defaults = {"mbtiles": False, "rmap": False, "sqlitedb": False}
        defaults.update(values)
        return SimpleNamespace(**defaults)

    def test_every_requested_derived_format_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "shade.rmap").write_bytes(b"rmap")
            args = self._args(rmap=True, sqlitedb=True)

            self.assertFalse(L._chunk_livrable_complet(root, args))

            (root / "shade.sqlitedb").write_bytes(b"db")
            self.assertTrue(L._chunk_livrable_complet(root, args))

    def test_empty_current_shading_list_does_not_reuse_stale_tifs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = root / "old_lrm.tif"
            stale.write_bytes(b"old")

            self.assertEqual(L._lister_tifs_ombrages(root, []), [])
            self.assertEqual(L._lister_tifs_ombrages(root, None), [stale])

    def test_derived_formats_must_refer_to_the_same_product_stems(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "shade_a.rmap").write_bytes(b"rmap")
            (root / "shade_b.sqlitedb").write_bytes(b"db")

            self.assertFalse(L._chunk_livrable_complet(
                root, self._args(rmap=True, sqlitedb=True)))

    def test_requested_derived_format_is_required_alongside_mbtiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "shade.mbtiles").write_bytes(b"mbtiles")
            args = self._args(mbtiles=True, rmap=True)

            with mock.patch.object(L, "_mbtiles_est_complete", return_value=True):
                self.assertFalse(L._chunk_livrable_complet(root, args))
                (root / "shade.rmap").write_bytes(b"rmap")
                self.assertTrue(L._chunk_livrable_complet(root, args))

    def test_each_mbtiles_stem_requires_its_requested_derivative(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for stem in ("shade_a", "shade_b"):
                (root / f"{stem}.mbtiles").write_bytes(b"mbtiles")
            (root / "shade_a.rmap").write_bytes(b"rmap")
            args = self._args(mbtiles=True, rmap=True)
            expected = [root / "shade_a.mbtiles", root / "shade_b.mbtiles"]

            with mock.patch.object(L, "_mbtiles_est_complete", return_value=True):
                self.assertFalse(L._chunk_livrable_complet(
                    root, args, expected))
                (root / "shade_b.rmap").write_bytes(b"rmap")
                self.assertTrue(L._chunk_livrable_complet(
                    root, args, expected))

    def test_expected_products_ignore_obsolete_files_but_not_missing_current_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "relief.v2.mbtiles"
            old = root / "old.mbtiles"
            current.write_bytes(b"current")
            old.write_bytes(b"corrupt old file")
            (root / "relief.v2.rmap").write_bytes(b"rmap")
            (root / "relief.v2.sqlitedb").write_bytes(b"db")
            (root / "old.rmap").write_bytes(b"stale")
            args = self._args(mbtiles=True, rmap=True, sqlitedb=True)

            def complete(path):
                return Path(path) == current

            with mock.patch.object(
                    L, "_mbtiles_est_complete", side_effect=complete):
                self.assertTrue(L._chunk_livrable_complet(
                    root, args, [current]))
                self.assertFalse(L._chunk_livrable_complet(
                    root, args, [current, root / "missing.mbtiles"]))

    def test_old_complete_family_cannot_replace_expected_current_product(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "old.rmap").write_bytes(b"rmap")
            (root / "old.sqlitedb").write_bytes(b"db")
            current = root / "current.mbtiles"
            args = self._args(rmap=True, sqlitedb=True)

            self.assertFalse(L._chunk_livrable_complet(
                root, args, [current]))

    def test_conversion_helpers_return_aggregate_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "shade.mbtiles"
            source.write_bytes(b"mbtiles")
            args = self._args(rmap=True, sqlitedb=True)

            with mock.patch.object(
                     L, "generer_rmap_depuis_mbtiles",
                     return_value=source.with_suffix(".rmap")), \
                 mock.patch.object(
                     L, "generer_sqlitedb_depuis_mbtiles", return_value=None):
                completed = L._convertir_formats(
                    source, args, decoupe_sortie=False, mbtiles_neuf=True)

            self.assertIs(completed, False)
            self.assertTrue(source.exists())

    def test_split_conversion_does_not_short_circuit_after_first_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mbtiles"
            first = root / "first.mbtiles"
            second = root / "second.mbtiles"
            source.write_bytes(b"source")
            args = self._args(rmap=True)
            args.cols_decoupe = 2
            args.rows_decoupe = 1
            args.split_width = 0.0
            args.tuiles_ecraser = False

            with mock.patch.object(
                     L, "decouper_mbtiles", return_value=[first, second]), \
                 mock.patch.object(
                     L, "_convertir_un_mbtiles",
                     side_effect=[False, True]) as convert:
                completed = L._convertir_formats(source, args)

            self.assertIs(completed, False)
            self.assertEqual(convert.call_count, 2)

    def test_output_format_change_invalidates_split_signature(self):
        zones = [(0, 0, 0.0, 0.0, 1000.0, 1000.0)]
        args = self._args(mbtiles=True)
        first = L._signature_config(args, zones)

        args.rmap = True
        second = L._signature_config(args, zones)

        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
