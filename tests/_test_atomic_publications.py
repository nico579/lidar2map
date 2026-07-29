"""Régressions ciblées des publications atomiques hors téléchargements.

Usage :
    python Tests/_test_atomic_publications.py
"""

import contextlib
import gzip
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
APP = Path(__file__).resolve().parent.parent / "lidar2map.py"
sys.path.insert(0, str(APP.parent))
SPEC = importlib.util.spec_from_file_location("l2m_atomic_publications", APP)
L = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = L
SPEC.loader.exec_module(L)


class AtomicPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_ctx.name)
        L._stop_event.clear()

    def tearDown(self):
        L._stop_event.clear()
        self.tmp_ctx.cleanup()

    def _assert_no_part(self):
        self.assertEqual(list(self.tmp.rglob("*.part")), [])

    def _record_part_paths(self):
        seen = []
        original = L._chemin_part

        def recorder(path):
            part = original(path)
            seen.append(part)
            self.assertEqual(part.suffix, ".part")
            return part

        return seen, recorder

    def test_atomic_text_failure_keeps_previous_final(self):
        final = self.tmp / "dalles_zone.txt"
        final.write_text("old", encoding="utf-8")
        seen, recorder = self._record_part_paths()

        with mock.patch.object(L, "_chemin_part", side_effect=recorder), \
             mock.patch.object(L.os, "replace",
                               side_effect=OSError("publication failed")):
            with self.assertRaises(OSError):
                L._ecrire_texte_atomique(final, "new")

        self.assertEqual(final.read_text(encoding="utf-8"), "old")
        self.assertTrue(seen)
        self._assert_no_part()

    def test_atomic_text_success_uses_part_and_leaves_no_staging(self):
        final = self.tmp / "dalles_zone.txt"
        final.write_text("old", encoding="utf-8")
        seen, recorder = self._record_part_paths()

        with mock.patch.object(L, "_chemin_part", side_effect=recorder):
            L._ecrire_texte_atomique(final, "new")

        self.assertEqual(final.read_text(encoding="utf-8"), "new")
        self.assertTrue(seen)
        self._assert_no_part()

    def _run_osm_map(self, fake_runner):
        source = self.tmp / "source.osm.pbf"
        source.write_bytes(b"source")
        with mock.patch.object(L, "_nettoyer_osmosis_temp_orphelins"), \
             mock.patch.object(L, "_verifier_mapwriter", return_value=True), \
             mock.patch.object(L, "_preparer_osmosis",
                               return_value=("osmosis", "java-home")), \
             mock.patch.object(L, "_run_osmosis_streaming",
                               side_effect=fake_runner), \
             mock.patch.object(L, "_sig_sidecar_ecrire"):
            with contextlib.redirect_stdout(io.StringIO()):
                return L.generer_carte_osm(
                    (6.0, 43.0, 6.1, 43.1),
                    self.tmp,
                    "zone",
                    source,
                    export_geojson=False,
                    ecraser_tuiles=True,
                )

    def _osmosis_output_parts(self, command):
        outputs = []
        for arg in command:
            value = str(arg)
            if not value.startswith("file="):
                continue
            path = Path(value.split("=", 1)[1])
            if ".map." in path.name or "_filtered.pbf." in path.name:
                outputs.append(path)
        self.assertEqual(len(outputs), 2)
        for path in outputs:
            self.assertEqual(path.suffix, ".part")
        return outputs

    def test_osmosis_failure_keeps_map_and_filtered_pbf(self):
        final_map = self.tmp / "zone.map"
        final_pbf = self.tmp / "zone_filtered.pbf"
        final_map.write_bytes(b"old-map")
        final_pbf.write_bytes(b"old-pbf")
        seen = []

        def runner(command, **_kwargs):
            outputs = self._osmosis_output_parts(command)
            seen.extend(outputs)
            for path in outputs:
                path.write_bytes(b"partial")
            return 7, "forced failure"

        result = self._run_osm_map(runner)

        self.assertIsNone(result)
        self.assertEqual(final_map.read_bytes(), b"old-map")
        self.assertEqual(final_pbf.read_bytes(), b"old-pbf")
        self.assertTrue(seen)
        self._assert_no_part()

    def test_osmosis_success_publishes_both_and_cleans_parts(self):
        final_map = self.tmp / "zone.map"
        final_pbf = self.tmp / "zone_filtered.pbf"
        final_map.write_bytes(b"old-map")
        final_pbf.write_bytes(b"old-pbf")
        seen = []

        def runner(command, **_kwargs):
            outputs = self._osmosis_output_parts(command)
            seen.extend(outputs)
            for path in outputs:
                if ".map." in path.name:
                    path.write_bytes(b"new-map")
                else:
                    path.write_bytes(b"new-pbf")
            return 0, ""

        result = self._run_osm_map(runner)

        self.assertEqual(result, final_map)
        self.assertEqual(final_map.read_bytes(), b"new-map")
        self.assertEqual(final_pbf.read_bytes(), b"new-pbf")
        self.assertTrue(seen)
        self._assert_no_part()

    def _write_point_geojson(self, path):
        path.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [6.05, 43.05]},
                "properties": {"source": "batiment"},
            }],
        }), encoding="utf-8")

    def test_osm_xml_interruption_keeps_previous_final(self):
        source = self.tmp / "source.geojson"
        self._write_point_geojson(source)
        final = self.tmp / "zone_ign.osm"
        final.write_bytes(b"old-osm")
        L._stop_event.set()

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                L.geojson_ign_vers_osm_xml(source, final)

        self.assertEqual(final.read_bytes(), b"old-osm")
        self._assert_no_part()

    def test_osm_xml_success_publishes_and_cleans_parts(self):
        source = self.tmp / "source.geojson"
        self._write_point_geojson(source)
        final = self.tmp / "zone_ign.osm"
        final.write_bytes(b"old-osm")
        seen, recorder = self._record_part_paths()

        with mock.patch.object(L, "_chemin_part", side_effect=recorder), \
             contextlib.redirect_stdout(io.StringIO()):
            result = L.geojson_ign_vers_osm_xml(source, final)

        self.assertTrue(result)
        self.assertIn(b"<osm ", final.read_bytes())
        self.assertTrue(seen)
        self._assert_no_part()

    def test_ign_map_runner_exception_keeps_previous_final(self):
        source = self.tmp / "source.geojson"
        self._write_point_geojson(source)
        final = self.tmp / "zone_ign.map"
        final.write_bytes(b"old-map")
        seen = []

        def convert(_source, osm_path, epsilon=None):
            Path(osm_path).write_bytes(b"<osm/>")
            return True

        def runner(command, **_kwargs):
            outputs = [
                Path(str(arg).split("=", 1)[1])
                for arg in command
                if str(arg).startswith("file=")
                and ".map." in str(arg)
            ]
            self.assertEqual(len(outputs), 1)
            self.assertEqual(outputs[0].suffix, ".part")
            seen.extend(outputs)
            outputs[0].write_bytes(b"partial-map")
            raise RuntimeError("forced osmosis exception")

        with mock.patch.object(L, "geojson_ign_vers_osm_xml",
                               side_effect=convert), \
             mock.patch.object(L, "_preparer_osmosis",
                               return_value=("osmosis", "java-home")), \
             mock.patch.object(L, "_run_osmosis_streaming",
                               side_effect=runner), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                L.generer_map_depuis_geojson_ign(
                    source,
                    self.tmp,
                    "zone",
                    (6.0, 43.0, 6.1, 43.1),
                    ecraser=True,
                )

        self.assertTrue(seen)
        self.assertEqual(final.read_bytes(), b"old-map")
        self._assert_no_part()

    def test_geojson_stream_error_keeps_previous_gzip(self):
        source = self.tmp / "broken.geojson"
        source.write_text('{"type":"FeatureCollection","features":[', encoding="utf-8")
        final = self.tmp / "layer.geojson.gz"
        with gzip.open(final, "wt", encoding="utf-8") as fh:
            json.dump({"type": "FeatureCollection", "features": []}, fh)
        old = final.read_bytes()

        with self.assertRaises(Exception):
            with contextlib.redirect_stdout(io.StringIO()):
                L._streamer_geojson_ajout_source(source, final, "layer")

        self.assertEqual(final.read_bytes(), old)
        self._assert_no_part()

    def _fake_osmium(self, fail_after_first=False):
        test = self

        class Object:
            tags = {"highway": "track", "name": "test"}

            @staticmethod
            def is_node():
                return True

            @staticmethod
            def is_way():
                return False

            @staticmethod
            def is_closed():
                return False

            @staticmethod
            def is_area():
                return False

        class FileProcessor:
            def __init__(self, _path):
                pass

            def with_locations(self):
                return self

            def with_areas(self):
                return self

            def __iter__(self):
                yield Object()
                if fail_after_first:
                    parts = list(test.tmp.rglob("*.part"))
                    test.assertTrue(parts)
                    test.assertTrue(all(p.suffix == ".part" for p in parts))
                    raise RuntimeError("forced PyOsmium failure")

        class Factory:
            @staticmethod
            def create_point(_obj):
                return '{"type":"Point","coordinates":[6.05,43.05]}'

        return types.SimpleNamespace(
            FileProcessor=FileProcessor,
            geom=types.SimpleNamespace(GeoJSONFactory=Factory),
        )

    def _osm_geojson_finals(self):
        return [
            self.tmp / "zone_osm.geojson.gz",
            self.tmp / "zone_osm.geojson",
            self.tmp / "zone_osm_highway.geojson.gz",
            self.tmp / "zone_osm_highway.geojson",
        ]

    def test_osm_geojson_failure_keeps_all_previous_finals(self):
        source = self.tmp / "source.pbf"
        source.write_bytes(b"pbf")
        finals = self._osm_geojson_finals()
        for index, final in enumerate(finals):
            final.write_bytes(f"old-{index}".encode())
        old = {final: final.read_bytes() for final in finals}

        with mock.patch.dict(
                sys.modules, {"osmium": self._fake_osmium(True)}), \
             contextlib.redirect_stdout(io.StringIO()):
            result = L.generer_geojson_osm(
                (6.0, 43.0, 6.1, 43.1),
                self.tmp,
                "zone",
                source,
                osm_tags=["highway=*"],
                ecraser_tuiles=True,
                formats=["gz", "geojson"],
            )

        self.assertIsNone(result)
        self.assertEqual(
            {final: final.read_bytes() for final in finals},
            old,
        )
        self._assert_no_part()

    def test_osm_geojson_success_publishes_complete_set(self):
        source = self.tmp / "source.pbf"
        source.write_bytes(b"pbf")
        finals = self._osm_geojson_finals()
        for final in finals:
            final.write_bytes(b"old")
        seen, recorder = self._record_part_paths()

        with mock.patch.dict(
                sys.modules, {"osmium": self._fake_osmium(False)}), \
             mock.patch.object(L, "_chemin_part", side_effect=recorder), \
             contextlib.redirect_stdout(io.StringIO()):
            result = L.generer_geojson_osm(
                (6.0, 43.0, 6.1, 43.1),
                self.tmp,
                "zone",
                source,
                osm_tags=["highway=*"],
                ecraser_tuiles=True,
                formats=["gz", "geojson"],
            )

        self.assertEqual(result, finals[0])
        for final in finals:
            opener = gzip.open if final.suffix == ".gz" else open
            with opener(final, "rt", encoding="utf-8") as fh:
                payload = json.load(fh)
            self.assertEqual(len(payload["features"]), 1)
        self.assertTrue(seen)
        self._assert_no_part()

    def _fake_fiona_modules(self, fail_after_first=False):
        test = self

        class Dataset:
            crs = "EPSG:2154"

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def __iter__(self):
                yield {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [700000.0, 6600000.0],
                    },
                    "properties": {"nom": "test"},
                }
                if fail_after_first:
                    parts = list(test.tmp.rglob("*.part"))
                    test.assertTrue(parts)
                    test.assertTrue(all(p.suffix == ".part" for p in parts))
                    raise RuntimeError("forced Fiona failure")

            def filter(self, bbox=None):
                return iter(self)

        fiona = types.ModuleType("fiona")
        fiona.__path__ = []
        fiona.open = lambda *_args, **_kwargs: Dataset()
        transform = types.ModuleType("fiona.transform")
        transform.transform_geom = lambda _src, _dst, geom: geom
        model = types.ModuleType("fiona.model")
        model.to_dict = lambda value: value
        return {
            "fiona": fiona,
            "fiona.transform": transform,
            "fiona.model": model,
        }

    @staticmethod
    def _fake_transformer():
        class Transformer:
            @staticmethod
            def transform(x, y):
                if isinstance(x, list):
                    return [6.05 for _ in x], [43.05 for _ in y]
                return 6.05, 43.05

        return Transformer()

    def test_bdtopo_extraction_failure_keeps_previous_formats(self):
        final_gz = self.tmp / "zone_ign_batiment.geojson.gz"
        final_raw = self.tmp / "zone_ign_batiment.geojson"
        final_gz.write_bytes(b"old-gz")
        final_raw.write_bytes(b"old-raw")

        with mock.patch.dict(
                sys.modules, self._fake_fiona_modules(True)), \
             mock.patch.object(L, "_get_transformer",
                               return_value=self._fake_transformer()), \
             contextlib.redirect_stdout(io.StringIO()):
            result = L._extraire_couche_bdtopo(
                self.tmp / "source.gpkg",
                "batiment",
                final_gz,
                ecraser=True,
                formats=["gz", "geojson"],
            )

        self.assertIsNone(result)
        self.assertEqual(final_gz.read_bytes(), b"old-gz")
        self.assertEqual(final_raw.read_bytes(), b"old-raw")
        self._assert_no_part()

    def test_bdtopo_extraction_publishes_formats_after_validation(self):
        final_gz = self.tmp / "zone_ign_batiment.geojson.gz"
        final_raw = self.tmp / "zone_ign_batiment.geojson"
        final_gz.write_bytes(b"old-gz")
        final_raw.write_bytes(b"old-raw")
        seen, recorder = self._record_part_paths()

        with mock.patch.dict(
                sys.modules, self._fake_fiona_modules(False)), \
             mock.patch.object(L, "_get_transformer",
                               return_value=self._fake_transformer()), \
             mock.patch.object(L, "_chemin_part", side_effect=recorder), \
             contextlib.redirect_stdout(io.StringIO()):
            result = L._extraire_couche_bdtopo(
                self.tmp / "source.gpkg",
                "batiment",
                final_gz,
                ecraser=True,
                formats=["gz", "geojson"],
            )

        self.assertEqual(result, final_gz)
        for final in (final_gz, final_raw):
            opener = gzip.open if final.suffix == ".gz" else open
            with opener(final, "rt", encoding="utf-8") as fh:
                payload = json.load(fh)
            self.assertEqual(len(payload["features"]), 1)
        self.assertTrue(seen)
        self._assert_no_part()

    def test_fusion_success_publishes_and_cleans_part(self):
        source = self.tmp / "source.geojson"
        source.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [6.0, 43.0]},
                "properties": {},
            }],
        }), encoding="utf-8")
        final = self.tmp / "fusion.geojson"
        final.write_text("old", encoding="utf-8")
        seen, recorder = self._record_part_paths()

        with mock.patch.object(L, "_chemin_part", side_effect=recorder), \
             contextlib.redirect_stdout(io.StringIO()):
            result, bbox = L.fusionner_geojson([source], final)

        self.assertEqual(result, final)
        self.assertEqual(bbox, (6.0, 43.0, 6.0, 43.0))
        self.assertEqual(
            len(json.loads(final.read_text(encoding="utf-8"))["features"]),
            1,
        )
        self.assertTrue(seen)
        self._assert_no_part()

    def test_horn_invalid_part_keeps_previous_final(self):
        source = self.tmp / "source.tif"
        source.write_bytes(b"dem")
        final = self.tmp / "zone_315_ombrage.tif"
        final.write_bytes(b"old-valid-tif")
        seen = []

        def writer(_source, jobs, **_kwargs):
            self.assertEqual(len(jobs), 1)
            part = Path(jobs[0][2])
            self.assertEqual(part.suffix, ".part")
            seen.append(part)
            part.write_bytes(b"invalid-new-tif")
            return True

        with mock.patch.object(L, "_source_a_des_donnees", return_value=True), \
             mock.patch.object(L, "_hillshade_chunked_multi",
                               side_effect=writer), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=False), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                L.generer_ombrages(
                    [source],
                    self.tmp,
                    choix=["315"],
                    nom_zone="zone",
                    ecraser_ombrages=True,
                )

        self.assertTrue(seen)
        self.assertEqual(final.read_bytes(), b"old-valid-tif")
        self._assert_no_part()

    def test_multi_cog_vrt_workspace_and_output_are_parts(self):
        sources = [self.tmp / "a.tif", self.tmp / "b.tif"]
        for source in sources:
            source.write_bytes(b"dem")
        final = self.tmp / "zone_315_ombrage.tif"
        seen = []

        def build_vrt(cogs, vrt_path, _resolution):
            self.assertEqual(cogs, sources)
            self.assertEqual(vrt_path.parent.suffix, ".part")
            self.assertTrue((vrt_path.parent / "_dalles.txt").exists())
            seen.append(vrt_path.parent)
            vrt_path.write_text("<VRTDataset/>", encoding="utf-8")

        def writer(source, jobs, **_kwargs):
            self.assertEqual(Path(source).parent.suffix, ".part")
            part = Path(jobs[0][2])
            self.assertEqual(part.suffix, ".part")
            seen.append(part)
            part.write_bytes(b"valid-new-tif")
            return True

        with mock.patch.object(L, "_build_vrt_xml", side_effect=build_vrt), \
             mock.patch.object(L, "_source_a_des_donnees", return_value=True), \
             mock.patch.object(L, "_hillshade_chunked_multi",
                               side_effect=writer), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=True), \
             mock.patch.object(L, "_creer_fichier"), \
             contextlib.redirect_stdout(io.StringIO()):
            result = L.generer_ombrages(
                sources,
                self.tmp,
                choix=["315"],
                nom_zone="zone",
                ecraser_ombrages=True,
            )

        self.assertIn(final, result)
        self.assertEqual(final.read_bytes(), b"valid-new-tif")
        self.assertTrue(seen)
        self._assert_no_part()


if __name__ == "__main__":
    unittest.main(verbosity=2)
