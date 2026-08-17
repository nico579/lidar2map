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

    def test_direct_all_hooks_run_in_part_directory_then_publish(self):
        nom = "tile.tif"
        final = self.tmp / nom
        old = self._old_bytes()
        final.write_bytes(old)
        seen = []

        def download(_url, path, timeout=60):
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

        def download(_url, path, timeout=60):
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
