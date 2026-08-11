"""Caractérisation hors réseau du convertisseur GeoJSON IGN -> OSM XML."""

from __future__ import annotations

import contextlib
import gzip
import io
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lidar2map as L  # noqa: E402


class GeojsonOsmCharacterizationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        L._stop_event.clear()

    def tearDown(self):
        L._stop_event.clear()
        self._tmp.cleanup()

    def _write_geojson(self, path: Path, features: list[dict]) -> None:
        payload = {"type": "FeatureCollection", "features": features}
        if path.suffix == ".gz":
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                json.dump(payload, stream)
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")

    @staticmethod
    def _feature(geometry: dict | None, **properties) -> dict:
        return {
            "type": "Feature",
            "geometry": geometry,
            "properties": {"source": "batiment", **properties},
        }

    def _convert(self, source: Path, final: Path, **kwargs) -> bool:
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            return L.geojson_ign_vers_osm_xml(source, final, **kwargs)

    def test_all_supported_geometries_keep_nodes_before_ways(self):
        source = self.root / "matrix_ign_batiment.geojson"
        final = self.root / "matrix.osm"
        features = [
            self._feature({"type": "Point", "coordinates": [0, 0]}),
            self._feature({
                "type": "MultiPoint",
                "coordinates": [[1, 1], [2, 2]],
            }),
            self._feature({
                "type": "LineString",
                "coordinates": [[3, 3], [4, 4]],
            }),
            self._feature({
                "type": "MultiLineString",
                "coordinates": [
                    [[5, 5], [6, 6]],
                    [[7, 7], [8, 8]],
                ],
            }),
            self._feature({
                "type": "Polygon",
                "coordinates": [
                    [[9, 9], [10, 9], [9, 10], [9, 9]],
                    [[9.1, 9.1], [9.2, 9.1], [9.1, 9.2], [9.1, 9.1]],
                ],
            }),
            self._feature({
                "type": "MultiPolygon",
                "coordinates": [
                    [[[11, 11], [12, 11], [11, 12], [11, 11]]],
                    [[[13, 13], [14, 13], [13, 14], [13, 13]]],
                ],
            }),
            self._feature({
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "Point", "coordinates": [15, 15]},
                    {
                        "type": "LineString",
                        "coordinates": [[16, 16], [17, 17]],
                    },
                    {
                        "type": "MultiLineString",
                        "coordinates": [
                            [[18, 18], [19, 19]],
                            [[20, 20], [21, 21]],
                        ],
                    },
                    {
                        "type": "Polygon",
                        "coordinates": [
                            [[22, 22], [23, 22], [22, 23], [22, 22]],
                        ],
                    },
                    {
                        "type": "MultiPolygon",
                        "coordinates": [
                            [[[24, 24], [25, 24], [24, 25], [24, 24]]],
                        ],
                    },
                ],
            }),
        ]
        self._write_geojson(source, features)

        self.assertTrue(self._convert(source, final, epsilon=0.0))

        root = ET.parse(final).getroot()
        children = list(root)
        nodes = root.findall("node")
        ways = root.findall("way")
        self.assertEqual(len(nodes), 31)
        self.assertEqual(len(ways), 11)
        self.assertEqual(
            [child.tag for child in children],
            ["bounds"] + ["node"] * 31 + ["way"] * 11,
        )
        node_ids = {node.attrib["id"] for node in nodes}
        self.assertEqual(len(node_ids), 31)
        self.assertTrue(all(int(node_id) < 0 for node_id in node_ids))
        self.assertTrue(all(int(way.attrib["id"]) < 0 for way in ways))
        closed_ways = 0
        for way in ways:
            refs = [nd.attrib["ref"] for nd in way.findall("nd")]
            self.assertGreaterEqual(len(refs), 2)
            self.assertTrue(set(refs) <= node_ids)
            if refs[0] == refs[-1]:
                closed_ways += 1
        self.assertEqual(closed_ways, 5)
        self.assertEqual(
            root.find("bounds").attrib,
            {
                "minlat": "0.0000000",
                "minlon": "0.0000000",
                "maxlat": "25.0000000",
                "maxlon": "25.0000000",
            },
        )

    def test_tags_bounds_and_xml_attributes_are_escaped(self):
        source = self.root / "escape_ign_batiment.geojson"
        final = self.root / "escape.osm"
        name = "A & <B> > C \"D\" 'E'"
        self._write_geojson(
            source,
            [self._feature(
                {"type": "Point", "coordinates": [6.125, 43.25]},
                nom=name,
            )],
        )

        self.assertTrue(self._convert(source, final))

        raw = final.read_text(encoding="utf-8")
        for entity in ("&amp;", "&lt;", "&gt;", "&quot;", "&apos;"):
            self.assertIn(entity, raw)
        root = ET.fromstring(raw)
        node = root.find("node")
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in node.findall("tag")}
        self.assertEqual(tags, {"building": "yes", "name": name})
        self.assertEqual(
            root.find("bounds").attrib,
            {
                "minlat": "43.2500000",
                "minlon": "6.1250000",
                "maxlat": "43.2500000",
                "maxlon": "6.1250000",
            },
        )

    def test_default_and_explicit_epsilon_reach_the_simplifier(self):
        source = self.root / "epsilon_ign_troncon_de_route.geojson"
        self._write_geojson(source, [self._feature({
            "type": "LineString",
            "coordinates": [[0, 0], [1, 0], [2, 1]],
        })])
        epsilons = []

        def simplify(coords, epsilon):
            epsilons.append(epsilon)
            return list(coords)

        with mock.patch.object(L, "_douglas_peucker", side_effect=simplify):
            self.assertTrue(self._convert(source, self.root / "default.osm"))
            self.assertTrue(self._convert(
                source,
                self.root / "explicit.osm",
                epsilon=0.0123,
            ))

        self.assertEqual(epsilons, [L._IGN_SIMPLIFY_EPSILON, 0.0123])

    def test_empty_input_keeps_previous_final_and_cleans_staging(self):
        source = self.root / "empty.geojson"
        final = self.root / "empty.osm"
        previous = b"previous-osm"
        final.write_bytes(previous)
        self._write_geojson(source, [self._feature(None)])

        self.assertFalse(self._convert(source, final))

        self.assertEqual(final.read_bytes(), previous)
        self.assertEqual(list(self.root.rglob("*.part")), [])

    def test_invalid_input_keeps_previous_final_and_cleans_staging(self):
        source = self.root / "invalid.geojson"
        final = self.root / "invalid.osm"
        previous = b"previous-osm"
        final.write_bytes(previous)
        first_feature = self._feature({
            "type": "Point",
            "coordinates": [6.0, 43.0],
        })
        source.write_text(
            '{"type":"FeatureCollection","features":['
            + json.dumps(first_feature)
            + ',',
            encoding="utf-8",
        )

        self.assertFalse(self._convert(source, final))

        self.assertEqual(final.read_bytes(), previous)
        self.assertEqual(list(self.root.rglob("*.part")), [])

    def test_publish_failure_keeps_previous_final_and_cleans_staging(self):
        source = self.root / "publish_ign_batiment.geojson"
        final = self.root / "publish.osm"
        previous = b"previous-osm"
        final.write_bytes(previous)
        self._write_geojson(
            source,
            [self._feature({"type": "Point", "coordinates": [6.0, 43.0]})],
        )

        with mock.patch.object(
            type(final),
            "replace",
            side_effect=OSError("forced replace failure"),
        ):
            self.assertFalse(self._convert(source, final))

        self.assertEqual(final.read_bytes(), previous)
        self.assertEqual(list(self.root.rglob("*.part")), [])

    def test_final_staging_path_failure_cleans_node_and_way_parts(self):
        source = self.root / "staging_ign_batiment.geojson"
        final = self.root / "staging.osm"
        previous = b"previous-osm"
        final.write_bytes(previous)
        self._write_geojson(
            source,
            [self._feature({"type": "Point", "coordinates": [6.0, 43.0]})],
        )
        original = L._chemin_part
        calls = []

        def fail_on_final(path):
            calls.append(Path(path))
            if len(calls) == 3:
                raise OSError("forced staging path failure")
            return original(path)

        with mock.patch.object(L, "_chemin_part", side_effect=fail_on_final):
            with self.assertRaises(OSError):
                self._convert(source, final)

        self.assertEqual(len(calls), 3)
        self.assertEqual(final.read_bytes(), previous)
        self.assertEqual(list(self.root.rglob("*.part")), [])

    def test_gzip_input_is_streamed(self):
        source = self.root / "source_ign_batiment.geojson.gz"
        final = self.root / "gzip.osm"
        self._write_geojson(
            source,
            [self._feature({"type": "Point", "coordinates": [6.0, 43.0]})],
        )

        self.assertTrue(self._convert(source, final))
        self.assertEqual(len(ET.parse(final).getroot().findall("node")), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
