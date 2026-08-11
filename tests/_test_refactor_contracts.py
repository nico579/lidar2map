"""Contrats de caractérisation à préserver pendant la modularisation.

Ces tests portent sur les façades et conventions entre composants. Ils ne
testent volontairement ni le réseau ni le détail des algorithmes scientifiques,
déjà couverts par les autres suites.
"""

from __future__ import annotations

import contextlib
import inspect
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "lidar2map.py"
sys.path.insert(0, str(ROOT))

import lidar2map as L  # noqa: E402
import _mbtiles_lidar as mbtiles_lidar  # noqa: E402
import _mbtiles_wmts as mbtiles_wmts  # noqa: E402
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
