"""Régressions du serveur web (--serve-gui, phase 1 : routes en lecture
seule) : sécurité (hote_autorise, calquée sur SecuriteWebTests dans
blink2video/test_serve_security_audit.py) et service réel des 3 routes +
fichiers statiques, comme test_phone_share.py le fait déjà pour
_PartageServeur.
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent

# spec_from_file_location n'ajoute pas le dossier du script à sys.path (même
# raison que le fixup en tête de lidar2map.py, ligne ~564) : chaque module
# testé est donc chargé explicitement par son chemin, pas par un `import`
# nu qui échouerait depuis Tests/. Enregistré dans sys.modules AVANT
# exec_module (comme le ferait un vrai import) : get_help() lit
# sys.modules[__name__].__doc__, absent sinon (KeyError, jamais atteint en
# usage réel où __name__ vaut toujours "__main__", déjà enregistré par
# Python lui-même).
_SPEC_L2M = importlib.util.spec_from_file_location("l2m_serve_web", ROOT / "lidar2map.py")
L2M = importlib.util.module_from_spec(_SPEC_L2M)
sys.modules[_SPEC_L2M.name] = L2M
_SPEC_L2M.loader.exec_module(L2M)

_SPEC_SW = importlib.util.spec_from_file_location("l2m_serve_web_module", ROOT / "_serve_web.py")
_serve_web = importlib.util.module_from_spec(_SPEC_SW)
_SPEC_SW.loader.exec_module(_serve_web)


class HoteAutoriseTests(unittest.TestCase):
    """Mêmes cas que SecuriteWebTests (blink2video) : hote_autorise() est
    une copie directe de celle de blink2video/serve.py, même construction
    d'instance sans socket réel (Handler.__new__, attributs posés à la
    main)."""

    def handler(self, client="127.0.0.1", host="127.0.0.1", trusted_host=""):
        handler = _serve_web.Handler.__new__(_serve_web.Handler)
        handler.client_address = (client, 12345)
        handler.headers = {"Host": host}
        handler.path = "/api/init"
        handler.trusted_host = trusted_host
        return handler

    def test_host_local_ne_suffit_pas_a_un_client_distant(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LIDAR2MAP_TRUSTED_LOOPBACK_PROXY", None)
            self.assertFalse(self.handler(client="192.0.2.4").hote_autorise())
            self.assertTrue(self.handler().hote_autorise())

    def test_host_invalide_refuse(self):
        self.assertFalse(self.handler(host="evil.example.com").hote_autorise())

    def test_origin_absente_ok_si_host_valide(self):
        self.assertTrue(self.handler().hote_autorise())

    def test_origin_valide_acceptee(self):
        handler = self.handler()
        handler.headers["Origin"] = "http://127.0.0.1"
        self.assertTrue(handler.hote_autorise())

    def test_origin_invalide_refusee(self):
        handler = self.handler()
        handler.headers["Origin"] = "http://attaquant.example"
        self.assertFalse(handler.hote_autorise())

    def test_origin_malformee_refusee_sans_lever(self):
        # urlparse lève ValueError sur certaines formes manifestement
        # invalides (IPv6 mal fermé) plutôt que de rendre un hostname vide :
        # même piège que celui audité et corrigé côté blink2video (voir
        # test_origin_malformee_refusee_sans_lever dans ce même dépôt).
        handler = self.handler()
        handler.headers["Origin"] = "http://[invalid"
        self.assertFalse(handler.hote_autorise())

    def test_hote_de_confiance_sans_opt_in_reste_refuse(self):
        handler = self.handler(client="100.101.194.5", host="100.101.194.5")
        self.assertFalse(handler.hote_autorise())

    def test_hote_de_confiance_accepte_un_client_distant_qui_le_designe(self):
        handler = self.handler(client="100.101.194.5", host="100.101.194.5",
                               trusted_host="100.101.194.5")
        self.assertTrue(handler.hote_autorise())

    def test_hote_de_confiance_n_elargit_pas_a_un_host_different(self):
        handler = self.handler(client="100.101.194.5", host="un-autre-host.example",
                               trusted_host="100.101.194.5")
        self.assertFalse(handler.hote_autorise())

    def test_proxy_local_exige_un_opt_in_et_un_host_loopback(self):
        with mock.patch.dict(os.environ, {"LIDAR2MAP_TRUSTED_LOOPBACK_PROXY": "1"}):
            self.assertTrue(self.handler(client="172.18.0.1").hote_autorise())
            self.assertFalse(
                self.handler(client="172.18.0.1", host="192.168.1.20").hote_autorise()
            )


class RoutesLectureSeuleTests(unittest.TestCase):
    """Serveur réellement démarré, routes interrogées en HTTP (comme
    test_phone_share.py le fait pour _PartageServeur) - branchées sur les
    vraies fonctions de lidar2map.py, pas des doublures."""

    def setUp(self):
        # clear-historique/set-lang appellent le vrai code, qui écrit sur
        # L2M._HISTORIQUE_PATH/_PREFS_PATH : sans isoler ces chemins, ce test
        # écrase le fichier réel de l'utilisateur à chaque exécution (vécu en
        # réel le 2026-09-18, historique de 50 entrées remplacé par [],
        # restauré depuis la sauvegarde pré-migration). Même pattern que
        # HistoryFixture dans _test_split_history.py.
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_ctx.name)
        self.old_historique_path = L2M._HISTORIQUE_PATH
        self.old_prefs_path = L2M._PREFS_PATH
        L2M._HISTORIQUE_PATH = self.tmp / "historique.json"
        L2M._PREFS_PATH = self.tmp / "preferences.json"

        self.api = L2M.Api()

        def _launch(cfg):
            erreur = L2M._valider_cfg_web(cfg or {})
            if erreur:
                return {"error": erreur}
            return self.api.launch(cfg or {})

        self.server = _serve_web.demarrer(
            bind="127.0.0.1", port=0, trusted_host="",
            gui_dir=ROOT / "gui",
            api_routes={
                "init": L2M._api_get_init_data,
                "historique": L2M._lire_historique,
                "usage": L2M._api_get_usage,
                "help": self.api.get_help,
                "projets": self.api.get_projets,
                "browse-dir": L2M._api_browse_dir,
                "autocomplete-ville": self.api.autocomplete_ville,
            },
            post_routes={
                "launch": _launch,
                "stop": lambda payload: {"result": self.api.stop()},
                "clear-historique": lambda _payload: self.api.clear_historique(),
                "set-lang": lambda payload: self.api.set_lang((payload or {}).get("code")),
            },
        )
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        L2M._HISTORIQUE_PATH = self.old_historique_path
        L2M._PREFS_PATH = self.old_prefs_path
        self.tmp_ctx.cleanup()

    def _get(self, path, headers=None):
        # /api/usage parcourt les vrais dossiers cache/production (os.walk) :
        # sur une machine avec un cache LiDAR déjà volumineux, ça peut
        # dépasser plusieurs secondes. 20s de marge, pas 5.
        req = urllib.request.Request(self.base + path, headers=headers or {})
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()

    def _post(self, path, payload=None):
        corps = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(
            self.base + path, data=corps, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read()

    def test_page_index_reference_les_fichiers_statiques_externes(self):
        status, body = self._get("/")
        html = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn('<link rel="stylesheet" href="/style.css">', html)
        self.assertIn('<script src="/web_bridge.js"></script>', html)
        self.assertIn('<script src="/app.js"></script>', html)
        self.assertNotIn("__LIDAR2MAP_CSS__", html)
        self.assertNotIn("__LIDAR2MAP_JS__", html)

    def test_fichiers_statiques_servis_tels_quels(self):
        _, body = self._get("/app.js")
        self.assertEqual(body, (ROOT / "gui" / "app.js").read_bytes())
        _, body = self._get("/style.css")
        self.assertEqual(body, (ROOT / "gui" / "style.css").read_bytes())
        _, body = self._get("/web_bridge.js")
        self.assertEqual(body, (ROOT / "gui" / "web_bridge.js").read_bytes())

    def test_api_init_renvoie_les_donnees_reelles(self):
        status, body = self._get("/api/init")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertGreater(len(data["couches"]), 0)
        self.assertIn("providers", data)
        self.assertIn("active_provider", data)

    def test_api_historique_renvoie_une_liste(self):
        status, body = self._get("/api/historique")
        self.assertEqual(status, 200)
        self.assertIsInstance(json.loads(body), list)

    def test_api_usage_renvoie_les_3_tiers_dans_l_ordre(self):
        status, body = self._get("/api/usage")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual([t["key"] for t in data["tiers"]],
                         ["cache", "production", "projets"])

    def test_api_usage_accepte_des_racines_custom_en_query_string(self):
        with tempfile.TemporaryDirectory() as td:
            status, body = self._get(f"/api/usage?cache_dir={td}")
            data = json.loads(body)
            cache_tier = next(t for t in data["tiers"] if t["key"] == "cache")
            self.assertEqual(Path(cache_tier["path"]), Path(td))

    def test_route_inconnue_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/nope")
        self.assertEqual(ctx.exception.code, 404)

    def test_host_non_autorise_refuse_avec_403(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/", headers={"Host": "evil.example.com"})
        self.assertEqual(ctx.exception.code, 403)

    def test_origin_non_autorisee_refuse_avec_403(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/init", headers={"Origin": "http://attaquant.example"})
        self.assertEqual(ctx.exception.code, 403)

    def test_api_help_renvoie_le_docstring_module(self):
        status, body = self._get("/api/help")
        self.assertEqual(status, 200)
        self.assertIn("lidar2map", json.loads(body))

    def test_api_projets_renvoie_une_liste(self):
        status, body = self._get("/api/projets")
        self.assertEqual(status, 200)
        self.assertIsInstance(json.loads(body), list)

    def test_api_browse_dir_liste_de_vrais_sous_dossiers(self):
        status, body = self._get(f"/api/browse-dir?path={ROOT}")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(Path(data["path"]), ROOT.resolve())
        self.assertIn("gui", data["dirs"])
        self.assertIn("Tests", data["dirs"])

    def test_api_launch_refuse_un_chemin_vers_un_dossier_systeme(self):
        cible = "C:\\Windows" if os.name == "nt" else "/etc"
        status, body = self._post("/api/launch", {"dossier": cible})
        data = json.loads(body)
        self.assertEqual(status, 200)  # erreur métier, pas HTTP
        self.assertIn("error", data)
        self.assertIsNone(self.api._process)  # rien n'a été lancé

    def test_api_set_lang_et_clear_historique_repondent_ok(self):
        status, body = self._post("/api/set-lang", {"code": "en"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])
        status, body = self._post("/api/clear-historique")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])

    def test_api_stop_sans_run_actif_ne_plante_pas(self):
        status, body = self._post("/api/stop")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"result": None})

    def test_post_route_inconnue_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post("/api/nope")
        self.assertEqual(ctx.exception.code, 404)

    def test_post_host_non_autorise_refuse_avec_403(self):
        corps = json.dumps({}).encode("utf-8")
        req = urllib.request.Request(
            self.base + "/api/set-lang", data=corps, method="POST",
            headers={"Content-Type": "application/json", "Host": "evil.example.com"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(ctx.exception.code, 403)


class ValidationCfgWebTests(unittest.TestCase):
    """_valider_cfg_web : les chemins de cfg deviennent une entrée non fiable
    une fois launch()/start_share() exposées en HTTP (section 7 de l'analyse
    de migration) - garde-fou minimal, pas un système de permissions."""

    def test_cfg_vide_ou_sans_chemin_est_acceptee(self):
        self.assertEqual(L2M._valider_cfg_web({}), "")
        self.assertEqual(L2M._valider_cfg_web({"nom": "test"}), "")

    def test_chemin_normal_est_accepte(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(L2M._valider_cfg_web({"dossier": td}), "")

    def test_racine_d_un_disque_est_refusee(self):
        cible = "C:\\" if os.name == "nt" else "/"
        self.assertNotEqual(L2M._valider_cfg_web({"dossier": cible}), "")

    def test_dossier_systeme_connu_est_refuse(self):
        cible = "C:\\Windows" if os.name == "nt" else "/etc"
        self.assertNotEqual(L2M._valider_cfg_web({"cache_dir": cible}), "")

    def test_cfg_non_dict_est_refusee(self):
        self.assertNotEqual(L2M._valider_cfg_web(None), "")
        self.assertNotEqual(L2M._valider_cfg_web("chemin"), "")


class BrowseDirTests(unittest.TestCase):
    """_api_browse_dir : navigateur de dossiers côté serveur, remplace le
    sélecteur natif pywebview (retiré)."""

    def test_liste_dossiers_et_ignore_les_fichiers_sans_filtre_extension(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sous_dossier").mkdir()
            (root / "notes.txt").write_text("x", encoding="utf-8")
            data = L2M._api_browse_dir(str(root))
            self.assertEqual(data["dirs"], ["sous_dossier"])
            self.assertEqual(data["files"], [])

    def test_filtre_extension_montre_uniquement_les_fichiers_correspondants(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "carte.mbtiles").write_text("x", encoding="utf-8")
            (root / "notes.txt").write_text("x", encoding="utf-8")
            data = L2M._api_browse_dir(str(root), exts=[".mbtiles"], mode="file")
            self.assertEqual(data["files"], ["carte.mbtiles"])

    def test_mode_file_sans_extension_montre_tous_les_fichiers(self):
        # Regression du 2026-09-18 : decouvert en testant vraiment la page
        # (le sous-dossier fusion_raster/ contenait un vrai .mbtiles de
        # 300 Mo, affiche comme "(dossier vide)"). pickFile('f-source-decoupe',
        # false, []) et pickFile('f-remote-identity', false, []) passent tous
        # les deux exts=[] volontairement (une identite SSH n'a pas
        # d'extension fixe) : sans le param mode, le serveur ne pouvait pas
        # distinguer ce cas de pick_dir et cachait les fichiers dans les deux
        # cas.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "id_ed25519").write_text("x", encoding="utf-8")
            data = L2M._api_browse_dir(str(root), mode="file")
            self.assertEqual(data["files"], ["id_ed25519"])

    def test_mode_dir_ignore_les_fichiers_meme_avec_extension_fournie(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "carte.mbtiles").write_text("x", encoding="utf-8")
            data = L2M._api_browse_dir(str(root), exts=[".mbtiles"], mode="dir")
            self.assertEqual(data["files"], [])

    def test_chemin_invalide_replie_sur_le_dossier_de_travail(self):
        data = L2M._api_browse_dir("Z:\\ce\\chemin\\n_existe\\pas\\du\\tout")
        self.assertTrue(Path(data["path"]).is_dir())

    def test_parent_est_none_a_la_racine_du_disque(self):
        racine = Path(ROOT.anchor)
        data = L2M._api_browse_dir(str(racine))
        self.assertIsNone(data["parent"])


if __name__ == "__main__":
    unittest.main()
