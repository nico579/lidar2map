"""Une découverte de dalles qui n'a pas tout vu ne doit pas répondre « hors
couverture » (audit du 2 octobre 2026, B12, B13, B14, B29).

L'orchestrateur traite une exception de découverte comme une panne à rejouer
(statut ko), et un dict vide comme une absence démontrée (statut ok, zone
terminée). Ces tests vérifient, sans réseau, que chaque provider lève plutôt
que de rendre un résultat partiel ou vide quand une partie de l'index manque.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
# Jamais les vrais dossiers d'état et de sorties de l'utilisateur (voir
# _dossiers.py) : run_tests.py en fournit un, sinon un dossier temporaire.
if not os.environ.get("LIDAR2MAP_HOME"):
    os.environ["LIDAR2MAP_HOME"] = tempfile.mkdtemp(prefix="lidar2map-tests-")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from providers import common, gb_scotland, si_arso, us_3dep_laz  # noqa: E402


class _Reponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _json(payload):
    return _Reponse(json.dumps(payload).encode())


class Dossier(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class CraigB13(Dossier):
    CAMPAGNES = (("c2019", "ta.zip", "dossier", ""),
                 ("c2021", "ta.zip", "dossier", ""))

    def test_un_index_de_campagne_indisponible_est_une_panne(self):
        with mock.patch.object(common, "_craig_ta_local", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                common.craig_dalles((0, 0, 1, 1), str, {}, self.tmp,
                                    campaigns=self.CAMPAGNES)
        self.assertIn("c2019", str(ctx.exception))

    def test_un_index_illisible_est_une_panne_et_quitte_le_cache(self):
        corrompu = self.tmp / "c2019__ta.zip"
        corrompu.write_bytes(b"pas un zip" * 200)
        with mock.patch.object(common, "_craig_ta_local",
                               return_value=corrompu):
            with self.assertRaises(RuntimeError):
                common.craig_dalles((0, 0, 1, 1), str, {}, self.tmp,
                                    campaigns=self.CAMPAGNES[:1])
        self.assertFalse(corrompu.exists())


class ArsoB29(Dossier):
    BBOX = (500000, 100000, 502000, 101000)   # cellules 500_100 et 501_100

    def _cache(self, contenu):
        chemin = self.tmp / "arso.json"
        chemin.write_text(json.dumps(contenu), encoding="utf-8")
        return chemin

    def test_cellule_inconnue_et_fishnet_en_panne_est_une_panne(self):
        cache = self._cache({"500_100": None})       # absence connue
        with mock.patch.object(si_arso, "_query_fishnet",
                               side_effect=OSError("timeout")):
            with self.assertRaises(RuntimeError) as ctx:
                si_arso.discover_dalles(None, self.BBOX, cache)
        self.assertIn("1 tile(s)", str(ctx.exception))

    def test_cellules_toutes_connues_sans_reseau(self):
        cache = self._cache({"500_100": None, "501_100": "b_35"})
        with mock.patch.object(si_arso, "_query_fishnet",
                               side_effect=AssertionError("réseau")):
            dalles = si_arso.discover_dalles(None, self.BBOX, cache)
        self.assertEqual(list(dalles), ["si_dmr1_501_100.tif"])


class ScotlandMemeDefaut(Dossier):
    def test_un_listing_en_panne_est_une_panne(self):
        bbox = (325000, 670000, 326000, 671000)       # Édimbourg
        with mock.patch.object(gb_scotland, "_list_prefix",
                               side_effect=OSError("503")):
            with self.assertRaises(RuntimeError):
                gb_scotland.discover_dalles(None, bbox, self.tmp / "gb.json")


class LgiaB14(Dossier):
    # Deux feuilles : 1111 et 2222, une tuile chacune.
    LISTE = ("/las/1111/1111-11-11.las\n/las/2222/2222-11-11.las\n")

    def _index(self, bases):
        texte = mock.MagicMock(return_value=_Reponse(self.LISTE.encode()))
        appels = []

        def base(nom, _ua):
            feuille = nom.split("-")[0]
            appels.append(feuille)
            return bases.get(feuille)

        with mock.patch.object(common.urllib.request, "urlopen", texte), \
             mock.patch.object(common, "_lgia_base_feuille", side_effect=base):
            try:
                return common._lgia_index(self.tmp / "lv.json", 2, "ua"), appels
            except RuntimeError as exc:
                return exc, appels

    def test_feuille_illisible_puis_relue(self):
        resultat, appels = self._index({"1111": (300, 200)})
        self.assertIsInstance(resultat, RuntimeError)
        self.assertEqual(sorted(appels), ["1111", "2222"])

        # Relance : seule la feuille manquante est remesurée.
        resultat, appels = self._index({"1111": (300, 200), "2222": (310, 200)})
        self.assertEqual(appels, ["2222"])
        self.assertEqual(resultat, {"1111-11-11": [305, 205],
                                    "2222-11-11": [315, 205]})

        # Index complet : plus aucune mesure.
        resultat, appels = self._index({})
        self.assertEqual(appels, [])
        self.assertEqual(len(resultat), 2)

    def test_ancien_cache_partiel_est_complete(self):
        # Ancien format {nom: [x, y]} sans la feuille 2222 (cache partiel B14).
        (self.tmp / "lv.json").write_text(
            json.dumps({"1111-11-11": [305, 205]}), encoding="utf-8")
        resultat, appels = self._index({"2222": (310, 200)})
        self.assertEqual(appels, ["2222"])
        self.assertEqual(len(resultat), 2)


class PaginationB12(unittest.TestCase):
    def _pages(self, pages):
        """urlopen simulé : rend les pages dans l'ordre, note les URLs."""
        urls = []

        def ouvrir(req, **_kwargs):
            urls.append(req.full_url)
            return _json(pages[len(urls) - 1])

        return urls, mock.patch.object(common.urllib.request, "urlopen",
                                       side_effect=ouvrir)

    def test_quebec_suit_les_pages_jusqu_au_total(self):
        page1 = {"numberMatched": 1001,
                 "features": [{"id": i} for i in range(1000)]}
        page2 = {"numberMatched": 1001, "features": [{"id": 1000}]}
        urls, patch = self._pages([page1, page2])
        with patch:
            feats = common.quebec_wfs_features("ws", "couche", (0, 0, 1, 1))
        self.assertEqual(len(feats), 1001)
        self.assertIn("startIndex=1000", urls[1])

    def test_quebec_index_tronque_leve(self):
        page1 = {"numberMatched": 1001,
                 "features": [{"id": i} for i in range(1000)]}
        urls, patch = self._pages([page1, {"numberMatched": 1001,
                                           "features": []}])
        with patch, self.assertRaises(common.WfsTronque):
            common.quebec_wfs_features("ws", "couche", (0, 0, 1, 1))

    def test_flandre_page_pleine_repart_triee(self):
        def feat(i):
            x = 150000 + 500 * i
            return {"properties": {"tile_location": f"t{i}.laz"},
                    "geometry": {"type": "Polygon", "coordinates": [[
                        [x, 200000], [x + 500, 200000], [x + 500, 200500],
                        [x, 200500], [x, 200000]]]}}
        pleine = {"features": [feat(i) for i in range(4000)]}
        page1 = {"numberMatched": 4001,
                 "features": [feat(i) for i in range(4000)]}
        page2 = {"numberMatched": 4001, "features": [feat(4000)]}
        urls, patch = self._pages([pleine, page1, page2])
        with patch:
            dalles = common.be_flanders_dalles((0, 0, 1, 1), lambda x, y: x, {})
        self.assertEqual(len(dalles), 4001)
        self.assertNotIn("startIndex", urls[0])
        self.assertIn("sortBy=tile_location", urls[1])

    def test_gugik_une_annee_en_panne_est_une_panne(self):
        # 2019 répond une feuille, 2018 est en panne : rendre la feuille 2019
        # seule cacherait les feuilles que seule 2018 couvre.
        gml = ("<wfs:FeatureCollection><wfs:member><x>"
               "<gugik:url_do_pobrania>https://pl/a.laz</gugik:url_do_pobrania>"
               "<gml:lowerCorner>500000 600000</gml:lowerCorner>"
               "</x></wfs:member></wfs:FeatureCollection>")

        def ouvrir(req, **_kwargs):
            if "LIDAR2018" in req.full_url:
                raise OSError("timeout")
            return _Reponse(gml.encode())

        with mock.patch.object(common.urllib.request, "urlopen",
                               side_effect=ouvrir):
            self.assertIsNone(common.gugik_dalles(
                (0, 0, 1, 1), lambda x, y: f"{x}_{y}", years=(2019, 2018)))

    def test_us_3dep_suit_le_lien_next(self):
        def feat(i):
            return {"assets": {"data": {"href": f"https://x/{i}.copc.laz"}},
                    "bbox": [-100 + i * 0.01, 40, -99.99 + i * 0.01, 40.01]}
        pages = [
            {"features": [feat(i) for i in range(100)],
             "links": [{"rel": "next", "href": "https://stac/search",
                        "body": {"token": "next:abc"}}]},
            {"features": [feat(i) for i in range(100, 105)], "links": []},
        ]
        corps = []

        def http_json(url, data=None):
            corps.append(json.loads(data))
            return pages[len(corps) - 1]

        with mock.patch.object(us_3dep_laz, "_http_json", side_effect=http_json):
            dalles = us_3dep_laz._discover((-101, 39, -98, 41), None, None)
        self.assertEqual(len(dalles), 105)
        self.assertEqual(corps[1]["token"], "next:abc")
        self.assertEqual(corps[1]["collections"], corps[0]["collections"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
