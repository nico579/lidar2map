"""Contrats de caractérisation à préserver pendant la modularisation.

Ces tests portent sur les façades et conventions entre composants. Ils ne
testent volontairement ni le réseau ni le détail des algorithmes scientifiques,
déjà couverts par les autres suites.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "lidar2map.py"
sys.path.insert(0, str(ROOT))

import lidar2map as L  # noqa: E402
import _geojson_geometry as geojson_geometry  # noqa: E402
import _geojson_merge as geojson_merge  # noqa: E402
import _geojson_merge_cli as geojson_merge_cli  # noqa: E402
import _geojson_osm_export as geojson_osm_export  # noqa: E402
import _geojson_mapsforge as geojson_mapsforge  # noqa: E402
import _geojson_osm_xml as geojson_osm_xml  # noqa: E402
import _geojson_raster as geojson_raster  # noqa: E402
import _mbtiles_lidar as mbtiles_lidar  # noqa: E402
import _mbtiles_wmts as mbtiles_wmts  # noqa: E402
import _osm_runtime as osm_runtime  # noqa: E402
import _terrain_sources as terrain_sources  # noqa: E402
import _terrain_zones as terrain_zones  # noqa: E402
import _terrain_geocoding as terrain_geocoding  # noqa: E402
import _terrain_resolution as terrain_resolution  # noqa: E402
import _terrain_chunks as terrain_chunks  # noqa: E402
import _terrain_download as terrain_download  # noqa: E402
import _terrain_prefetch as terrain_prefetch  # noqa: E402
import _terrain_shading as terrain_shading  # noqa: E402
import _mbtiles_wmts_helpers as mbtiles_wmts_helpers  # noqa: E402
import _ombrages_provider as ombrages_provider  # noqa: E402
import _shading_specs as shading_specs  # noqa: E402
import _ombrages_pures as ombrages_pures  # noqa: E402
import _raster_formats as raster_formats  # noqa: E402
import _split_deliverables as split_deliverables  # noqa: E402
import _split_manifest as split_manifest  # noqa: E402
import _split_planning as split_planning  # noqa: E402
import _split_runner as split_runner  # noqa: E402
import _split_sliding as split_sliding  # noqa: E402
import _wfs_pipeline as wfs_pipeline  # noqa: E402
import _bdtopo_bulk as bdtopo_bulk  # noqa: E402
import _bdtopo_layers as bdtopo_layers  # noqa: E402
import _vector_acquisition as vector_acquisition  # noqa: E402
import _vector_outputs as vector_outputs  # noqa: E402
import _osm_outputs as osm_outputs  # noqa: E402
import _osm_map_pipeline as osm_map_pipeline  # noqa: E402
import _osm_policy as osm_policy  # noqa: E402


class PublicFacadeContractTests(unittest.TestCase):
    """Le script principal reste une façade compatible pendant les extractions."""

    def test_refactor_seams_remain_importable_from_main_module(self):
        expected_callables = (
            "Manifeste",
            "_calculer_sous_zones_priori",
            "_cle_chunk",
            "_convertir_formats",
            "_convertir_un_mbtiles",
            "_identite_chunk",
            "_parse_block",
            "_run_split_priori",
            "_run_split_priori_lidar_glissant",
            "_signature_config",
            "_voisins_dossiers",
            "_ecrire_json_atomique",
            "_discover_providers",
            "generer_ombrages",
            "generer_mbtiles_lidar",
            "generer_mbtiles_wmts",
            "generer_rmap_depuis_mbtiles",
            "generer_sqlitedb_depuis_mbtiles",
            "main",
            "lancer_gui",
        )
        for name in expected_callables:
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(L, name, None)), name)
        self.assertIs(L.Manifeste, split_manifest.Manifeste)
        self.assertIs(L._contexte_manifeste, split_manifest._contexte_manifeste)
        self.assertIs(L._ResultatChunk, split_deliverables._ResultatChunk)
        self.assertIs(
            L._normaliser_resultat_chunk,
            split_deliverables._normaliser_resultat_chunk,
        )
        self.assertIs(L._cle_chunk, split_planning._cle_chunk)
        self.assertIs(L._identite_chunk, split_planning._identite_chunk)
        self.assertIs(
            L._DependancesRunnerClassique,
            split_runner._DependancesRunnerClassique,
        )
        self.assertIs(
            L._DependancesRunnerGlissant,
            split_sliding._DependancesRunnerGlissant,
        )
        self.assertIs(L._voisins_dossiers, split_sliding._voisins_dossiers)
        self.assertIs(
            L._DependancesMbtilesWMTS,
            mbtiles_wmts._DependancesMbtilesWMTS,
        )
        self.assertIs(
            L._generer_mbtiles_wmts_impl,
            mbtiles_wmts.generer_mbtiles_wmts,
        )
        self.assertIs(
            L._DependancesMbtilesLidar,
            mbtiles_lidar._DependancesMbtilesLidar,
        )
        self.assertIs(
            L._generer_mbtiles_lidar_impl,
            mbtiles_lidar.generer_mbtiles_lidar,
        )
        self.assertIs(L._bbox_depuis_gdalinfo, mbtiles_lidar._bbox_depuis_gdalinfo)
        self.assertIs(L._warped_3857_valide, mbtiles_lidar._warped_3857_valide)
        self.assertIs(L._tile_workers_defaut, mbtiles_lidar._tile_workers_defaut)
        self.assertIs(
            L._DependancesTelechargementWmts,
            mbtiles_wmts_helpers._DependancesTelechargementWmts,
        )
        self.assertIs(
            L._telecharger_tuile_impl, mbtiles_wmts_helpers.telecharger_tuile,
        )
        self.assertIs(
            L._lire_zoom_limites_wmts_impl,
            mbtiles_wmts_helpers._lire_zoom_limites_wmts,
        )
        self.assertIs(L._bbox_valide_wgs84, mbtiles_wmts_helpers._bbox_valide_wgs84)
        self.assertIs(L.deg_to_tile, mbtiles_wmts_helpers.deg_to_tile)
        self.assertIs(L.calculer_grille_xyz, mbtiles_wmts_helpers.calculer_grille_xyz)
        self.assertIs(L.compter_tuiles_xyz, mbtiles_wmts_helpers.compter_tuiles_xyz)
        self.assertIs(L.estimer_taille, mbtiles_wmts_helpers.estimer_taille)
        self.assertIs(L.construire_url_wmts, mbtiles_wmts_helpers.construire_url_wmts)
        self.assertIs(L._wmts_get_conn, mbtiles_wmts_helpers._wmts_get_conn)
        self.assertIs(L._wmts_fetch_impl, mbtiles_wmts_helpers._wmts_fetch)
        self.assertIs(L._est_image_valide, mbtiles_wmts_helpers._est_image_valide)
        self.assertIs(
            L._wmts_close_all_conns, mbtiles_wmts_helpers._wmts_close_all_conns,
        )
        self.assertIs(L.SVF_GAMMA, ombrages_pures.SVF_GAMMA)
        self.assertIs(L._stop_event, ombrages_pures._stop_event)
        self.assertIs(L._NUMBA_KERNELS_CACHE, ombrages_pures._NUMBA_KERNELS_CACHE)
        self.assertIs(
            L._get_numba_svf_opos_kernel, ombrages_pures._get_numba_svf_opos_kernel,
        )
        self.assertIs(L._hillshade_numpy, ombrages_pures._hillshade_numpy)
        self.assertIs(
            L._hillshade_multi_numpy, ombrages_pures._hillshade_multi_numpy,
        )
        self.assertIs(L._slope_numpy, ombrages_pures._slope_numpy)
        self.assertIs(L._hillshade_chunked, ombrages_pures._hillshade_chunked)
        self.assertIs(
            L._hillshade_chunked_multi, ombrages_pures._hillshade_chunked_multi,
        )
        self.assertIs(L._lire_dem_rasterio, ombrages_pures._lire_dem_rasterio)
        self.assertIs(L._lrm_array, ombrages_pures._lrm_array)
        self.assertIs(L._lrm_chunked, ombrages_pures._lrm_chunked)
        self.assertIs(L._nodata_mask, ombrages_pures._nodata_mask)
        self.assertIs(L._rrim_chunked, ombrages_pures._rrim_chunked)
        self.assertIs(L._source_a_des_donnees, ombrages_pures._source_a_des_donnees)
        self.assertIs(L._svf_chunked, ombrages_pures._svf_chunked)
        self.assertIs(L._svf_numpy, ombrages_pures._svf_numpy)
        self.assertIs(L._svf_opos_chunked, ombrages_pures._svf_opos_chunked)
        self.assertIs(
            L._sauver_array_georef_impl, ombrages_pures._sauver_array_georef,
        )
        self.assertIs(
            L._publier_tif_atomique_impl, ombrages_pures._publier_tif_atomique,
        )
        self.assertIs(L._build_vrt_xml_impl, ombrages_pures._build_vrt_xml)
        self.assertIs(
            L._DependancesFetchProvider, ombrages_provider._DependancesFetchProvider,
        )
        self.assertIs(
            L._extraire_tiff_multipart_impl, ombrages_provider._extraire_tiff_multipart,
        )
        self.assertIs(
            L._post_fetch_si_besoin_impl, ombrages_provider._post_fetch_si_besoin,
        )
        self.assertIs(
            L._fetch_provider_shadings_impl,
            ombrages_provider._fetch_provider_shadings,
        )
        self.assertIs(L._vat_compose, ombrages_provider._vat_compose)
        self.assertIs(L._mstp_chunked, ombrages_provider._mstp_chunked)
        self.assertIs(L._e4mstp_compose, ombrages_provider._e4mstp_compose)
        self.assertIs(L._SHADING_TYPES, shading_specs._SHADING_TYPES)
        self.assertIs(L.SHADING_TYPES_ORDRE, shading_specs.SHADING_TYPES_ORDRE)
        self.assertIs(L.SHADING_TOUS, shading_specs.SHADING_TOUS)
        self.assertIs(
            L._resoudre_preset_shading, shading_specs._resoudre_preset_shading,
        )
        self.assertIs(L.parser_shading_spec, shading_specs.parser_shading_spec)
        self.assertIs(L._blob_vers_jpeg, raster_formats._blob_vers_jpeg)
        self.assertIs(L._build_map_info, raster_formats._build_map_info)
        self.assertIs(
            L._sqlitedb_schema_courant,
            raster_formats._sqlitedb_schema_courant,
        )
        for name in (
            "_IGN_LAYER_TAGS",
            "_IGN_SIMPLIFY_EPSILON",
            "_OVERLAY_DEFAUT",
            "_OVERLAY_STYLE",
            "_OVERLAY_TILE_WARN",
            "_clip_polygone_rect",
            "_douglas_peucker",
            "_epsilon_depuis_surface_km2",
            "_overlay_sequences",
            "_overlay_style_key",
            "_seg_inter_box",
            "_tags_pour_layer",
        ):
            with self.subTest(geojson_symbol=name):
                self.assertIs(
                    getattr(L, name),
                    getattr(geojson_geometry, name),
                )
        self.assertIs(
            L._DependancesGeojsonOsmXml,
            geojson_osm_xml._DependancesGeojsonOsmXml,
        )
        self.assertIs(
            L._geojson_ign_vers_osm_xml_impl,
            geojson_osm_xml.geojson_ign_vers_osm_xml,
        )
        self.assertIs(
            L._DependancesRasterGeojson,
            geojson_raster._DependancesRasterGeojson,
        )
        self.assertIs(
            L._rasteriser_geojson_transparent_impl,
            geojson_raster.rasteriser_geojson_transparent,
        )
        self.assertIs(
            L._DependancesGeojsonMapsforge,
            geojson_mapsforge._DependancesGeojsonMapsforge,
        )
        self.assertIs(
            L._generer_map_depuis_geojson_ign_impl,
            geojson_mapsforge.generer_map_depuis_geojson_ign,
        )

    def _cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["LIDAR2MAP_BOOTSTRAP"] = "none"
        env["PYTHONUTF8"] = "1"
        with tempfile.TemporaryDirectory() as tmp:
            return subprocess.run(
                [sys.executable, str(APP), *args],
                cwd=tmp,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=30,
                check=False,
            )

    def test_version_is_a_stable_command(self):
        completed = self._cli("--version")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(
            f"lidar2map {L.VERSION} ({L.VERSION_DATE}), multi-provider",
            completed.stdout.splitlines(),
        )

    def test_help_keeps_the_documented_workflow_surface(self):
        completed = self._cli("--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for flag in (
            "--lidar",
            "--provider",
            "--zone-city",
            "--zone-bbox",
            "--shadings",
            "--file-formats",
            "--osm",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, completed.stdout)

    def test_lidar_aliases_reach_the_same_validation_boundary(self):
        common = (
            "--provider", "fr-ign",
            "--zone-bbox", "6.0,43.3,6.1,43.4",
            "--zoom-min", "19", "--zoom-max", "18",
        )
        english = self._cli("--lidar", *common)
        legacy = self._cli("--ignlidar", *common)
        for completed in (english, legacy):
            self.assertEqual(completed.returncode, 2)
            output = completed.stdout + completed.stderr
            self.assertIn("--zoom-min (19) > --zoom-max (18)", output)

    def test_global_provider_and_negative_bbox_survive_pre_parsing(self):
        completed = self._cli(
            "--lidar",
            "--provider=fr-ign",
            "--zone-bbox", "-6.1,43.3,-6.0,43.4",
            "--zoom-min", "19", "--zoom-max", "18",
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 2, output)
        self.assertIn("--zoom-min (19) > --zoom-max (18)", output)
        self.assertNotIn("unrecognized arguments", output)
        self.assertNotIn("--provider is required", output)


class SplitPlanningContractTests(unittest.TestCase):
    def test_grid_facade_matches_the_extracted_planner(self):
        params = (0.0, 0.0, 10_000.0, 5_000.0, 0, 2.0)
        expected = split_planning._calculer_sous_zones_priori(*params)
        self.assertEqual(L._calculer_sous_zones_priori(*params), expected)
        zones, description = expected
        self.assertEqual(len(zones), 15)
        self.assertEqual(description, "~2 km/morceau (3×5)")

    def test_chunk_identity_is_stable_and_one_based(self):
        self.assertEqual(L._cle_chunk(0, 0), "001x001")
        self.assertEqual(
            L._identite_chunk("zone", 11, 4),
            ("012x005", "zone_012x005"),
        )

    def test_signature_facade_injects_the_active_provider(self):
        args = SimpleNamespace(zoom_min=13, zoom_max=18, mbtiles=True)
        zones = [(0, 0, 0.0, 0.0, 1000.0, 1000.0)]
        signature = L._signature_config(args, zones)
        self.assertEqual(
            signature,
            split_planning._signature_config(args, zones, provider=L.PROVIDER),
        )
        self.assertNotEqual(
            signature,
            L._signature_config(
                SimpleNamespace(zoom_min=13, zoom_max=17, mbtiles=True),
                zones,
            ),
        )
        zones_etendues = [
            (ligne, colonne, colonne * 1000.0, ligne * 1000.0,
             (colonne + 1) * 1000.0, (ligne + 1) * 1000.0)
            for ligne in range(2)
            for colonne in range(2)
        ]
        self.assertEqual(signature, L._signature_config(args, zones_etendues))
        self.assertNotEqual(
            split_planning._signature_config(
                args,
                zones,
                provider=SimpleNamespace(CODE="provider-a"),
            ),
            split_planning._signature_config(
                args,
                zones,
                provider=SimpleNamespace(CODE="provider-b"),
            ),
        )

    def test_block_parser_facade_preserves_validation(self):
        self.assertEqual(L._parse_block(" 2 / 3 "), (2, 3))
        self.assertIsNone(L._parse_block(""))
        with self.assertRaises(ValueError):
            L._parse_block("4/3")


class SplitSlidingContractTests(unittest.TestCase):
    def test_neighbor_facade_returns_the_eight_surrounding_chunks(self):
        root = Path("root")
        neighbors = L._voisins_dossiers(root, "zone", 1, 1, 3, 3)
        self.assertEqual(len(neighbors), 8)
        self.assertEqual(
            {path.name for path in neighbors},
            {
                "zone_001x001",
                "zone_001x002",
                "zone_001x003",
                "zone_002x001",
                "zone_002x003",
                "zone_003x001",
                "zone_003x002",
                "zone_003x003",
            },
        )

    def test_neighbor_facade_clips_grid_edges(self):
        neighbors = L._voisins_dossiers(Path("root"), "zone", 0, 0, 3, 3)
        self.assertEqual(
            {path.name for path in neighbors},
            {"zone_001x002", "zone_002x001", "zone_002x002"},
        )


class MbtilesWmtsFacadeContractTests(unittest.TestCase):
    """La façade WMTS relit ses coutures à CHAQUE appel.

    C'est la condition qui rend l'extraction transparente : les suites
    historiques monkeypatchent `L.telecharger_tuile`, `L._valider_sqlite_part`,
    `L._chemin_part` et `L._log_req` sur le module principal. Une capture des
    dépendances à l'import (constante de module) les ignorerait en silence.
    """

    def _capturer_dependances(self, **surcharges):
        contexte = contextlib.ExitStack()
        with contexte:
            implementation = contexte.enter_context(mock.patch.object(
                L,
                "_generer_mbtiles_wmts_impl",
                return_value=Path("out.mbtiles"),
            ))
            for nom, valeur in surcharges.items():
                contexte.enter_context(mock.patch.object(L, nom, valeur))
            L.generer_mbtiles_wmts(
                Path("out.mbtiles"), iter(()), 0, "zone", "jpg",
                10, 10, "TEST", "normal", "image/jpeg", "", False, 1,
            )
        return implementation.call_args.kwargs["dependances"]

    def test_wmts_facade_injects_current_application_seams(self):
        deps = self._capturer_dependances()
        self.assertIs(deps.chemin_part, L._chemin_part)
        self.assertIs(deps.nettoyer_sqlite_part, L._nettoyer_sqlite_part)
        self.assertIs(deps.valider_sqlite_part, L._valider_sqlite_part)
        self.assertIs(deps.telecharger_tuile, L.telecharger_tuile)
        self.assertIs(deps.est_image_valide, L._est_image_valide)
        self.assertIs(deps.fermer_connexions_wmts, L._wmts_close_all_conns)
        self.assertIs(deps.log_req, L._log_req)
        self.assertIs(deps.stop_event, L._stop_event)
        self.assertIs(deps.zone_hors_couverture, L.ZoneHorsCouvertureWMTS)
        self.assertEqual(deps.endpoint_prive, L.WMTS_URL)
        self.assertEqual(deps.endpoint_public, L.WMTS_URL_PUB)
        self.assertEqual(deps.batch_insert, L.BATCH_MBTILES_INSERT)
        self.assertEqual(deps.seuil_err_consec, L.SEUIL_ERR_CONSEC)
        self.assertEqual(deps.seuil_hors_couverture, L.SEUIL_HORS_COUVERTURE)

    def test_wmts_facade_reads_monkeypatched_seams_at_call_time(self):
        remplacant = mock.Mock(name="telecharger_tuile-patché")
        deps = self._capturer_dependances(telecharger_tuile=remplacant)
        self.assertIs(deps.telecharger_tuile, remplacant)
        # Restauré hors du patch : la façade ne fige rien.
        self.assertIs(self._capturer_dependances().telecharger_tuile,
                      L.telecharger_tuile)


class MbtilesLidarFacadeContractTests(unittest.TestCase):
    """La façade LiDAR relit ses coutures à CHAQUE appel, comme son jumeau WMTS.

    `PROVIDER` est remplacé par certaines suites via `L.PROVIDER = ...` (pas
    `mock.patch.object`, cf. `_test_atomic_downloads.py`) : la valeur injectée
    doit donc être relue sur `L.PROVIDER.CRS_NATIF` à chaque appel, pas
    capturée une fois à l'import.
    """

    def _capturer_dependances(self, **surcharges):
        contexte = contextlib.ExitStack()
        with contexte:
            implementation = contexte.enter_context(mock.patch.object(
                L,
                "_generer_mbtiles_lidar_impl",
                return_value=Path("out.mbtiles"),
            ))
            for nom, valeur in surcharges.items():
                contexte.enter_context(mock.patch.object(L, nom, valeur))
            L.generer_mbtiles_lidar(
                Path("source.tif"), Path("."), "zone",
                zoom_min=14, zoom_max=14,
            )
        return implementation.call_args.kwargs["dependances"]

    def test_lidar_facade_injects_current_application_seams(self):
        deps = self._capturer_dependances()
        self.assertIs(deps.chemin_part, L._chemin_part)
        self.assertIs(deps.nettoyer_sqlite_part, L._nettoyer_sqlite_part)
        self.assertIs(deps.valider_sqlite_part, L._valider_sqlite_part)
        self.assertIs(deps.mbtiles_a_regenerer, L._mbtiles_a_regenerer)
        self.assertIs(deps.creer_fichier, L._creer_fichier)
        self.assertIs(deps.formater_duree, L._hms)
        self.assertIs(deps.stop_event, L._stop_event)
        self.assertIs(deps.get_transformer, L._get_transformer)
        self.assertIs(deps.natif_vers_wgs84, L._natif_vers_wgs84)
        self.assertIs(deps.bbox_enveloppe_transform, L._bbox_enveloppe_transform)
        self.assertEqual(deps.batch_insert, L.BATCH_MBTILES_INSERT)
        self.assertEqual(deps.crs_natif, L.PROVIDER.CRS_NATIF)

    def test_lidar_facade_reads_monkeypatched_seams_at_call_time(self):
        remplacant = mock.Mock(name="_creer_fichier-patché")
        deps = self._capturer_dependances(_creer_fichier=remplacant)
        self.assertIs(deps.creer_fichier, remplacant)
        # Restauré hors du patch : la façade ne fige rien.
        self.assertIs(self._capturer_dependances().creer_fichier,
                      L._creer_fichier)

    def test_lidar_facade_reads_the_active_provider_at_call_time(self):
        ancien_provider = L.PROVIDER
        try:
            L.PROVIDER = SimpleNamespace(CRS_NATIF="EPSG:2056")
            deps = self._capturer_dependances()
            self.assertEqual(deps.crs_natif, "EPSG:2056")
        finally:
            L.PROVIDER = ancien_provider


class WmtsDownloadFacadeContractTests(unittest.TestCase):
    """`telecharger_tuile` et `_lire_zoom_limites_wmts` partagent une seule
    structure de dépendances, reconstruite à chaque appel — même si aucune
    suite ne patche encore `MAX_TENTATIVES`/`DELAI_RETRY` spécifiquement pour
    le WMTS (elle le fait pour les jumeaux LAZ : `telecharger_dalle_directe`,
    `telecharger_copc_fenetre`, `telecharger_cog_fenetre`), la cohérence avec
    ces jumeaux et la possibilité d'un futur test de retry motivent
    l'injection."""

    def test_telecharger_tuile_facade_injects_current_seams(self):
        expected = object()
        with mock.patch.object(
            L, "_telecharger_tuile_impl", return_value=expected,
        ) as implementation:
            result = L.telecharger_tuile(
                10, 1, 2, "TEST", "normal", "image/jpeg", "", False)
        self.assertIs(result, expected)
        deps = implementation.call_args.kwargs["dependances"]
        self.assertEqual(deps.wmts_url, L.WMTS_URL)
        self.assertEqual(deps.wmts_url_pub, L.WMTS_URL_PUB)
        self.assertIs(deps.wmts_fetch, L._wmts_fetch)
        self.assertEqual(deps.http_ua, L._HTTP_UA)
        self.assertEqual(deps.max_tentatives, L.MAX_TENTATIVES)
        self.assertEqual(deps.delai_retry, L.DELAI_RETRY)

    def test_telecharger_tuile_facade_reads_monkeypatched_max_tentatives(self):
        with mock.patch.object(L, "MAX_TENTATIVES", 1), mock.patch.object(
            L, "_telecharger_tuile_impl", return_value=None,
        ) as implementation:
            L.telecharger_tuile(10, 1, 2, "TEST", "normal", "image/jpeg", "", False)
        self.assertEqual(
            implementation.call_args.kwargs["dependances"].max_tentatives, 1)

    def test_telecharger_tuile_facade_reads_directly_reassigned_wmts_fetch(self):
        """Reproduit le style de monkeypatch de `_test_robustesse.py` /
        `_test_interactions.py` : affectation directe, pas `mock.patch.object`."""
        ancien = L._wmts_fetch
        remplacant = lambda url: (200, "image/jpeg", b"\xff\xd8\xff")  # noqa: E731
        try:
            L._wmts_fetch = remplacant
            with mock.patch.object(
                L, "_telecharger_tuile_impl", return_value=None,
            ) as implementation:
                L.telecharger_tuile(10, 1, 2, "TEST", "normal", "image/jpeg", "", False)
            self.assertIs(
                implementation.call_args.kwargs["dependances"].wmts_fetch,
                remplacant,
            )
        finally:
            L._wmts_fetch = ancien

    def test_lire_zoom_limites_facade_injects_current_seams(self):
        expected = (10, 18)
        with mock.patch.object(
            L, "_lire_zoom_limites_wmts_impl", return_value=expected,
        ) as implementation:
            result = L._lire_zoom_limites_wmts("TEST", False)
        self.assertEqual(result, expected)
        deps = implementation.call_args.kwargs["dependances"]
        self.assertEqual(deps.wmts_url, L.WMTS_URL)
        self.assertEqual(deps.wmts_url_pub, L.WMTS_URL_PUB)
        self.assertEqual(deps.http_ua, L._HTTP_UA)


class TerrainZonesContractTests(unittest.TestCase):
    def test_zone_names_and_presence_are_delegated_to_pure_module(self):
        args = SimpleNamespace(zone_ville=None, zone_gps="43.3,6.0",
                               zone_bbox=None, zone_departement=None,
                               zone_region=None)
        self.assertEqual(L._nom_zone_gps_auto(43.3, 6.0),
                         terrain_zones.nom_zone_gps_auto(43.3, 6.0))
        self.assertEqual(L._nom_zone_bbox_auto(6, 43, 6.1, 43.1),
                         terrain_zones.nom_zone_bbox_auto(6, 43, 6.1, 43.1))
        self.assertTrue(L._zone_cli_presente(args))

    def test_approximate_projection_round_trips_in_france(self):
        x, y = terrain_zones.wgs84_to_lamb93_approx(6.0423, 43.3156)
        lon, lat = terrain_zones.lamb93_to_wgs84_approx(x, y)
        self.assertAlmostEqual(lon, 6.0423, places=4)
        self.assertAlmostEqual(lat, 43.3156, places=4)

    def test_bbox_envelope_densifies_all_edges(self):
        result = terrain_zones.bbox_enveloppe_transform(
            lambda x, y: (x + y * y, y), 0, 0, 10, 1, densify=21,
        )
        self.assertEqual(result, (0, 0, 11, 1))

    def test_geofabrik_region_helpers_are_sorted_and_deduplicated(self):
        catalog = {"83": "paca", "06": "paca", "75": "idf"}
        self.assertEqual(terrain_zones.regions_disponibles(catalog), ["idf", "paca"])
        self.assertEqual(
            terrain_zones.departements_de_region(catalog, "paca"), ["06", "83"],
        )
        self.assertEqual(L._regions_disponibles(), sorted(set(L._GEOFABRIK.values())))

    def test_department_parser_keeps_ranges_corsica_and_overseas_codes(self):
        valeur = "1-3, 2a,2B,971, 83,,9"
        attendu = ["01", "02", "03", "2A", "2B", "971", "83", "09"]
        self.assertEqual(terrain_zones.parser_departements(valeur), attendu)
        self.assertEqual(L._parser_departements(valeur), attendu)
        self.assertEqual(terrain_zones.parser_departements("3-1"), [])

    def test_provider_crs_facades_read_provider_and_transformer_late(self):
        transformeur = mock.Mock()
        transformeur.transform.return_value = (7.4, 47.0)
        get_transformer = mock.Mock(return_value=transformeur)
        provider = SimpleNamespace(CRS_NATIF="EPSG:2056")
        with mock.patch.object(L, "PROVIDER", provider), \
             mock.patch.object(L, "_get_transformer", get_transformer):
            self.assertEqual(L._natif_vers_wgs84(2600000, 1200000), (7.4, 47.0))
        get_transformer.assert_called_once_with("EPSG:2056", "EPSG:4326")
        transformeur.transform.assert_called_once_with(2600000, 1200000)

    def test_france_fallback_works_but_foreign_fallback_fails_closed(self):
        def indisponible(*_args):
            raise ImportError("pyproj absent")

        x, y = terrain_zones.wgs84_vers_natif(
            6.0423, 43.3156, crs_natif="EPSG:2154", get_transformer=indisponible,
        )
        self.assertGreater(x, 0)
        self.assertGreater(y, 0)
        with self.assertRaisesRegex(RuntimeError, "EPSG:2056"):
            terrain_zones.wgs84_vers_natif(
                7.4, 47.0, crs_natif="EPSG:2056", get_transformer=indisponible,
            )


class SourceAutonomeContractTests(unittest.TestCase):
    """Caractérise `_traiter_source_autonome`, extraite de `main()` en 8b.

    Extraction mécanique (aucun changement de comportement visé) : ces tests
    verrouillent le comportement observé AVANT l'extraction pour détecter toute
    dérive, y compris les quirks pré-existants qui ne sont pas corrigés ici.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_facades_keep_signatures_and_reload_dependencies(self):
        self.assertEqual(
            str(inspect.signature(L._traiter_source_autonome)), "(args)"
        )
        self.assertEqual(str(inspect.signature(L._traiter_source_wmts)), "(args)")
        seams = {
            "generer_rmap_depuis_mbtiles": mock.Mock(),
            "generer_sqlitedb_depuis_mbtiles": mock.Mock(),
            "_historique_depuis_argv": mock.Mock(),
            "_HIST_T_DEBUT": 123.0,
        }
        with mock.patch.multiple(L, **seams):
            dependencies = L._dependances_sources_terrain()
        self.assertIsInstance(
            dependencies, terrain_sources.DependancesSourcesTerrain
        )
        self.assertIs(
            dependencies.generer_rmap, seams["generer_rmap_depuis_mbtiles"]
        )
        self.assertIs(
            dependencies.generer_sqlitedb,
            seams["generer_sqlitedb_depuis_mbtiles"],
        )
        self.assertIs(dependencies.historique, seams["_historique_depuis_argv"])
        self.assertEqual(dependencies.hist_t_debut, 123.0)

    def test_no_source_is_a_no_op(self):
        args = SimpleNamespace(source=None)
        self.assertIsNone(L._traiter_source_autonome(args))
        self.assertIsNone(args.source)

    def test_missing_non_tif_source_exits_with_error(self):
        args = SimpleNamespace(source=str(self.tmp / "absent.mbtiles"))
        with self.assertRaises(SystemExit) as ctx:
            L._traiter_source_autonome(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_missing_tif_source_exits_despite_recompute_message(self):
        """Quirk PRÉ-EXISTANT (non introduit par 8b, non corrigé ici) : le
        message « Recompute from tiles... » laisse entendre que le run continue
        sans --source, mais `ext` devient "" après `args.source = None` et tombe
        dans la branche « unrecognised extension » → sys.exit(1) quand même.
        Caractérisé tel quel pour que l'extraction ne dérive pas ce comportement
        au passage ; un vrai correctif est un changement de comportement séparé."""
        args = SimpleNamespace(source=str(self.tmp / "absent.tif"))
        with self.assertRaises(SystemExit) as ctx:
            L._traiter_source_autonome(args)
        self.assertEqual(ctx.exception.code, 1)
        self.assertIsNone(args.source)

    def test_unreadable_extension_exits_with_error(self):
        f = self.tmp / "notes.txt"
        f.write_text("x", encoding="utf-8")
        args = SimpleNamespace(source=str(f))
        with self.assertRaises(SystemExit) as ctx:
            L._traiter_source_autonome(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_mbtiles_source_without_output_format_exits_with_error(self):
        f = self.tmp / "zone.mbtiles"
        f.write_bytes(b"fake")
        args = SimpleNamespace(source=str(f), rmap=False, sqlitedb=False)
        with self.assertRaises(SystemExit) as ctx:
            L._traiter_source_autonome(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_mbtiles_source_converts_and_exits_zero_on_success(self):
        f = self.tmp / "zone.mbtiles"
        f.write_bytes(b"fake")
        args = SimpleNamespace(source=str(f), rmap=True, sqlitedb=True)
        with mock.patch.object(
            L, "generer_rmap_depuis_mbtiles", return_value=Path("zone.rmap"),
        ) as rmap_impl, mock.patch.object(
            L, "generer_sqlitedb_depuis_mbtiles", return_value=Path("zone.sqlitedb"),
        ) as sqlitedb_impl, mock.patch.object(
            L, "_historique_depuis_argv",
        ) as hist:
            with self.assertRaises(SystemExit) as ctx:
                L._traiter_source_autonome(args)
        self.assertEqual(ctx.exception.code, 0)
        rmap_impl.assert_called_once_with(f, ecraser=True)
        sqlitedb_impl.assert_called_once_with(f, ecraser=True)
        hist.assert_called_once()
        self.assertEqual(hist.call_args.kwargs.get("statut"), "ok")

    def test_mbtiles_source_conversion_failure_exits_nonzero(self):
        f = self.tmp / "zone.mbtiles"
        f.write_bytes(b"fake")
        args = SimpleNamespace(source=str(f), rmap=True, sqlitedb=False)
        with mock.patch.object(
            L, "generer_rmap_depuis_mbtiles", return_value=None,
        ), mock.patch.object(L, "_historique_depuis_argv") as hist:
            with self.assertRaises(SystemExit) as ctx:
                L._traiter_source_autonome(args)
        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(hist.call_args.kwargs.get("statut"), "ko")

    def test_pbf_source_without_osm_flag_exits_with_error(self):
        f = self.tmp / "region.pbf"
        f.write_bytes(b"fake")
        args = SimpleNamespace(source=str(f), osm=False)
        with self.assertRaises(SystemExit) as ctx:
            L._traiter_source_autonome(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_pbf_source_with_osm_flag_passes_through_unchanged(self):
        f = self.tmp / "region.pbf"
        f.write_bytes(b"fake")
        args = SimpleNamespace(source=str(f), osm=True)
        self.assertIsNone(L._traiter_source_autonome(args))
        self.assertEqual(args.source, str(f))

    def test_tif_source_epsg3857_marks_already_warped(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        f = self.tmp / "warped.tif"
        with rasterio.open(str(f), "w", driver="GTiff", dtype="uint8", count=1,
                           height=4, width=4, crs="EPSG:3857",
                           transform=from_origin(0, 0, 1, 1)) as ds:
            ds.write(np.zeros((4, 4), dtype=np.uint8), 1)
        args = SimpleNamespace(source=str(f))
        self.assertIsNone(L._traiter_source_autonome(args))
        self.assertTrue(args._source_already_warped)

    def test_tif_source_other_crs_requires_warp(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        f = self.tmp / "natif.tif"
        with rasterio.open(str(f), "w", driver="GTiff", dtype="uint8", count=1,
                           height=4, width=4, crs="EPSG:2154",
                           transform=from_origin(900000, 6250000, 1, 1)) as ds:
            ds.write(np.zeros((4, 4), dtype=np.uint8), 1)
        args = SimpleNamespace(source=str(f))
        self.assertIsNone(L._traiter_source_autonome(args))
        self.assertFalse(args._source_already_warped)


class SourceEtCoucheWmtsContractTests(unittest.TestCase):
    """Caractérise `_traiter_source_wmts` et `_resoudre_couche_wmts`, extraites
    de `main_wmts()` (jumeau de 8b/8c pour le point d'entrée `--raster`)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _args_source(self, **kw):
        base = dict(source=None, rmap=False, sqlitedb=False)
        base.update(kw)
        return SimpleNamespace(**base)

    def test_source_no_op_when_absent(self):
        self.assertIsNone(L._traiter_source_wmts(self._args_source()))

    def test_source_missing_file_exits_with_error(self):
        args = self._args_source(source=str(self.tmp / "absent.mbtiles"))
        with self.assertRaises(SystemExit) as ctx:
            L._traiter_source_wmts(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_source_wrong_extension_exits_with_error(self):
        f = self.tmp / "notes.txt"
        f.write_text("x", encoding="utf-8")
        args = self._args_source(source=str(f))
        with self.assertRaises(SystemExit) as ctx:
            L._traiter_source_wmts(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_source_without_output_format_exits_with_error(self):
        f = self.tmp / "zone.mbtiles"
        f.write_bytes(b"fake")
        args = self._args_source(source=str(f))
        with self.assertRaises(SystemExit) as ctx:
            L._traiter_source_wmts(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_source_converts_and_exits_zero_on_success(self):
        f = self.tmp / "zone.mbtiles"
        f.write_bytes(b"fake")
        args = self._args_source(source=str(f), rmap=True, sqlitedb=True)
        with mock.patch.object(
            L, "generer_rmap_depuis_mbtiles", return_value=Path("zone.rmap"),
        ) as rmap_impl, mock.patch.object(
            L, "generer_sqlitedb_depuis_mbtiles", return_value=Path("zone.sqlitedb"),
        ) as sqlitedb_impl, mock.patch.object(L, "_historique_depuis_argv") as hist:
            with self.assertRaises(SystemExit) as ctx:
                L._traiter_source_wmts(args)
        self.assertEqual(ctx.exception.code, 0)
        rmap_impl.assert_called_once_with(f, ecraser=True)
        sqlitedb_impl.assert_called_once_with(f, ecraser=True)
        self.assertEqual(hist.call_args.kwargs.get("statut"), "ok")

    def test_source_conversion_failure_exits_nonzero(self):
        f = self.tmp / "zone.mbtiles"
        f.write_bytes(b"fake")
        args = self._args_source(source=str(f), rmap=True)
        with mock.patch.object(
            L, "generer_rmap_depuis_mbtiles", return_value=None,
        ), mock.patch.object(L, "_historique_depuis_argv") as hist:
            with self.assertRaises(SystemExit) as ctx:
                L._traiter_source_wmts(args)
        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(hist.call_args.kwargs.get("statut"), "ko")

    def _args_couche(self, **kw):
        base = dict(couche=None, formats_image="auto", zoom_min=10,
                    zoom_max=15, apikey="")
        base.update(kw)
        return SimpleNamespace(**base)

    def test_default_couche_resolves_to_planign(self):
        args = self._args_couche()
        with mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=None):
            layer, style, img_fmt, apikey_requis, fmt_ext, zmin, zmax = (
                L._resoudre_couche_wmts(args))
        self.assertEqual(args.couche, "planign")
        self.assertEqual(layer, "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2")
        self.assertEqual(fmt_ext, "png")
        self.assertFalse(apikey_requis)

    def test_known_alias_resolves_from_couches_table(self):
        args = self._args_couche(couche="ortho")
        with mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=None):
            layer, style, img_fmt, apikey_requis, fmt_ext, zmin, zmax = (
                L._resoudre_couche_wmts(args))
        self.assertEqual(layer, L.COUCHES["ortho"][0])
        self.assertEqual(fmt_ext, "jpg")

    def test_direct_layer_identifier_infers_format_and_apikey(self):
        args = self._args_couche(couche="GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN100")
        with mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=None):
            layer, style, img_fmt, apikey_requis, fmt_ext, zmin, zmax = (
                L._resoudre_couche_wmts(args))
        self.assertEqual(layer, "GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN100")
        self.assertTrue(apikey_requis)   # "MAPS" déclenche apikey_requis
        self.assertEqual(fmt_ext, "jpg")  # "MAPS" déclenche aussi le format JPEG

    def test_zoom_capping_narrows_to_layer_capabilities(self):
        args = self._args_couche(couche="planign", zoom_min=5, zoom_max=20)
        with mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=(8, 18)):
            *_, zmin, zmax = L._resoudre_couche_wmts(args)
        self.assertEqual((zmin, zmax), (8, 18))
        self.assertEqual((args.zoom_min, args.zoom_max), (8, 18))

    def test_zoom_capping_noop_when_capabilities_unavailable(self):
        args = self._args_couche(couche="planign", zoom_min=5, zoom_max=20)
        with mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=None):
            *_, zmin, zmax = L._resoudre_couche_wmts(args)
        self.assertEqual((zmin, zmax), (5, 20))

    def test_zoom_min_max_normalized_when_swapped(self):
        args = self._args_couche(couche="planign", zoom_min=15, zoom_max=10)
        with mock.patch.object(L, "_lire_zoom_limites_wmts", return_value=None):
            *_, zmin, zmax = L._resoudre_couche_wmts(args)
        self.assertEqual((zmin, zmax), (10, 15))


class GeocodageZoneContractTests(unittest.TestCase):
    @staticmethod
    def _reponse_json(payload):
        return contextlib.nullcontext(
            SimpleNamespace(read=lambda: json.dumps(payload).encode("utf-8"))
        )

    def test_nominatim_facade_keeps_signature_and_reads_seams_late(self):
        self.assertTrue(callable(terrain_geocoding.geocoder_ville_wgs84))
        provider = SimpleNamespace(COUNTRY="ch")
        ouvrir = mock.Mock(name="urlopen")
        journaliser = mock.Mock(name="log_req")
        attendu = object()
        with mock.patch.object(L, "PROVIDER", provider), \
             mock.patch.object(L.urllib.request, "urlopen", ouvrir), \
             mock.patch.object(L, "_log_req", journaliser), \
             mock.patch.object(L, "_geocoder_ville_wgs84_impl",
                               return_value=attendu) as implementation:
            resultat = L.geocoder_ville_wgs84("Lausanne")
        self.assertIs(resultat, attendu)
        self.assertEqual(str(inspect.signature(L.geocoder_ville_wgs84)), "(nom_ville)")
        kwargs = implementation.call_args.kwargs
        self.assertEqual(kwargs["country"], "ch")
        self.assertIs(kwargs["urlopen"], ouvrir)
        self.assertIs(kwargs["log_req"], journaliser)

    def test_nominatim_accepts_an_administrative_place_and_scopes_country(self):
        payload = [{
            "lat": "43.32934", "lon": "6.04574", "class": "place",
            "addresstype": "village", "display_name": "Garéoult, France",
        }]
        provider = SimpleNamespace(COUNTRY="fr")
        with mock.patch.object(L, "PROVIDER", provider), \
             mock.patch.object(L.urllib.request, "urlopen",
                               return_value=self._reponse_json(payload)) as ouvrir, \
             mock.patch.object(L, "_log_req"):
            lat, lon = L.geocoder_ville_wgs84("Garéoult")
        self.assertAlmostEqual(lat, 43.32934)
        self.assertAlmostEqual(lon, 6.04574)
        self.assertIn("countrycodes=fr", ouvrir.call_args.args[0].full_url)

    def test_nominatim_rejects_a_poi_and_network_failure_is_non_fatal(self):
        poi = [{
            "lat": "43", "lon": "6", "class": "shop",
            "addresstype": "supermarket", "display_name": "Un commerce",
        }]
        with mock.patch.object(L.urllib.request, "urlopen",
                               return_value=self._reponse_json(poi)), \
             mock.patch.object(L, "_log_req"):
            self.assertEqual(L.geocoder_ville_wgs84("ambigu"), (None, None))
        with mock.patch.object(L.urllib.request, "urlopen",
                               side_effect=L.urllib.error.URLError("offline")), \
             mock.patch.object(L, "_log_req"):
            self.assertEqual(L.geocoder_ville_wgs84("offline"), (None, None))

    def test_department_cache_avoids_network_and_keeps_margin(self):
        with tempfile.TemporaryDirectory() as td:
            cache = Path(td)
            (cache / "dep_bbox_cache.json").write_text(json.dumps({
                "83": {"nom": "Var", "lon_min": 5.6, "lat_min": 43.0,
                       "lon_max": 6.8, "lat_max": 43.6},
            }), encoding="utf-8")
            with mock.patch.object(L, "DOSSIER_CACHE", cache), \
                 mock.patch.object(L, "_bbox_enveloppe_transform",
                                   return_value=(1000, 2000, 3000, 4000)), \
                 mock.patch.object(L.urllib.request, "urlopen") as ouvrir:
                resultat = L.geocoder_departement("83")
        ouvrir.assert_not_called()
        self.assertEqual(resultat, ("Var", 500, 1500, 3500, 4500))

    def test_department_facade_keeps_signature_and_reads_seams_late(self):
        attendu = object()
        with mock.patch.object(L, "_geocoder_departement_impl",
                               return_value=attendu) as implementation:
            resultat = L.geocoder_departement("83")
        self.assertIs(resultat, attendu)
        self.assertEqual(str(inspect.signature(L.geocoder_departement)), "(num_dep)")
        kwargs = implementation.call_args.kwargs
        self.assertIs(kwargs["cache_dir"], L.DOSSIER_CACHE)
        self.assertIs(kwargs["bbox_transform"], L._bbox_enveloppe_transform)
        self.assertIs(kwargs["wgs84_vers_natif"], L._wgs84_vers_natif)
        self.assertIs(kwargs["ecrire_json_atomique"], L._ecrire_json_atomique)
        self.assertIs(kwargs["urlopen"], L.urllib.request.urlopen)

    def test_department_overpass_retries_three_times_then_fails(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(L, "DOSSIER_CACHE", Path(td)), \
             mock.patch.object(L.urllib.request, "urlopen",
                               side_effect=L.urllib.error.URLError("offline")) as ouvrir, \
             mock.patch.object(L.time, "sleep") as dormir, \
             mock.patch.object(L, "_log_req"):
            resultat = L.geocoder_departement("999")
        self.assertEqual(resultat, (None, None, None, None, None))
        self.assertEqual(ouvrir.call_count, 3)
        self.assertEqual(dormir.call_count, 2)

    def test_department_overpass_success_publishes_cache_atomically(self):
        payload = {"elements": [{
            "bounds": {"minlat": 43.0, "maxlat": 43.6,
                       "minlon": 5.6, "maxlon": 6.8},
            "tags": {"name": "Var"},
        }]}
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(L, "DOSSIER_CACHE", Path(td)), \
             mock.patch.object(L.urllib.request, "urlopen",
                               return_value=self._reponse_json(payload)), \
             mock.patch.object(L, "_bbox_enveloppe_transform",
                               return_value=(1000, 2000, 3000, 4000)), \
             mock.patch.object(L, "_ecrire_json_atomique") as publier, \
             mock.patch.object(L, "_log_req"):
            resultat = L.geocoder_departement("83")
        self.assertEqual(resultat, ("Var", 500, 1500, 3500, 4500))
        chemin, cache = publier.call_args.args[:2]
        self.assertEqual(chemin.name, "dep_bbox_cache.json")
        self.assertEqual(cache["83"]["nom"], "Var")

    def test_region_aggregates_department_bounds_and_aborts_on_failure(self):
        with mock.patch.object(L, "_departements_de_region",
                               return_value=["04", "83"]), \
             mock.patch.object(L, "geocoder_departement", side_effect=[
                 ("Alpes", 10, 20, 30, 40), ("Var", 5, 25, 35, 50),
             ]):
            self.assertEqual(
                L.geocoder_region("paca"), ("Paca", 5, 20, 35, 50),
            )
        with mock.patch.object(L, "_departements_de_region",
                               return_value=["04", "83"]), \
             mock.patch.object(L, "geocoder_departement", side_effect=[
                 ("Alpes", 10, 20, 30, 40), (None, None, None, None, None),
             ]):
            self.assertEqual(
                L.geocoder_region("paca"), (None, None, None, None, None),
            )

    def test_region_facade_keeps_signature_and_unknown_slug_is_non_fatal(self):
        with mock.patch.object(L, "_geocoder_region_impl",
                               return_value=object()) as implementation:
            L.geocoder_region("paca")
        self.assertEqual(str(inspect.signature(L.geocoder_region)), "(slug)")
        kwargs = implementation.call_args.kwargs
        self.assertIs(kwargs["departements_de_region"], L._departements_de_region)
        self.assertIs(kwargs["regions_disponibles"], L._regions_disponibles)
        self.assertIs(kwargs["geocoder_departement"], L.geocoder_departement)
        with mock.patch.object(L, "_departements_de_region", return_value=[]), \
             mock.patch.object(L, "_regions_disponibles", return_value=["paca"]):
            self.assertEqual(
                L.geocoder_region("atlantide"), (None, None, None, None, None),
            )


class ResolutionZoneContractTests(unittest.TestCase):
    """Caractérise `_resoudre_zone_lidar`, extraite de `main()` en 8c.

    Les 5 branches --zone-* et le sharding --block sont interdépendants
    (bbox/nom_zone/cx/cy réutilisés d'une section à l'autre) : contrairement à
    8a/8b, une erreur de recopie ici corromprait silencieusement la zone
    traitée plutôt que de casser un test. Les géocodeurs réseau
    (`geocoder_region`/`geocoder_departement`/`geocoder_ville_natif`) sont
    mockés ; les conversions CRS pures (`_wgs84_vers_natif`,
    `_bbox_enveloppe_transform`, `calculer_grille_bbox`, `calculer_grille`)
    tournent réellement (déterministes, sans réseau, déjà couvertes ailleurs).
    """

    def _args(self, **kw):
        base = dict(
            source=None, zone_departement=None, zone_bbox=None,
            zone_ville=None, zone_gps=None, zone_region=None,
            zone_nom=None, zone_width=None, block="",
        )
        base.update(kw)
        return SimpleNamespace(**base)

    def test_facade_keeps_signature_and_rebuilds_all_dependencies(self):
        self.assertTrue(callable(terrain_resolution.resoudre_zone_lidar))
        attendu = object()
        args = self._args(zone_gps="43.3,6.0")
        with mock.patch.object(L, "_resoudre_zone_lidar_impl",
                               return_value=attendu) as implementation:
            resultat = L._resoudre_zone_lidar(args, False)
        self.assertIs(resultat, attendu)
        self.assertEqual(
            str(inspect.signature(L._resoudre_zone_lidar)), "(args, _osm_seul)",
        )
        deps = implementation.call_args.kwargs["dependances"]
        self.assertIs(deps.provider, L.PROVIDER)
        self.assertIs(deps.geocoder_region, L.geocoder_region)
        self.assertIs(deps.geocoder_departement, L.geocoder_departement)
        self.assertIs(deps.wgs84_vers_natif, L._wgs84_vers_natif)
        self.assertIs(deps.parse_block, L._parse_block)

    def test_no_zone_option_exits_with_error(self):
        with self.assertRaises(SystemExit) as ctx:
            L._resoudre_zone_lidar(self._args(), False)
        self.assertEqual(ctx.exception.code, 1)

    def test_source_tif_without_zone_exits_with_error(self):
        args = self._args(source="dem.tif")
        with self.assertRaises(SystemExit) as ctx:
            L._resoudre_zone_lidar(args, False)
        self.assertEqual(ctx.exception.code, 1)

    def test_departement_mode_resolves_bbox_and_name(self):
        with mock.patch.object(
            L, "geocoder_departement",
            return_value=("Var", 900000, 6200000, 950000, 6250000),
        ):
            bbox, nom_zone, cx, cy, blk = L._resoudre_zone_lidar(
                self._args(zone_departement="83"), False)
        self.assertEqual(nom_zone, "var_83")
        self.assertIsNone(blk)
        # calculer_grille_bbox (LiDAR, non osm_seul) borne un carré >= l'enveloppe.
        self.assertLessEqual(bbox[0], 900000)
        self.assertGreaterEqual(bbox[2], 950000)

    def test_departement_mode_osm_seul_uses_raw_department_bbox(self):
        with mock.patch.object(
            L, "geocoder_departement",
            return_value=("Var", 900000, 6200000, 950000, 6250000),
        ):
            bbox, nom_zone, cx, cy, blk = L._resoudre_zone_lidar(
                self._args(zone_departement="83"), True)
        self.assertEqual(bbox, (900000, 6200000, 950000, 6250000))

    def test_departement_mode_geocoder_failure_exits(self):
        with mock.patch.object(L, "geocoder_departement",
                               return_value=(None, 0, 0, 0, 0)):
            with self.assertRaises(SystemExit) as ctx:
                L._resoudre_zone_lidar(self._args(zone_departement="999"), False)
        self.assertEqual(ctx.exception.code, 1)

    def test_region_mode_lidar_geocodes_union_bbox(self):
        with mock.patch.object(
            L, "geocoder_region",
            return_value=("Provence-Alpes-Côte d'Azur", 800000, 6100000,
                         1000000, 6300000),
        ) as geocode:
            bbox, nom_zone, cx, cy, blk = L._resoudre_zone_lidar(
                self._args(zone_region="paca"), False)
        geocode.assert_called_once()
        self.assertEqual(nom_zone, "paca")

    def test_region_mode_osm_seul_skips_geocoding_uses_sentinel(self):
        with mock.patch.object(L, "_regions_disponibles",
                               return_value=["paca"]), \
             mock.patch.object(L, "geocoder_region") as geocode:
            bbox, nom_zone, cx, cy, blk = L._resoudre_zone_lidar(
                self._args(zone_region="paca"), True)
        geocode.assert_not_called()
        self.assertEqual(bbox, (0.0, 0.0, 0.0, 0.0))

    def test_region_mode_osm_seul_unknown_region_exits(self):
        with mock.patch.object(L, "_regions_disponibles", return_value=["paca"]):
            with self.assertRaises(SystemExit) as ctx:
                L._resoudre_zone_lidar(self._args(zone_region="atlantide"), True)
        self.assertEqual(ctx.exception.code, 1)

    def test_bbox_mode_valid_converts_crs_and_centers(self):
        bbox, nom_zone, cx, cy, blk = L._resoudre_zone_lidar(
            self._args(zone_bbox="6.0,43.3,6.1,43.4"), False)
        self.assertIsNotNone(bbox)
        self.assertNotEqual((cx, cy), (0.0, 0.0))
        self.assertIsNone(blk)

    def test_bbox_mode_swapped_corners_are_reordered_not_rejected(self):
        # W,S,E,N inversé (E,N,W,S) : le code réordonne au lieu d'exiger la
        # bonne convention (message d'aide séparé côté producteur WMTS, R2#17).
        bbox_ok, _, _, _, _ = L._resoudre_zone_lidar(
            self._args(zone_bbox="6.0,43.3,6.1,43.4"), False)
        bbox_swapped, _, _, _, _ = L._resoudre_zone_lidar(
            self._args(zone_bbox="6.1,43.4,6.0,43.3"), False)
        self.assertEqual(bbox_ok, bbox_swapped)

    def test_bbox_mode_invalid_format_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            L._resoudre_zone_lidar(self._args(zone_bbox="not,a,bbox"), False)
        self.assertEqual(ctx.exception.code, 1)

    def test_bbox_mode_degenerate_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            L._resoudre_zone_lidar(
                self._args(zone_bbox="6.0,43.3,6.0,43.4"), False)
        self.assertEqual(ctx.exception.code, 1)

    def test_bbox_mode_out_of_range_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            L._resoudre_zone_lidar(
                self._args(zone_bbox="600.0,43.3,601.0,43.4"), False)
        self.assertEqual(ctx.exception.code, 1)

    def test_gps_mode_valid_converts_to_native_crs(self):
        bbox, nom_zone, cx, cy, blk = L._resoudre_zone_lidar(
            self._args(zone_gps="43.3156,6.0423", zone_width=5.0), False)
        self.assertNotEqual((cx, cy), (0.0, 0.0))
        self.assertIsNotNone(bbox)

    def test_gps_mode_invalid_format_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            L._resoudre_zone_lidar(self._args(zone_gps="invalid"), False)
        self.assertEqual(ctx.exception.code, 1)

    def test_gps_mode_out_of_range_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            L._resoudre_zone_lidar(self._args(zone_gps="200.0,6.0"), False)
        self.assertEqual(ctx.exception.code, 1)

    def test_city_mode_resolves_via_geocoder(self):
        with mock.patch.object(L, "geocoder_ville_natif",
                               return_value=(920000, 6230000)):
            bbox, nom_zone, cx, cy, blk = L._resoudre_zone_lidar(
                self._args(zone_ville="gareoult", zone_width=5.0), False)
        self.assertEqual((cx, cy), (920000, 6230000))
        self.assertEqual(nom_zone, "gareoult")

    def test_city_mode_geocoder_failure_exits(self):
        with mock.patch.object(L, "geocoder_ville_natif",
                               return_value=(None, None)):
            with self.assertRaises(SystemExit) as ctx:
                L._resoudre_zone_lidar(self._args(zone_ville="nulle_part"), False)
        self.assertEqual(ctx.exception.code, 1)

    def test_city_mode_width_grid_uses_zone_width_or_20km_default(self):
        with mock.patch.object(L, "geocoder_ville_natif",
                               return_value=(920000, 6230000)), \
             mock.patch.object(L, "calculer_grille") as grille:
            grille.return_value = (0, 0, 1, 1)
            L._resoudre_zone_lidar(
                self._args(zone_ville="gareoult", zone_width=None), False)
        grille.assert_called_once_with(920000, 6230000, 10.0)   # 20/2 par défaut

    def test_variant_tag_suffixes_zone_name(self):
        ancien_provider = L.PROVIDER
        try:
            L.PROVIDER = SimpleNamespace(
                CRS_NATIF=ancien_provider.CRS_NATIF,
                variant_tag=lambda: "laz",
            )
            with mock.patch.object(L, "geocoder_ville_natif",
                                   return_value=(920000, 6230000)):
                _, nom_zone, _, _, _ = L._resoudre_zone_lidar(
                    self._args(zone_ville="gareoult", zone_width=5.0), False)
        finally:
            L.PROVIDER = ancien_provider
        self.assertTrue(nom_zone.endswith("_laz"))

    def test_block_sharding_narrows_bbox_and_suffixes_name(self):
        bbox, nom_zone, cx, cy, blk = L._resoudre_zone_lidar(
            self._args(zone_bbox="6.0,43.3,6.4,43.7", block="1/4"), False)
        self.assertEqual(blk, (1, 4))
        self.assertTrue(nom_zone.endswith("_b1"))
        # Le bloc est un quart de l'emprise totale (partition par ligne/colonne).
        largeur_bloc = bbox[2] - bbox[0]
        with_no_block, _, _, _, _ = L._resoudre_zone_lidar(
            self._args(zone_bbox="6.0,43.3,6.4,43.7"), False)
        largeur_totale = with_no_block[2] - with_no_block[0]
        self.assertLess(largeur_bloc, largeur_totale)

    def test_block_invalid_spec_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            L._resoudre_zone_lidar(
                self._args(zone_bbox="6.0,43.3,6.1,43.4", block="not-a-block"),
                False)
        self.assertEqual(ctx.exception.code, 1)

    def test_block_skipped_when_osm_seul(self):
        bbox, nom_zone, cx, cy, blk = L._resoudre_zone_lidar(
            self._args(zone_bbox="6.0,43.3,6.1,43.4", block="1/4"), True)
        self.assertEqual(blk, (1, 4))          # parsé et retourné...
        self.assertFalse(nom_zone.endswith("_b1"))   # ...mais pas appliqué


class OmbragesProviderFacadeContractTests(unittest.TestCase):
    """`_extraire_tiff_multipart`/`_post_fetch_si_besoin`/`_fetch_provider_shadings`
    gardent leur signature historique ; l'injection (PROVIDER, callable
    `_extraire_tiff_multipart`) est absorbée par la façade."""

    def test_extraire_tiff_multipart_facade_injects_current_chunk_size(self):
        with mock.patch.object(
            L, "_extraire_tiff_multipart_impl", return_value=None,
        ) as impl:
            L._extraire_tiff_multipart("chemin.tif")
        self.assertEqual(impl.call_args.args, ("chemin.tif",))
        self.assertEqual(impl.call_args.kwargs["http_chunk_size"], L.HTTP_CHUNK_SIZE)

    def test_post_fetch_facade_injects_current_provider_and_extraction(self):
        with mock.patch.object(
            L, "_post_fetch_si_besoin_impl", return_value=None,
        ) as impl:
            L._post_fetch_si_besoin("chemin.tif")
        self.assertEqual(impl.call_args.args, ("chemin.tif",))
        self.assertIs(impl.call_args.kwargs["provider"], L.PROVIDER)
        self.assertIs(
            impl.call_args.kwargs["extraire_tiff_multipart"],
            L._extraire_tiff_multipart,
        )

    def test_post_fetch_facade_reads_monkeypatched_extraction_at_call_time(self):
        """Reproduit le style de `_test_atomic_downloads.py` : `_extraire_tiff_multipart`
        est remplacée en bloc, puis un appelant qui en dépend est invoqué —
        l'appel interne doit voir le remplacement (même piège que `_wmts_fetch`,
        cf. 7c)."""
        remplacant = mock.Mock(name="_extraire_tiff_multipart-patché")
        with mock.patch.object(L, "_extraire_tiff_multipart", remplacant), \
             mock.patch.object(L, "_post_fetch_si_besoin_impl") as impl:
            L._post_fetch_si_besoin("chemin.tif")
        self.assertIs(impl.call_args.kwargs["extraire_tiff_multipart"], remplacant)

    def test_fetch_provider_shadings_facade_injects_current_seams(self):
        with mock.patch.object(
            L, "_fetch_provider_shadings_impl", return_value=None,
        ) as impl:
            L._fetch_provider_shadings([], (0, 0, 1, 1), Path("."), "zone",
                                       False, {})
        deps = impl.call_args.kwargs["dependances"]
        self.assertIs(deps.provider, L.PROVIDER)
        self.assertIs(deps.extraire_tiff_multipart, L._extraire_tiff_multipart)
        self.assertIs(deps.chemin_part, L._chemin_part)
        self.assertIs(deps.creer_fichier, L._creer_fichier)
        self.assertIs(deps.formater_duree, L._hms)
        self.assertIs(deps.valider_tif, L._valider_tif_dalle)
        self.assertIs(deps.normaliser_nom, L.normaliser_nom)
        self.assertEqual(deps.http_chunk_size, L.HTTP_CHUNK_SIZE)

    def test_fetch_provider_shadings_facade_reads_reassigned_provider(self):
        ancien_provider = L.PROVIDER
        try:
            L.PROVIDER = SimpleNamespace(WCS_URL="https://example.invalid")
            with mock.patch.object(
                L, "_fetch_provider_shadings_impl", return_value=None,
            ) as impl:
                L._fetch_provider_shadings([], (0, 0, 1, 1), Path("."), "zone",
                                           False, {})
            self.assertIs(
                impl.call_args.kwargs["dependances"].provider, L.PROVIDER,
            )
        finally:
            L.PROVIDER = ancien_provider


class OmbragesPuresFacadeContractTests(unittest.TestCase):
    """Les 3 fonctions à couture (`_sauver_array_georef`, `_publier_tif_atomique`,
    `_build_vrt_xml`) restent appelables avec leur signature historique
    (3 positionnels) : la façade absorbe l'injection sans toucher aux points
    d'appel existants ni aux tests qui les monkeypatchent en bloc."""

    def test_sauver_array_georef_facade_injects_current_formater_duree(self):
        expected = object()
        with mock.patch.object(
            L, "_sauver_array_georef_impl", return_value=expected,
        ) as impl:
            result = L._sauver_array_georef("arr", "src", "dst")
        self.assertIs(result, expected)
        self.assertEqual(impl.call_args.args, ("arr", "src", "dst"))
        self.assertIs(impl.call_args.kwargs["formater_duree"], L._hms)

    def test_publier_tif_atomique_facade_injects_current_valider_tif(self):
        expected = object()
        with mock.patch.object(
            L, "_publier_tif_atomique_impl", return_value=expected,
        ) as impl:
            result = L._publier_tif_atomique("part", "final")
        self.assertIs(result, expected)
        self.assertEqual(impl.call_args.args, ("part", "final"))
        self.assertIs(impl.call_args.kwargs["valider_tif"], L._valider_tif_dalle)

    def test_publier_tif_atomique_facade_reads_monkeypatched_validator(self):
        remplacant = mock.Mock(name="_valider_tif_dalle-patché")
        with mock.patch.object(L, "_valider_tif_dalle", remplacant), \
             mock.patch.object(L, "_publier_tif_atomique_impl") as impl:
            L._publier_tif_atomique("part", "final")
        self.assertIs(impl.call_args.kwargs["valider_tif"], remplacant)

    def test_build_vrt_xml_facade_injects_current_ecrire_texte_atomique(self):
        expected = object()
        with mock.patch.object(
            L, "_build_vrt_xml_impl", return_value=expected,
        ) as impl:
            result = L._build_vrt_xml(["a.tif"], "out.vrt", 0.5)
        self.assertIs(result, expected)
        self.assertEqual(impl.call_args.args, (["a.tif"], "out.vrt", 0.5))
        self.assertIs(
            impl.call_args.kwargs["ecrire_texte_atomique"], L._ecrire_texte_atomique,
        )


class RasterFormatFacadeContractTests(unittest.TestCase):
    def test_rmap_facade_injects_current_atomic_services(self):
        expected = object()
        with mock.patch.object(
            L,
            "_generer_rmap_depuis_mbtiles_impl",
            return_value=expected,
        ) as implementation:
            result = L.generer_rmap_depuis_mbtiles(
                Path("source.mbtiles"),
                ecraser=True,
            )

        self.assertIs(result, expected)
        kwargs = implementation.call_args.kwargs
        self.assertIs(kwargs["chemin_part"], L._chemin_part)
        self.assertIs(kwargs["blob_vers_jpeg"], L._blob_vers_jpeg)
        self.assertIs(kwargs["build_map_info"], L._build_map_info)
        self.assertEqual(kwargs["seuil_rmap_padding"], L.SEUIL_RMAP_PADDING)

    def test_sqlitedb_facade_injects_current_atomic_services(self):
        expected = object()
        with mock.patch.object(
            L,
            "_generer_sqlitedb_depuis_mbtiles_impl",
            return_value=expected,
        ) as implementation:
            result = L.generer_sqlitedb_depuis_mbtiles(Path("source.mbtiles"))

        self.assertIs(result, expected)
        kwargs = implementation.call_args.kwargs
        self.assertIs(kwargs["chemin_part"], L._chemin_part)
        self.assertIs(kwargs["nettoyer_sqlite_part"], L._nettoyer_sqlite_part)
        self.assertIs(kwargs["valider_sqlite_part"], L._valider_sqlite_part)
        self.assertIs(kwargs["schema_courant"], L._sqlitedb_schema_courant)
        self.assertEqual(
            kwargs["batch_sqlitedb_insert"],
            L.BATCH_SQLITEDB_INSERT,
        )

    def test_multi_format_facade_uses_current_split_and_unit_callbacks(self):
        expected = object()
        args = SimpleNamespace()
        with mock.patch.object(
            L,
            "_convertir_formats_impl",
            return_value=expected,
        ) as implementation:
            result = L._convertir_formats(Path("source.mbtiles"), args)

        self.assertIs(result, expected)
        kwargs = implementation.call_args.kwargs
        self.assertIs(kwargs["decouper"], L.decouper_mbtiles)
        self.assertIs(kwargs["convertir_un"], L._convertir_un_mbtiles)


class ProviderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider_dir = ROOT / "providers"
        cls.primary_paths = sorted(
            path for path in cls.provider_dir.glob("*.py")
            if not path.stem.startswith("_")
            and not path.stem.endswith("_laz")
            and path.stem != "common"
        )
        cls.laz_paths = sorted(cls.provider_dir.glob("*_laz.py"))
        cls.primary_modules = {
            path: L._import_patchable_source_module("providers", path.stem)
            for path in cls.primary_paths
        }
        cls.catalog = L._discover_providers()
        cls.catalog_by_code = {entry["code"]: entry for entry in cls.catalog}

    def test_catalog_contains_every_primary_provider_once(self):
        expected_codes = [
            self.primary_modules[path].CODE for path in self.primary_paths
        ]
        actual_codes = [entry["code"] for entry in self.catalog]
        self.assertEqual(actual_codes, expected_codes)
        self.assertEqual(len(actual_codes), len(set(actual_codes)))
        self.assertIn("fr-ign", actual_codes)

    def test_every_primary_provider_respects_the_pipeline_contract(self):
        from providers.common import COUNTRY_INFO

        for path, module in self.primary_modules.items():
            with self.subTest(provider=path.stem):
                self.assertEqual(module.CODE, path.stem.replace("_", "-"))
                self.assertIsInstance(module.NAME, str)
                self.assertTrue(module.NAME)
                self.assertIsInstance(module.LICENSE, str)
                self.assertTrue(module.LICENSE)
                self.assertIsInstance(module.DOC_URL, str)
                self.assertTrue(module.DOC_URL)
                self.assertIn(module.COUNTRY, COUNTRY_INFO)
                self.assertIsInstance(module.CRS_NATIF, str)
                self.assertTrue(module.CRS_NATIF)
                self.assertGreater(float(module.RESOLUTION_M), 0)
                self.assertGreater(int(module.SEUIL_DALLE_VALIDE), 0)
                self.assertTrue(callable(module.dalle_filename))
                self.assertTrue(callable(module.subdir_from_name))
                self.assertTrue(callable(module.discover_dalles))
                parameters = list(
                    inspect.signature(module.discover_dalles).parameters
                )
                self.assertEqual(
                    parameters[:4],
                    ["bbox_wgs84", "bbox_natif", "cache_path", "workers"],
                )

                entry = self.catalog_by_code[module.CODE]
                self.assertEqual(entry["name"], module.NAME)
                self.assertEqual(entry["country"], module.COUNTRY)
                self.assertEqual(
                    entry["resolution_m"], float(module.RESOLUTION_M)
                )

    def test_laz_twins_stay_capabilities_of_their_parent_provider(self):
        expected_keys = {
            "hmin": "LAZ_HMIN",
            "hmax": "LAZ_HMAX",
            "ground": "LAZ_GROUND",
            "csf_threshold": "LAZ_CSF_THRESHOLD",
            "csf_resolution": "LAZ_CSF_RESOLUTION",
            "csf_rigidness": "LAZ_CSF_RIGIDNESS",
            "download_workers_max": "DOWNLOAD_WORKERS_MAX",
        }
        for path in self.laz_paths:
            twin = L._import_patchable_source_module("providers", path.stem)
            parent_code = path.stem[:-4].replace("_", "-")
            with self.subTest(provider=twin.CODE):
                self.assertEqual(twin.CODE, f"{parent_code}-laz")
                self.assertNotIn(twin.CODE, self.catalog_by_code)
                self.assertIn(parent_code, self.catalog_by_code)
                capability = self.catalog_by_code[parent_code].get("laz")
                self.assertIsNotNone(capability)
                self.assertEqual(
                    capability["classes"],
                    ",".join(str(value) for value in twin.LAZ_CLASSES),
                )
                for catalog_key, module_key in expected_keys.items():
                    expected = getattr(twin, module_key)
                    actual = capability[catalog_key]
                    if catalog_key not in ("ground", "csf_rigidness",
                                            "download_workers_max"):
                        expected = float(expected)
                    elif catalog_key in ("csf_rigidness",
                                          "download_workers_max"):
                        expected = int(expected)
                    else:
                        expected = str(expected)
                    self.assertEqual(actual, expected)


class GeojsonMapsforgeFacadeContractTests(unittest.TestCase):
    def _capturer_dependances(self, **surcharges):
        expected = object()
        with contextlib.ExitStack() as stack:
            for name, value in surcharges.items():
                stack.enter_context(mock.patch.object(L, name, value))
            implementation = stack.enter_context(mock.patch.object(
                L,
                "_generer_map_depuis_geojson_ign_impl",
                return_value=expected,
            ))
            result = L.generer_map_depuis_geojson_ign(
                "source.geojson",
                "sortie",
                "zone",
                (6.0, 43.0, 6.1, 43.1),
                ecraser=True,
                epsilon=0.001,
            )

        self.assertIs(result, expected)
        implementation.assert_called_once()
        self.assertEqual(
            implementation.call_args.args,
            (
                "source.geojson",
                "sortie",
                "zone",
                (6.0, 43.0, 6.1, 43.1),
            ),
        )
        self.assertTrue(implementation.call_args.kwargs["ecraser"])
        self.assertEqual(implementation.call_args.kwargs["epsilon"], 0.001)
        return implementation.call_args.kwargs["dependances"]

    def test_facade_keeps_its_signature_and_injects_current_seams(self):
        self.assertEqual(
            list(inspect.signature(L.generer_map_depuis_geojson_ign).parameters),
            [
                "geojson_src",
                "dossier_ville",
                "nom_zone",
                "bbox_wgs84",
                "ecraser",
                "epsilon",
            ],
        )
        deps = self._capturer_dependances()
        self.assertIs(
            deps.convertir_geojson_osm_xml,
            L.geojson_ign_vers_osm_xml,
        )
        self.assertIs(deps.preparer_osmosis, L._preparer_osmosis)
        self.assertIs(deps.run_osmosis_streaming, L._run_osmosis_streaming)
        self.assertIs(deps.chemin_part, L._chemin_part)
        self.assertIs(deps.hash_config, L._hash_config)
        self.assertIs(deps.sig_sidecar_stale, L._sig_sidecar_stale)
        self.assertIs(deps.sig_sidecar_ecrire, L._sig_sidecar_ecrire)
        self.assertIs(deps.java_opts_extra, L._java_opts_extra)
        self.assertIs(deps.log_req, L._log_req)
        self.assertIs(deps.formater_duree, L._hms)
        self.assertIs(deps.windows, L.WINDOWS)

    def test_facade_reads_reassigned_seams_at_call_time(self):
        seams = {
            "geojson_ign_vers_osm_xml": mock.Mock(name="convertir_xml"),
            "_preparer_osmosis": mock.Mock(name="preparer_osmosis"),
            "_run_osmosis_streaming": mock.Mock(name="run_osmosis"),
            "_chemin_part": mock.Mock(name="chemin_part"),
            "_hash_config": mock.Mock(name="hash_config"),
            "_sig_sidecar_stale": mock.Mock(name="sig_stale"),
            "_sig_sidecar_ecrire": mock.Mock(name="sig_ecrire"),
            "_java_opts_extra": mock.Mock(name="java_opts_extra"),
            "_log_req": mock.Mock(name="log_req"),
            "_hms": mock.Mock(name="hms"),
            "WINDOWS": not L.WINDOWS,
        }
        deps = self._capturer_dependances(**seams)

        self.assertIs(
            deps.convertir_geojson_osm_xml,
            seams["geojson_ign_vers_osm_xml"],
        )
        self.assertIs(deps.preparer_osmosis, seams["_preparer_osmosis"])
        self.assertIs(
            deps.run_osmosis_streaming,
            seams["_run_osmosis_streaming"],
        )
        self.assertIs(deps.chemin_part, seams["_chemin_part"])
        self.assertIs(deps.hash_config, seams["_hash_config"])
        self.assertIs(deps.sig_sidecar_stale, seams["_sig_sidecar_stale"])
        self.assertIs(deps.sig_sidecar_ecrire, seams["_sig_sidecar_ecrire"])
        self.assertIs(deps.java_opts_extra, seams["_java_opts_extra"])
        self.assertIs(deps.log_req, seams["_log_req"])
        self.assertIs(deps.formater_duree, seams["_hms"])
        self.assertIs(deps.windows, seams["WINDOWS"])


class GeojsonRasterFacadeContractTests(unittest.TestCase):
    def _capturer_dependances(self, **surcharges):
        expected = object()
        with contextlib.ExitStack() as stack:
            for name, value in surcharges.items():
                stack.enter_context(mock.patch.object(L, name, value))
            implementation = stack.enter_context(mock.patch.object(
                L,
                "_rasteriser_geojson_transparent_impl",
                return_value=expected,
            ))
            result = L.rasteriser_geojson_transparent(
                "source.geojson",
                "sortie.sqlitedb",
                13,
                17,
                ecraser=True,
                supersample=3,
                bbox_wgs84=(6.0, 43.0, 6.1, 43.1),
            )

        self.assertIs(result, expected)
        implementation.assert_called_once()
        self.assertEqual(
            implementation.call_args.args,
            ("source.geojson", "sortie.sqlitedb", 13, 17),
        )
        self.assertEqual(
            implementation.call_args.kwargs,
            {
                "ecraser": True,
                "supersample": 3,
                "bbox_wgs84": (6.0, 43.0, 6.1, 43.1),
                "dependances": implementation.call_args.kwargs["dependances"],
            },
        )
        return implementation.call_args.kwargs["dependances"]

    def test_facade_keeps_its_signature_and_injects_current_seams(self):
        self.assertEqual(
            list(inspect.signature(L.rasteriser_geojson_transparent).parameters),
            [
                "geojson_path",
                "sqlitedb_out",
                "zoom_min",
                "zoom_max",
                "ecraser",
                "supersample",
                "bbox_wgs84",
            ],
        )
        deps = self._capturer_dependances()
        self.assertIs(deps.chemin_part, L._chemin_part)
        self.assertIs(deps.nettoyer_sqlite_part, L._nettoyer_sqlite_part)
        self.assertIs(deps.valider_sqlite_part, L._valider_sqlite_part)
        self.assertIs(deps.stop_event, L._stop_event)
        self.assertIs(deps.deg_to_tile, L.deg_to_tile)
        self.assertIs(deps.overlay_style, L._OVERLAY_STYLE)
        self.assertIs(deps.overlay_defaut, L._OVERLAY_DEFAUT)
        self.assertIs(deps.overlay_tile_warn, L._OVERLAY_TILE_WARN)
        self.assertIs(deps.overlay_style_key, L._overlay_style_key)
        self.assertIs(deps.overlay_sequences, L._overlay_sequences)
        self.assertIs(deps.clip_polygone_rect, L._clip_polygone_rect)
        self.assertIs(deps.seg_inter_box, L._seg_inter_box)

    def test_facade_reads_reassigned_seams_at_call_time(self):
        seams = {
            "_chemin_part": mock.Mock(name="chemin_part"),
            "_nettoyer_sqlite_part": mock.Mock(name="nettoyer_sqlite_part"),
            "_valider_sqlite_part": mock.Mock(name="valider_sqlite_part"),
            "_stop_event": mock.Mock(name="stop_event"),
            "deg_to_tile": mock.Mock(name="deg_to_tile"),
            "_OVERLAY_STYLE": {"test": ((1, 2, 3, 4), 1, False)},
            "_OVERLAY_DEFAUT": ((5, 6, 7, 8), 2, True),
            "_OVERLAY_TILE_WARN": 123,
            "_overlay_style_key": mock.Mock(name="overlay_style_key"),
            "_overlay_sequences": mock.Mock(name="overlay_sequences"),
            "_clip_polygone_rect": mock.Mock(name="clip_polygone_rect"),
            "_seg_inter_box": mock.Mock(name="seg_inter_box"),
        }
        deps = self._capturer_dependances(**seams)

        self.assertIs(deps.chemin_part, seams["_chemin_part"])
        self.assertIs(
            deps.nettoyer_sqlite_part, seams["_nettoyer_sqlite_part"]
        )
        self.assertIs(
            deps.valider_sqlite_part, seams["_valider_sqlite_part"]
        )
        self.assertIs(deps.stop_event, seams["_stop_event"])
        self.assertIs(deps.deg_to_tile, seams["deg_to_tile"])
        self.assertIs(deps.overlay_style, seams["_OVERLAY_STYLE"])
        self.assertIs(deps.overlay_defaut, seams["_OVERLAY_DEFAUT"])
        self.assertEqual(deps.overlay_tile_warn, 123)
        self.assertIs(deps.overlay_style_key, seams["_overlay_style_key"])
        self.assertIs(deps.overlay_sequences, seams["_overlay_sequences"])
        self.assertIs(deps.clip_polygone_rect, seams["_clip_polygone_rect"])
        self.assertIs(deps.seg_inter_box, seams["_seg_inter_box"])


class GeojsonOsmXmlFacadeContractTests(unittest.TestCase):
    def _capturer_dependances(self, **surcharges):
        with contextlib.ExitStack() as stack:
            for name, value in surcharges.items():
                stack.enter_context(mock.patch.object(L, name, value))
            implementation = stack.enter_context(mock.patch.object(
                L,
                "_geojson_ign_vers_osm_xml_impl",
                return_value=True,
            ))
            self.assertTrue(L.geojson_ign_vers_osm_xml(
                "source.geojson",
                "sortie.osm",
                epsilon=0.0123,
            ))

        implementation.assert_called_once()
        self.assertEqual(
            implementation.call_args.args,
            ("source.geojson", "sortie.osm"),
        )
        self.assertEqual(implementation.call_args.kwargs["epsilon"], 0.0123)
        return implementation.call_args.kwargs["dependances"]

    def test_facade_keeps_its_signature_and_injects_current_seams(self):
        self.assertEqual(
            list(inspect.signature(L.geojson_ign_vers_osm_xml).parameters),
            ["geojson_path", "osm_xml_path", "epsilon"],
        )
        deps = self._capturer_dependances()
        self.assertIs(deps.chemin_part, L._chemin_part)
        self.assertIs(deps.stop_event, L._stop_event)
        self.assertIs(deps.layer_tags, L._IGN_LAYER_TAGS)
        self.assertIs(deps.tags_pour_layer, L._tags_pour_layer)
        self.assertIs(deps.douglas_peucker, L._douglas_peucker)
        self.assertIs(deps.epsilon_defaut, L._IGN_SIMPLIFY_EPSILON)

    def test_facade_reads_reassigned_seams_at_call_time(self):
        chemin_part = mock.Mock(name="chemin_part")
        stop_event = mock.Mock(name="stop_event")
        layer_tags = {"test": {"note": "test"}}
        tags_pour_layer = mock.Mock(name="tags_pour_layer")
        douglas_peucker = mock.Mock(name="douglas_peucker")
        deps = self._capturer_dependances(
            _chemin_part=chemin_part,
            _stop_event=stop_event,
            _IGN_LAYER_TAGS=layer_tags,
            _tags_pour_layer=tags_pour_layer,
            _douglas_peucker=douglas_peucker,
            _IGN_SIMPLIFY_EPSILON=0.987,
        )

        self.assertIs(deps.chemin_part, chemin_part)
        self.assertIs(deps.stop_event, stop_event)
        self.assertIs(deps.layer_tags, layer_tags)
        self.assertIs(deps.tags_pour_layer, tags_pour_layer)
        self.assertIs(deps.douglas_peucker, douglas_peucker)
        self.assertEqual(deps.epsilon_defaut, 0.987)


class GeojsonGeometryContractTests(unittest.TestCase):
    """Contrats purs du domaine GeoJSON, indépendants des IO et d'osmosis."""

    def test_layer_tags_and_overlay_style_keep_their_precedence(self):
        self.assertIs(
            L._tags_pour_layer("batiment"),
            geojson_geometry._IGN_LAYER_TAGS["batiment"],
        )
        self.assertEqual(
            L._tags_pour_layer("zone_ign_troncon_hydrographique"),
            {"waterway": "stream"},
        )
        self.assertEqual(
            L._tags_pour_layer("couche_inconnue"),
            {"note": "couche_inconnue"},
        )
        self.assertEqual(
            L._overlay_style_key(
                {"_cle": "railway", "source": "zone_ign_batiment"},
            ),
            "railway",
        )
        self.assertEqual(
            L._overlay_style_key({"source": "zone_ign_batiment"}),
            "building",
        )
        self.assertEqual(
            L._overlay_style_key({}, "zone_ign_plan_d_eau"),
            "natural",
        )
        self.assertEqual(L._overlay_style_key({"highway": "track"}), "highway")
        self.assertIsNone(L._overlay_style_key({"name": "sans style"}))

    def test_geometry_collection_preserves_polygon_holes(self):
        exterior = [[0, 0], [4, 0], [4, 4], [0, 0]]
        hole = [[1, 1], [2, 1], [1, 2], [1, 1]]
        geometry = {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                {"type": "Polygon", "coordinates": [exterior, hole]},
                {"type": "Point", "coordinates": [2, 2]},
            ],
        }

        lines, polygons = L._overlay_sequences(geometry)

        self.assertEqual(lines, [[[0, 0], [1, 1]]])
        self.assertEqual(polygons, [[exterior, hole]])

    def test_multi_geometries_are_flattened_without_points(self):
        polygon_a = [[[0, 0], [1, 0], [0, 1], [0, 0]]]
        polygon_b = [[[2, 2], [3, 2], [2, 3], [2, 2]]]

        lines, polygons = L._overlay_sequences({
            "type": "GeometryCollection",
            "geometries": [
                {
                    "type": "MultiLineString",
                    "coordinates": [
                        [[0, 0], [1, 1]],
                        [[2, 2], [3, 3]],
                    ],
                },
                {
                    "type": "MultiPolygon",
                    "coordinates": [polygon_a, polygon_b],
                },
                {"type": "MultiPoint", "coordinates": [[4, 4], [5, 5]]},
            ],
        })

        self.assertEqual(
            lines,
            [[[0, 0], [1, 1]], [[2, 2], [3, 3]]],
        )
        self.assertEqual(polygons, [polygon_a, polygon_b])

    def test_douglas_peucker_keeps_endpoints_and_significant_turns(self):
        points = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (2.0, 1.0)]
        original = list(points)

        simplified = L._douglas_peucker(points, epsilon=0.1)

        self.assertEqual(simplified, [points[0], points[2], points[3]])
        self.assertEqual(points[0], simplified[0])
        self.assertEqual(points[-1], simplified[-1])
        self.assertEqual(points, original)

    def test_surface_epsilon_keeps_documented_thresholds(self):
        metres_par_degre = 111_000.0
        cases = (
            (199.9, 3.0),
            (200.0, 8.0),
            (999.9, 8.0),
            (1_000.0, 15.0),
            (15_000.0, 25.0),
            (100_000.0, 40.0),
        )
        for surface, metres in cases:
            with self.subTest(surface=surface):
                self.assertEqual(
                    L._epsilon_depuis_surface_km2(surface),
                    metres / metres_par_degre,
                )


class ManifestContractTests(unittest.TestCase):
    def test_concurrent_batches_are_persisted_without_loss_or_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "manifeste.json"
            manifest = L.Manifeste(manifest_path)
            manifest.debut_morceau("chunk", "zone")
            barrier = threading.Barrier(8)

            def register_batch(worker: int):
                paths = [root / f"w{worker}_{index}.tif" for index in range(10)]
                barrier.wait(timeout=10)
                manifest.enregistrer_fichiers(paths + paths[:2], "chunk")
                return {str(path.resolve()) for path in paths}

            with ThreadPoolExecutor(max_workers=8) as pool:
                expected = set().union(*pool.map(register_batch, range(8)))

            manifest.fin_morceau("chunk", 12)
            persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(set(persisted["fichiers"]["chunk"]), expected)
            self.assertEqual(len(persisted["fichiers"]["chunk"]), 80)
            self.assertTrue(L.Manifeste(manifest_path).deja_traite("chunk"))
            self.assertEqual(list(root.rglob("*.part")), [])

    def test_nested_tracking_restores_the_outer_thread_local_context(self):
        class Recorder:
            def __init__(self):
                self.calls = []

            def enregistrer_fichier(self, path, key):
                self.calls.append((Path(path).name, key))

        outer = Recorder()
        inner = Recorder()
        with L._contexte_manifeste(outer, "outer"):
            L._creer_fichier("before.tif")
            with L._contexte_manifeste(inner, "inner"):
                L._creer_fichier("inside.tif")
            L._creer_fichier("after.tif")
        L._creer_fichier("outside.tif")

        self.assertEqual(
            outer.calls,
            [("before.tif", "outer"), ("after.tif", "outer")],
        )
        self.assertEqual(inner.calls, [("inside.tif", "inner")])


class WfsPipelineContractTests(unittest.TestCase):
    def test_wfs_facade_keeps_signature_and_reloads_dependencies(self):
        self.assertEqual(
            str(inspect.signature(L.telecharger_wfs)),
            "(typename, lon_min, lat_min, lon_max, lat_max, nom_zone, "
            "dossier_sortie, ecraser_telechargement=False, formats=None)",
        )
        seams = {
            "WFS_URL": "https://wfs.example/ows",
            "_HTTP_UA": "test-agent",
            "WFS_PAGE": 17,
            "_chemin_part": mock.Mock(name="chemin_part"),
            "_stop_event": mock.Mock(name="stop_event"),
            "_gunzip_vers_fichier": mock.Mock(name="gunzip"),
            "_gzip_depuis_fichier": mock.Mock(name="gzip"),
            "_log_req": mock.Mock(name="log_req"),
            "_hms": mock.Mock(name="hms"),
        }
        with contextlib.ExitStack() as stack:
            for name, value in seams.items():
                stack.enter_context(mock.patch.object(L, name, value))
            dependencies = L._dependances_wfs()

        self.assertEqual(dependencies.wfs_url, seams["WFS_URL"])
        self.assertEqual(dependencies.http_ua, seams["_HTTP_UA"])
        self.assertEqual(dependencies.page_size, seams["WFS_PAGE"])
        self.assertIs(dependencies.chemin_part, seams["_chemin_part"])
        self.assertIs(dependencies.stop_event, seams["_stop_event"])
        self.assertIs(
            dependencies.gunzip_vers_fichier, seams["_gunzip_vers_fichier"]
        )
        self.assertIs(
            dependencies.gzip_depuis_fichier, seams["_gzip_depuis_fichier"]
        )
        self.assertIs(dependencies.log_req, seams["_log_req"])
        self.assertIs(dependencies.formater_duree, seams["_hms"])

    def test_wfs_facade_delegates_all_arguments(self):
        marker = object()
        with mock.patch.object(
            L, "_telecharger_wfs_impl", return_value=marker
        ) as implementation:
            result = L.telecharger_wfs(
                "NS:layer", 1, 2, 3, 4, "zone", "output",
                ecraser_telechargement=True,
                formats=["gz", "geojson"],
            )
        self.assertIs(result, marker)
        self.assertEqual(
            implementation.call_args.args,
            ("NS:layer", 1, 2, 3, 4, "zone", "output"),
        )
        self.assertTrue(
            implementation.call_args.kwargs["ecraser_telechargement"]
        )
        self.assertEqual(
            implementation.call_args.kwargs["formats"], ["gz", "geojson"]
        )
        self.assertIsInstance(
            implementation.call_args.kwargs["dependances"],
            wfs_pipeline.DependancesWfs,
        )

    def test_wfs_output_names_keep_bdtopo_compatibility_and_avoid_collisions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            short, raw, compressed = wfs_pipeline._sorties_wfs(
                "BDTOPO_V3:cours_d_eau", "zone", root
            )
            self.assertEqual(short, "cours_d_eau")
            self.assertEqual(raw.name, "zone_ign_cours_d_eau.geojson")
            self.assertEqual(compressed, Path(str(raw) + ".gz"))
            first = wfs_pipeline._sorties_wfs("NS:a-b", "zone", root)[1]
            second = wfs_pipeline._sorties_wfs("NS:a_b", "zone", root)[1]
            self.assertNotEqual(first, second)


class VectorAcquisitionContractTests(unittest.TestCase):
    @staticmethod
    def _dependencies(*, bulk_result, wfs_results):
        bulk = mock.Mock(return_value=bulk_result)
        wfs = mock.Mock(side_effect=wfs_results)

        class Executor:
            maximum = None

            def __init__(self, max_workers):
                type(self).maximum = max_workers

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            @staticmethod
            def map(function, values):
                return [function(value) for value in values]

        dependencies = vector_acquisition.DependancesAcquisitionVecteur(
            telecharger_bulk=bulk,
            telecharger_wfs=wfs,
            executor_factory=Executor,
        )
        return dependencies, bulk, wfs, Executor

    def test_facade_keeps_signature_and_reads_dependencies_late(self):
        self.assertEqual(
            str(inspect.signature(L._acquerir_couches_vecteur)),
            "(couches_resolues, bbox_wgs84, nom_zone, dossier, *, "
            "num_dep=None, ecraser=False, formats=None, workers=1)",
        )
        seams = {
            "_telecharger_bdtopo_bulk": mock.Mock(name="bulk"),
            "telecharger_wfs": mock.Mock(name="wfs"),
            "ThreadPoolExecutor": mock.Mock(name="executor"),
        }
        with contextlib.ExitStack() as stack:
            for name, value in seams.items():
                stack.enter_context(mock.patch.object(L, name, value))
            dependencies = L._dependances_acquisition_vecteur()
        self.assertIs(dependencies.telecharger_bulk, seams["_telecharger_bdtopo_bulk"])
        self.assertIs(dependencies.telecharger_wfs, seams["telecharger_wfs"])
        self.assertIs(dependencies.executor_factory, seams["ThreadPoolExecutor"])

    def test_complete_bulk_does_not_call_wfs(self):
        outputs = [Path("zone_ign_a.geojson.gz"), Path("zone_ign_b.geojson")]
        dependencies, bulk, wfs, _executor = self._dependencies(
            bulk_result=outputs, wfs_results=[]
        )
        with contextlib.redirect_stdout(io.StringIO()):
            result = vector_acquisition.acquerir_couches_vecteur(
                [("NS:a", "A"), ("NS:b", "B")],
                (1, 2, 3, 4), "zone", Path("out"),
                num_dep="83", dependances=dependencies,
            )
        self.assertEqual(result, outputs)
        bulk.assert_called_once()
        wfs.assert_not_called()

    def test_partial_bulk_retries_only_missing_layers_in_order(self):
        first = Path("zone_ign_a.geojson.gz")
        recovered = Path("zone_ign_b.geojson.gz")
        dependencies, _bulk, wfs, _executor = self._dependencies(
            bulk_result=[first], wfs_results=[recovered, None]
        )
        with contextlib.redirect_stdout(io.StringIO()):
            result = vector_acquisition.acquerir_couches_vecteur(
                [("NS:a", "A"), ("NS:b", "B"), ("NS:c", "C")],
                (1, 2, 3, 4), "zone", Path("out"),
                num_dep="83", ecraser=True, formats=["gz"],
                dependances=dependencies,
            )
        self.assertEqual(result, [first, recovered])
        self.assertEqual([call.args[0] for call in wfs.call_args_list], ["NS:b", "NS:c"])
        self.assertTrue(all(call.kwargs["ecraser_telechargement"] for call in wfs.call_args_list))

    def test_empty_bulk_retries_each_layer_only_once(self):
        dependencies, _bulk, wfs, _executor = self._dependencies(
            bulk_result=[], wfs_results=[None, None]
        )
        with contextlib.redirect_stdout(io.StringIO()):
            result = vector_acquisition.acquerir_couches_vecteur(
                [("NS:a", "A"), ("NS:b", "B")],
                (1, 2, 3, 4), "zone", Path("out"),
                num_dep="83", dependances=dependencies,
            )
        self.assertEqual(result, [])
        self.assertEqual(wfs.call_count, 2)

    def test_bulk_failure_uses_parallel_standard_wfs(self):
        outputs = [Path("a.gz"), Path("b.gz")]
        dependencies, _bulk, wfs, executor = self._dependencies(
            bulk_result=None, wfs_results=outputs
        )
        with contextlib.redirect_stdout(io.StringIO()):
            result = vector_acquisition.acquerir_couches_vecteur(
                [("NS:a", "A"), ("NS:b", "B")],
                (1, 2, 3, 4), "zone", Path("out"),
                num_dep="83", workers=8, dependances=dependencies,
            )
        self.assertEqual(result, outputs)
        self.assertEqual(wfs.call_count, 2)
        self.assertEqual(executor.maximum, 2)


class OsmGeojsonExportContractTests(unittest.TestCase):
    def test_facade_keeps_signature_and_delegates_to_extracted_module(self):
        self.assertIs(
            L._generer_geojson_osm_impl,
            geojson_osm_export.generer_geojson_osm,
        )
        self.assertEqual(
            str(inspect.signature(L.generer_geojson_osm)),
            "(bbox_wgs84, dossier_ville, nom_zone, osm_pbf, osm_tags=None, "
            "ecraser_tuiles=False, formats=None)",
        )
        marker = object()
        with mock.patch.object(
                L, "_generer_geojson_osm_impl", return_value=marker,
        ) as implementation:
            result = L.generer_geojson_osm(
                (1, 2, 3, 4), "out", "zone", "source.pbf",
                osm_tags=["highway=*"], ecraser_tuiles=True,
                formats=["gz", "geojson"],
            )

        self.assertIs(result, marker)
        self.assertEqual(implementation.call_args.args[:4], (
            (1, 2, 3, 4), "out", "zone", "source.pbf",
        ))
        self.assertIsInstance(
            implementation.call_args.kwargs["dependances"],
            geojson_osm_export.DependancesExportOsm,
        )

    def test_dependencies_are_rebuilt_from_late_bound_facade_seams(self):
        seams = {
            "_osm_filtre_cles": mock.Mock(),
            "_osm_cle_match": mock.Mock(),
            "_chemin_part": mock.Mock(),
            "_gunzip_vers_fichier": mock.Mock(),
            "_publier_groupe_atomique": mock.Mock(),
            "_hms": mock.Mock(),
        }
        patches = [mock.patch.object(L, name, value)
                   for name, value in seams.items()]
        for patcher in patches:
            patcher.start()
        try:
            dependencies = L._dependances_export_osm()
        finally:
            for patcher in reversed(patches):
                patcher.stop()

        self.assertIs(dependencies.osm_filtre_cles, seams["_osm_filtre_cles"])
        self.assertIs(dependencies.osm_cle_match, seams["_osm_cle_match"])
        self.assertIs(dependencies.chemin_part, seams["_chemin_part"])
        self.assertIs(
            dependencies.gunzip_vers_fichier,
            seams["_gunzip_vers_fichier"],
        )
        self.assertIs(
            dependencies.publier_groupe_atomique,
            seams["_publier_groupe_atomique"],
        )
        self.assertIs(dependencies.formater_duree, seams["_hms"])


class GeojsonMergeContractTests(unittest.TestCase):
    def test_facade_keeps_signature_and_delegates_to_extracted_module(self):
        self.assertIs(L._fusionner_geojson_impl, geojson_merge.fusionner_geojson)
        self.assertEqual(
            str(inspect.signature(L.fusionner_geojson)),
            "(fichiers, sortie, fichiers_ignores=None)",
        )
        result = object()
        ignored = []
        with mock.patch.object(
                L, "_fusionner_geojson_impl", return_value=result
        ) as implementation:
            self.assertIs(
                L.fusionner_geojson(["source"], "sortie", ignored), result,
            )

        args, kwargs = implementation.call_args
        self.assertEqual(args, (["source"], "sortie"))
        self.assertIs(kwargs["fichiers_ignores"], ignored)
        self.assertIsInstance(
            kwargs["dependances"], geojson_merge.DependancesFusionGeojson,
        )

    def test_dependencies_are_rebuilt_from_late_bound_facade_seams(self):
        chemin_part = object()
        stop_event = object()
        lire_geojson = object()
        with mock.patch.object(L, "_chemin_part", chemin_part), \
             mock.patch.object(L, "_stop_event", stop_event), \
             mock.patch.object(L, "_lire_geojson", lire_geojson):
            dependencies = L._dependances_fusion_geojson()

        self.assertIs(dependencies.chemin_part, chemin_part)
        self.assertIs(dependencies.stop_event, stop_event)
        self.assertIs(dependencies.lire_geojson, lire_geojson)

    def test_reader_facade_delegates_to_extracted_reader(self):
        marker = object()
        with mock.patch.object(
                L, "_lire_geojson_impl", return_value=marker
        ) as reader:
            self.assertIs(L._lire_geojson("source.geojson"), marker)
        reader.assert_called_once_with("source.geojson")


class GeojsonMergeCliContractTests(unittest.TestCase):
    def _dependencies(self, **overrides):
        values = {
            "fusionner_geojson": mock.Mock(),
            "epsilon_depuis_surface_km2": mock.Mock(return_value=0.001),
            "epsilon_defaut": 0.0001,
            "generer_map": mock.Mock(return_value=Path("zone.map")),
            "rasteriser": mock.Mock(return_value=Path("zone.sqlitedb")),
        }
        values.update(overrides)
        return geojson_merge_cli.DependancesFusionCli(**values)

    def test_source_resolution_and_default_output_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_b = root / "b.geojson"
            source_a = root / "a.geojson"
            source_b.touch()
            source_a.touch()
            missing = root / "missing.geojson"

            sources = geojson_merge_cli.resoudre_sources_fusion([
                str(root / "*.geojson"), str(missing),
            ])

            self.assertEqual(sources, [str(source_a), str(source_b), str(missing)])
            self.assertEqual(
                geojson_merge_cli.determiner_sortie_fusion(sources),
                root / "a_fusion.geojson.gz",
            )
            self.assertEqual(
                geojson_merge_cli.determiner_sortie_fusion(
                    sources, dossier=root / "out", no_gz=True,
                ),
                root / "out" / "a_fusion.geojson",
            )

    def test_requested_derivatives_are_all_of_and_all_are_attempted(self):
        output = Path("fusion.geojson.gz")
        fusion = mock.Mock(return_value=(output, (6.0, 43.0, 6.1, 43.1)))
        map_generator = mock.Mock(return_value=None)
        rasterizer = mock.Mock(return_value=Path("fusion.sqlitedb"))
        dependencies = self._dependencies(
            fusionner_geojson=fusion,
            generer_map=map_generator,
            rasteriser=rasterizer,
        )

        result = geojson_merge_cli.executer_fusion_cli(
            ["source.geojson"],
            output,
            formats=["map", "transparent-raster"],
            dependances=dependencies,
        )

        self.assertFalse(result.complet)
        self.assertTrue(result.fusion_ok)
        self.assertFalse(result.map_ok)
        self.assertTrue(result.raster_ok)
        map_generator.assert_called_once()
        rasterizer.assert_called_once()

    def test_failed_fusion_skips_all_derived_outputs(self):
        dependencies = self._dependencies(
            fusionner_geojson=mock.Mock(return_value=(None, None)),
        )

        result = geojson_merge_cli.executer_fusion_cli(
            ["source.geojson"],
            "fusion.geojson.gz",
            formats=["map", "transparent-raster"],
            dependances=dependencies,
        )

        self.assertFalse(result.complet)
        dependencies.generer_map.assert_not_called()
        dependencies.rasteriser.assert_not_called()

    def test_facade_keeps_signature_and_reads_dependencies_late(self):
        self.assertEqual(
            str(inspect.signature(L._executer_fusion_cli)),
            "(fichiers, sortie, *, formats, simplification=None, "
            "zoom_min=8, zoom_max=18)",
        )
        fusion = mock.Mock()
        epsilon = mock.Mock()
        map_generator = mock.Mock()
        rasterizer = mock.Mock()
        with mock.patch.object(L, "fusionner_geojson", fusion), \
             mock.patch.object(L, "_epsilon_depuis_surface_km2", epsilon), \
             mock.patch.object(L, "_IGN_SIMPLIFY_EPSILON", 0.002), \
             mock.patch.object(L, "generer_map_depuis_geojson_ign", map_generator), \
             mock.patch.object(L, "rasteriser_geojson_transparent", rasterizer):
            dependencies = L._dependances_fusion_cli()

        self.assertIs(dependencies.fusionner_geojson, fusion)
        self.assertIs(dependencies.epsilon_depuis_surface_km2, epsilon)
        self.assertEqual(dependencies.epsilon_defaut, 0.002)
        self.assertIs(dependencies.generer_map, map_generator)
        self.assertIs(dependencies.rasteriser, rasterizer)


class VectorOutputContractTests(unittest.TestCase):
    def test_facade_keeps_signature_and_reads_dependencies_late(self):
        self.assertEqual(
            str(inspect.signature(L._produire_sorties_vecteur)),
            "(sorties, dossier, nom_zone, bbox_wgs84, *, formats=None, "
            "ecraser=False, simplification=None, zoom_min=8, zoom_max=18)",
        )
        marker = object()
        with mock.patch.object(
            L, "_produire_sorties_vecteur_impl", return_value=marker
        ) as implementation:
            result = L._produire_sorties_vecteur(
                ["source"], "output", "zone", (1, 2, 3, 4), formats=["map"]
            )
        self.assertIs(result, marker)
        dependencies = implementation.call_args.kwargs["dependances"]
        self.assertIsInstance(
            dependencies, vector_outputs.DependancesSortiesVecteur
        )
        self.assertIs(dependencies.fusionner_geojson, L._fusionner_geojson_compat)
        self.assertIs(dependencies.generer_map, L.generer_map_depuis_geojson_ign)

    def test_requested_outputs_are_all_of_and_keep_the_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.geojson.gz"
            source.write_bytes(b"kept")
            generated_map = mock.Mock(return_value=root / "zone.map")
            generated_raster = mock.Mock(return_value=None)
            dependencies = vector_outputs.DependancesSortiesVecteur(
                fusionner_geojson=mock.Mock(),
                epsilon_depuis_surface_km2=mock.Mock(return_value=0.001),
                generer_map=generated_map,
                rasteriser=generated_raster,
            )
            with contextlib.redirect_stdout(io.StringIO()):
                result = vector_outputs.produire_sorties_vecteur(
                    [source], root, "zone", (6.0, 43.0, 6.1, 43.1),
                    formats=["map", "transparent-raster"],
                    simplification=10.0,
                    dependances=dependencies,
                )

            self.assertFalse(result.complet)
            self.assertEqual(result.source_geojson, source)
            self.assertEqual(source.read_bytes(), b"kept")
            self.assertAlmostEqual(generated_map.call_args.kwargs["epsilon"],
                                   10.0 / 111_000.0)
            generated_raster.assert_called_once()


class OsmOutputContractTests(unittest.TestCase):
    def test_facade_keeps_signature_and_reads_dependencies_late(self):
        self.assertEqual(
            str(inspect.signature(L._produire_sorties_osm)),
            "(bbox_wgs84, dossier, nom_zone, osm_pbf, *, formats, "
            "osm_tags=None, ecraser=False, skip_bbox=False, zoom_min=8, "
            "zoom_max=18)",
        )
        marker = object()
        with mock.patch.object(
            L, "_produire_sorties_osm_impl", return_value=marker
        ) as implementation, mock.patch.object(
            L, "generer_carte_osm"
        ) as map_generator, mock.patch.object(
            L, "rasteriser_geojson_transparent"
        ) as rasterizer:
            result = L._produire_sorties_osm(
                (1, 2, 3, 4), "output", "zone", "source.pbf",
                formats=["map"],
            )
        self.assertIs(result, marker)
        dependencies = implementation.call_args.kwargs["dependances"]
        self.assertIsInstance(dependencies, osm_outputs.DependancesSortiesOsm)
        self.assertIs(dependencies.generer_carte, map_generator)
        self.assertIs(dependencies.rasteriser, rasterizer)

    def test_map_failure_makes_the_aggregate_incomplete(self):
        dependencies = osm_outputs.DependancesSortiesOsm(
            generer_carte=mock.Mock(return_value=None),
            rasteriser=mock.Mock(),
        )
        result = osm_outputs.produire_sorties_osm(
            (1, 2, 3, 4), "output", "zone", "source.pbf",
            formats=["map"], dependances=dependencies,
        )
        self.assertFalse(result.complet)
        dependencies.rasteriser.assert_not_called()

    def test_missing_overlay_source_is_an_explicit_failure(self):
        dependencies = osm_outputs.DependancesSortiesOsm(
            generer_carte=mock.Mock(return_value=Path("output/zone.map")),
            rasteriser=mock.Mock(),
        )
        with tempfile.TemporaryDirectory() as temporary:
            result = osm_outputs.produire_sorties_osm(
                (1, 2, 3, 4), temporary, "zone", "source.pbf",
                formats=["transparent-raster"], dependances=dependencies,
            )
        self.assertFalse(result.complet)
        dependencies.rasteriser.assert_not_called()

    def test_all_requested_outputs_are_attempted_and_must_succeed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "zone_osm.geojson.gz"
            source.write_bytes(b"geojson")
            generated_map = root / "zone.map"
            generated_map.write_bytes(b"map")
            dependencies = osm_outputs.DependancesSortiesOsm(
                generer_carte=mock.Mock(return_value=generated_map),
                rasteriser=mock.Mock(return_value=None),
            )
            result = osm_outputs.produire_sorties_osm(
                (1, 2, 3, 4), root, "zone", "source.pbf",
                formats=["map", "transparent-raster"], zoom_min=8,
                zoom_max=18, dependances=dependencies,
            )
        self.assertFalse(result.complet)
        dependencies.rasteriser.assert_called_once()
        self.assertEqual(dependencies.rasteriser.call_args.args[2:4], (13, 18))


class OsmMapPipelineContractTests(unittest.TestCase):
    def test_facade_keeps_signature_and_delegates_to_extracted_module(self):
        self.assertIs(
            L._generer_carte_osm_impl,
            osm_map_pipeline.generer_carte_osm,
        )
        self.assertEqual(
            str(inspect.signature(L.generer_carte_osm)),
            "(bbox_wgs84, dossier_ville, nom_zone, osm_pbf, osm_tags=None, "
            "export_geojson=True, ecraser_tuiles=False, skip_bbox=False, "
            "geojson_formats=None, want_map=True)",
        )
        marker = object()
        with mock.patch.object(
            L, "_generer_carte_osm_impl", return_value=marker
        ) as implementation:
            result = L.generer_carte_osm(
                (1, 2, 3, 4), "output", "zone", "source.pbf",
                osm_tags=["highway=*"], export_geojson=False,
                ecraser_tuiles=True, skip_bbox=True,
                geojson_formats=["geojson"], want_map=True,
            )
        self.assertIs(result, marker)
        self.assertIsInstance(
            implementation.call_args.kwargs["dependances"],
            osm_map_pipeline.DependancesCarteOsm,
        )

    def test_dependencies_are_rebuilt_from_late_bound_facade_seams(self):
        seams = {
            "_chemin_part": mock.Mock(),
            "_preparer_osmosis": mock.Mock(),
            "_run_osmosis_streaming": mock.Mock(),
            "generer_geojson_osm": mock.Mock(),
            "_verifier_mapwriter": mock.Mock(),
            "_publier_groupe_atomique": mock.Mock(),
        }
        with contextlib.ExitStack() as stack:
            for name, value in seams.items():
                stack.enter_context(mock.patch.object(L, name, value))
            dependencies = L._dependances_carte_osm()
        self.assertIs(dependencies.chemin_part, seams["_chemin_part"])
        self.assertIs(dependencies.preparer_osmosis, seams["_preparer_osmosis"])
        self.assertIs(
            dependencies.executer_osmosis, seams["_run_osmosis_streaming"]
        )
        self.assertIs(
            dependencies.generer_geojson, seams["generer_geojson_osm"]
        )
        self.assertIs(
            dependencies.verifier_mapwriter, seams["_verifier_mapwriter"]
        )
        self.assertIs(
            dependencies.publier_groupe_atomique,
            seams["_publier_groupe_atomique"],
        )


class OsmPolicyContractTests(unittest.TestCase):
    def test_historical_facades_keep_signatures_and_delegate(self):
        self.assertIs(L._OSM_TAG_RE, osm_policy.OSM_TAG_RE)
        expected = {
            "_valider_osm_tags": "(osm_tags)",
            "_osm_filtre_cles": "(osm_tags)",
            "_osm_cle_match": "(tags, cles, vals_par_cle)",
            "_hash_config": "(payload)",
            "_sig_sidecar_stale": "(chemin, sig)",
            "_sig_sidecar_ecrire": "(chemin, sig)",
            "_signature_osm": "(bbox_wgs84, osm_tags, osm_pbf, skip_bbox)",
        }
        for name, signature in expected.items():
            self.assertEqual(str(inspect.signature(getattr(L, name))), signature)

        marker = object()
        with mock.patch.object(
            L._osm_policy_impl, "osm_filtre_cles", return_value=marker,
        ) as implementation:
            self.assertIs(L._osm_filtre_cles(["highway=path"]), marker)
        implementation.assert_called_once_with(["highway=path"])

    def test_signature_and_sidecar_rebuild_late_bound_dependencies(self):
        signature = object()
        with mock.patch.object(L, "_hash_config", return_value=signature) as hasher:
            self.assertIs(
                L._signature_osm((1, 2, 3, 4), ["highway=*"], "x.pbf", False),
                signature,
            )
        hasher.assert_called_once()

        writer = mock.Mock()
        with mock.patch.object(L, "_ecrire_texte_atomique", writer):
            L._sig_sidecar_ecrire("zone.map", "signature")
        writer.assert_called_once_with(Path("zone.map.sig"), "signature")

    def test_invalid_filter_keeps_historical_exit_and_message(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            L._valider_osm_tags(["highway=* & whoami"])
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("no shell metacharacters", output.getvalue())


class BdtopoLayerContractTests(unittest.TestCase):
    def test_facades_keep_signatures_and_reload_dependencies(self):
        self.assertEqual(
            str(inspect.signature(L._streamer_geojson_ajout_source)),
            "(src_geojson, dst_gz, source_name)",
        )
        self.assertEqual(
            str(inspect.signature(L._extraire_couche_bdtopo)),
            "(gpkg_path, layer_name, sortie_gz, bbox_l93=None, "
            "ecraser=False, formats=None)",
        )
        seams = {
            "_chemin_part": mock.Mock(name="chemin_part"),
            "_gunzip_vers_fichier": mock.Mock(name="gunzip"),
            "_gzip_depuis_fichier": mock.Mock(name="gzip"),
            "_get_transformer": mock.Mock(name="transformer"),
            "_streamer_geojson_ajout_source": mock.Mock(name="streamer"),
            "_hms": mock.Mock(name="hms"),
        }
        with contextlib.ExitStack() as stack:
            for name, value in seams.items():
                stack.enter_context(mock.patch.object(L, name, value))
            dependencies = L._dependances_couches_bdtopo()

        self.assertIsInstance(
            dependencies, bdtopo_layers.DependancesCouchesBdtopo
        )
        self.assertIs(dependencies.chemin_part, seams["_chemin_part"])
        self.assertIs(
            dependencies.streamer_geojson,
            seams["_streamer_geojson_ajout_source"],
        )
        self.assertIs(dependencies.get_transformer, seams["_get_transformer"])

    def test_facades_delegate_to_extracted_implementations(self):
        marker = object()
        with mock.patch.object(
            L, "_streamer_geojson_ajout_source_impl", return_value=7
        ) as streamer:
            self.assertEqual(L._streamer_geojson_ajout_source("a", "b", "c"), 7)
        self.assertEqual(streamer.call_args.args, ("a", "b", "c"))
        self.assertIs(streamer.call_args.kwargs["chemin_part"], L._chemin_part)

        with mock.patch.object(
            L, "_extraire_couche_bdtopo_impl", return_value=marker
        ) as extraction:
            result = L._extraire_couche_bdtopo(
                "source", "layer", "output", (1, 2, 3, 4), True, ["gz"]
            )
        self.assertIs(result, marker)
        self.assertEqual(extraction.call_args.args, ("source", "layer", "output"))
        self.assertEqual(extraction.call_args.kwargs["bbox_l93"], (1, 2, 3, 4))
        self.assertTrue(extraction.call_args.kwargs["ecraser"])
        self.assertIsInstance(
            extraction.call_args.kwargs["dependances"],
            bdtopo_layers.DependancesCouchesBdtopo,
        )


class BdtopoBulkContractTests(unittest.TestCase):
    def test_facades_keep_signatures_and_reload_dependencies(self):
        self.assertEqual(
            str(inspect.signature(L._decouvrir_url_bdtopo_gpkg)), "(num_dep)"
        )
        self.assertEqual(
            str(inspect.signature(L._telecharger_bdtopo_gpkg)),
            "(num_dep, url, nom_ressource, ecraser=False)",
        )
        self.assertEqual(
            str(inspect.signature(L._telecharger_bdtopo_bulk)),
            "(num_dep, couches_resolues, nom_zone, dossier_sortie, "
            "bbox_l93=None, ecraser=False, formats=None)",
        )
        seams = {
            "BDTOPO_API_URL": "https://api.invalid",
            "BDTOPO_DL_BASE": "https://download.invalid",
            "_HTTP_UA": "test-agent",
            "DOSSIER_CACHE": Path("cache-test"),
            "_log_req": mock.Mock(name="log_req"),
            "_chemin_part": mock.Mock(name="chemin_part"),
            "_urlopen": mock.Mock(name="urlopen"),
            "_stop_event": mock.Mock(name="stop_event"),
            "_hms": mock.Mock(name="hms"),
        }
        with contextlib.ExitStack() as stack:
            for name, value in seams.items():
                stack.enter_context(mock.patch.object(L, name, value))
            dependencies = L._dependances_bdtopo_bulk()

        self.assertEqual(dependencies.api_url, seams["BDTOPO_API_URL"])
        self.assertEqual(dependencies.download_base, seams["BDTOPO_DL_BASE"])
        self.assertEqual(dependencies.cache_root, seams["DOSSIER_CACHE"])
        self.assertIs(dependencies.ouvrir_url, seams["_urlopen"])
        self.assertIs(dependencies.chemin_part, seams["_chemin_part"])
        self.assertIs(dependencies.stop_event, seams["_stop_event"])

    def test_facades_delegate_to_extracted_implementations(self):
        marker = object()
        with mock.patch.object(
            L, "_decouvrir_url_bdtopo_gpkg_impl", return_value=marker
        ) as discovery:
            self.assertIs(L._decouvrir_url_bdtopo_gpkg("83"), marker)
        discovery.assert_called_once()
        self.assertEqual(discovery.call_args.args, ("83",))
        self.assertIsInstance(
            discovery.call_args.kwargs["dependances"],
            bdtopo_bulk.DependancesBdtopo,
        )

        with mock.patch.object(
            L, "_telecharger_bdtopo_gpkg_impl", return_value=marker
        ) as download:
            self.assertIs(
                L._telecharger_bdtopo_gpkg("83", "url", "resource", True), marker
            )
        self.assertEqual(download.call_args.args, ("83", "url", "resource"))
        self.assertTrue(download.call_args.kwargs["ecraser"])

        with mock.patch.object(
            L, "_telecharger_bdtopo_bulk_impl", return_value=marker
        ) as bulk:
            result = L._telecharger_bdtopo_bulk(
                "83", [("NS:a", "A")], "zone", "output", formats=["gz"]
            )
        self.assertIs(result, marker)
        self.assertEqual(
            bulk.call_args.args,
            ("83", [("NS:a", "A")], "zone", "output"),
        )
        self.assertIsInstance(
            bulk.call_args.kwargs["dependances"],
            bdtopo_bulk.DependancesOrchestrationBdtopo,
        )

    def test_bulk_keeps_success_order_and_omits_failed_layers(self):
        extraction = mock.Mock(side_effect=[Path("first.gz"), None, Path("third.gz")])
        dependencies = bdtopo_bulk.DependancesOrchestrationBdtopo(
            decouvrir_ressource=mock.Mock(return_value=("url", "resource")),
            telecharger_gpkg=mock.Mock(return_value=Path("source.gpkg")),
            extraire_couche=extraction,
            correspondance_couches={"a": "layer_a"},
        )
        couches = [("NS:a", "A"), ("NS:b", "B"), ("NS:c", "C")]
        with contextlib.redirect_stdout(io.StringIO()):
            result = bdtopo_bulk.telecharger_bdtopo_bulk(
                "83",
                couches,
                "zone",
                Path("output"),
                bbox_l93=(1, 2, 3, 4),
                ecraser=True,
                formats=["gz", "geojson"],
                dependances=dependencies,
            )

        self.assertEqual(result, [Path("first.gz"), Path("third.gz")])
        self.assertEqual(
            [call.args[1] for call in extraction.call_args_list],
            ["layer_a", "b", "c"],
        )
        self.assertTrue(all(call.kwargs["ecraser"] for call in extraction.call_args_list))

    def test_bulk_critical_acquisition_failures_return_none(self):
        extraction = mock.Mock()
        for discovery, download in (((None, None), Path("unused")),
                                    (("url", "name"), None)):
            dependencies = bdtopo_bulk.DependancesOrchestrationBdtopo(
                decouvrir_ressource=mock.Mock(return_value=discovery),
                telecharger_gpkg=mock.Mock(return_value=download),
                extraire_couche=extraction,
                correspondance_couches={},
            )
            with self.subTest(discovery=discovery), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(
                    bdtopo_bulk.telecharger_bdtopo_bulk(
                        "83", [], "zone", "output", dependances=dependencies
                    )
                )
        extraction.assert_not_called()

    def test_atom_discovery_sorts_dates_then_numeric_versions(self):
        names = (
            "BDTOPO_3-9_TOUSTHEMES_GPKG_LAMB93_D083_2026-06-15",
            "BDTOPO_3-10_TOUSTHEMES_GPKG_LAMB93_D083_2026-06-15",
            "BDTOPO_9-9_TOUSTHEMES_GPKG_LAMB93_D083_2025-12-15",
        )
        entries = "".join(
            f"<entry><title>{name}</title><id>{name}</id></entry>" for name in names
        )
        xml = (
            '<feed xmlns="http://www.w3.org/2005/Atom">' + entries + "</feed>"
        ).encode("utf-8")

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return xml

        dependencies = bdtopo_bulk.DependancesBdtopo(
            api_url="https://api.invalid",
            download_base="https://download.invalid",
            http_ua="agent",
            cache_root=Path("cache"),
            log_req=mock.Mock(),
            chemin_part=mock.Mock(),
            ouvrir_url=mock.Mock(),
            stop_event=mock.Mock(),
            formater_duree=mock.Mock(),
        )
        with mock.patch.object(
            bdtopo_bulk.urllib.request, "urlopen", return_value=Response()
        ), contextlib.redirect_stdout(io.StringIO()):
            url, name = bdtopo_bulk.decouvrir_url_bdtopo_gpkg(
                "83", dependances=dependencies
            )
        self.assertEqual(name, names[1])
        self.assertEqual(url, f"https://download.invalid/{name}/{name}.7z")


class OsmosisRuntimeContractTests(unittest.TestCase):
    def test_historical_facades_keep_their_signatures(self):
        self.assertEqual(
            str(inspect.signature(L._promouvoir_dossier)),
            "(tmp_dir, dest_dir)",
        )
        self.assertEqual(
            str(inspect.signature(L._telecharger_osmosis_local)), "()"
        )
        self.assertEqual(
            str(inspect.signature(L._telecharger_jre_local)), "()"
        )
        self.assertEqual(str(inspect.signature(L._verifier_mapwriter)), "()")
        self.assertEqual(str(inspect.signature(L._telecharger_outils)), "()")
        self.assertEqual(
            str(inspect.signature(L._bin_outil)), "(racine, pattern)"
        )
        self.assertEqual(str(inspect.signature(L._trouver_java)), "()")
        self.assertEqual(str(inspect.signature(L._trouver_osmosis)), "()")
        self.assertEqual(str(inspect.signature(L._java_opts_extra)), "()")
        self.assertEqual(
            str(inspect.signature(L._preparer_osmosis)),
            "(dossier_hint=None)",
        )
        self.assertEqual(
            str(inspect.signature(L._run_osmosis_streaming)),
            "(cmd_or_str, shell, env)",
        )
        self.assertEqual(
            str(inspect.signature(L._nettoyer_osmosis_temp_orphelins)),
            "(verbose=False, min_age_s=300)",
        )

    def test_prepare_facade_resolves_all_seams_at_call_time(self):
        seams = {
            "_verifier_mapwriter": mock.Mock(return_value=True),
            "_trouver_java": mock.Mock(return_value=str(Path("java") / "bin" / "java")),
            "_trouver_osmosis": mock.Mock(return_value="osmosis"),
        }
        with mock.patch.multiple(L, **seams):
            result = L._preparer_osmosis(Path("hint"))
        self.assertEqual(result, ("osmosis", str(Path("java"))))
        for seam in seams.values():
            seam.assert_called_once_with()

    def test_prepare_short_circuits_failures_in_order(self):
        cases = (
            (False, "java", "osmosis", (1, 0, 0)),
            (True, None, "osmosis", (1, 1, 0)),
            (True, "java/bin/java", None, (1, 1, 1)),
        )
        for mapwriter_ok, java, osmosis, expected_calls in cases:
            verify = mock.Mock(return_value=mapwriter_ok)
            find_java = mock.Mock(return_value=java)
            find_osmosis = mock.Mock(return_value=osmosis)
            with self.subTest(calls=expected_calls), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    osm_runtime.preparer_osmosis(
                        verifier_mapwriter=verify,
                        trouver_java=find_java,
                        trouver_osmosis=find_osmosis,
                    ),
                    (None, None),
                )
            self.assertEqual(
                (verify.call_count, find_java.call_count, find_osmosis.call_count),
                expected_calls,
            )

    def test_java_options_only_isolate_frozen_bundle(self):
        bundle = Path("folder with spaces")
        self.assertEqual(
            osm_runtime.java_opts_extra(frozen=False, bundle_dir=bundle), ""
        )
        self.assertEqual(
            osm_runtime.java_opts_extra(frozen=True, bundle_dir=bundle),
            ' "-Duser.home=folder with spaces"',
        )

    def test_streaming_filters_live_output_and_keeps_bounded_stderr_tail(self):
        stderr_lines = [f"info-{index}" for index in range(505)] + ["SEVERE boom"]

        class Process:
            returncode = 7
            stdout = io.BytesIO(b"ordinary stdout\nWARNING visible\n")
            stderr = io.BytesIO(("\n".join(stderr_lines) + "\n").encode())

            def wait(self):
                return self.returncode

        fake_subprocess = SimpleNamespace(
            PIPE=object(), Popen=mock.Mock(return_value=Process())
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code, diagnostic = osm_runtime.run_osmosis_streaming(
                ["osmosis"], False, {"A": "B"},
                subprocess_module=fake_subprocess,
            )
        self.assertEqual(code, 7)
        self.assertIn("WARNING visible", output.getvalue())
        self.assertIn("SEVERE boom", output.getvalue())
        self.assertNotIn("ordinary stdout", output.getvalue())
        tail = diagnostic.splitlines()
        self.assertEqual(len(tail), 500)
        self.assertEqual(tail[-1], "SEVERE boom")
        self.assertNotIn("info-0", tail)
        fake_subprocess.Popen.assert_called_once_with(
            ["osmosis"], stdout=fake_subprocess.PIPE,
            stderr=fake_subprocess.PIPE, shell=False, env={"A": "B"},
        )

    def test_orphan_cleanup_ignores_recent_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "idxNodes-old.tmp"
            recent = root / "idxWays-recent.tmp"
            unrelated = root / "other.tmp"
            old.write_bytes(b"1234")
            recent.write_bytes(b"12")
            unrelated.write_bytes(b"1")
            os.utime(old, (100, 100))
            os.utime(recent, (950, 950))

            self.assertEqual(
                osm_runtime.nettoyer_osmosis_temp_orphelins(
                    min_age_s=300, temp_dir=root, maintenant=1000
                ),
                (1, 4),
            )
            self.assertFalse(old.exists())
            self.assertTrue(recent.exists())
            self.assertTrue(unrelated.exists())

    def test_binary_discovery_requires_bin_and_is_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "osmosis"
            second = root / "z" / "bin" / "osmosis"
            first = root / "a" / "bin" / "osmosis"
            for path in (outside, second, first):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual(osm_runtime.bin_outil(root, "osmosis"), first)

    def test_java_discovery_prefers_bundle_then_cache_then_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            home = root / "home"
            bundle_java = bundle / "jre" / "z" / "bin" / "java"
            cache_java = home / "jre" / "a" / "bin" / "java"
            for path in (bundle_java, cache_java):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            download = mock.Mock(return_value="downloaded-java")

            self.assertEqual(
                osm_runtime.trouver_java(
                    frozen=True, bundle_dir=bundle, lidar2map_home=home,
                    windows=False, telecharger_jre_local=download,
                ),
                str(bundle_java),
            )
            bundle_java.unlink()
            self.assertEqual(
                osm_runtime.trouver_java(
                    frozen=True, bundle_dir=bundle, lidar2map_home=home,
                    windows=False, telecharger_jre_local=download,
                ),
                str(cache_java),
            )
            cache_java.unlink()
            self.assertEqual(
                osm_runtime.trouver_java(
                    frozen=False, bundle_dir=bundle, lidar2map_home=home,
                    windows=False, telecharger_jre_local=download,
                ),
                "downloaded-java",
            )
            download.assert_called_once_with()

    def test_java_discovery_uses_windows_name_and_reports_download_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            java = root / "home" / "jre" / "bin" / "java.exe"
            java.parent.mkdir(parents=True)
            java.touch()
            self.assertEqual(
                osm_runtime.trouver_java(
                    frozen=False, bundle_dir=root / "bundle",
                    lidar2map_home=root / "home", windows=True,
                    telecharger_jre_local=mock.Mock(side_effect=AssertionError),
                ),
                str(java),
            )
            java.unlink()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = osm_runtime.trouver_java(
                    frozen=False, bundle_dir=root / "bundle",
                    lidar2map_home=root / "home", windows=True,
                    telecharger_jre_local=mock.Mock(return_value=None),
                )
            self.assertIsNone(result)
            self.assertIn("cannot obtain a JRE", output.getvalue())

    def test_osmosis_discovery_prefers_valid_bundle_then_fixed_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            home = root / "home"
            invalid = bundle / "osmosis" / "osmosis"
            bundled = bundle / "osmosis" / "version" / "bin" / "osmosis"
            cached = home / "osmosis" / "bin" / "osmosis"
            for path in (invalid, bundled, cached):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            download = mock.Mock(return_value="downloaded-osmosis")
            self.assertEqual(
                osm_runtime.trouver_osmosis(
                    frozen=True, bundle_dir=bundle, lidar2map_home=home,
                    windows=False, telecharger_osmosis_local=download,
                ),
                str(bundled),
            )
            bundled.unlink()
            self.assertEqual(
                osm_runtime.trouver_osmosis(
                    frozen=True, bundle_dir=bundle, lidar2map_home=home,
                    windows=False, telecharger_osmosis_local=download,
                ),
                str(cached),
            )
            cached.unlink()
            self.assertEqual(
                osm_runtime.trouver_osmosis(
                    frozen=False, bundle_dir=bundle, lidar2map_home=home,
                    windows=False, telecharger_osmosis_local=download,
                ),
                "downloaded-osmosis",
            )
            download.assert_called_once_with()

    def test_discovery_facades_inject_current_paths_platform_and_downloaders(self):
        sentinel = object()
        with mock.patch.object(
            L._osmosis_runtime_impl, "trouver_java", return_value=sentinel
        ) as find_java, mock.patch.object(
            L._osmosis_runtime_impl, "trouver_osmosis", return_value=sentinel
        ) as find_osmosis, mock.patch.object(
            L.sys, "frozen", True, create=True
        ), mock.patch.multiple(
            L,
            BUNDLE_DIR=Path("current-bundle"),
            LIDAR2MAP_HOME=Path("current-home"),
            WINDOWS=True,
        ):
            self.assertIs(L._trouver_java(), sentinel)
            self.assertIs(L._trouver_osmosis(), sentinel)

        self.assertEqual(find_java.call_args.kwargs["bundle_dir"], Path("current-bundle"))
        self.assertEqual(find_java.call_args.kwargs["lidar2map_home"], Path("current-home"))
        self.assertTrue(find_java.call_args.kwargs["windows"])
        self.assertIs(
            find_java.call_args.kwargs["telecharger_jre_local"],
            L._telecharger_jre_local,
        )
        self.assertIs(
            find_osmosis.call_args.kwargs["telecharger_osmosis_local"],
            L._telecharger_osmosis_local,
        )

    def test_directory_promotion_restores_previous_on_second_rename_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "installed"
            staging = root / "staging"
            destination.mkdir()
            staging.mkdir()
            (destination / "old.txt").write_text("old", encoding="utf-8")
            (staging / "new.txt").write_text("new", encoding="utf-8")
            original_replace = Path.replace

            def replace(path, target):
                if path == staging:
                    raise OSError("promotion failed")
                return original_replace(path, target)

            with mock.patch.object(Path, "replace", autospec=True, side_effect=replace):
                with self.assertRaisesRegex(OSError, "promotion failed"):
                    osm_runtime.promouvoir_dossier(staging, destination)
            self.assertEqual(
                (destination / "old.txt").read_text(encoding="utf-8"), "old"
            )
            self.assertTrue(staging.exists())
            self.assertFalse(list(root.glob("installed.previous.*.part")))

    @staticmethod
    def _zip_bytes(root, members):
        archive = root / "fixture.zip"
        with zipfile.ZipFile(archive, "w") as output:
            for name, data in members.items():
                output.writestr(name, data)
        return archive.read_bytes()

    @staticmethod
    def _part_path(path):
        path = Path(path)
        return path.with_name(path.name + ".part")

    def test_osmosis_install_validates_then_replaces_incomplete_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            old = home / "osmosis"
            old.mkdir()
            (old / "incomplete.txt").write_text("old", encoding="utf-8")
            payload = self._zip_bytes(
                home, {"osmosis-0.49.2/bin/osmosis": "#!/bin/sh"}
            )

            def retrieve(_url, destination, reporthook):
                Path(destination).write_bytes(payload)
                reporthook(1, len(payload), len(payload))

            with contextlib.redirect_stdout(io.StringIO()):
                result = osm_runtime.telecharger_osmosis_local(
                    lidar2map_home=home,
                    windows=False,
                    chemin_part=self._part_path,
                    safe_zip_extractall=L._safe_zip_extractall,
                    promouvoir=osm_runtime.promouvoir_dossier,
                    trouver_binaire=osm_runtime.bin_outil,
                    urlretrieve=retrieve,
                )
            installed = old / "osmosis-0.49.2" / "bin" / "osmosis"
            self.assertEqual(result, str(installed))
            self.assertTrue(installed.is_file())
            self.assertFalse((old / "incomplete.txt").exists())
            self.assertFalse(list(home.glob("osmosis.*.part")))

    def test_osmosis_bad_archive_and_interrupt_preserve_cache_and_clean_staging(self):
        for failure in ("bad-zip", "interrupt"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                old = home / "osmosis"
                old.mkdir()
                marker = old / "old.txt"
                marker.write_text("old", encoding="utf-8")

                def retrieve(_url, destination, reporthook=None):
                    del reporthook
                    if failure == "interrupt":
                        raise KeyboardInterrupt
                    Path(destination).write_bytes(b"not a zip")

                kwargs = dict(
                    lidar2map_home=home,
                    windows=False,
                    chemin_part=self._part_path,
                    safe_zip_extractall=L._safe_zip_extractall,
                    promouvoir=osm_runtime.promouvoir_dossier,
                    trouver_binaire=osm_runtime.bin_outil,
                    urlretrieve=retrieve,
                )
                with contextlib.redirect_stdout(io.StringIO()):
                    if failure == "interrupt":
                        with self.assertRaises(KeyboardInterrupt):
                            osm_runtime.telecharger_osmosis_local(**kwargs)
                    else:
                        self.assertIsNone(
                            osm_runtime.telecharger_osmosis_local(**kwargs)
                        )
                self.assertTrue(marker.exists())
                self.assertFalse(list(home.glob("osmosis.*.part")))

    def test_jre_zip_install_validates_then_promotes(self):
        class Response:
            def __init__(self, url, payload=b""):
                self.url = url
                self.headers = {"Content-Length": str(len(payload))}
                self._stream = io.BytesIO(payload)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, size=-1):
                return self._stream.read(size)

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            old = home / "jre"
            old.mkdir()
            (old / "incomplete.txt").write_text("old", encoding="utf-8")
            payload = self._zip_bytes(
                home, {"jdk-21-jre/bin/java.exe": "binary"}
            )
            responses = iter(
                (Response("https://final.invalid/jre"), Response("unused", payload))
            )
            with contextlib.redirect_stdout(io.StringIO()):
                result = osm_runtime.telecharger_jre_local(
                    lidar2map_home=home,
                    windows=True,
                    platform_system=lambda: "Windows",
                    platform_machine=lambda: "AMD64",
                    chemin_part=self._part_path,
                    safe_zip_extractall=L._safe_zip_extractall,
                    promouvoir=osm_runtime.promouvoir_dossier,
                    request=lambda url, headers: (url, headers),
                    urlopen=lambda _request, timeout: next(responses),
                )
            installed = old / "jdk-21-jre" / "bin" / "java.exe"
            self.assertEqual(result, str(installed))
            self.assertTrue(installed.is_file())
            self.assertFalse((old / "incomplete.txt").exists())
            self.assertFalse(list(home.glob("jre.*.part")))

    def test_jre_bad_archive_and_interrupt_preserve_cache_and_clean_staging(self):
        class Response:
            def __init__(self, url, payload=b"", failure=None):
                self.url = url
                self.headers = {"Content-Length": str(len(payload))}
                self._stream = io.BytesIO(payload)
                self._failure = failure

            def __enter__(self):
                if self._failure is not None:
                    raise self._failure
                return self

            def __exit__(self, *_args):
                return False

            def read(self, size=-1):
                return self._stream.read(size)

        for failure in ("bad-zip", "interrupt"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                old = home / "jre"
                old.mkdir()
                marker = old / "old.txt"
                marker.write_text("old", encoding="utf-8")
                second = (
                    Response("unused", failure=KeyboardInterrupt())
                    if failure == "interrupt"
                    else Response("unused", b"not a zip")
                )
                responses = iter((Response("https://final.invalid/jre"), second))
                kwargs = dict(
                    lidar2map_home=home,
                    windows=True,
                    platform_system=lambda: "Windows",
                    platform_machine=lambda: "AMD64",
                    chemin_part=self._part_path,
                    safe_zip_extractall=L._safe_zip_extractall,
                    promouvoir=osm_runtime.promouvoir_dossier,
                    request=lambda url, headers: (url, headers),
                    urlopen=lambda _request, timeout: next(responses),
                )
                with contextlib.redirect_stdout(io.StringIO()):
                    if failure == "interrupt":
                        with self.assertRaises(KeyboardInterrupt):
                            osm_runtime.telecharger_jre_local(**kwargs)
                    else:
                        self.assertIsNone(osm_runtime.telecharger_jre_local(**kwargs))
                self.assertTrue(marker.exists())
                self.assertFalse(list(home.glob("jre.*.part")))

    def test_jre_tar_rejects_path_traversal_without_publishing(self):
        class Response:
            def __init__(self, url, payload=b""):
                self.url = url
                self.headers = {"Content-Length": str(len(payload))}
                self._stream = io.BytesIO(payload)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, size=-1):
                return self._stream.read(size)

        malicious = io.BytesIO()
        with tarfile.open(fileobj=malicious, mode="w:gz") as archive:
            member = tarfile.TarInfo("../escape")
            member.size = 1
            archive.addfile(member, io.BytesIO(b"x"))

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            responses = iter(
                (
                    Response("https://final.invalid/jre"),
                    Response("unused", malicious.getvalue()),
                )
            )
            with contextlib.redirect_stdout(io.StringIO()):
                result = osm_runtime.telecharger_jre_local(
                    lidar2map_home=home,
                    windows=False,
                    platform_system=lambda: "Linux",
                    platform_machine=lambda: "x86_64",
                    chemin_part=self._part_path,
                    safe_zip_extractall=L._safe_zip_extractall,
                    promouvoir=osm_runtime.promouvoir_dossier,
                    request=lambda url, headers: (url, headers),
                    urlopen=lambda _request, timeout: next(responses),
                )
            self.assertIsNone(result)
            self.assertFalse((home.parent / "escape").exists())
            self.assertFalse((home / "jre").exists())
            self.assertFalse(list(home.glob("jre.*.part")))

    def test_install_facades_inject_current_network_and_atomic_seams(self):
        marker = object()
        with mock.patch.object(
            L._osmosis_runtime_impl,
            "telecharger_osmosis_local",
            return_value=marker,
        ) as install_osmosis, mock.patch.object(
            L._osmosis_runtime_impl,
            "telecharger_jre_local",
            return_value=marker,
        ) as install_jre:
            self.assertIs(L._telecharger_osmosis_local(), marker)
            self.assertIs(L._telecharger_jre_local(), marker)
        self.assertIs(
            install_osmosis.call_args.kwargs["safe_zip_extractall"],
            L._safe_zip_extractall,
        )
        self.assertIs(
            install_osmosis.call_args.kwargs["promouvoir"], L._promouvoir_dossier
        )
        self.assertIs(
            install_osmosis.call_args.kwargs["urlretrieve"],
            L.urllib.request.urlretrieve,
        )
        self.assertIs(
            install_jre.call_args.kwargs["urlopen"], L.urllib.request.urlopen
        )
        self.assertIs(
            install_jre.call_args.kwargs["platform_system"], L.platform.system
        )

    def test_mapwriter_frozen_and_cached_paths_never_download(self):
        forbidden = mock.Mock(side_effect=AssertionError("network forbidden"))
        self.assertTrue(
            osm_runtime.verifier_mapwriter(
                frozen=True,
                home_dir=Path("unused"),
                chemin_part=self._part_path,
                urlretrieve=forbidden,
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            jar = (
                home / ".openstreetmap" / "osmosis" / "plugins"
                / osm_runtime.MAPWRITER_JAR
            )
            jar.parent.mkdir(parents=True)
            jar.write_bytes(b"jar")
            self.assertTrue(
                osm_runtime.verifier_mapwriter(
                    frozen=False,
                    home_dir=home,
                    chemin_part=self._part_path,
                    urlretrieve=forbidden,
                )
            )
        forbidden.assert_not_called()

    def test_mapwriter_download_publishes_part_then_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            seen = {}

            def retrieve(url, destination, reporthook):
                seen["url"] = url
                seen["destination"] = Path(destination)
                Path(destination).write_bytes(b"complete jar")
                reporthook(1, 12, 12)

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(
                    osm_runtime.verifier_mapwriter(
                        frozen=False,
                        home_dir=home,
                        chemin_part=self._part_path,
                        urlretrieve=retrieve,
                    )
                )
            jar = (
                home / ".openstreetmap" / "osmosis" / "plugins"
                / osm_runtime.MAPWRITER_JAR
            )
            self.assertEqual(seen["url"], osm_runtime.MAPWRITER_URL)
            self.assertNotEqual(seen["destination"], jar)
            self.assertEqual(jar.read_bytes(), b"complete jar")
            self.assertFalse(seen["destination"].exists())

    def test_mapwriter_failure_and_interrupt_clean_part_without_touching_final(self):
        for failure in ("replace", "interrupt"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                plugins = home / ".openstreetmap" / "osmosis" / "plugins"
                jar = plugins / osm_runtime.MAPWRITER_JAR

                def retrieve(_url, destination, reporthook):
                    del reporthook
                    Path(destination).write_bytes(b"staging")
                    if failure == "interrupt":
                        raise KeyboardInterrupt

                def replace(_source, _destination):
                    jar.write_bytes(b"concurrent old")
                    raise OSError("replace failed")

                kwargs = dict(
                    frozen=False,
                    home_dir=home,
                    chemin_part=self._part_path,
                    urlretrieve=retrieve,
                    remplacer=replace,
                )
                with contextlib.redirect_stdout(io.StringIO()):
                    if failure == "interrupt":
                        with self.assertRaises(KeyboardInterrupt):
                            osm_runtime.verifier_mapwriter(**kwargs)
                    else:
                        self.assertFalse(osm_runtime.verifier_mapwriter(**kwargs))
                if failure == "replace":
                    self.assertEqual(jar.read_bytes(), b"concurrent old")
                else:
                    self.assertFalse(jar.exists())
                self.assertFalse(list(plugins.glob("*.part")))

    def test_tool_orchestrator_attempts_every_tool_and_reports_each_status(self):
        events = []

        def step(name, result):
            def call():
                events.append(name)
                return result
            return call

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertIsNone(
                osm_runtime.telecharger_outils(
                    trouver_java=step("java", None),
                    trouver_osmosis=step("osmosis", "osmosis"),
                    verifier_mapwriter=step("mapwriter", False),
                )
            )
        self.assertEqual(events, ["java", "osmosis", "mapwriter"])
        rendered = output.getvalue()
        self.assertIn("JRE: download failed", rendered)
        self.assertIn("osmosis already present", rendered)
        self.assertIn("mapwriter: download failed", rendered)

    def test_mapwriter_and_tool_facades_resolve_current_seams(self):
        marker = object()
        with mock.patch.object(
            L._osmosis_runtime_impl, "verifier_mapwriter", return_value=marker
        ) as verify, mock.patch.object(
            L._osmosis_runtime_impl, "telecharger_outils", return_value=marker
        ) as download_tools:
            self.assertIs(L._verifier_mapwriter(), marker)
            self.assertIs(L._telecharger_outils(), marker)
        self.assertIs(verify.call_args.kwargs["chemin_part"], L._chemin_part)
        self.assertIs(
            verify.call_args.kwargs["urlretrieve"], L.urllib.request.urlretrieve
        )
        self.assertIs(
            download_tools.call_args.kwargs["trouver_java"], L._trouver_java
        )
        self.assertIs(
            download_tools.call_args.kwargs["verifier_mapwriter"],
            L._verifier_mapwriter,
        )


class ShadingInstancePlanningContractTests(unittest.TestCase):
    @staticmethod
    def _resolve(choices=(), instances=(), messages=None, **changes):
        values = dict(
            elevation_soleil=25.0,
            svf_gamma=2.0,
            svf_conv="rvt",
            svf_dist=20.0,
            resolution_m=0.5,
            elevation_defaut=25.0,
            shading_types={
                "315",
                "045",
                "135",
                "225",
                "multi",
                "slope",
                "svf",
                "opos",
                "oneg",
                "lrm",
                "rrim",
                "vat",
                "e4mstp",
            },
            imprimer=(messages.append if messages is not None else lambda _msg: None),
        )
        values.update(changes)
        return terrain_shading.resoudre_instances_ombrages(
            list(choices), list(instances), **values
        )

    def test_canonical_instances_keep_defaults_and_historical_suffixes(self):
        result = self._resolve(
            choices=(
                "315",
                "multi",
                "slope",
                "svf",
                "opos",
                "oneg",
                "lrm",
                "rrim",
                "vat",
                "e4mstp",
            )
        )
        self.assertEqual(
            [item[2] for item in result],
            [
                "315_ombrage",
                "multi_ombrage",
                "slope_ombrage",
                "svf_rvt_20m_g2p0_ombrage",
                "opos_20m_g2p0_ombrage",
                "oneg_20m_g2p0_ombrage",
                "lrm_ombrage",
                "rrim_ombrage",
                "vat_ombrage",
                "e4mstp_ombrage",
            ],
        )
        by_type = {typ: params for typ, params, _suffix in result}
        self.assertEqual(by_type["315"], {"elevation": 25.0})
        self.assertEqual(
            by_type["svf"], {"conv": "rvt", "dist": 20.0, "gamma": 2.0}
        )
        self.assertEqual(by_type["lrm"], {"sigma": 7.5})
        self.assertEqual(by_type["e4mstp"], {"dist": 20.0, "gamma": 0.8})

    def test_explicit_parameters_are_encoded_without_mutating_inputs(self):
        instances = [
            ("315", {"elevation": 35}),
            ("lrm", {"sigma": 5}),
            ("vat", {"dist": 30.4, "gamma": 1.25}),
            ("e4mstp", {"dist": 50, "gamma": 0.75}),
            (
                "svf",
                {"dist": 20, "gamma": 1.24, "conv": "flux", "sweep": True},
            ),
        ]
        snapshot = [(typ, dict(params)) for typ, params in instances]
        result = self._resolve(instances=instances)
        self.assertEqual(instances, snapshot)
        self.assertEqual(
            [item[2] for item in result],
            [
                "315_e35_ombrage",
                "lrm_s5m_ombrage",
                "vat_30m_g1p2_ombrage",
                "e4mstp_50m_g0p8_ombrage",
                "svf_flux_20m_g1p2_ombrage",
            ],
        )
        self.assertTrue(result[-1][1]["sweep"])

    def test_unknown_and_colliding_instances_keep_first_and_warn_selectively(self):
        messages = []
        result = self._resolve(
            choices=("svf", "unknown"),
            instances=(
                ("svf", {}),
                ("svf", {"dist": 20.4}),
            ),
            messages=messages,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2], "svf_rvt_20m_g2p0_ombrage")
        self.assertEqual(len(messages), 2)
        self.assertIn("unknown shading type ignored", messages[0])
        self.assertIn("collapses to the same name", messages[1])

    def test_orchestrator_keeps_signature_and_delegates_instance_planning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.tif"
            source.touch()
            planner = mock.Mock(return_value=[])
            with mock.patch.object(L, "_resoudre_instances_ombrages", planner):
                self.assertEqual(
                    L.generer_ombrages(
                        source,
                        root,
                        choix=["svf"],
                        elevation_soleil=35,
                        nom_zone="zone",
                        svf_gamma=1.2,
                        svf_conv="rvt",
                        svf_dist=40,
                        instances=[("lrm", {"sigma": 5})],
                    ),
                    [],
                )
            self.assertEqual(planner.call_args.args[0], ["svf"])
            self.assertEqual(
                planner.call_args.args[1], [("lrm", {"sigma": 5})]
            )
            self.assertEqual(planner.call_args.kwargs["resolution_m"], L.RESOLUTION_M)
            self.assertIs(planner.call_args.kwargs["shading_types"], L._SHADING_TYPES)
        self.assertEqual(
            str(inspect.signature(L.generer_ombrages)),
            "(cogs, dossier_ville, choix=None, elevation_soleil=None, "
            "nom_zone=None, ecraser_ombrages=False, ecraser_tuiles=False, "
            "use_sweep=False, svf_gamma=None, svf_conv=None, svf_dist=None, "
            "bbox_natif=None, instances=None)",
        )


class ShadingOrchestratorExtractionContractTests(unittest.TestCase):
    @staticmethod
    def _dependencies(**changes):
        return replace(L._dependances_generer_ombrages(), **changes)

    @staticmethod
    def _part_path(path):
        path = Path(path)
        return path.with_name(path.name + ".test.part")

    def test_public_facade_forwards_all_arguments_with_late_dependencies(self):
        dependencies = object()
        result = object()
        implementation = mock.Mock(return_value=result)
        instances = [("lrm", {"sigma": 5})]
        bbox = (1, 2, 3, 4)
        with (
            mock.patch.object(
                L, "_dependances_generer_ombrages", return_value=dependencies
            ),
            mock.patch.object(L, "_generer_ombrages_impl", implementation),
        ):
            actual = L.generer_ombrages(
                "source",
                "folder",
                choix=["multi"],
                elevation_soleil=35,
                nom_zone="zone",
                ecraser_ombrages=True,
                ecraser_tuiles=True,
                use_sweep=True,
                svf_gamma=1.4,
                svf_conv="rvt",
                svf_dist=40,
                bbox_natif=bbox,
                instances=instances,
            )
        self.assertIs(actual, result)
        implementation.assert_called_once_with(
            "source",
            "folder",
            choix=["multi"],
            elevation_soleil=35,
            nom_zone="zone",
            ecraser_ombrages=True,
            ecraser_tuiles=True,
            use_sweep=True,
            svf_gamma=1.4,
            svf_conv="rvt",
            svf_dist=40,
            bbox_natif=bbox,
            instances=instances,
            dependances=dependencies,
        )

    def test_vrt_is_registered_and_transaction_directory_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cogs = [root / "a.tif", root / "b.tif"]
            for cog in cogs:
                cog.touch()
            registered = []

            def build_vrt(_sources, destination, _resolution):
                destination.write_text("<VRTDataset/>", encoding="utf-8")

            dependencies = self._dependencies(
                resoudre_instances_ombrages=lambda *_args, **_kwargs: [],
                chemin_part=self._part_path,
                creer_fichier=registered.append,
                build_vrt_xml=build_vrt,
                normaliser_nom=lambda value: value,
                imprimer=lambda *_args, **_kwargs: None,
            )
            result = terrain_shading.generer_ombrages(
                cogs,
                root,
                choix=[],
                nom_zone="zone",
                dependances=dependencies,
            )
            transaction = root / "_tmp.test.part"
            self.assertEqual(result, [])
            self.assertEqual(
                [path.name for path in registered], ["_dalles.txt", "_mnt_complet.vrt"]
            )
            self.assertFalse(transaction.exists())

    def test_vrt_failure_is_explicit_and_cleans_transaction_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cogs = [root / "a.tif", root / "b.tif"]
            for cog in cogs:
                cog.touch()

            def fail_build(*_args):
                raise OSError("disk full")

            dependencies = self._dependencies(
                resoudre_instances_ombrages=lambda *_args, **_kwargs: [],
                chemin_part=self._part_path,
                creer_fichier=lambda _path: None,
                build_vrt_xml=fail_build,
                imprimer=lambda *_args, **_kwargs: None,
            )
            with self.assertRaisesRegex(RuntimeError, "Construction VRT échouée"):
                terrain_shading.generer_ombrages(
                    cogs,
                    root,
                    choix=[],
                    nom_zone="zone",
                    dependances=dependencies,
                )
            self.assertFalse((root / "_tmp.test.part").exists())

    def test_horn_output_is_published_only_after_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.tif"
            source.touch()
            jobs_seen = []
            registered = []

            def generate(_source, jobs, **_kwargs):
                jobs_seen.extend(jobs)
                for _kind, _params, destination in jobs:
                    destination.write_bytes(b"complete")
                return True

            def publish(part, final):
                part.replace(final)

            dependencies = self._dependencies(
                resoudre_instances_ombrages=lambda *_args, **_kwargs: [
                    ("slope", {}, "slope_ombrage")
                ],
                chemin_part=self._part_path,
                creer_fichier=registered.append,
                source_a_des_donnees=lambda _source: True,
                publier_tif_atomique=publish,
                hillshade_chunked_multi=generate,
                normaliser_nom=lambda value: value,
                formater_duree=lambda _seconds: "0s",
                imprimer=lambda *_args, **_kwargs: None,
            )
            expected = root / "zone_slope_ombrage.tif"
            result = terrain_shading.generer_ombrages(
                source,
                root,
                choix=["slope"],
                nom_zone="zone",
                dependances=dependencies,
            )
            self.assertEqual(result, [expected])
            self.assertEqual(expected.read_bytes(), b"complete")
            self.assertEqual(jobs_seen[0][0], "slope")
            self.assertEqual(registered, [expected])
            self.assertFalse(self._part_path(expected).exists())

    def test_horn_failure_keeps_previous_final_and_removes_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.tif"
            source.touch()
            final = root / "zone_slope_ombrage.tif"
            final.write_bytes(b"previous")

            def fail_after_partial(_source, jobs, **_kwargs):
                jobs[0][2].write_bytes(b"partial")
                return False

            dependencies = self._dependencies(
                resoudre_instances_ombrages=lambda *_args, **_kwargs: [
                    ("slope", {}, "slope_ombrage")
                ],
                chemin_part=self._part_path,
                creer_fichier=lambda _path: None,
                source_a_des_donnees=lambda _source: True,
                hillshade_chunked_multi=fail_after_partial,
                normaliser_nom=lambda value: value,
                imprimer=lambda *_args, **_kwargs: None,
            )
            with self.assertRaisesRegex(RuntimeError, "shading\\(s\\) failed"):
                terrain_shading.generer_ombrages(
                    source,
                    root,
                    choix=["slope"],
                    nom_zone="zone",
                    ecraser_ombrages=True,
                    dependances=dependencies,
                )
            self.assertEqual(final.read_bytes(), b"previous")
            self.assertFalse(self._part_path(final).exists())


class TerrainChunkContractTests(unittest.TestCase):
    def _dependencies(self, root, discover, events):
        provider = SimpleNamespace(
            CODE="provider-x",
            CRS_NATIF="EPSG:2154",
            discover_dalles=discover,
        )

        class Transformer:
            @staticmethod
            def transform(x, y):
                return x, y

        def get_transformer(src, dst):
            events.append(("transformer", src, dst))
            return Transformer()

        def bbox_transform(transform, *bbox):
            events.append(("bbox", transform(1, 2), bbox))
            return 6.0, 43.0, 6.1, 43.1

        @contextlib.contextmanager
        def manifest_context(manifest, key):
            events.append(("enter", manifest, key))
            try:
                yield
            finally:
                events.append(("exit", manifest, key))

        def active_folder(args, project):
            events.append(("folder", args, project))
            return root / "tiles"

        def download(*args, **kwargs):
            events.append(("download", args, kwargs))

        return terrain_chunks.DependancesMorceauTerrain(
            provider=provider,
            get_transformer=get_transformer,
            bbox_enveloppe_transform=bbox_transform,
            dossier_cache=root / "cache",
            dossier_travail=root / "work",
            lidar_subdir=Path("lidar/provider"),
            dossier_dalles_actif=active_folder,
            contexte_manifeste=manifest_context,
            telecharger_dalles_zone=download,
            decouvrir_et_telecharger_ombrage=lambda *_args, **_kwargs: None,
            resoudre_choix_ombrages=lambda _args: ([], []),
            lister_dalles_zone=lambda *_args: [],
            generer_ombrages=lambda *_args, **_kwargs: None,
            elevation_soleil=25.0,
            supprimer_fichiers=lambda *_args, **_kwargs: None,
        )

    def test_lookahead_discovers_margin_and_returns_only_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls = []

            def discover(bbox_wgs, bbox_native, cache):
                calls.append((bbox_wgs, bbox_native, cache))
                return {"b.tif": "u2", "a.tif": "u1"}

            dependencies = self._dependencies(root, discover, [])
            self.assertEqual(
                terrain_chunks.dalles_zone_lookahead(
                    (1, 2, 3, 4), dependances=dependencies
                ),
                {"a.tif", "b.tif"},
            )
            self.assertEqual(calls[0][0], (5.95, 42.95, 6.1499999999999995, 43.15))
            self.assertEqual(calls[0][1], (1, 2, 3, 4))
            self.assertEqual(calls[0][2], root / "cache/discover_provider-x.json")

    def test_lookahead_is_best_effort_for_empty_and_failed_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty = self._dependencies(root, lambda *_args: {}, [])
            self.assertIsNone(
                terrain_chunks.dalles_zone_lookahead(
                    (1, 2, 3, 4), dependances=empty
                )
            )

            def failure(*_args):
                raise OSError("offline")

            failed = self._dependencies(root, failure, [])
            self.assertIsNone(
                terrain_chunks.dalles_zone_lookahead(
                    (1, 2, 3, 4), dependances=failed
                )
            )

    def test_chunk_prepares_directories_context_and_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = []
            discovered = {"tile.tif": "https://invalid/tile"}
            dependencies = self._dependencies(
                root, lambda *_args: discovered, events
            )
            args = SimpleNamespace(dossier=None, telechargement=True)
            result = terrain_chunks.decouvrir_et_telecharger_ombrage(
                args,
                (1, 2, 3, 4),
                "zone_001",
                "zone",
                "manifest",
                "001",
                quiet=True,
                dependances=dependencies,
            )
            project = root / "work/Projets/zone/lidar/provider/zone_001"
            tiles = root / "tiles"
            self.assertEqual(result, (discovered, tiles, project))
            self.assertTrue(project.is_dir())
            self.assertTrue(tiles.is_dir())
            self.assertIn(("enter", "manifest", "001_dl"), events)
            self.assertIn(("exit", "manifest", "001_dl"), events)
            download = next(event for event in events if event[0] == "download")
            self.assertEqual(download[1][0:4], (discovered, (1, 2, 3, 4), tiles, project))
            self.assertEqual(download[2], {"quiet": True})

    def test_chunk_explicit_root_and_no_download_keep_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            explicit = root / "explicit"
            events = []
            discovered = {}
            dependencies = self._dependencies(
                root, lambda *_args: discovered, events
            )
            args = SimpleNamespace(
                dossier=str(explicit), telechargement=False
            )
            result = terrain_chunks.decouvrir_et_telecharger_ombrage(
                args,
                (1, 2, 3, 4),
                "chunk",
                "ignored-zone",
                None,
                "key",
                dependances=dependencies,
            )
            self.assertEqual(result[0], {})
            self.assertEqual(result[2], explicit.resolve() / "chunk")
            self.assertFalse(any(event[0] == "download" for event in events))

    def test_chunk_discovery_failures_are_retryable_runtime_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(dossier=None, telechargement=True)
            for result, expected in (
                (None, "tile discovery unavailable"),
                (OSError("offline"), r"tile discovery failed .*offline"),
            ):
                def discover(*_args, result=result):
                    if isinstance(result, BaseException):
                        raise result
                    return result

                dependencies = self._dependencies(root, discover, [])
                with self.subTest(result=result), self.assertRaisesRegex(
                    RuntimeError, expected
                ):
                    terrain_chunks.decouvrir_et_telecharger_ombrage(
                        args,
                        (1, 2, 3, 4),
                        "chunk",
                        "zone",
                        None,
                        "key",
                        dependances=dependencies,
                    )

    def test_chunk_facades_keep_signatures_and_reload_dependencies(self):
        marker = object()
        dependencies = object()
        with mock.patch.object(
            L, "_dependances_morceau_terrain", return_value=dependencies
        ), mock.patch.object(
            L, "_dalles_zone_lookahead_impl", return_value=marker
        ) as lookahead, mock.patch.object(
            L, "_decouvrir_et_telecharger_ombrage_impl", return_value=marker
        ) as download:
            self.assertIs(L._dalles_zone_lookahead((1, 2, 3, 4)), marker)
            args = SimpleNamespace()
            self.assertIs(
                L._decouvrir_et_telecharger_ombrage(
                    args, (1, 2, 3, 4), "chunk", "zone", None, "key", True
                ),
                marker,
            )
        self.assertIs(lookahead.call_args.kwargs["dependances"], dependencies)
        self.assertIs(download.call_args.kwargs["dependances"], dependencies)
        self.assertEqual(
            str(inspect.signature(L._dalles_zone_lookahead)), "(bbox_natif)"
        )
        self.assertEqual(
            str(inspect.signature(L._decouvrir_et_telecharger_ombrage)),
            "(args, bbox_natif, nom_z, nom_zone_base, manifeste, cle, quiet=False)",
        )

    def _classic_args(self, **changes):
        values = dict(
            zone_bbox="original-bbox",
            zone_nom="original-name",
            dossier=None,
            telechargement=True,
            ombrages=["svf"],
            ombrages_elevation=None,
            ombrages_ecraser=True,
            sweep_horizon=True,
            svf_gamma=0.8,
            svf_conv=2,
            svf_dist=30.0,
            mbtiles=True,
            rmap=False,
            sqlitedb=False,
        )
        values.update(changes)
        return SimpleNamespace(**values)

    def _classic_dependencies(self, root, discover):
        events = []
        provider = SimpleNamespace(
            CODE="provider-x",
            CRS_NATIF="EPSG:2154",
            discover_dalles=discover,
        )

        class Transformer:
            @staticmethod
            def transform(x, y):
                return x, y

        @contextlib.contextmanager
        def manifest_context(manifest, key):
            events.append(("enter", manifest, key))
            try:
                yield
            finally:
                events.append(("exit", manifest, key))

        def tile(*args, **kwargs):
            events.append(("tile", args, kwargs))
            kwargs["mbtiles_attendus"].append(root / "expected.mbtiles")
            return False

        dependencies = terrain_chunks.DependancesLidarClassique(
            provider=provider,
            dossier_travail=root / "work",
            dossier_cache=root / "cache",
            lidar_subdir=Path("lidar/provider"),
            get_transformer=lambda *args: events.append(
                ("transformer", args)
            )
            or Transformer(),
            bbox_enveloppe_transform=lambda transform, *bbox: events.append(
                ("bbox", transform(1, 2), bbox)
            )
            or (6.0, 43.0, 6.1, 43.1),
            dossier_dalles_actif=lambda *args: events.append(("folder", args))
            or root / "tiles",
            contexte_manifeste=manifest_context,
            telecharger_dalles_zone=lambda *args, **kwargs: events.append(
                ("download", args, kwargs)
            ),
            resoudre_choix_ombrages=lambda args: events.append(
                ("resolve", args)
            )
            or (["svf"], [{"type": "svf"}]),
            lister_dalles_zone=lambda *args: events.append(("list-tiles", args))
            or [root / "tile.tif"],
            generer_ombrages=lambda *args, **kwargs: events.append(
                ("shade", args, kwargs)
            )
            or [root / "shade.tif"],
            elevation_soleil=25.0,
            lister_tifs_ombrages=lambda *args: events.append(("list-tifs", args))
            or list(args[1] or []),
            tuiler_tifs_ombrages=tile,
            resultat_chunk=lambda ok, paths: (ok, tuple(paths)),
        )
        return dependencies, events

    def test_classic_lidar_transaction_forwards_halo_shading_and_tiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            discovery = []

            def discover(*args):
                discovery.append(args)
                return {"tile.tif": "url"}

            dependencies, events = self._classic_dependencies(root, discover)
            args = self._classic_args()
            result = terrain_chunks.traiter_bbox_lidar(
                args,
                (1000, 2000, 5000, 8000),
                "chunk",
                "zone",
                "manifest",
                "key",
                dependances=dependencies,
            )
            project = root / "work/Projets/zone/lidar/provider/chunk"
            margin_bbox = (600.0, 1600.0, 5400.0, 8400.0)
            self.assertEqual(result, (False, (root / "expected.mbtiles",)))
            self.assertEqual(args.zone_bbox, "original-bbox")
            self.assertEqual(args.zone_nom, "original-name")
            self.assertTrue(project.is_dir())
            self.assertTrue((root / "tiles").is_dir())
            self.assertEqual(
                discovery,
                [
                    (
                        (5.95, 42.95, 6.1499999999999995, 43.15),
                        margin_bbox,
                        root / "cache/discover_provider-x.json",
                    )
                ],
            )
            download = next(event for event in events if event[0] == "download")
            self.assertEqual(
                download[1][0:4],
                ({"tile.tif": "url"}, margin_bbox, root / "tiles", project),
            )
            shading = next(event for event in events if event[0] == "shade")
            self.assertEqual(shading[1][1:], (project, ["svf"]))
            self.assertEqual(shading[2]["bbox_natif"], margin_bbox)
            self.assertEqual(shading[2]["elevation_soleil"], 25.0)
            self.assertEqual(shading[2]["instances"], [{"type": "svf"}])
            tiling = next(event for event in events if event[0] == "tile")
            self.assertEqual(tiling[1][1], [root / "shade.tif"])
            self.assertEqual(tiling[1][2:5], (project, "chunk", (1000, 2000, 5000, 8000)))
            self.assertEqual(tiling[2]["tampon_coin_max_m"], 400.0)
            self.assertIn(("enter", "manifest", "key"), events)

    def test_classic_lidar_tiles_only_uses_floor_halo_and_none_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dependencies, events = self._classic_dependencies(
                root, lambda *_args: {}
            )
            dependencies = replace(
                dependencies,
                tuiler_tifs_ombrages=lambda *args, **kwargs: events.append(
                    ("tile", args, kwargs)
                )
                or True,
            )
            result = terrain_chunks.traiter_bbox_lidar(
                self._classic_args(telechargement=False, ombrages=[]),
                (0, 0, 1000, 2000),
                "chunk",
                "zone",
                None,
                "key",
                dependances=dependencies,
            )
            self.assertEqual(result, (True, ()))
            self.assertFalse(any(event[0] == "download" for event in events))
            self.assertFalse(any(event[0] == "shade" for event in events))
            listed = next(event for event in events if event[0] == "list-tifs")
            self.assertIsNone(listed[1][1])
            tiling = next(event for event in events if event[0] == "tile")
            self.assertEqual(tiling[2]["tampon_coin_max_m"], 300.0)

    def test_classic_lidar_without_output_format_keeps_empty_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            explicit = root / "explicit"
            dependencies, events = self._classic_dependencies(
                root, lambda *_args: {}
            )
            dependencies = replace(
                dependencies,
                tuiler_tifs_ombrages=mock.Mock(
                    side_effect=AssertionError("no output requested")
                ),
            )
            result = terrain_chunks.traiter_bbox_lidar(
                self._classic_args(
                    dossier=str(explicit),
                    telechargement=False,
                    ombrages=[],
                    mbtiles=False,
                    rmap=False,
                    sqlitedb=False,
                ),
                (0, 0, 1000, 1000),
                "chunk",
                "zone",
                None,
                "key",
                dependances=dependencies,
            )
            self.assertEqual(result, (True, ()))
            self.assertTrue((explicit.resolve() / "chunk").is_dir())
            self.assertFalse(any(event[0] == "tile" for event in events))

    def test_classic_lidar_discovery_failures_restore_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for outcome, expected in (
                (None, "tile discovery unavailable"),
                (OSError("offline"), r"tile discovery failed .*offline"),
            ):
                def discover(*_args, outcome=outcome):
                    if isinstance(outcome, BaseException):
                        raise outcome
                    return outcome

                dependencies, _events = self._classic_dependencies(root, discover)
                args = self._classic_args()
                with self.subTest(outcome=outcome), self.assertRaisesRegex(
                    RuntimeError, expected
                ):
                    terrain_chunks.traiter_bbox_lidar(
                        args,
                        (0, 0, 1000, 1000),
                        "chunk",
                        "zone",
                        None,
                        "key",
                        dependances=dependencies,
                    )
                self.assertEqual(args.zone_bbox, "original-bbox")
                self.assertEqual(args.zone_nom, "original-name")

    def test_classic_lidar_facade_keeps_signature_and_dependencies_late(self):
        marker = object()
        dependencies = object()
        with mock.patch.object(
            L, "_dependances_lidar_classique", return_value=dependencies
        ), mock.patch.object(
            L, "_traiter_bbox_lidar_impl", return_value=marker
        ) as implementation:
            self.assertIs(
                L._traiter_bbox_lidar(
                    "args", (1, 2, 3, 4), "chunk", "zone", "manifest", "key"
                ),
                marker,
            )
        self.assertIs(
            implementation.call_args.kwargs["dependances"], dependencies
        )
        self.assertEqual(
            str(inspect.signature(L._traiter_bbox_lidar)),
            "(args, bbox_natif, nom_z, nom_zone_base, manifeste, cle)",
        )

    def _shading_args(self, **changes):
        values = dict(
            zone_bbox="original-bbox",
            zone_nom="original-name",
            ombrages=[],
            ombrages_elevation=None,
            ombrages_ecraser=False,
            sweep_horizon=False,
            svf_gamma=None,
            svf_conv=None,
            svf_dist=None,
            telechargement=False,
            nettoyage=False,
            nettoyage_garder_dalles=False,
            dossier_dalles=None,
        )
        values.update(changes)
        return SimpleNamespace(**values)

    def test_shading_transaction_consumes_prefetch_and_restores_args(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = []

            def forbidden(*_args, **_kwargs):
                raise AssertionError("discovery must be skipped")

            dependencies = replace(
                self._dependencies(root, lambda *_args: {}, events),
                decouvrir_et_telecharger_ombrage=forbidden,
            )
            args = self._shading_args()
            callback = mock.Mock()
            terrain_chunks.traiter_bbox_lidar_ombrage(
                args,
                (1, 2, 3, 4),
                "chunk",
                "zone",
                None,
                "key",
                dalles_precharge=({}, root / "tiles", root / "project"),
                on_download_done=callback,
                dependances=dependencies,
            )
            callback.assert_called_once_with()
            self.assertEqual(args.zone_bbox, "original-bbox")
            self.assertEqual(args.zone_nom, "original-name")

    def test_shading_transaction_forwards_all_generation_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = []
            generated = []
            dependencies = replace(
                self._dependencies(root, lambda *_args: {}, events),
                decouvrir_et_telecharger_ombrage=lambda *_args: (
                    {"tile.tif": "url"},
                    root / "tiles",
                    root / "project",
                ),
                resoudre_choix_ombrages=lambda _args: (
                    ["svf"],
                    [{"type": "svf"}],
                ),
                lister_dalles_zone=lambda *args: generated.append(
                    ("list", args)
                )
                or [root / "tile.tif"],
                generer_ombrages=lambda *args, **kwargs: generated.append(
                    ("generate", args, kwargs)
                ),
                elevation_soleil=27.0,
            )
            args = self._shading_args(
                ombrages=["svf"],
                ombrages_ecraser=True,
                sweep_horizon=True,
                svf_gamma=0.8,
                svf_conv=2,
                svf_dist=30.0,
            )
            terrain_chunks.traiter_bbox_lidar_ombrage(
                args,
                (1, 2, 3, 4),
                "chunk",
                "zone",
                "manifest",
                "key",
                dependances=dependencies,
            )
            generation = next(item for item in generated if item[0] == "generate")
            self.assertEqual(generation[1][0], [root / "tile.tif"])
            self.assertEqual(generation[1][1:], (root / "project", ["svf"]))
            self.assertEqual(
                generation[2],
                {
                    "elevation_soleil": 27.0,
                    "nom_zone": "chunk",
                    "ecraser_ombrages": True,
                    "use_sweep": True,
                    "svf_gamma": 0.8,
                    "svf_conv": 2,
                    "svf_dist": 30.0,
                    "bbox_natif": (1, 2, 3, 4),
                    "instances": [{"type": "svf"}],
                },
            )
            self.assertIn(("enter", "manifest", "key"), events)
            self.assertIn(("exit", "manifest", "key"), events)

    def test_shading_cleanup_preserves_tile_and_cloud_cache_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            removed = []
            active = root / "active"
            cloud = root / "cloud"
            dependencies = replace(
                self._dependencies(root, lambda *_args: {}, []),
                dossier_dalles_actif=lambda _args, *_rest: active,
                decouvrir_et_telecharger_ombrage=lambda *_args: (
                    {}, active, root / "project"
                ),
                supprimer_fichiers=lambda *args, **kwargs: removed.append(
                    (args, kwargs)
                ),
            )

            class Manifest:
                def fichiers_morceau(self, key):
                    self.key = key
                    return ["download.tif"]

            manifest = Manifest()
            args = self._shading_args(
                telechargement=True,
                nettoyage=True,
                nettoyage_garder_dalles=True,
                _cloud_cache_dir=cloud,
            )
            terrain_chunks.traiter_bbox_lidar_ombrage(
                args,
                (1, 2, 3, 4),
                "chunk",
                "zone",
                manifest,
                "key",
                noms_dalles_a_garder={"shared.tif"},
                dependances=dependencies,
            )
            self.assertEqual(manifest.key, "key_dl")
            self.assertEqual(
                removed,
                [
                    (
                        (["download.tif"], [active, cloud]),
                        {"noms_garder": {"shared.tif"}},
                    )
                ],
            )

    def test_shading_failure_restores_args_and_keeps_downloads_for_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            removed = mock.Mock()
            dependencies = replace(
                self._dependencies(root, lambda *_args: {}, []),
                decouvrir_et_telecharger_ombrage=lambda *_args: (
                    {"tile.tif": "url"}, root / "tiles", root / "project"
                ),
                resoudre_choix_ombrages=lambda _args: (["svf"], []),
                lister_dalles_zone=lambda *_args: [root / "tile.tif"],
                generer_ombrages=mock.Mock(side_effect=RuntimeError("shading failed")),
                supprimer_fichiers=removed,
            )
            args = self._shading_args(
                ombrages=["svf"], telechargement=True, nettoyage=True
            )
            with self.assertRaisesRegex(RuntimeError, "shading failed"):
                terrain_chunks.traiter_bbox_lidar_ombrage(
                    args,
                    (1, 2, 3, 4),
                    "chunk",
                    "zone",
                    SimpleNamespace(fichiers_morceau=lambda _key: ["tile"]),
                    "key",
                    dependances=dependencies,
                )
            self.assertEqual(args.zone_bbox, "original-bbox")
            self.assertEqual(args.zone_nom, "original-name")
            removed.assert_not_called()

    def test_shading_facade_keeps_signature_and_reads_dependencies_late(self):
        marker = object()
        dependencies = object()
        with mock.patch.object(
            L, "_dependances_morceau_terrain", return_value=dependencies
        ), mock.patch.object(
            L, "_traiter_bbox_lidar_ombrage_impl", return_value=marker
        ) as implementation:
            self.assertIs(
                L._traiter_bbox_lidar_ombrage(
                    "args",
                    (1, 2, 3, 4),
                    "chunk",
                    "zone",
                    "manifest",
                    "key",
                    "prefetch",
                    "callback",
                    {"shared.tif"},
                ),
                marker,
            )
        self.assertIs(
            implementation.call_args.kwargs["dependances"], dependencies
        )
        self.assertEqual(
            str(inspect.signature(L._traiter_bbox_lidar_ombrage)),
            "(args, bbox_natif, nom_z, nom_zone_base, manifeste, cle, "
            "dalles_precharge=None, on_download_done=None, "
            "noms_dalles_a_garder=None)",
        )

    def _tiling_args(self, **changes):
        values = dict(
            zone_bbox="original-bbox",
            zone_nom="original-name",
            mbtiles=True,
            rmap=False,
            sqlitedb=False,
            dossier=None,
            zoom_min=10,
            zoom_max=18,
            tuiles_ecraser=False,
            formats_image="jpeg",
            qualite_image=85,
        )
        values.update(changes)
        return SimpleNamespace(**values)

    def _tiling_dependencies(self, root, *, tifs=(), neighbors=()):
        events = []

        @contextlib.contextmanager
        def manifest_context(manifest, key):
            events.append(("enter", manifest, key))
            try:
                yield
            finally:
                events.append(("exit", manifest, key))

        def generate(*args, **kwargs):
            events.append(("generate", args, kwargs))
            return root / "generated.mbtiles"

        dependencies = terrain_chunks.DependancesTuilageMorceau(
            dossier_travail=root / "work",
            lidar_subdir=Path("lidar/provider"),
            voisins_dossiers=lambda *args: events.append(
                ("neighbors", args)
            )
            or list(neighbors),
            contexte_manifeste=manifest_context,
            lister_tifs_ombrages=lambda *args: events.append(("list", args))
            or list(tifs),
            build_vrt_xml=lambda *args: events.append(("vrt", args)),
            creer_fichier=lambda path: events.append(("register", path)),
            mbtiles_a_regenerer=lambda *args, **kwargs: events.append(
                ("freshness", args, kwargs)
            )
            or True,
            generer_mbtiles_lidar=generate,
            tile_workers_defaut=lambda: 3,
            convertir_formats=lambda *args, **kwargs: events.append(
                ("convert", args, kwargs)
            )
            or True,
            resultat_chunk=lambda ok, paths: (ok, tuple(paths)),
            imprimer=lambda message: events.append(("print", message)),
        )
        return dependencies, events

    def test_tiling_without_requested_format_is_noop_and_restores_args(self):
        with tempfile.TemporaryDirectory() as tmp:
            dependencies, events = self._tiling_dependencies(Path(tmp))
            args = self._tiling_args(mbtiles=False, rmap=False, sqlitedb=False)
            self.assertIsNone(
                terrain_chunks.traiter_bbox_lidar_tuilage(
                    args,
                    (0, 0, 900, 600),
                    "chunk",
                    "zone",
                    None,
                    "key",
                    0,
                    0,
                    1,
                    1,
                    dependances=dependencies,
                )
            )
            self.assertEqual(events, [])
            self.assertEqual(args.zone_bbox, "original-bbox")
            self.assertEqual(args.zone_nom, "original-name")

    def test_tiling_single_shading_generates_expected_mbtiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tif = root / "work/Projets/zone/lidar/provider/chunk/chunk_svf.tif"
            tif.parent.mkdir(parents=True)
            tif.write_bytes(b"tif")
            dependencies, events = self._tiling_dependencies(root, tifs=[tif])
            args = self._tiling_args()
            result = terrain_chunks.traiter_bbox_lidar_tuilage(
                args,
                (0, 0, 900, 600),
                "chunk",
                "zone",
                "manifest",
                "key",
                0,
                0,
                1,
                1,
                dependances=dependencies,
            )
            expected = tif.parent / "chunk_svf_z10-18.mbtiles"
            self.assertEqual(result, (True, (expected,)))
            self.assertIn(("enter", "manifest", "key_t"), events)
            generation = next(event for event in events if event[0] == "generate")
            self.assertEqual(generation[1][0:3], (tif, tif.parent, "chunk_svf"))
            self.assertEqual(generation[2]["tampon_coin_max_m"], 200.0)
            self.assertEqual(generation[2]["tile_workers"], 3)
            freshness = next(event for event in events if event[0] == "freshness")
            self.assertEqual(freshness[1][0], expected)
            self.assertEqual(freshness[2], {"source": tif})
            self.assertEqual(args.zone_bbox, "original-bbox")
            self.assertEqual(args.zone_nom, "original-name")

    def test_tiling_neighbor_builds_and_registers_vrt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            city = root / "work/Projets/zone/lidar/provider/chunk"
            city.mkdir(parents=True)
            tif = city / "chunk_svf.tif"
            tif.write_bytes(b"tif")
            neighbor = root / "neighbor"
            neighbor.mkdir()
            neighbor_tif = neighbor / "neighbor_svf.tif"
            neighbor_tif.write_bytes(b"neighbor")
            dependencies, events = self._tiling_dependencies(
                root, tifs=[tif], neighbors=[neighbor]
            )

            class Dataset:
                transform = SimpleNamespace(a=0.5)

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return False

            fake_rasterio = SimpleNamespace(open=lambda _path: Dataset())
            with mock.patch.dict(sys.modules, {"rasterio": fake_rasterio}):
                terrain_chunks.traiter_bbox_lidar_tuilage(
                    self._tiling_args(),
                    (0, 0, 900, 600),
                    "chunk",
                    "zone",
                    None,
                    "key",
                    0,
                    0,
                    1,
                    2,
                    dependances=dependencies,
                )
            vrt = city / "_voisins_svf.vrt"
            self.assertIn(("vrt", ([tif, neighbor_tif], vrt, 0.5)), events)
            self.assertIn(("register", vrt), events)
            generation = next(event for event in events if event[0] == "generate")
            self.assertEqual(generation[1][0], vrt)

    def test_tiling_converts_every_family_and_aggregates_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            city = root / "work/Projets/zone/lidar/provider/chunk"
            city.mkdir(parents=True)
            tifs = [city / "chunk_svf.tif", city / "chunk_lrm.tif"]
            for tif in tifs:
                tif.write_bytes(b"tif")
            dependencies, events = self._tiling_dependencies(root, tifs=tifs)
            outcomes = iter((False, True))
            dependencies = replace(
                dependencies,
                convertir_formats=lambda *args, **kwargs: events.append(
                    ("convert", args, kwargs)
                )
                or next(outcomes),
            )
            result = terrain_chunks.traiter_bbox_lidar_tuilage(
                self._tiling_args(),
                (0, 0, 900, 600),
                "chunk",
                "zone",
                None,
                "key",
                0,
                0,
                1,
                1,
                dependances=dependencies,
            )
            self.assertFalse(result[0])
            self.assertEqual(len(result[1]), 2)
            self.assertEqual(
                len([event for event in events if event[0] == "convert"]), 2
            )

    def test_tiling_reuses_existing_mbtiles_without_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            city = root / "work/Projets/zone/lidar/provider/chunk"
            city.mkdir(parents=True)
            tif = city / "chunk_svf.tif"
            tif.write_bytes(b"tif")
            dependencies, events = self._tiling_dependencies(root, tifs=[tif])
            dependencies = replace(
                dependencies,
                mbtiles_a_regenerer=lambda *_args, **_kwargs: False,
                generer_mbtiles_lidar=mock.Mock(
                    side_effect=AssertionError("must reuse")
                ),
            )
            terrain_chunks.traiter_bbox_lidar_tuilage(
                self._tiling_args(),
                (0, 0, 900, 600),
                "chunk",
                "zone",
                None,
                "key",
                0,
                0,
                1,
                1,
                dependances=dependencies,
            )
            conversion = next(event for event in events if event[0] == "convert")
            self.assertEqual(conversion[1][0], city / "chunk_svf_z10-18.mbtiles")
            self.assertFalse(conversion[2]["mbtiles_neuf"])
            self.assertTrue(any(event[0] == "print" for event in events))

    def test_tiling_failure_restores_args_and_facade_keeps_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            city = root / "work/Projets/zone/lidar/provider/chunk"
            city.mkdir(parents=True)
            tif = city / "chunk_svf.tif"
            tif.write_bytes(b"tif")
            dependencies, _events = self._tiling_dependencies(root, tifs=[tif])
            dependencies = replace(
                dependencies,
                generer_mbtiles_lidar=mock.Mock(
                    side_effect=RuntimeError("tiling failed")
                ),
            )
            args = self._tiling_args()
            with self.assertRaisesRegex(RuntimeError, "tiling failed"):
                terrain_chunks.traiter_bbox_lidar_tuilage(
                    args,
                    (0, 0, 900, 600),
                    "chunk",
                    "zone",
                    None,
                    "key",
                    0,
                    0,
                    1,
                    1,
                    dependances=dependencies,
                )
            self.assertEqual(args.zone_bbox, "original-bbox")
            self.assertEqual(args.zone_nom, "original-name")

        marker = object()
        dependencies = object()
        with mock.patch.object(
            L, "_dependances_tuilage_morceau", return_value=dependencies
        ), mock.patch.object(
            L, "_traiter_bbox_lidar_tuilage_impl", return_value=marker
        ) as implementation:
            self.assertIs(
                L._traiter_bbox_lidar_tuilage(
                    "args", (1, 2, 3, 4), "chunk", "zone", None, "key", 0, 1, 2, 3
                ),
                marker,
            )
        self.assertIs(
            implementation.call_args.kwargs["dependances"], dependencies
        )
        self.assertEqual(
            str(inspect.signature(L._traiter_bbox_lidar_tuilage)),
            "(args, bbox_natif, nom_z, nom_zone_base, manifeste, cle, "
            "i_lat, i_lon, n_lat, n_lon)",
        )

    def _wmts_args(self, **changes):
        values = dict(
            zone_nom="original-name",
            zoom_min=18,
            zoom_max=10,
            dossier=None,
            formats_image="jpeg",
            qualite_image=77,
            couche="layer-id",
            tuiles_ecraser=False,
            apikey="secret",
            workers=3,
            telechargement_ecraser=False,
        )
        values.update(changes)
        return SimpleNamespace(**values)

    def _wmts_dependencies(self, root):
        events = []

        @contextlib.contextmanager
        def manifest_context(manifest, key):
            events.append(("enter", manifest, key))
            try:
                yield
            finally:
                events.append(("exit", manifest, key))

        tiles = object()

        def generate(**kwargs):
            events.append(("generate", kwargs))
            kwargs["chemin"].touch()

        dependencies = terrain_chunks.DependancesWmtsMorceau(
            dossier_travail=root / "work",
            dossier_cache=root / "cache",
            contexte_manifeste=manifest_context,
            calculer_grille_xyz=lambda *args: events.append(("grid", args)) or tiles,
            compter_tuiles_xyz=lambda *args: events.append(("count", args)) or 42,
            jpeg_quality_sortie=lambda *args: events.append(("quality", args)) or 77,
            nom_mbtiles_wmts=lambda *args: events.append(("name", args))
            or f"{args[0]}_layer_z{args[2]}-{args[3]}_q{args[4]}",
            mbtiles_a_regenerer=lambda *args: events.append(("freshness", args))
            or True,
            generer_mbtiles_wmts=generate,
            convertir_formats=lambda *args, **kwargs: events.append(
                ("convert", args, kwargs)
            )
            or True,
            resultat_chunk=lambda ok, paths: (ok, tuple(paths)),
        )
        return dependencies, events, tiles

    def test_wmts_transaction_normalizes_zooms_and_forwards_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dependencies, events, tiles = self._wmts_dependencies(root)
            args = self._wmts_args()
            result = terrain_chunks.traiter_bbox_wmts(
                args,
                (6.0, 43.0, 6.1, 43.1),
                "chunk",
                "zone",
                "LAYER",
                "normal",
                "image/jpeg",
                "jpg",
                True,
                "manifest",
                "key",
                dependances=dependencies,
            )
            expected = (
                root
                / "work/Projets/zone/raster/chunk/chunk_layer_z10-18_q77.mbtiles"
            )
            self.assertEqual(result, (True, (expected,)))
            self.assertEqual(args.zone_nom, "original-name")
            self.assertIn(("enter", "manifest", "key"), events)
            self.assertIn(
                ("grid", (43.0, 6.0, 43.1, 6.1, 10, 18)), events
            )
            generation = next(event[1] for event in events if event[0] == "generate")
            self.assertIs(generation["tuiles_iter"], tiles)
            self.assertEqual(generation["chemin"], expected)
            self.assertEqual(generation["total"], 42)
            self.assertEqual(generation["bbox_wgs84"], (6.0, 43.0, 6.1, 43.1))
            self.assertEqual(generation["jpeg_quality"], 77)
            self.assertEqual(generation["dossier_cache"], root / "cache/ign_raster")
            self.assertTrue((root / "cache/ign_raster").is_dir())

    def test_wmts_transaction_reuses_existing_mbtiles_and_explicit_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dependencies, events, _tiles = self._wmts_dependencies(root)
            output = root / "explicit"
            expected = output / "chunk/chunk_layer_z10-18_q77.mbtiles"
            expected.parent.mkdir(parents=True)
            expected.touch()
            dependencies = replace(
                dependencies,
                mbtiles_a_regenerer=lambda *_args: False,
                generer_mbtiles_wmts=mock.Mock(
                    side_effect=AssertionError("must reuse")
                ),
            )
            result = terrain_chunks.traiter_bbox_wmts(
                self._wmts_args(dossier=str(output)),
                (6.0, 43.0, 6.1, 43.1),
                "chunk",
                "zone",
                "LAYER",
                "normal",
                "image/jpeg",
                "jpg",
                False,
                None,
                "key",
                dependances=dependencies,
            )
            self.assertEqual(result, (True, (expected,)))
            conversion = next(event for event in events if event[0] == "convert")
            self.assertEqual(conversion[1][0], expected)
            self.assertFalse(conversion[2]["mbtiles_neuf"])

    def test_wmts_transaction_reports_missing_generated_mbtiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dependencies, events, _tiles = self._wmts_dependencies(root)
            dependencies = replace(
                dependencies,
                generer_mbtiles_wmts=lambda **_kwargs: None,
                convertir_formats=mock.Mock(
                    side_effect=AssertionError("missing file cannot be converted")
                ),
            )
            result = terrain_chunks.traiter_bbox_wmts(
                self._wmts_args(),
                (6.0, 43.0, 6.1, 43.1),
                "chunk",
                "zone",
                "LAYER",
                "normal",
                "image/jpeg",
                "jpg",
                False,
                None,
                "key",
                dependances=dependencies,
            )
            self.assertFalse(result[0])
            self.assertEqual(len(result[1]), 1)
            self.assertFalse(any(event[0] == "convert" for event in events))

    def test_wmts_transaction_propagates_conversion_status_and_restores_on_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dependencies, _events, _tiles = self._wmts_dependencies(root)
            failed_conversion = replace(
                dependencies, convertir_formats=lambda *_args, **_kwargs: False
            )
            result = terrain_chunks.traiter_bbox_wmts(
                self._wmts_args(),
                (6.0, 43.0, 6.1, 43.1),
                "chunk",
                "zone",
                "LAYER",
                "normal",
                "image/jpeg",
                "jpg",
                False,
                None,
                "key",
                dependances=failed_conversion,
            )
            self.assertFalse(result[0])

            args = self._wmts_args()
            failure = replace(
                dependencies,
                generer_mbtiles_wmts=mock.Mock(
                    side_effect=RuntimeError("WMTS failed")
                ),
            )
            with self.assertRaisesRegex(RuntimeError, "WMTS failed"):
                terrain_chunks.traiter_bbox_wmts(
                    args,
                    (6.0, 43.0, 6.1, 43.1),
                    "chunk",
                    "zone",
                    "LAYER",
                    "normal",
                    "image/jpeg",
                    "jpg",
                    False,
                    None,
                    "key",
                    dependances=failure,
                )
            self.assertEqual(args.zone_nom, "original-name")

    def test_wmts_facade_keeps_signature_and_reads_dependencies_late(self):
        marker = object()
        dependencies = object()
        with mock.patch.object(
            L, "_dependances_wmts_morceau", return_value=dependencies
        ), mock.patch.object(
            L, "_traiter_bbox_wmts_impl", return_value=marker
        ) as implementation:
            self.assertIs(
                L._traiter_bbox_wmts(
                    "args",
                    (1, 2, 3, 4),
                    "chunk",
                    "zone",
                    "layer",
                    "style",
                    "format",
                    "extension",
                    True,
                    "manifest",
                    "key",
                ),
                marker,
            )
        self.assertIs(
            implementation.call_args.kwargs["dependances"], dependencies
        )
        self.assertEqual(
            str(inspect.signature(L._traiter_bbox_wmts)),
            "(args, bbox_wgs84, nom_z, nom_zone_base, layer, style, img_fmt, "
            "fmt_ext, apikey_requis, manifeste, cle)",
        )


class TerrainTilingContractTests(unittest.TestCase):
    @staticmethod
    def _args(**changes):
        values = dict(
            zoom_min=10,
            zoom_max=18,
            tuiles_ecraser=False,
            formats_image="jpeg",
            qualite_image=85,
        )
        values.update(changes)
        return SimpleNamespace(**values)

    @staticmethod
    def _dependencies(events, outcomes=()):
        conversions = iter(outcomes)

        def generate(*args, **kwargs):
            events.append(("generate", args, kwargs))
            return Path(f"{args[2]}.generated.mbtiles")

        return terrain_chunks.DependancesTuilageOmbrages(
            mbtiles_a_regenerer=lambda *args, **kwargs: events.append(
                ("freshness", args, kwargs)
            )
            or True,
            generer_mbtiles_lidar=generate,
            tile_workers_defaut=lambda: 4,
            convertir_formats=lambda *args, **kwargs: events.append(
                ("convert", args, kwargs)
            )
            or next(conversions),
            imprimer=lambda message: events.append(("print", message)),
        )

    def test_common_tiling_empty_input_is_success_without_side_effect(self):
        events = []
        dependencies = self._dependencies(events)
        self.assertTrue(
            terrain_chunks.tuiler_tifs_ombrages(
                self._args(),
                [],
                Path("output"),
                "zone",
                (1, 2, 3, 4),
                dependances=dependencies,
            )
        )
        self.assertEqual(events, [])

    def test_common_tiling_generates_every_family_and_aggregates_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = []
            dependencies = self._dependencies(events, outcomes=(False, True))
            tifs = [
                root / "zone_svf_tuilage_z18.tif",
                root / "foreign_lrm.tif",
            ]
            expected = []
            result = terrain_chunks.tuiler_tifs_ombrages(
                self._args(tuiles_ecraser=True),
                tifs,
                root,
                "zone",
                (1, 2, 3, 4),
                decoupe_sortie=False,
                verbose=True,
                tampon_coin_max_m=300.0,
                mbtiles_attendus=expected,
                dependances=dependencies,
            )
            self.assertFalse(result)
            self.assertEqual(
                expected,
                [
                    root / "zone_svf_z10-18.mbtiles",
                    root / "zone_foreign_lrm_z10-18.mbtiles",
                ],
            )
            generations = [event for event in events if event[0] == "generate"]
            self.assertEqual(len(generations), 2)
            first = generations[0]
            self.assertEqual(first[1], (tifs[0], root, "zone_svf"))
            self.assertEqual(
                first[2],
                {
                    "zoom_min": 10,
                    "zoom_max": 18,
                    "format_tuiles": "jpeg",
                    "jpeg_quality": 85,
                    "bbox_natif": (1, 2, 3, 4),
                    "tampon_coin_max_m": 300.0,
                    "ecraser_tuiles": True,
                    "tile_workers": 4,
                },
            )
            conversions = [event for event in events if event[0] == "convert"]
            self.assertEqual(len(conversions), 2)
            self.assertTrue(
                all(not event[2]["decoupe_sortie"] for event in conversions)
            )
            self.assertEqual(
                [event[1] for event in events if event[0] == "print"],
                ["  zone_svf_tuilage_z18.tif", "  foreign_lrm.tif"],
            )

    def test_common_tiling_reuses_fresh_mbtiles_without_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = []
            dependencies = replace(
                self._dependencies(events, outcomes=(True,)),
                mbtiles_a_regenerer=lambda *args, **kwargs: events.append(
                    ("freshness", args, kwargs)
                )
                or False,
                generer_mbtiles_lidar=mock.Mock(
                    side_effect=AssertionError("must reuse")
                ),
            )
            tif = root / "zone_lrm.tif"
            self.assertTrue(
                terrain_chunks.tuiler_tifs_ombrages(
                    self._args(),
                    [tif],
                    root,
                    "zone",
                    (1, 2, 3, 4),
                    dependances=dependencies,
                )
            )
            expected = root / "zone_lrm_z10-18.mbtiles"
            freshness = next(event for event in events if event[0] == "freshness")
            self.assertEqual(freshness[1][0], expected)
            self.assertEqual(freshness[2], {"source": tif})
            conversion = next(event for event in events if event[0] == "convert")
            self.assertEqual(conversion[1][0], expected)
            self.assertTrue(conversion[2]["decoupe_sortie"])
            self.assertFalse(conversion[2]["mbtiles_neuf"])
            self.assertTrue(
                any("Existing MBTiles" in event[1] for event in events if event[0] == "print")
            )

    def test_common_tiling_facade_keeps_signature_and_dependencies_late(self):
        marker = object()
        dependencies = object()
        with mock.patch.object(
            L, "_dependances_tuilage_ombrages", return_value=dependencies
        ), mock.patch.object(
            L, "_tuiler_tifs_ombrages_impl", return_value=marker
        ) as implementation:
            self.assertIs(
                L._tuiler_tifs_ombrages(
                    "args",
                    "tifs",
                    "folder",
                    "zone",
                    "bbox",
                    False,
                    True,
                    300,
                    "expected",
                ),
                marker,
            )
        self.assertIs(
            implementation.call_args.kwargs["dependances"], dependencies
        )
        self.assertEqual(
            str(inspect.signature(L._tuiler_tifs_ombrages)),
            "(args, tifs, dossier_ville, nom_zone, bbox, decoupe_sortie=True, "
            "verbose=False, tampon_coin_max_m=0, mbtiles_attendus=None)",
        )


class TerrainDownloadContractTests(unittest.TestCase):
    def _args(self, **changes):
        values = dict(
            telechargement_forcer=False,
            telechargement_ecraser=False,
            telechargement_compresser=False,
            workers=3,
            laz_parallel=1,
        )
        values.update(changes)
        return SimpleNamespace(**values)

    def test_tile_path_rejects_traversal_and_keeps_legacy_root_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "legacy.tif"
            legacy.write_bytes(b"legacy")
            provider = SimpleNamespace(
                subdir_from_name=lambda name: (
                    "0958" if name != "plain.tif" else ""
                )
            )
            with mock.patch.object(L, "PROVIDER", provider):
                self.assertEqual(L.chemin_dalle(root, "legacy.tif"), legacy)
                self.assertEqual(
                    L.chemin_dalle(root, "new.tif"),
                    root / "0958" / "new.tif",
                )
                self.assertEqual(
                    L.chemin_dalle(root, "plain.tif"), root / "plain.tif"
                )
                for unsafe in (
                    "../x.tif",
                    "..\\x.tif",
                    "/x.tif",
                    "C:\\x.tif",
                ):
                    with self.subTest(unsafe=unsafe), self.assertRaises(
                        ValueError
                    ):
                        L.chemin_dalle(root, unsafe)

    def test_active_tile_folder_routes_override_windowed_laz_and_cache(self):
        args = SimpleNamespace(dossier_dalles=None)
        cache = Path("cache-root")
        production = Path("production-root")
        project = Path("project-root")
        with mock.patch.object(L, "DOSSIER_CACHE", cache), mock.patch.object(
            L, "DOSSIER_PRODUCTION", production
        ), mock.patch.object(L, "LIDAR_SUBDIR", Path("lidar/provider")):
            with mock.patch.object(
                L, "PROVIDER", SimpleNamespace(CODE="p", COG_WINDOWED=True)
            ):
                self.assertEqual(
                    L._dossier_dalles_actif(args, project), project
                )
            with mock.patch.object(
                L, "PROVIDER", SimpleNamespace(CODE="p-laz")
            ):
                self.assertEqual(
                    L._dossier_dalles_actif(args),
                    production / "lidar/provider",
                )
            with mock.patch.object(L, "PROVIDER", SimpleNamespace(CODE="p")):
                self.assertEqual(
                    L._dossier_dalles_actif(args), cache / "lidar/provider"
                )
                args.dossier_dalles = "."
                self.assertEqual(
                    L._dossier_dalles_actif(args), Path(".").resolve()
                )

    def test_tile_validator_accepts_classic_and_big_tiff_magic(self):
        reads = []

        class Dataset:
            width = 10
            height = 12
            count = 1
            res = (0.5, 0.5)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, band, window=None):
                reads.append((band, window))

        fake_rasterio = SimpleNamespace(
            open=lambda _path: Dataset(),
            windows=SimpleNamespace(Window=lambda *args: args),
        )
        magics = (
            b"II\x2a\x00",
            b"MM\x00\x2a",
            b"II\x2b\x00",
            b"MM\x00\x2b",
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            sys.modules, {"rasterio": fake_rasterio}
        ):
            for index, magic in enumerate(magics):
                path = Path(tmp) / f"valid-{index}.tif"
                path.write_bytes(magic)
                with self.subTest(magic=magic):
                    self.assertTrue(L._valider_tif_dalle(path))
        self.assertEqual(len(reads), 4)

    def test_tile_validator_rejects_bad_magic_metadata_and_data(self):
        class Dataset:
            width = 10
            height = 10
            count = 1
            res = (1.0, 1.0)
            fail_read = False

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _band, window=None):
                if self.fail_read:
                    raise OSError("truncated data")

        dataset = Dataset()
        fake_rasterio = SimpleNamespace(
            open=lambda _path: dataset,
            windows=SimpleNamespace(Window=lambda *args: args),
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            sys.modules, {"rasterio": fake_rasterio}
        ):
            path = Path(tmp) / "tile.tif"
            path.write_bytes(b"not-a-tiff")
            self.assertFalse(L._valider_tif_dalle(path))
            path.write_bytes(b"II\x2a\x00")
            for attribute, value in (
                ("width", 0),
                ("height", 0),
                ("count", 0),
                ("res", (0.0, 1.0)),
                ("res", (1e9, 1.0)),
                ("fail_read", True),
            ):
                previous = getattr(dataset, attribute)
                setattr(dataset, attribute, value)
                with self.subTest(attribute=attribute, value=value):
                    self.assertFalse(L._valider_tif_dalle(path))
                setattr(dataset, attribute, previous)

    def test_tile_support_facades_keep_signatures_and_late_dependencies(self):
        marker = object()
        provider = SimpleNamespace()
        cache = Path("late-cache")
        production = Path("late-production")
        subdir = Path("late-lidar")
        args = SimpleNamespace(dossier_dalles=None)
        with mock.patch.object(L, "PROVIDER", provider), mock.patch.object(
            L, "DOSSIER_CACHE", cache
        ), mock.patch.object(
            L, "DOSSIER_PRODUCTION", production
        ), mock.patch.object(L, "LIDAR_SUBDIR", subdir), mock.patch.object(
            L, "_nom_dalle_sur_impl", return_value=marker
        ) as safe_impl, mock.patch.object(
            L, "_chemin_dalle_impl", return_value=marker
        ) as path_impl, mock.patch.object(
            L, "_dossier_dalles_actif_impl", return_value=marker
        ) as folder_impl, mock.patch.object(
            L, "_valider_tif_dalle_impl", return_value=marker
        ) as validator_impl:
            self.assertIs(L._nom_dalle_sur("tile.tif"), marker)
            self.assertIs(L.chemin_dalle(Path("root"), "tile.tif"), marker)
            self.assertIs(L._dossier_dalles_actif(args, Path("project")), marker)
            self.assertIs(L._valider_tif_dalle("tile.tif"), marker)

        safe_impl.assert_called_once_with("tile.tif")
        self.assertIs(path_impl.call_args.kwargs["provider"], provider)
        self.assertIs(path_impl.call_args.kwargs["nom_dalle_sur"], L._nom_dalle_sur)
        self.assertIs(folder_impl.call_args.kwargs["provider"], provider)
        self.assertEqual(folder_impl.call_args.kwargs["dossier_cache"], cache)
        self.assertEqual(
            folder_impl.call_args.kwargs["dossier_production"], production
        )
        self.assertEqual(folder_impl.call_args.kwargs["lidar_subdir"], subdir)
        validator_impl.assert_called_once_with("tile.tif")
        self.assertEqual(str(inspect.signature(L._nom_dalle_sur)), "(nom)")
        self.assertEqual(
            str(inspect.signature(L.chemin_dalle)), "(dossier_dalles, nom)"
        )
        self.assertEqual(
            str(inspect.signature(L._dossier_dalles_actif)),
            "(args, dossier_ville=None)",
        )
        self.assertEqual(
            str(inspect.signature(L._valider_tif_dalle)), "(chemin)"
        )

    def test_robust_tif_listing_keeps_root_and_one_level_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "direct.TIF"
            direct.write_bytes(b"x")
            child = root / "child"
            child.mkdir()
            nested = child / "nested.tif"
            nested.write_bytes(b"x")
            deep = child / "deep"
            deep.mkdir()
            (deep / "ignored.tif").write_bytes(b"x")
            self.assertEqual(
                set(L._rglob_tif_robuste(root)), {direct, nested}
            )

        messages = []

        class Inaccessible:
            def __fspath__(self):
                raise OSError("offline disk")

        self.assertEqual(
            terrain_download.rglob_tif_robuste(
                Inaccessible(), imprimer=messages.append
            ),
            [],
        )
        self.assertIn("tiles folder inaccessible", messages[0])

    def test_cloud_cache_policy_routes_shared_and_windowed_clouds(self):
        cache = Path("cache")
        subdir = Path("lidar/provider")
        values = []
        provider = SimpleNamespace(
            COG_WINDOWED=False,
            COPC_WINDOWED=False,
            set_cloud_cache_dir=values.append,
        )
        args = SimpleNamespace(dossier_dalles=None)
        terrain_download.configurer_cloud_cache(
            args,
            provider=provider,
            dossier_cache=cache,
            lidar_subdir=subdir,
        )
        self.assertEqual(values, [cache / subdir])
        self.assertEqual(args._cloud_cache_dir, cache / subdir)

        for change in (
            {"COG_WINDOWED": True},
            {"COPC_WINDOWED": True},
        ):
            with self.subTest(change=change):
                values.clear()
                setattr(provider, next(iter(change)), True)
                terrain_download.configurer_cloud_cache(
                    args,
                    provider=provider,
                    dossier_cache=cache,
                    lidar_subdir=subdir,
                )
                self.assertEqual(values, [None])
                self.assertIsNone(args._cloud_cache_dir)
                setattr(provider, next(iter(change)), False)

        args.dossier_dalles = "explicit"
        values.clear()
        terrain_download.configurer_cloud_cache(
            args,
            provider=provider,
            dossier_cache=cache,
            lidar_subdir=subdir,
        )
        self.assertEqual(values, [None])

    def test_laz_profile_uses_injected_state_and_reports_pipeline_bound(self):
        profile = {
            "dl_n": 0,
            "dl_s": 0.0,
            "conv_n": 0,
            "conv_s": 0.0,
            "conv_max": 0.0,
        }
        lock = threading.Lock()
        terrain_download.laz_prof_add(
            12.0, 8.0, enabled=True, lock=lock, profile=profile
        )
        terrain_download.laz_prof_add(
            conv_s=10.0, enabled=True, lock=lock, profile=profile
        )
        self.assertEqual(
            profile,
            {
                "dl_n": 1,
                "dl_s": 12.0,
                "conv_n": 2,
                "conv_s": 18.0,
                "conv_max": 10.0,
            },
        )
        messages = []
        terrain_download.laz_prof_resume(
            20.0,
            3,
            2,
            enabled=True,
            lock=lock,
            profile=profile,
            imprimer=messages.append,
        )
        self.assertEqual(len(messages), 2)
        self.assertIn("download 1 dalles", messages[0])
        self.assertIn("borne découplé ~9s", messages[1])
        self.assertIn("gain potentiel x2.2", messages[1])

    def test_prefetch_is_depth_one_and_consumes_only_matching_result(self):
        events = []

        class ImmediateThread:
            def __init__(self, *, target, daemon):
                events.append(("thread", daemon))
                self.target = target

            def start(self):
                events.append("start")
                self.target()

            def join(self):
                events.append("join")

        def discover(*args, **kwargs):
            events.append(("discover", args[1], args[2], args[5], kwargs))
            return "prefetched"

        prefetch = terrain_prefetch.PrefetchDalles(
            terrain_prefetch.DependancesPrefetchDalles(
                espace_libre_go=lambda _path: 100.0,
                decouvrir_et_telecharger_ombrage=discover,
                thread_factory=ImmediateThread,
            )
        )
        args = SimpleNamespace(min_free_gb=2.0)
        prefetch.lancer(
            args, "manifest", Path("root"), "zone", (0, 0, 1, 2, 3, 4), "001"
        )
        prefetch.lancer(
            args, "manifest", Path("root"), "zone", (0, 0, 5, 6, 7, 8), "002"
        )
        self.assertIsNone(prefetch.recuperer("other"))
        self.assertEqual(prefetch.recuperer("001"), "prefetched")
        self.assertEqual(
            [event for event in events if isinstance(event, tuple) and event[0] == "discover"],
            [("discover", (1, 2, 3, 4), "zone_001", "001", {"quiet": True})],
        )
        self.assertIsNone(prefetch.recuperer("001"))

    def test_prefetch_low_disk_and_failure_degrade_to_synchronous_path(self):
        calls = []
        messages = []

        class ImmediateThread:
            def __init__(self, *, target, daemon):
                self.target = target

            def start(self):
                self.target()

            def join(self):
                calls.append("join")

        def failure(*_args, **_kwargs):
            calls.append("discover")
            raise OSError("network down")

        dependencies = terrain_prefetch.DependancesPrefetchDalles(
            espace_libre_go=lambda _path: 3.0,
            decouvrir_et_telecharger_ombrage=failure,
            thread_factory=ImmediateThread,
            imprimer=messages.append,
        )
        prefetch = terrain_prefetch.PrefetchDalles(dependencies)
        args = SimpleNamespace(min_free_gb=2.0)
        prefetch.lancer(args, None, Path("root"), "zone", (0, 0, 1, 2, 3, 4), "low")
        self.assertEqual(calls, [])
        args.min_free_gb = 0.0
        prefetch.lancer(args, None, Path("root"), "zone", (0, 0, 1, 2, 3, 4), "err")
        self.assertIsNone(prefetch.recuperer("err"))
        self.assertEqual(calls, ["discover", "join"])
        self.assertIn("Prefetch err: OSError: network down", messages[0])

    def test_cache_and_prefetch_facades_keep_signatures_and_late_seams(self):
        marker = object()
        provider = SimpleNamespace()
        with mock.patch.object(L, "_rglob_tif_robuste_impl", return_value=marker) as listing, mock.patch.object(
            L, "_configurer_cloud_cache_impl", return_value=marker
        ) as cache_impl, mock.patch.object(L, "PROVIDER", provider), mock.patch.object(
            L, "DOSSIER_CACHE", Path("late-cache")
        ), mock.patch.object(L, "LIDAR_SUBDIR", Path("late-subdir")):
            self.assertIs(L._rglob_tif_robuste(Path("root")), marker)
            self.assertIs(
                L._configurer_cloud_cache(SimpleNamespace(dossier_dalles=None)),
                marker,
            )
        listing.assert_called_once()
        self.assertIs(cache_impl.call_args.kwargs["provider"], provider)
        self.assertEqual(str(inspect.signature(L._rglob_tif_robuste)), "(dossier)")
        self.assertEqual(str(inspect.signature(L._configurer_cloud_cache)), "(args)")
        self.assertEqual(str(inspect.signature(L._laz_prof_add)), "(dl_s=None, conv_s=None)")
        self.assertEqual(
            str(inspect.signature(L._laz_prof_resume)),
            "(wall_s, n_dl_workers, laz_parallel)",
        )
        self.assertEqual(str(inspect.signature(L._PrefetchDalles)), "()")

    def _dependencies(self, provider, events, *, result="ok"):
        def path_for(root, name):
            return Path(root) / name

        def downloader(*args):
            name, _url, root = args[:3]
            events.append(("download", name, args[3:]))
            if result == "ok":
                path_for(root, name).write_bytes(b"x" * 32)
            return result

        def write_manifest(path, bbox, names):
            events.append(("manifest", Path(path), bbox, tuple(names)))

        def register(paths):
            events.append(("register", tuple(Path(p) for p in paths)))

        return terrain_download.DependancesTelechargementTerrain(
            provider=provider,
            nom_dalle_sur=lambda name: "/" not in name and "\\" not in name,
            chemin_dalle=path_for,
            seuil_dalle_valide=10,
            telecharger_cog_fenetre=downloader,
            telecharger_copc_fenetre=downloader,
            telecharger_dalle_directe=downloader,
            dl_workers_effectif=terrain_download.dl_workers_effectif,
            hms=lambda _seconds: "0s",
            laz_prof_resume=lambda wall, workers, parallel: events.append(
                ("profile", workers, parallel, wall >= 0)
            ),
            ecrire_dalles_zone=write_manifest,
            creer_fichiers=register,
            thread_pool_executor=ThreadPoolExecutor,
            as_completed=as_completed,
            time=__import__("time"),
        )

    def test_worker_policy_never_exceeds_provider_cap(self):
        self.assertEqual(terrain_download.dl_workers_effectif(8, 3, 6), 3)
        self.assertEqual(terrain_download.dl_workers_effectif(2, 3, 3), 3)
        self.assertEqual(terrain_download.dl_workers_effectif(2, None, 5), 5)

    def test_each_provider_mode_routes_and_persists_the_same_tile(self):
        modes = (
            ("direct", False, False),
            ("cog", True, False),
            ("copc", False, True),
        )
        for name, cog, copc in modes:
            with self.subTest(mode=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                tiles = root / "tiles"
                project = root / "project"
                tiles.mkdir()
                project.mkdir()
                events = []
                provider = SimpleNamespace(
                    COG_WINDOWED=cog,
                    COPC_WINDOWED=copc,
                    DOWNLOAD_WORKERS_MAX=2,
                )
                dependencies = self._dependencies(provider, events)
                terrain_download.telecharger_dalles_zone(
                    {"tile.tif": "https://invalid/tile"},
                    (1, 2, 3, 4),
                    tiles,
                    project,
                    self._args(workers=8, laz_parallel=4),
                    quiet=True,
                    dependances=dependencies,
                )
                download = next(event for event in events if event[0] == "download")
                if name == "direct":
                    self.assertEqual(download[2], (False, False))
                else:
                    self.assertEqual(download[2], ((1, 2, 3, 4), False))
                manifest = next(event for event in events if event[0] == "manifest")
                self.assertEqual(manifest[3], ("tile.tif",))
                registered = next(event for event in events if event[0] == "register")
                self.assertEqual(registered[1], (tiles / "tile.tif",))
                profile = next(event for event in events if event[0] == "profile")
                self.assertEqual(profile[1:3], (2, 4))

    def test_error_stops_before_manifest_and_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tiles = root / "tiles"
            project = root / "project"
            tiles.mkdir()
            project.mkdir()
            events = []
            dependencies = self._dependencies(
                SimpleNamespace(COG_WINDOWED=False, COPC_WINDOWED=False),
                events,
                result="erreur",
            )
            with self.assertRaises(RuntimeError):
                terrain_download.telecharger_dalles_zone(
                    {"tile.tif": "https://invalid/tile"},
                    (0, 0, 1, 1),
                    tiles,
                    project,
                    self._args(),
                    quiet=True,
                    dependances=dependencies,
                )
            self.assertFalse(any(event[0] == "manifest" for event in events))
            self.assertFalse(any(event[0] == "register" for event in events))

    def test_cached_tile_and_cloud_are_registered_without_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tiles = root / "tiles"
            project = root / "project"
            tiles.mkdir()
            project.mkdir()
            tile = tiles / "tile.tif"
            cloud = tiles / "tile.laz"
            tile.write_bytes(b"x" * 32)
            cloud.write_bytes(b"cloud")
            events = []
            provider = SimpleNamespace(
                COG_WINDOWED=False,
                COPC_WINDOWED=False,
                cloud_path=lambda _tile: cloud,
            )
            dependencies = self._dependencies(provider, events)
            terrain_download.telecharger_dalles_zone(
                {"tile.tif": "https://invalid/tile"},
                (0, 0, 1, 1),
                tiles,
                project,
                self._args(),
                quiet=True,
                dependances=dependencies,
            )
            self.assertFalse(any(event[0] == "download" for event in events))
            registered = next(event for event in events if event[0] == "register")
            self.assertEqual(set(registered[1]), {tile, cloud})

    def test_each_overwrite_flag_forces_cached_direct_download(self):
        for flag in ("telechargement_forcer", "telechargement_ecraser"):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                tile = root / "tile.tif"
                tile.write_bytes(b"cached" * 8)
                events = []
                dependencies = self._dependencies(
                    SimpleNamespace(COG_WINDOWED=False, COPC_WINDOWED=False),
                    events,
                )
                terrain_download.telecharger_dalles_zone(
                    {"tile.tif": "https://invalid/tile"},
                    (0, 0, 1, 1),
                    root,
                    root,
                    self._args(
                        **{flag: True}, telechargement_compresser=True
                    ),
                    quiet=True,
                    dependances=dependencies,
                )
                download = next(
                    event for event in events if event[0] == "download"
                )
                self.assertEqual(download[2], (True, True))

    def test_absent_tile_is_non_fatal_but_not_persisted(self):
        events = []
        dependencies = self._dependencies(
            SimpleNamespace(COG_WINDOWED=False, COPC_WINDOWED=False),
            events,
            result="absent",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            terrain_download.telecharger_dalles_zone(
                {"tile.tif": "https://invalid/tile"},
                (0, 0, 1, 1),
                root,
                root,
                self._args(),
                quiet=True,
                dependances=dependencies,
            )
        self.assertFalse(any(event[0] == "manifest" for event in events))
        registered = next(event for event in events if event[0] == "register")
        self.assertEqual(registered[1], ())

    def test_unsafe_remote_name_is_dropped_before_path_resolution(self):
        events = []
        dependencies = self._dependencies(
            SimpleNamespace(COG_WINDOWED=False, COPC_WINDOWED=False), events
        )
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(
            io.StringIO()
        ) as output:
            root = Path(tmp)
            terrain_download.telecharger_dalles_zone(
                {"../escape.tif": "https://invalid/escape"},
                (0, 0, 1, 1),
                root,
                root,
                self._args(),
                quiet=True,
                dependances=dependencies,
            )
        self.assertIn("unsafe name", output.getvalue())
        self.assertFalse(any(event[0] == "download" for event in events))

    def test_inventory_header_checks_bbox_provider_and_accepts_legacy(self):
        bbox = (1.2, 2.2, 3.8, 4.8)
        header = terrain_download.dalles_zone_entete(bbox, "provider-a")
        self.assertEqual(
            header,
            "# bbox:1,2,4,5\n# provider:provider-a",
        )
        self.assertTrue(
            terrain_download.dalles_zone_hdr_ok(
                header.splitlines(), bbox, "provider-a"
            )
        )
        self.assertFalse(
            terrain_download.dalles_zone_hdr_ok(
                header.splitlines(), bbox, "provider-b"
            )
        )
        self.assertTrue(
            terrain_download.dalles_zone_hdr_ok(
                ["# bbox:1,2,4,5", "tile.tif"], bbox, "provider-b"
            )
        )
        self.assertFalse(
            terrain_download.dalles_zone_hdr_ok(
                ["# bbox:0,0,0,0"], bbox, "provider-a"
            )
        )

    def test_inventory_listing_uses_matching_manifest_then_expected_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tiles = root / "tiles"
            project = root / "project"
            tiles.mkdir()
            project.mkdir()
            (tiles / "manifest.tif").write_bytes(b"m" * 20)
            (tiles / "expected.tif").write_bytes(b"e" * 20)
            inventory = project / "dalles_zone.txt"
            inventory.write_text(
                "# bbox:0,0,1,1\n# provider:p\nmanifest.tif\n",
                encoding="utf-8",
            )

            def list_with(valid_header):
                return terrain_download.lister_dalles_zone(
                    ["expected.tif"],
                    tiles,
                    project,
                    (0, 0, 1, 1),
                    hdr_ok=lambda _lines, _bbox: valid_header,
                    chemin_dalle=lambda folder, name: Path(folder) / name,
                    seuil_dalle_valide=10,
                )

            self.assertEqual(list_with(True), [tiles / "manifest.tif"])
            self.assertEqual(list_with(False), [tiles / "expected.tif"])

    def test_inventory_listing_skips_invalid_paths_and_small_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = root / "valid.tif"
            small = root / "small.tif"
            valid.write_bytes(b"v" * 20)
            small.write_bytes(b"x")

            def resolve(_folder, name):
                if name == "unsafe.tif":
                    raise ValueError("unsafe")
                if name == "io.tif":
                    raise OSError("io")
                return root / name

            result = terrain_download.lister_dalles_zone(
                ["unsafe.tif", "io.tif", "small.tif", "valid.tif"],
                root,
                root / "missing-project",
                (0, 0, 1, 1),
                hdr_ok=mock.Mock(),
                chemin_dalle=resolve,
                seuil_dalle_valide=10,
            )
            self.assertEqual(result, [valid])

    def test_inventory_writer_sorts_deduplicates_and_registers(self):
        writes = []
        registered = []
        terrain_download.ecrire_dalles_zone(
            "inventory.txt",
            (0, 1, 2, 3),
            ["b.tif", "a.tif", "b.tif"],
            provider_code="p",
            ecrire_texte_atomique=lambda path, content: writes.append(
                (path, content)
            ),
            creer_fichier=registered.append,
        )
        self.assertEqual(
            writes,
            [
                (
                    "inventory.txt",
                    "# bbox:0,1,2,3\n# provider:p\na.tif\nb.tif",
                )
            ],
        )
        self.assertEqual(registered, [Path("inventory.txt")])

    def test_inventory_facades_keep_signatures_and_late_dependencies(self):
        provider = SimpleNamespace(CODE="late-provider")
        atomic = mock.Mock()
        register = mock.Mock()
        path_resolver = mock.Mock()
        sentinel = object()
        with mock.patch.object(L, "PROVIDER", provider), mock.patch.object(
            L, "_ecrire_texte_atomique", atomic
        ), mock.patch.object(L, "_creer_fichier", register), mock.patch.object(
            L, "chemin_dalle", path_resolver
        ), mock.patch.object(
            L, "_lister_dalles_zone_impl", return_value=sentinel
        ) as listing, mock.patch.object(
            L, "_ecrire_dalles_zone_impl"
        ) as writing:
            result = L._lister_dalles_zone([], Path("tiles"), Path("project"), (0, 0, 1, 1))
            L._ecrire_dalles_zone("zone.txt", (0, 0, 1, 1), ["a.tif"])
        self.assertIs(result, sentinel)
        self.assertIs(listing.call_args.kwargs["hdr_ok"], L._dalles_zone_hdr_ok)
        self.assertIs(listing.call_args.kwargs["chemin_dalle"], path_resolver)
        self.assertEqual(writing.call_args.kwargs["provider_code"], "late-provider")
        self.assertIs(writing.call_args.kwargs["ecrire_texte_atomique"], atomic)
        self.assertIs(writing.call_args.kwargs["creer_fichier"], register)
        self.assertEqual(
            str(inspect.signature(L._lister_dalles_zone)),
            "(noms_attendus, dossier_dalles, dossier_ville, bbox)",
        )
        self.assertEqual(
            str(inspect.signature(L._ecrire_dalles_zone)),
            "(path, bbox, noms)",
        )
        self.assertEqual(str(inspect.signature(L._dalles_zone_entete)), "(bbox)")
        self.assertEqual(
            str(inspect.signature(L._dalles_zone_hdr_ok)), "(lignes, bbox)"
        )

    def test_direct_download_facade_rebuilds_all_runtime_dependencies(self):
        marker = object()
        provider = SimpleNamespace()
        path_resolver = mock.Mock()
        stage = mock.Mock()
        downloader = mock.Mock()
        validator = mock.Mock()
        with mock.patch.object(L, "PROVIDER", provider), mock.patch.object(
            L, "chemin_dalle", path_resolver
        ), mock.patch.object(L, "_stage_dalle_part", stage), mock.patch.object(
            L, "_download_to_tmp", downloader
        ), mock.patch.object(L, "_valider_tif_dalle", validator), mock.patch.object(
            L, "_telecharger_dalle_directe_impl", return_value=marker
        ) as implementation:
            result = L.telecharger_dalle_directe(
                "tile.tif",
                "https://example.invalid/tile",
                Path("tiles"),
                ecraser=True,
                compresser=True,
            )
        self.assertIs(result, marker)
        dependencies = implementation.call_args.kwargs["dependances"]
        self.assertIs(dependencies.provider, provider)
        self.assertIs(dependencies.chemin_dalle, path_resolver)
        self.assertIs(dependencies.stage_dalle_part, stage)
        self.assertIs(dependencies.download_to_tmp, downloader)
        self.assertIs(dependencies.valider_tif_dalle, validator)
        self.assertIs(
            dependencies.lier_nuage_existant_au_stage,
            L._lier_nuage_existant_au_stage,
        )
        self.assertIs(
            dependencies.comprimer_dalle_deflate, L._comprimer_dalle_deflate
        )
        self.assertIs(dependencies.publier_nuage_stage, L._publier_nuage_stage)
        self.assertEqual(
            str(inspect.signature(L.telecharger_dalle_directe)),
            "(nom, url_wms, dossier, ecraser=False, compresser=False)",
        )
        self.assertEqual(
            str(inspect.signature(L._stage_dalle_part)), "(chemin_final)"
        )
        self.assertEqual(
            str(inspect.signature(L._chemins_nuage_stage)),
            "(chemin_final, chemin_part)",
        )

    def test_copc_facades_rebuild_all_runtime_dependencies(self):
        from providers import common

        marker = object()
        provider = SimpleNamespace()
        path_resolver = mock.Mock()
        transform = mock.Mock()
        copc_reader = mock.Mock()
        stage = mock.Mock()
        validator = mock.Mock()
        publish_cloud = mock.Mock()
        register = mock.Mock()
        lock = object()
        post_fetch = mock.Mock()
        with mock.patch.object(L, "PROVIDER", provider), mock.patch.object(
            L, "chemin_dalle", path_resolver
        ), mock.patch.object(
            L, "_bbox_enveloppe_transform", transform
        ), mock.patch.object(
            common, "copc_window_to_las", copc_reader
        ), mock.patch.object(L, "_stage_dalle_part", stage), mock.patch.object(
            L, "_valider_tif_dalle", validator
        ), mock.patch.object(
            L, "_publier_nuage_stage", publish_cloud
        ), mock.patch.object(L, "_creer_fichier", register), mock.patch.object(
            L, "_telecharger_copc_fenetre_impl", return_value=marker
        ) as implementation:
            result = L.telecharger_copc_fenetre(
                "tile.tif",
                "https://example.invalid/copc",
                Path("tiles"),
                (1, 2, 3, 4),
                ecraser=True,
            )
        self.assertIs(result, marker)
        dependencies = implementation.call_args.kwargs["dependances"]
        self.assertIs(dependencies.provider, provider)
        self.assertIs(dependencies.chemin_dalle, path_resolver)
        self.assertIs(dependencies.bbox_enveloppe_transform, transform)
        self.assertIs(dependencies.copc_window_to_las, copc_reader)
        self.assertIs(dependencies.stage_dalle_part, stage)
        self.assertIs(dependencies.valider_tif_dalle, validator)
        self.assertIs(dependencies.publier_nuage_stage, publish_cloud)
        self.assertIs(dependencies.creer_fichier, register)
        self.assertIs(dependencies.copc_post_fetch_crs, L._copc_post_fetch_crs)

        with mock.patch.object(L, "PROVIDER", provider), mock.patch.object(
            L, "_copc_crs_lock", lock
        ), mock.patch.object(
            L, "_post_fetch_si_besoin", post_fetch
        ), mock.patch.object(
            L, "_copc_post_fetch_crs_impl", return_value=marker
        ) as post_fetch_impl:
            self.assertIs(L._copc_post_fetch_crs(26917, "stage.tif"), marker)
        self.assertIs(post_fetch_impl.call_args.kwargs["provider"], provider)
        self.assertIs(post_fetch_impl.call_args.kwargs["lock"], lock)
        self.assertIs(
            post_fetch_impl.call_args.kwargs["post_fetch_si_besoin"], post_fetch
        )
        self.assertEqual(
            str(inspect.signature(L.telecharger_copc_fenetre)),
            "(nom, url, dossier_dalles, bbox, ecraser=False)",
        )
        self.assertEqual(
            str(inspect.signature(L._copc_post_fetch_crs)),
            "(epsg, chemin_part)",
        )

    def test_cog_facades_rebuild_all_runtime_dependencies(self):
        marker = object()
        provider = SimpleNamespace()
        path_resolver = mock.Mock()
        stage = mock.Mock()
        cache = mock.Mock()
        transformer = mock.Mock()
        bbox_transform = mock.Mock()
        validator = mock.Mock()
        register = mock.Mock()
        with mock.patch.object(L, "PROVIDER", provider), mock.patch.object(
            L, "chemin_dalle", path_resolver
        ), mock.patch.object(L, "_stage_dalle_part", stage), mock.patch.object(
            L, "_cog_cache_couvre", cache
        ), mock.patch.object(L, "_get_transformer", transformer), mock.patch.object(
            L, "_valider_tif_dalle", validator
        ), mock.patch.object(L, "_creer_fichier", register), mock.patch.object(
            L, "_telecharger_cog_fenetre_impl", return_value=marker
        ) as implementation:
            result = L.telecharger_cog_fenetre(
                "tile.tif",
                "https://example.invalid/cog.tif",
                Path("tiles"),
                (1, 2, 3, 4),
                ecraser=True,
            )
        self.assertIs(result, marker)
        dependencies = implementation.call_args.kwargs["dependances"]
        self.assertIs(dependencies.provider, provider)
        self.assertIs(dependencies.chemin_dalle, path_resolver)
        self.assertIs(dependencies.stage_dalle_part, stage)
        self.assertIs(dependencies.cog_cache_couvre, cache)
        self.assertIs(dependencies.get_transformer, transformer)
        self.assertIs(dependencies.valider_tif_dalle, validator)
        self.assertIs(dependencies.creer_fichier, register)
        self.assertEqual(dependencies.max_cog_window_px, L._MAX_COG_WINDOW_PX)

        with mock.patch.object(L, "PROVIDER", provider), mock.patch.object(
            L, "_get_transformer", transformer
        ), mock.patch.object(
            L, "_bbox_enveloppe_transform", bbox_transform
        ), mock.patch.object(
            L, "_cog_cache_couvre_impl", return_value=marker
        ) as cache_impl:
            self.assertIs(L._cog_cache_couvre("tile.tif", (1, 2, 3, 4)), marker)
        self.assertIs(cache_impl.call_args.kwargs["provider"], provider)
        self.assertIs(
            cache_impl.call_args.kwargs["get_transformer"], transformer
        )
        self.assertIs(
            cache_impl.call_args.kwargs["bbox_enveloppe_transform"],
            bbox_transform,
        )
        self.assertEqual(
            str(inspect.signature(L.telecharger_cog_fenetre)),
            "(nom, url, dossier_dalles, bbox, ecraser=False)",
        )
        self.assertEqual(
            str(inspect.signature(L._cog_cache_couvre)),
            "(chemin, bbox_natif)",
        )

    def test_historical_facade_rebuilds_current_dependencies(self):
        marker = object()
        direct = mock.Mock()
        provider = SimpleNamespace()
        args = self._args()
        with mock.patch.object(L, "PROVIDER", provider), mock.patch.object(
            L, "telecharger_dalle_directe", direct
        ), mock.patch.object(
            L, "_telecharger_dalles_zone_impl", return_value=marker
        ) as implementation:
            result = L._telecharger_dalles_zone(
                {}, (0, 0, 1, 1), Path("tiles"), Path("project"), args, quiet=True
            )
        self.assertIs(result, marker)
        dependencies = implementation.call_args.kwargs["dependances"]
        self.assertIs(dependencies.provider, provider)
        self.assertIs(dependencies.telecharger_dalle_directe, direct)
        self.assertIs(dependencies.dl_workers_effectif, L._dl_workers_effectif)
        self.assertIs(dependencies.chemin_dalle, L.chemin_dalle)
        self.assertEqual(
            str(inspect.signature(L._telecharger_dalles_zone)),
            "(dalles_dict, bbox, dossier_dalles, dossier_ville, args, quiet=False)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
