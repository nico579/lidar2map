"""Caractérisation atomique du producteur MBTiles LiDAR (phase 7d).

Miroir de `_test_atomic_publications.py` côté WMTS (phase 7a), mais sur le
producteur complet `generer_mbtiles_lidar()` : warp réel via rasterio, tuilage
réel, encodage réel. C'est la condition posée par docs/plan_refonte.fr.md
avant l'extraction 7e — verrouiller le comportement via le producteur entier,
pas via un helper isolé, pour que l'extraction ne puisse pas déplacer
silencieusement une garantie que seul l'assemblage complet exerce (ordre des
`try/except`, moment où le pool d'encodage est fermé, moment où le `.part`
est jeté).
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import rasterio
from rasterio.transform import from_origin
from PIL import Image

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"

import importlib.util  # noqa: E402

_APP = Path(__file__).resolve().parent.parent / "lidar2map.py"
_spec = importlib.util.spec_from_file_location("l2m_lidar_atomic", str(_APP))
L = importlib.util.module_from_spec(_spec)
sys.modules["l2m_lidar_atomic"] = L
_spec.loader.exec_module(L)


def _ecrire_source(chemin, cote_px=256, res=0.5, x0=900000.0, y1=6250000.0,
                    bruit=False):
    """GeoTIFF uint8 monobande minimal (Lambert93), assez petit pour un run
    rapide (warp + un seul niveau de zoom) tout en exerçant le pipeline réel.

    `bruit=True` produit un contenu peu compressible : nécessaire pour le test
    de réutilisation du cache warpé, dont le seuil réel (`> 1_000_000` octets,
    cf. `generer_mbtiles_lidar`) écarterait un warpé trivial-sinusoïdal alors
    qu'il compresse à quelques ko."""
    if bruit:
        rng = np.random.default_rng(0)
        arr = rng.integers(0, 255, (cote_px, cote_px), dtype=np.uint8)
    else:
        yy, xx = np.mgrid[0:cote_px, 0:cote_px]
        arr = ((np.sin(xx / 12.0) * np.sin(yy / 12.0) * 0.5 + 0.5) * 254 + 1
               ).astype(np.uint8)
    prof = dict(driver="GTiff", dtype="uint8", count=1,
                height=cote_px, width=cote_px, crs="EPSG:2154",
                transform=from_origin(x0, y1, res, res))
    with rasterio.open(str(chemin), "w", **prof) as ds:
        ds.write(arr, 1)
    return (x0, y1 - cote_px * res, x0 + cote_px * res, y1)


class MbtilesLidarAtomicTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _run_source_fraiche(self, nom, **kwargs):
        """Écrit une source neuve et appelle le producteur complet dessus."""
        src = self.tmp / f"{nom}.tif"
        bbox = _ecrire_source(src)
        options = dict(zoom_min=15, zoom_max=15, format_tuiles="auto",
                       bbox_natif=bbox, tile_workers=1, ecraser_tuiles=True)
        options.update(kwargs)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            resultat = L.generer_mbtiles_lidar(src, self.tmp, nom, **options)
        return resultat, buf.getvalue()

    def _assert_no_staging(self):
        residus = [p for p in self.tmp.rglob("*")
                  if p.is_file() and (".part" in p.name
                                       or p.name.endswith("-wal")
                                       or p.name.endswith("-shm"))]
        self.assertEqual(residus, [])

    def test_full_success_publishes_and_cleans_staging(self):
        resultat, _ = self._run_source_fraiche("zone_ok")
        self.assertIsNotNone(resultat)
        self.assertTrue(resultat.exists())
        self._assert_no_staging()

    def test_validation_failure_keeps_previous_final(self):
        final = self.tmp / "zone_validation_z15-15.mbtiles"
        final.write_bytes(b"previous-mbtiles")
        with mock.patch.object(L, "_valider_sqlite_part",
                                side_effect=RuntimeError("invalid staging")):
            with self.assertRaises(RuntimeError):
                self._run_source_fraiche("zone_validation")
        self.assertEqual(final.read_bytes(), b"previous-mbtiles")
        self._assert_no_staging()

    def test_encoder_exception_keeps_previous_final(self):
        """Une exception dans l'encodeur (JPEG/PNG) ou un worker du pool doit
        se propager sans publier de MBTiles tronqué. `tile_workers=1` force le
        chemin séquentiel (`_pool is None`) pour rendre le point d'échec
        déterministe ; le chemin pool partage le même appelant `_encode_tile`."""
        final = self.tmp / "zone_encode_fail_z15-15.mbtiles"
        final.write_bytes(b"previous-mbtiles")
        original_save = Image.Image.save
        appels = {"n": 0}

        def save_qui_echoue_une_fois(self_img, *a, **kw):
            appels["n"] += 1
            if appels["n"] == 1:
                raise OSError("disk full (simulated encoder failure)")
            return original_save(self_img, *a, **kw)

        with mock.patch.object(Image.Image, "save", save_qui_echoue_une_fois):
            with self.assertRaises(OSError):
                self._run_source_fraiche("zone_encode_fail")
        self.assertEqual(final.read_bytes(), b"previous-mbtiles")
        self._assert_no_staging()

    def test_cooperative_stop_keeps_previous_final(self):
        final = self.tmp / "zone_stop_z15-15.mbtiles"
        final.write_bytes(b"previous-mbtiles")
        L._stop_event.set()
        try:
            with self.assertRaises(KeyboardInterrupt):
                self._run_source_fraiche("zone_stop")
        finally:
            L._stop_event.clear()
        self.assertEqual(final.read_bytes(), b"previous-mbtiles")
        self._assert_no_staging()

    def test_full_producer_reuses_warp_cache_on_rerun(self):
        """La réutilisation du cache warpé n'est vérifiée qu'à travers le
        producteur complet : un test sur `_warped_3857_valide` seul ne prouve
        pas que `generer_mbtiles_lidar` choisit réellement de le réutiliser."""
        src = self.tmp / "zone_cache.tif"
        bbox = _ecrire_source(src, cote_px=1200, bruit=True)
        # zoom 19 (pas 15 comme les autres scénarios) : le seuil réel de
        # réutilisation exige un warpé > 1 Mo (garde-fou contre un warpé
        # trivial mal formé), qu'un run à basse résolution n'atteint jamais.
        options = dict(zoom_min=19, zoom_max=19, format_tuiles="auto",
                       bbox_natif=bbox, tile_workers=1)

        with contextlib.redirect_stdout(io.StringIO()):
            resultat_1 = L.generer_mbtiles_lidar(
                src, self.tmp, "zone_cache", ecraser_tuiles=True, **{
                    k: v for k, v in options.items() if k != "ecraser_tuiles"
                })
        self.assertIsNotNone(resultat_1)
        warped = self.tmp / "zone_cache_tuilage_z19.tif"
        self.assertTrue(warped.exists())
        mtime_avant = warped.stat().st_mtime_ns

        # Reprise sans --tuiles-ecraser : la source n'a pas changé (fichier
        # non réécrit), seul le mbtiles manquant doit être régénéré.
        (self.tmp / "zone_cache_z19-19.mbtiles").unlink()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            resultat_2 = L.generer_mbtiles_lidar(
                src, self.tmp, "zone_cache", ecraser_tuiles=False, **{
                    k: v for k, v in options.items() if k != "ecraser_tuiles"
                })

        self.assertIsNotNone(resultat_2)
        self.assertEqual(warped.stat().st_mtime_ns, mtime_avant)
        self.assertIn("reused", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
