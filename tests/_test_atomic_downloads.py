"""Régressions ciblées : publication atomique des téléchargements.

Usage :
    python Tests/_test_atomic_downloads.py
"""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
APP = Path(__file__).resolve().parent.parent / "lidar2map.py"
sys.path.insert(0, str(APP.parent))
SPEC = importlib.util.spec_from_file_location("l2m_atomic_downloads", APP)
L = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = L
SPEC.loader.exec_module(L)


class AtomicDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_ctx.name)
        self.old_provider = L.PROVIDER

    def tearDown(self):
        L.PROVIDER = self.old_provider
        self.tmp_ctx.cleanup()

    def _old_bytes(self):
        return b"OLD" * (L.SEUIL_DALLE_VALIDE // 3 + 2)

    def _assert_no_part(self):
        self.assertEqual(list(self.tmp.rglob("*.part")), [])

    def test_http_urlopen_applies_default_and_overridden_headers(self):
        response = object()
        with mock.patch.object(
                L.urllib.request, "urlopen", return_value=response
        ) as ouvrir:
            self.assertIs(
                L._urlopen(
                    "https://example.invalid/data",
                    headers={"Authorization": "Bearer secret"},
                    timeout=7,
                ),
                response,
            )

        request = ouvrir.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), L._HTTP_UA)
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertEqual(ouvrir.call_args.kwargs, {"timeout": 7})

        with mock.patch.object(L.urllib.request, "urlopen") as ouvrir:
            L._urlopen("https://example.invalid", {"User-Agent": "custom"})
        self.assertEqual(
            ouvrir.call_args.args[0].get_header("User-agent"), "custom"
        )

    def test_download_facade_reloads_urlopen_and_chunk_size(self):
        marker = object()
        replacement = mock.Mock(name="urlopen")
        with mock.patch.object(L, "_urlopen", replacement), mock.patch.object(
                L._http_helpers_impl,
                "telecharger_vers_tmp",
                return_value=marker,
        ) as implementation:
            self.assertIs(
                L._download_to_tmp("https://example.invalid", self.tmp / "x", (2, 9)),
                marker,
            )

        self.assertEqual(implementation.call_args.args[:2], (
            "https://example.invalid", self.tmp / "x"
        ))
        self.assertEqual(implementation.call_args.kwargs["timeout"], (2, 9))
        self.assertIs(implementation.call_args.kwargs["ouvrir_url"], replacement)
        self.assertEqual(
            implementation.call_args.kwargs["taille_bloc"], L.HTTP_CHUNK_SIZE
        )

    def test_stream_download_closes_response_and_rejects_truncation(self):
        class Response:
            def __init__(self, body, announced):
                self.body = body
                self.position = 0
                self.headers = {
                    "content-type": "image/tiff",
                    "content-length": str(announced),
                }
                self.closed = False

            def read(self, size):
                block = self.body[self.position:self.position + size]
                self.position += len(block)
                return block

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.closed = True

        response = Response(b"12345", announced=8)
        timeouts = []

        def ouvrir(_url, timeout):
            timeouts.append(timeout)
            return response

        with mock.patch.object(L, "_urlopen", side_effect=ouvrir):
            with self.assertRaisesRegex(IOError, "Transfert tronqué"):
                L._download_to_tmp(
                    "https://example.invalid", self.tmp / "truncated.part", (3, 12)
                )

        self.assertEqual(timeouts, [12])
        self.assertTrue(response.closed)
        self.assertEqual((self.tmp / "truncated.part").read_bytes(), b"12345")

    def test_stream_download_maps_http_errors(self):
        def erreur(code):
            return urllib.error.HTTPError(
                "https://example.invalid", code, "error", None, None
            )

        with mock.patch.object(L, "_urlopen", side_effect=erreur(404)):
            self.assertEqual(
                L._download_to_tmp("https://example.invalid", self.tmp / "404.part"),
                0,
            )
        with mock.patch.object(L, "_urlopen", side_effect=erreur(503)):
            with self.assertRaisesRegex(IOError, "HTTP 503"):
                L._download_to_tmp("https://example.invalid", self.tmp / "503.part")

    def test_stream_download_only_maps_explicit_provider_500_to_absent(self):
        error = urllib.error.HTTPError(
            "https://example.invalid", 500, "Internal Server Error", None, None
        )

        with mock.patch.object(L, "_urlopen", side_effect=error):
            with self.assertRaisesRegex(IOError, "HTTP 500"):
                L._download_to_tmp(
                    "https://example.invalid", self.tmp / "default-500.part"
                )

        with mock.patch.object(L, "_urlopen", side_effect=error):
            self.assertEqual(
                L._download_to_tmp(
                    "https://example.invalid",
                    self.tmp / "provider-500.part",
                    codes_absence=frozenset({404, 500}),
                ),
                0,
            )

    def test_direct_download_forwards_provider_no_coverage_codes(self):
        from providers import gb_england

        codes_seen = []

        def download(_url, _path, timeout=60, **kwargs):
            codes_seen.append(kwargs.get("codes_absence"))
            return 0

        L.PROVIDER = gb_england
        with mock.patch.object(L, "_download_to_tmp", side_effect=download), \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_dalle_directe(
                "sea.tif", "https://example.invalid/500", self.tmp
            )

        self.assertEqual(result, "absent")
        self.assertEqual(codes_seen, [gb_england.NO_COVERAGE_HTTP_CODES])
        self._assert_no_part()

    def test_direct_all_hooks_run_in_part_directory_then_publish(self):
        nom = "tile.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)
        seen = []

        def download(_url, path, timeout=60, **_kwargs):
            path = Path(path)
            seen.append(("download", path))
            self.assertTrue(path.parent.name.endswith(".part"))
            self.assertEqual(path.name, nom)
            self.assertEqual(final.read_bytes(), old)
            path.write_bytes(b"RAW")
            return L.SEUIL_DALLE_VALIDE + 1

        def post_fetch(path):
            path = Path(path)
            seen.append(("post_fetch", path))
            self.assertTrue(path.parent.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), old)
            path.write_bytes(b"FETCHED")

        def post_download(path):
            path = Path(path)
            seen.append(("post_download", path))
            self.assertTrue(path.parent.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), old)
            path.write_bytes(b"HOOKED")

        def compress(path):
            path = Path(path)
            seen.append(("compress", path))
            self.assertTrue(path.parent.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), old)
            path.write_bytes(b"COMPRESSED")

        L.PROVIDER = SimpleNamespace(
            subdir_from_name=lambda _nom: "",
            post_download=post_download,
        )
        with mock.patch.object(L, "_download_to_tmp", side_effect=download), \
             mock.patch.object(L, "_post_fetch_si_besoin",
                               side_effect=post_fetch), \
             mock.patch.object(L, "_comprimer_dalle_deflate",
                               side_effect=compress), \
             mock.patch.object(L, "_valider_tif_dalle",
                               side_effect=lambda p: Path(p).exists()), \
             mock.patch.object(L, "_creer_fichier"), \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_dalle_directe(
                nom, "https://example.invalid/tile", self.tmp,
                ecraser=True, compresser=True)

        self.assertEqual(result, "ok")
        self.assertEqual(final.read_bytes(), b"COMPRESSED")
        self.assertEqual(
            [name for name, _path in seen],
            ["download", "post_fetch", "post_download", "compress"])
        self._assert_no_part()

    def test_direct_failure_keeps_previous_final(self):
        nom = "tile.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)

        def download(_url, path, timeout=60, **_kwargs):
            Path(path).write_bytes(b"RAW")
            return L.SEUIL_DALLE_VALIDE + 1

        def post_fetch(path):
            Path(path).write_bytes(b"VALID_STAGE")

        def fail_post_download(path):
            self.assertTrue(Path(path).parent.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), old)
            raise RuntimeError("reprojection interrompue")

        L.PROVIDER = SimpleNamespace(
            subdir_from_name=lambda _nom: "",
            post_download=fail_post_download,
        )
        with mock.patch.object(L, "_download_to_tmp", side_effect=download), \
             mock.patch.object(L, "_post_fetch_si_besoin",
                               side_effect=post_fetch), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=True), \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_dalle_directe(
                nom, "https://example.invalid/tile", self.tmp,
                ecraser=True)

        self.assertEqual(result, "erreur")
        self.assertEqual(final.read_bytes(), old)
        self._assert_no_part()

    def test_pre_download_receives_logical_tif_inside_part(self):
        nom = "tile.tif"
        final = self.tmp / nom
        final.write_bytes(b"invalid-old")

        def pre_download(path):
            path = Path(path)
            self.assertEqual(path.name, nom)
            self.assertTrue(path.parent.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), b"invalid-old")
            path.write_bytes(b"FROM_CACHE")
            return True

        L.PROVIDER = SimpleNamespace(
            subdir_from_name=lambda _nom: "",
            pre_download=pre_download,
        )
        with mock.patch.object(
                L, "_download_to_tmp",
                side_effect=AssertionError("réseau appelé malgré le cache")), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=True), \
             mock.patch.object(L, "_creer_fichier"), \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_dalle_directe(
                nom, "https://example.invalid/tile", self.tmp)

        self.assertEqual(result, "ok")
        self.assertEqual(final.read_bytes(), b"FROM_CACHE")
        self._assert_no_part()

    def test_stage_directory_is_removed_on_keyboard_interrupt(self):
        final = self.tmp / "tile.tif"
        final.write_bytes(b"OLD")
        with self.assertRaises(KeyboardInterrupt):
            with L._stage_dalle_part(final) as staged:
                self.assertEqual(staged.name, final.name)
                self.assertTrue(staged.parent.name.endswith(".part"))
                staged.write_bytes(b"NEW")
                staged.with_suffix(".aux.xml").write_text("sidecar")
                raise KeyboardInterrupt
        self.assertEqual(final.read_bytes(), b"OLD")
        self._assert_no_part()

    def test_direct_valid_cache_skips_every_staging_and_network_effect(self):
        final = self.tmp / "tile.tif"
        final.write_bytes(self._old_bytes())
        L.PROVIDER = SimpleNamespace(subdir_from_name=lambda _nom: "")
        with mock.patch.object(
            L, "_stage_dalle_part", side_effect=AssertionError("staging")
        ), mock.patch.object(
            L, "_download_to_tmp", side_effect=AssertionError("network")
        ), mock.patch.object(L, "_creer_fichier") as register:
            result = L.telecharger_dalle_directe(
                "tile.tif", "https://example.invalid/tile", self.tmp
            )
        self.assertEqual(result, "skip")
        register.assert_not_called()

    def test_direct_transient_failure_retries_then_publishes(self):
        final = self.tmp / "tile.tif"
        attempts = []

        def download(_url, path, timeout=60, **_kwargs):
            attempts.append(Path(path))
            if len(attempts) == 1:
                raise OSError("temporary")
            Path(path).write_bytes(b"VALID")
            return L.SEUIL_DALLE_VALIDE + 1

        L.PROVIDER = SimpleNamespace(subdir_from_name=lambda _nom: "")
        with mock.patch.object(L, "_download_to_tmp", side_effect=download), \
             mock.patch.object(L, "_post_fetch_si_besoin"), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=True), \
             mock.patch.object(L, "_creer_fichier"), \
             mock.patch.object(L.time, "sleep") as sleep, \
             mock.patch.object(L, "MAX_TENTATIVES", 3):
            result = L.telecharger_dalle_directe(
                "tile.tif", "https://example.invalid/tile", self.tmp
            )
        self.assertEqual(result, "ok")
        self.assertEqual(len(attempts), 2)
        sleep.assert_called_once_with(L.DELAI_RETRY)
        self.assertEqual(final.read_bytes(), b"VALID")
        self._assert_no_part()

    def test_direct_cloud_cache_is_linked_for_hook_without_republication(self):
        final = self.tmp / "tile.tif"
        cloud = final.with_suffix(".laz")
        cloud.write_bytes(b"CLOUD")
        seen = []

        def pre_download(path):
            staged_cloud = Path(path).with_suffix(".laz")
            seen.append(staged_cloud.read_bytes())
            Path(path).write_bytes(b"FROM_CLOUD")
            return True

        L.PROVIDER = SimpleNamespace(
            subdir_from_name=lambda _nom: "",
            cloud_path=lambda path: Path(path).with_suffix(".laz"),
            pre_download=pre_download,
        )
        with mock.patch.object(
                L, "_download_to_tmp",
                side_effect=AssertionError("network called despite cloud")), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=True), \
             mock.patch.object(L, "_creer_fichier"), \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_dalle_directe(
                "tile.tif", "https://example.invalid/tile", self.tmp
            )
        self.assertEqual(result, "ok")
        self.assertEqual(seen, [b"CLOUD"])
        self.assertEqual(cloud.read_bytes(), b"CLOUD")
        self.assertEqual(final.read_bytes(), b"FROM_CLOUD")
        self._assert_no_part()

    def test_direct_small_server_error_retries_but_plain_payload_is_absent(self):
        calls = []

        def download(url, path, timeout=60, **_kwargs):
            calls.append(url)
            if url.endswith("json"):
                Path(path).write_bytes(b'{"error":"temporary"}')
            else:
                Path(path).write_bytes(b"outside coverage")
            return 20

        L.PROVIDER = SimpleNamespace(subdir_from_name=lambda _nom: "")
        with mock.patch.object(L, "_download_to_tmp", side_effect=download), \
             mock.patch.object(L.time, "sleep"), \
             mock.patch.object(L, "MAX_TENTATIVES", 2):
            server_error = L.telecharger_dalle_directe(
                "error.tif", "https://example.invalid/json", self.tmp
            )
            absent = L.telecharger_dalle_directe(
                "absent.tif", "https://example.invalid/plain", self.tmp
            )
        self.assertEqual(server_error, "erreur")
        self.assertEqual(absent, "absent")
        self.assertEqual(calls.count("https://example.invalid/json"), 2)
        self.assertEqual(calls.count("https://example.invalid/plain"), 1)
        self._assert_no_part()

    def test_direct_invalid_compressed_stage_keeps_previous_final(self):
        final = self.tmp / "tile.tif"
        old = self._old_bytes()
        final.write_bytes(old)

        def download(_url, path, timeout=60, **_kwargs):
            Path(path).write_bytes(b"RAW")
            return L.SEUIL_DALLE_VALIDE + 1

        def compress(path):
            Path(path).write_bytes(b"BROKEN")

        validations = iter((True, False))
        L.PROVIDER = SimpleNamespace(subdir_from_name=lambda _nom: "")
        with mock.patch.object(L, "_download_to_tmp", side_effect=download), \
             mock.patch.object(L, "_post_fetch_si_besoin"), \
             mock.patch.object(L, "_comprimer_dalle_deflate", side_effect=compress), \
             mock.patch.object(
                 L, "_valider_tif_dalle", side_effect=lambda _path: next(validations)
             ), mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_dalle_directe(
                "tile.tif",
                "https://example.invalid/tile",
                self.tmp,
                ecraser=True,
                compresser=True,
            )
        self.assertEqual(result, "erreur")
        self.assertEqual(final.read_bytes(), old)
        self._assert_no_part()

    def test_direct_new_cloud_is_published_only_after_tif_validation(self):
        final = self.tmp / "tile.tif"
        cloud = final.with_suffix(".laz")

        def download(_url, path, timeout=60, **_kwargs):
            Path(path).write_bytes(b"RAW")
            return L.SEUIL_DALLE_VALIDE + 1

        def post_fetch(path):
            Path(path).write_bytes(b"VALID_TIF")
            Path(path).with_suffix(".laz").write_bytes(b"NEW_CLOUD")

        L.PROVIDER = SimpleNamespace(
            subdir_from_name=lambda _nom: "",
            cloud_path=lambda path: Path(path).with_suffix(".laz"),
        )
        with mock.patch.object(L, "_download_to_tmp", side_effect=download), \
             mock.patch.object(L, "_post_fetch_si_besoin", side_effect=post_fetch), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=True), \
             mock.patch.object(L, "_creer_fichier"), \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_dalle_directe(
                "tile.tif", "https://example.invalid/tile", self.tmp
            )
        self.assertEqual(result, "ok")
        self.assertEqual(final.read_bytes(), b"VALID_TIF")
        self.assertEqual(cloud.read_bytes(), b"NEW_CLOUD")
        self._assert_no_part()

    def test_direct_404_exact_remains_error_grid_remains_absent(self):
        class Provider:
            def __init__(self, exact):
                self.DISCOVER_EXACT = exact

            @staticmethod
            def subdir_from_name(_nom):
                return ""

        with mock.patch.object(L, "_download_to_tmp", return_value=0), \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            L.PROVIDER = Provider(True)
            exact = L.telecharger_dalle_directe(
                "exact.tif", "https://example.invalid/404", self.tmp)
            L.PROVIDER = Provider(False)
            grid = L.telecharger_dalle_directe(
                "grid.tif", "https://example.invalid/404", self.tmp)

        self.assertEqual(exact, "erreur")
        self.assertEqual(grid, "absent")
        self._assert_no_part()

    def test_copc_failure_keeps_previous_final(self):
        from providers import common

        nom = "copc.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)
        paths = []

        def copc(_url, _bbox, path):
            path = Path(path)
            paths.append(path)
            self.assertEqual(path.name, nom)
            self.assertTrue(path.parent.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), old)
            path.write_bytes(b"LASF")
            return 60_000, 26917

        def fail_post_fetch(path):
            self.assertTrue(Path(path).parent.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), old)
            raise RuntimeError("conversion COPC interrompue")

        L.PROVIDER = SimpleNamespace(
            subdir_from_name=lambda _nom: "",
            set_crs=lambda _epsg: None,
        )
        with mock.patch.object(common, "copc_window_to_las",
                               side_effect=copc), \
             mock.patch.object(
                 L, "_bbox_enveloppe_transform",
                 side_effect=lambda _fn, *coords: coords), \
             mock.patch.object(L, "_post_fetch_si_besoin",
                               side_effect=fail_post_fetch):
            result = L.telecharger_copc_fenetre(
                nom, "https://example.invalid/copc", self.tmp,
                (1, 2, 3, 4), ecraser=True)

        self.assertEqual(result, "erreur")
        self.assertEqual(final.read_bytes(), old)
        self.assertEqual(len(paths), 1)
        self._assert_no_part()

    def test_copc_success_signs_transforms_validates_then_publishes(self):
        from providers import common

        nom = "copc.tif"
        final = self.tmp / nom
        events = []

        class Provider:
            SEUIL_DALLE_VALIDE = 7

            @staticmethod
            def subdir_from_name(_nom):
                return ""

            @staticmethod
            def sign_url(url):
                events.append(("sign", url))
                return url + "?signed=1"

            @staticmethod
            def set_crs(epsg):
                events.append(("crs", epsg))

        def transform(_fn, *coords):
            events.append(("transform", coords))
            return (10.0, 20.0, 30.0, 40.0)

        def copc(url, bbox, path):
            events.append(("copc", url, bbox))
            Path(path).write_bytes(b"LASF")
            return 60_000, 26917

        def post_fetch(path):
            events.append(("post_fetch", Path(path).name))
            Path(path).write_bytes(self._old_bytes())

        def validate(path):
            events.append(("validate", Path(path).name))
            return True

        def publish_cloud(final_path, stage_path):
            events.append(("cloud", Path(final_path).name, Path(stage_path).name))

        def register(path):
            events.append(("register", Path(path).name))

        L.PROVIDER = Provider()
        with mock.patch.object(
                common, "copc_window_to_las", side_effect=copc), \
             mock.patch.object(
                 L, "_bbox_enveloppe_transform", side_effect=transform), \
             mock.patch.object(
                 L, "_post_fetch_si_besoin", side_effect=post_fetch), \
             mock.patch.object(L, "_valider_tif_dalle", side_effect=validate), \
             mock.patch.object(
                 L, "_publier_nuage_stage", side_effect=publish_cloud), \
             mock.patch.object(L, "_creer_fichier", side_effect=register):
            result = L.telecharger_copc_fenetre(
                nom, "https://example.invalid/copc", self.tmp,
                (1, 2, 3, 4))

        self.assertEqual(result, "ok")
        self.assertTrue(final.is_file())
        self.assertLess(events.index(("crs", 26917)),
                        events.index(("post_fetch", nom)))
        self.assertLess(events.index(("validate", nom)),
                        events.index(("cloud", nom, nom)))
        self.assertLess(events.index(("cloud", nom, nom)),
                        events.index(("register", nom)))
        self.assertIn(
            ("copc", "https://example.invalid/copc?signed=1",
             (10.0, 20.0, 30.0, 40.0)),
            events,
        )
        self._assert_no_part()

    def test_copc_quasi_empty_window_is_absent_without_conversion(self):
        from providers import common

        L.PROVIDER = SimpleNamespace(subdir_from_name=lambda _nom: "")
        with mock.patch.object(
                common, "copc_window_to_las", return_value=(49_999, 26917)), \
             mock.patch.object(
                 L, "_bbox_enveloppe_transform",
                 side_effect=lambda _fn, *coords: coords), \
             mock.patch.object(L, "_copc_post_fetch_crs") as convert, \
             mock.patch.object(L, "_valider_tif_dalle") as validate:
            result = L.telecharger_copc_fenetre(
                "empty.tif", "https://example.invalid/copc", self.tmp,
                (1, 2, 3, 4))

        self.assertEqual(result, "absent")
        convert.assert_not_called()
        validate.assert_not_called()
        self.assertFalse((self.tmp / "empty.tif").exists())
        self._assert_no_part()

    def test_copc_keyboard_interrupt_propagates_and_cleans_stage(self):
        from providers import common

        L.PROVIDER = SimpleNamespace(subdir_from_name=lambda _nom: "")
        with mock.patch.object(
                common, "copc_window_to_las",
                side_effect=KeyboardInterrupt), \
             mock.patch.object(
                 L, "_bbox_enveloppe_transform",
                 side_effect=lambda _fn, *coords: coords):
            with self.assertRaises(KeyboardInterrupt):
                L.telecharger_copc_fenetre(
                    "stop.tif", "https://example.invalid/copc", self.tmp,
                    (1, 2, 3, 4))

        self.assertFalse((self.tmp / "stop.tif").exists())
        self._assert_no_part()

    def test_cog_post_download_failure_keeps_previous_final(self):
        nom = "window.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)
        fake_rasterio, fake_windows = self._fake_rasterio(final, old)

        def fail_post_download(path):
            path = Path(path)
            self.assertEqual(path.name, nom)
            self.assertTrue(path.parent.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), old)
            raise RuntimeError("warp interrompu")

        L.PROVIDER = SimpleNamespace(
            CRS_NATIF="EPSG:2154",
            subdir_from_name=lambda _nom: "",
            post_download=fail_post_download,
        )
        with mock.patch.dict(
                sys.modules,
                {"rasterio": fake_rasterio,
                 "rasterio.windows": fake_windows}), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=True), \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_cog_fenetre(
                nom, "https://example.invalid/cog.tif", self.tmp,
                (1, 1, 3, 3), ecraser=True)

        self.assertEqual(result, "erreur")
        self.assertEqual(final.read_bytes(), old)
        self._assert_no_part()

    def test_cog_success_applies_gdal_hook_validates_and_publishes(self):
        nom = "window.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)
        fake_rasterio, fake_windows = self._fake_rasterio(final, old)
        events = []
        open_fake = fake_rasterio.open

        def open_record(path, mode=None, **kwargs):
            events.append(("open", str(path), mode))
            return open_fake(path, mode, **kwargs)

        def validate(path):
            events.append(("validate", Path(path).name))
            return True

        def post_download(path):
            events.append(("post", Path(path).name))

        fake_rasterio.open = open_record
        L.PROVIDER = SimpleNamespace(
            CRS_NATIF="EPSG:2154",
            subdir_from_name=lambda _nom: "",
            gdal_env_options=lambda: {"GDAL_HTTP_HEADERS": "X-Test: yes"},
            post_download=post_download,
        )
        with mock.patch.dict(
                sys.modules,
                {"rasterio": fake_rasterio,
                 "rasterio.windows": fake_windows}), \
             mock.patch.object(L, "_valider_tif_dalle", side_effect=validate), \
             mock.patch.object(L, "_creer_fichier") as register, \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_cog_fenetre(
                nom, "https://example.invalid/cog.tif", self.tmp,
                (1, 1, 3, 3), ecraser=True)

        self.assertEqual(result, "ok")
        self.assertEqual(final.read_bytes(), b"NEW_COG")
        self.assertEqual(
            [event[0] for event in events if event[0] in {"validate", "post"}],
            ["validate", "post", "validate"],
        )
        self.assertIn(("open", "/vsicurl/https://example.invalid/cog.tif", None),
                      events)
        register.assert_called_once_with(final)
        self._assert_no_part()

    def test_cog_non_intersection_is_absent_and_keeps_previous_final(self):
        nom = "outside.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)
        fake_rasterio, fake_windows = self._fake_rasterio(final, old)
        L.PROVIDER = SimpleNamespace(
            CRS_NATIF="EPSG:2154", subdir_from_name=lambda _nom: ""
        )
        with mock.patch.dict(
                sys.modules,
                {"rasterio": fake_rasterio,
                 "rasterio.windows": fake_windows}), \
             mock.patch.object(L, "_valider_tif_dalle") as validate, \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_cog_fenetre(
                nom, "https://example.invalid/cog.tif", self.tmp,
                (20, 20, 30, 30), ecraser=True)

        self.assertEqual(result, "absent")
        self.assertEqual(final.read_bytes(), old)
        validate.assert_not_called()
        self._assert_no_part()

    def test_cog_transient_open_failure_retries_then_publishes(self):
        nom = "retry.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)
        fake_rasterio, fake_windows = self._fake_rasterio(final, old)
        open_fake = fake_rasterio.open
        attempts = []

        def open_retry(path, mode=None, **kwargs):
            if mode != "w":
                attempts.append(str(path))
                if len(attempts) == 1:
                    raise OSError("temporary range failure")
            return open_fake(path, mode, **kwargs)

        fake_rasterio.open = open_retry
        L.PROVIDER = SimpleNamespace(
            CRS_NATIF="EPSG:2154", subdir_from_name=lambda _nom: ""
        )
        with mock.patch.dict(
                sys.modules,
                {"rasterio": fake_rasterio,
                 "rasterio.windows": fake_windows}), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=True), \
             mock.patch.object(L, "MAX_TENTATIVES", 2), \
             mock.patch.object(L, "DELAI_RETRY", 0), \
             mock.patch.object(L.time, "sleep") as sleep:
            result = L.telecharger_cog_fenetre(
                nom, "https://example.invalid/cog.tif", self.tmp,
                (1, 1, 3, 3), ecraser=True)

        self.assertEqual(result, "ok")
        self.assertEqual(len(attempts), 2)
        sleep.assert_called_once_with(0)
        self.assertEqual(final.read_bytes(), b"NEW_COG")
        self._assert_no_part()

    def test_cog_keyboard_interrupt_propagates_and_cleans_stage(self):
        nom = "stop-cog.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)
        fake_rasterio, fake_windows = self._fake_rasterio(final, old)
        fake_rasterio.open = mock.Mock(side_effect=KeyboardInterrupt)
        L.PROVIDER = SimpleNamespace(
            CRS_NATIF="EPSG:2154", subdir_from_name=lambda _nom: ""
        )
        with mock.patch.dict(
                sys.modules,
                {"rasterio": fake_rasterio,
                 "rasterio.windows": fake_windows}), \
             mock.patch.object(L, "MAX_TENTATIVES", 2):
            with self.assertRaises(KeyboardInterrupt):
                L.telecharger_cog_fenetre(
                    nom, "https://example.invalid/cog.tif", self.tmp,
                    (1, 1, 3, 3), ecraser=True)

        self.assertEqual(final.read_bytes(), old)
        self._assert_no_part()

    def test_cog_large_window_is_written_in_bounded_row_blocks(self):
        nom = "large-window.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)
        fake_rasterio, fake_windows = self._fake_rasterio(final, old)
        Window = fake_windows.Window
        fake_windows.from_bounds = lambda *_args, **_kwargs: Window(
            0, 0, 2, 2050
        )
        open_fake = fake_rasterio.open
        writes = []

        def open_record(path, mode=None, **kwargs):
            dataset = open_fake(path, mode, **kwargs)
            if mode == "w":
                write = dataset.write

                def write_record(data, window=None):
                    writes.append(window)
                    return write(data, window=window)

                dataset.write = write_record
            return dataset

        fake_rasterio.open = open_record
        L.PROVIDER = SimpleNamespace(
            CRS_NATIF="EPSG:2154", subdir_from_name=lambda _nom: ""
        )
        with mock.patch.dict(
                sys.modules,
                {"rasterio": fake_rasterio,
                 "rasterio.windows": fake_windows}), \
             mock.patch.object(L, "_valider_tif_dalle", return_value=True), \
             mock.patch.object(L, "_MAX_COG_WINDOW_PX", 1), \
             mock.patch.object(L, "MAX_TENTATIVES", 1):
            result = L.telecharger_cog_fenetre(
                nom, "https://example.invalid/cog.tif", self.tmp,
                (1, 1, 3, 3), ecraser=True)

        self.assertEqual(result, "ok")
        self.assertEqual(
            [(window.row_off, window.height) for window in writes],
            [(0, 1024), (1024, 1024), (2048, 2)],
        )
        self.assertEqual(final.read_bytes(), b"NEW_COG")
        self._assert_no_part()

    def test_cog_cache_reprojects_requested_bbox_to_fragment_crs(self):
        fake_rasterio = types.ModuleType("rasterio")

        class Source:
            bounds = SimpleNamespace(left=100, bottom=200, right=300, top=400)
            crs = SimpleNamespace(to_epsg=lambda: 3857)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        fake_rasterio.open = lambda _path: Source()
        transformer = SimpleNamespace(transform=mock.Mock())
        L.PROVIDER = SimpleNamespace(CRS_NATIF="EPSG:2154")
        with mock.patch.dict(sys.modules, {"rasterio": fake_rasterio}), \
             mock.patch.object(
                 L, "_get_transformer", return_value=transformer
             ) as get_transformer, \
             mock.patch.object(
                 L, "_bbox_enveloppe_transform",
                 return_value=(101, 201, 299, 399),
             ) as transform_bbox:
            result = L._cog_cache_couvre(
                "fragment.tif", (1, 2, 3, 4)
            )

        self.assertTrue(result)
        get_transformer.assert_called_once_with("EPSG:2154", "EPSG:3857")
        transform_bbox.assert_called_once_with(
            transformer.transform, 1, 2, 3, 4
        )

    def _fake_rasterio(self, final, old):
        fake = types.ModuleType("rasterio")
        windows = types.ModuleType("rasterio.windows")

        class Window:
            def __init__(self, col_off=0, row_off=0, width=4, height=4):
                self.col_off = col_off
                self.row_off = row_off
                self.width = width
                self.height = height

            def round_offsets(self, op=None):
                return self

            def round_lengths(self, op=None):
                return self

        class Data:
            size = 16
            shape = (1, 4, 4)

        class Source:
            bounds = SimpleNamespace(left=0, bottom=0, right=10, top=10)
            crs = SimpleNamespace(to_epsg=lambda: 2154)
            profile = {"driver": "GTiff", "dtype": "float32", "count": 1}
            transform = object()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, window=None):
                return Data()

            def window_transform(self, _window):
                return object()

        class Destination:
            def __init__(self, path):
                self.path = Path(path)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def write(self, _data, window=None):
                self.assert_stage()
                self.path.write_bytes(b"NEW_COG")

            def assert_stage(self):
                if not self.path.parent.name.endswith(".part"):
                    raise AssertionError(self.path)
                if final.read_bytes() != old:
                    raise AssertionError("ancien final modifié avant publication")

        class Env:
            def __init__(self, **_kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        def open_fake(path, mode=None, **_kwargs):
            if mode == "w":
                return Destination(path)
            return Source()

        windows.Window = Window
        windows.from_bounds = lambda *_args, **_kwargs: Window()
        fake.windows = windows
        fake.Env = Env
        fake.open = open_fake
        return fake, windows

    def test_provider_shading_truncated_transfer_keeps_final(self):
        final = self.tmp / "zone_multi_ombrage.tif"
        old = b"OLD_SHADING"
        final.write_bytes(old)
        payload = b"II\x2a\x00short"

        class Response:
            headers = {
                "content-type": "image/tiff",
                "content-length": str(len(payload) + 10),
            }

            def __init__(self):
                self.done = False

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _size):
                if self.done:
                    return b""
                self.done = True
                return payload

        choices = ["multi"]
        L.PROVIDER = SimpleNamespace()
        with mock.patch("urllib.request.urlopen",
                        side_effect=lambda *_a, **_k: Response()), \
             mock.patch.object(L, "_valider_tif_dalle",
                               side_effect=AssertionError(
                                   "validation appelée après transfert tronqué")):
            L._fetch_provider_shadings(
                choices, (0, 0, 1, 1), self.tmp, "zone", True,
                {"multi": ("coverage", 1.0, "https://example.invalid/wcs")})

        self.assertEqual(choices, ["multi"])
        self.assertEqual(final.read_bytes(), old)
        self._assert_no_part()

    def test_provider_shading_validates_part_then_publishes(self):
        final = self.tmp / "zone_multi_ombrage.tif"
        old = b"OLD_SHADING"
        final.write_bytes(old)
        payload = b"II\x2a\x00complete"
        seen = []

        class Response:
            headers = {
                "content-type": "image/tiff",
                "content-length": str(len(payload)),
            }

            def __init__(self):
                self.done = False

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _size):
                if self.done:
                    return b""
                self.done = True
                return payload

        def extract(path):
            path = Path(path)
            seen.append(("extract", path))
            self.assertTrue(path.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), old)

        def validate(path):
            path = Path(path)
            seen.append(("validate", path))
            self.assertTrue(path.name.endswith(".part"))
            self.assertEqual(final.read_bytes(), old)
            return True

        choices = ["multi"]
        L.PROVIDER = SimpleNamespace()
        with mock.patch("urllib.request.urlopen", return_value=Response()), \
             mock.patch.object(L, "_extraire_tiff_multipart",
                               side_effect=extract), \
             mock.patch.object(L, "_valider_tif_dalle",
                               side_effect=validate), \
             mock.patch.object(L, "_creer_fichier"):
            L._fetch_provider_shadings(
                choices, (0, 0, 1, 1), self.tmp, "zone", True,
                {"multi": ("coverage", 1.0, "https://example.invalid/wcs")})

        self.assertEqual(choices, [])
        self.assertEqual(final.read_bytes(), payload)
        self.assertEqual([name for name, _path in seen],
                         ["extract", "validate"])
        self._assert_no_part()


if __name__ == "__main__":
    unittest.main(verbosity=2)
