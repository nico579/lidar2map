"""Caracterisation hors reseau du rasteriseur GeoJSON transparent."""

from __future__ import annotations

import contextlib
import gzip
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lidar2map as L  # noqa: E402


class GeojsonRasterCharacterizationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        L._stop_event.clear()

    def tearDown(self):
        L._stop_event.clear()
        self._tmp.cleanup()

    @staticmethod
    def _line_feature() -> dict:
        return {
            "type": "Feature",
            "properties": {"_cle": "highway", "highway": "track"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[6.044, 43.328], [6.046, 43.330]],
            },
        }

    @staticmethod
    def _point_feature() -> dict:
        return {
            "type": "Feature",
            "properties": {"source": "batiment"},
            "geometry": {"type": "Point", "coordinates": [6.045, 43.329]},
        }

    def _write_geojson(
        self,
        path: Path,
        features: list[dict],
    ) -> None:
        payload = {"type": "FeatureCollection", "features": features}
        if path.suffix == ".gz":
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                json.dump(payload, stream)
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")

    def _run(
        self,
        source: Path,
        final: Path,
        **kwargs,
    ):
        options = {
            "zoom_min": 14,
            "zoom_max": 14,
            "ecraser": True,
            "supersample": 1,
        }
        options.update(kwargs)
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            return L.rasteriser_geojson_transparent(
                source,
                final,
                **options,
            )

    def _assert_no_sqlite_staging(self) -> None:
        residues = [
            path
            for path in self.root.rglob("*")
            if path.is_file()
            and (
                ".part" in path.name
                or path.name.endswith("-wal")
                or path.name.endswith("-shm")
                or path.name.endswith("-journal")
            )
        ]
        self.assertEqual(residues, [])

    @staticmethod
    def _deg_to_tile_failure_after_sqlite_open(error):
        """Echoue au premier appel de ``deg_to_tile`` apres sqlite3.connect.

        Avec un seul niveau de zoom, le rasteriseur appelle deux fois ce helper
        pour estimer la grille, ouvre ensuite le chantier SQLite, puis le
        rappelle pour construire les buckets du niveau. Le troisieme appel est
        donc une couture deterministe pour caracteriser un abandon apres
        ouverture de la base, sans alourdir le jeu de geometries.
        """
        original = L.deg_to_tile
        calls = 0

        def fail(lat, lon, zoom):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise error
            return original(lat, lon, zoom)

        return fail

    @staticmethod
    @contextlib.contextmanager
    def _capture_sqlite_connections():
        """Capture et referme par securite les handles SQLite du scenario."""
        original = L.sqlite3.connect
        connections = []

        def connect(*args, **kwargs):
            connection = original(*args, **kwargs)
            connections.append(connection)
            return connection

        try:
            with mock.patch.object(L.sqlite3, "connect", side_effect=connect):
                yield
        finally:
            for connection in connections:
                connection.close()

    def test_existing_output_is_reused_and_missing_source_is_non_destructive(self):
        source = self.root / "missing.geojson"
        final = self.root / "existing.sqlitedb"
        previous = b"previous-overlay"
        final.write_bytes(previous)

        reused = self._run(source, final, ecraser=False)
        self.assertEqual(reused, final)
        self.assertEqual(final.read_bytes(), previous)

        regenerated = self._run(source, final, ecraser=True)
        self.assertIsNone(regenerated)
        self.assertEqual(final.read_bytes(), previous)
        self._assert_no_sqlite_staging()

    def test_non_drawable_or_outside_features_keep_previous_final(self):
        cases = (
            (
                "point",
                [self._point_feature()],
                None,
            ),
            (
                "outside-bbox",
                [self._line_feature()],
                (7.0, 44.0, 7.01, 44.01),
            ),
        )
        for name, features, bbox in cases:
            with self.subTest(case=name):
                source = self.root / f"{name}.geojson"
                final = self.root / f"{name}.sqlitedb"
                previous = f"previous-{name}".encode()
                self._write_geojson(source, features)
                final.write_bytes(previous)

                result = self._run(source, final, bbox_wgs84=bbox)

                self.assertIsNone(result)
                self.assertEqual(final.read_bytes(), previous)
                self._assert_no_sqlite_staging()

    def test_gzip_success_uses_atomic_staging_and_writes_osmand_png_tiles(self):
        source = self.root / "zone_ign_routes.geojson.gz"
        final = self.root / "overlay.sqlitedb"
        final.write_bytes(b"previous-overlay")
        self._write_geojson(source, [self._line_feature()])
        seen = []
        original_chemin_part = L._chemin_part

        def record_part(path):
            target = Path(path)
            part = original_chemin_part(target)
            seen.append((target, part))
            return part

        with mock.patch.object(L, "_chemin_part", side_effect=record_part):
            result = self._run(source, final)

        self.assertEqual(result, final)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], final)
        self.assertEqual(seen[0][1].suffix, ".part")
        self.assertFalse(seen[0][1].exists())

        connection = sqlite3.connect(str(final))
        try:
            info = connection.execute(
                "SELECT minzoom, maxzoom, tilenumbering FROM info"
            ).fetchone()
            locale = connection.execute(
                "SELECT locale FROM android_metadata"
            ).fetchone()
            rows = connection.execute(
                "SELECT z, image FROM tiles ORDER BY z, x, y"
            ).fetchall()
        finally:
            connection.close()

        self.assertEqual(info, (14, 14, "simple"))
        self.assertEqual(locale, ("fr_FR",))
        self.assertTrue(rows)
        self.assertEqual({row[0] for row in rows}, {14})
        self.assertTrue(all(row[1].startswith(b"\x89PNG\r\n\x1a\n") for row in rows))

        image = Image.open(io.BytesIO(rows[0][1])).convert("RGBA")
        self.assertEqual(image.size, (256, 256))
        alpha_min, alpha_max = image.getchannel("A").getextrema()
        self.assertEqual(alpha_min, 0)
        self.assertGreater(alpha_max, 0)
        self._assert_no_sqlite_staging()

    def test_validation_failure_keeps_previous_final_after_close_and_cleans(self):
        source = self.root / "validation.geojson"
        final = self.root / "validation.sqlitedb"
        previous = b"previous-overlay"
        self._write_geojson(source, [self._line_feature()])
        final.write_bytes(previous)
        validations = []

        def reject_after_close(part, tables):
            part = Path(part)
            probe = part.with_name(f"{part.name}.closed-probe")
            part.replace(probe)
            probe.replace(part)
            validations.append((part, tables))
            raise RuntimeError("invalid transparent raster staging")

        original_cleanup = L._nettoyer_sqlite_part
        with mock.patch.object(
            L,
            "_valider_sqlite_part",
            side_effect=reject_after_close,
        ), mock.patch.object(
            L,
            "_nettoyer_sqlite_part",
            wraps=original_cleanup,
        ) as cleanup:
            with self.assertRaises(RuntimeError):
                self._run(source, final)

        self.assertEqual(len(validations), 1)
        self.assertGreater(validations[0][1]["tiles"], 0)
        self.assertEqual(validations[0][1]["android_metadata"], 1)
        self.assertEqual(validations[0][1]["info"], 1)
        cleanup.assert_called_once_with(validations[0][0])
        self.assertEqual(final.read_bytes(), previous)
        self.assertEqual(list(self.root.rglob("*.closed-probe")), [])
        self._assert_no_sqlite_staging()

    def test_keyboard_interrupt_after_sqlite_open_cleans_all_staging(self):
        """Une interruption apres ouverture nettoie le chantier atomique."""
        source = self.root / "interrupt-after-open.geojson"
        final = self.root / "interrupt-after-open.sqlitedb"
        previous = b"previous-overlay"
        self._write_geojson(source, [self._line_feature()])
        final.write_bytes(previous)
        failure = self._deg_to_tile_failure_after_sqlite_open(
            KeyboardInterrupt("forced after sqlite open")
        )

        with self._capture_sqlite_connections():
            with mock.patch.object(L, "deg_to_tile", side_effect=failure):
                with self.assertRaises(KeyboardInterrupt):
                    self._run(source, final)

        self.assertEqual(final.read_bytes(), previous)
        self._assert_no_sqlite_staging()

    def test_exception_after_sqlite_open_cleans_all_staging(self):
        """Une exception apres ouverture nettoie le chantier atomique."""
        source = self.root / "exception-after-open.geojson"
        final = self.root / "exception-after-open.sqlitedb"
        previous = b"previous-overlay"
        self._write_geojson(source, [self._line_feature()])
        final.write_bytes(previous)
        failure = self._deg_to_tile_failure_after_sqlite_open(
            RuntimeError("forced after sqlite open")
        )

        with self._capture_sqlite_connections():
            with mock.patch.object(L, "deg_to_tile", side_effect=failure):
                with self.assertRaises(RuntimeError):
                    self._run(source, final)

        self.assertEqual(final.read_bytes(), previous)
        self._assert_no_sqlite_staging()

    def test_publication_replace_failure_cleans_staging_and_keeps_previous(self):
        """Un echec de publication conserve l'ancien livrable sans residu."""
        source = self.root / "replace-failure.geojson"
        final = self.root / "replace-failure.sqlitedb"
        previous = b"previous-overlay"
        self._write_geojson(source, [self._line_feature()])
        final.write_bytes(previous)

        with mock.patch.object(
            Path,
            "replace",
            side_effect=OSError("forced publication failure"),
        ):
            with self.assertRaises(OSError):
                self._run(source, final)

        self.assertEqual(final.read_bytes(), previous)
        self._assert_no_sqlite_staging()

    def test_cooperative_stop_keeps_previous_final_without_staging(self):
        source = self.root / "interrupted.geojson"
        final = self.root / "interrupted.sqlitedb"
        previous = b"previous-overlay"
        self._write_geojson(source, [self._line_feature()])
        final.write_bytes(previous)
        stop_event = mock.Mock()
        stop_event.is_set.return_value = True

        with mock.patch.object(L, "_stop_event", stop_event):
            with self.assertRaises(KeyboardInterrupt):
                self._run(source, final)

        stop_event.is_set.assert_called()
        self.assertEqual(final.read_bytes(), previous)
        self._assert_no_sqlite_staging()


if __name__ == "__main__":
    unittest.main(verbosity=2)
