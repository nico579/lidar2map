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
                "set-trusted-host": lambda payload: self.api.set_trusted_host((payload or {}).get("host", "")),
                "set-autostart": lambda payload: self.api.set_autostart(bool((payload or {}).get("actif"))),
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

    def test_api_set_trusted_host_persiste_et_applique_a_chaud(self):
        # « à chaud » : Handler.trusted_host est un attribut de classe, la
        # nouvelle valeur doit s'appliquer sans redémarrer le serveur créé
        # dans setUp (contrairement à blink2video, qui doit relancer son
        # process serve.py pour un changement équivalent).
        #
        # L2M.Api.set_trusted_host() fait `import _serve_web` (nom canonique,
        # comme en usage réel où _serve_web.py n'est chargé qu'une fois) - ce
        # n'est PAS le module `_serve_web` importé en tête de ce fichier de
        # test sous l'alias l2m_serve_web_module (pour ne pas polluer le
        # sys.modules canonique). Un troisième chargement, sous le nom
        # canonique cette fois, apparaît donc dans sys.modules dès le premier
        # appel : c'est LUI qu'il faut interroger pour vérifier ce que le
        # code de production modifie réellement, pas l'alias de ce fichier.
        status, body = self._post("/api/set-trusted-host", {"host": "100.64.1.2"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])
        self.assertEqual(L2M._lire_prefs().get("trusted_host"), "100.64.1.2")
        self.assertEqual(sys.modules["_serve_web"].Handler.trusted_host, "100.64.1.2")
        self.assertEqual(L2M._api_get_init_data()["trusted_host"], "100.64.1.2")

    def test_api_set_trusted_host_espaces_sont_retires(self):
        status, body = self._post("/api/set-trusted-host", {"host": "  100.64.1.2  "})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])
        self.assertEqual(L2M._lire_prefs().get("trusted_host"), "100.64.1.2")

    def test_api_set_trusted_host_type_invalide_est_refuse(self):
        status, body = self._post("/api/set-trusted-host", {"host": 12345})
        self.assertEqual(status, 200)  # erreur métier, pas HTTP
        data = json.loads(body)
        self.assertFalse(data["ok"])
        self.assertIn("error", data)

    def test_api_set_autostart_active_appelle_autostart_enable(self):
        # import _autostart (nom canonique, pas un alias) : Api.set_autostart()
        # fait le même import dans lidar2map.py, donc cible la même instance
        # déjà en cache dans sys.modules - même piège que _serve_web (mocker
        # un alias différent mockerait une copie que le code réel n'utilise
        # jamais). enable()/disable() sont mockés : jamais toucher au vrai
        # dossier Démarrage Windows pendant ce test (voir test_autostart.py
        # pour le test du VRAI mécanisme, avec un chemin isolé).
        import _autostart
        with mock.patch.object(_autostart, "enable") as m_enable, \
             mock.patch.object(_autostart, "is_enabled", return_value=True):
            status, body = self._post("/api/set-autostart", {"actif": True})
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["ok"])
        self.assertTrue(data["actif"])
        m_enable.assert_called_once()

    def test_api_set_autostart_desactive_appelle_autostart_disable(self):
        import _autostart
        with mock.patch.object(_autostart, "disable") as m_disable, \
             mock.patch.object(_autostart, "is_enabled", return_value=False):
            status, body = self._post("/api/set-autostart", {"actif": False})
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["ok"])
        self.assertFalse(data["actif"])
        m_disable.assert_called_once()

    def test_api_set_autostart_erreur_remontee_proprement(self):
        import _autostart
        with mock.patch.object(_autostart, "enable", side_effect=RuntimeError("OS non supporte")):
            status, body = self._post("/api/set-autostart", {"actif": True})
        self.assertEqual(status, 200)  # erreur métier, pas HTTP
        data = json.loads(body)
        self.assertFalse(data["ok"])
        self.assertIn("error", data)

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


class InstanceExistanteEtPortLibreTests(unittest.TestCase):
    """Régression du 2026-09-19 : avant la migration, relancer l'exe ouvrait
    toujours une fenêtre indépendante (calcul possible en parallèle) ; un
    serveur unique par port ne le permet plus tout seul. _instance_existante
    distingue « un lidar2map tourne déjà ici » d'un service tiers qui
    occuperait le port par coïncidence ; _premier_port_libre fournit le port
    une fois la décision (rejoindre ou lancer en parallèle) prise ailleurs."""

    def _demarrer_lidar2map(self):
        server = _serve_web.demarrer(
            bind="127.0.0.1", port=0, trusted_host="", gui_dir=ROOT / "gui",
            api_routes={"init": L2M._api_get_init_data}, post_routes={},
        )
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def test_detecte_une_vraie_instance_lidar2map(self):
        port = self._demarrer_lidar2map()
        self.assertTrue(L2M._instance_existante("127.0.0.1", port))

    def test_rien_n_ecoute_sur_un_port_libre(self):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port_libre = s.getsockname()[1]
        self.assertFalse(L2M._instance_existante("127.0.0.1", port_libre))

    def test_ignore_un_service_tiers_qui_repond_autre_chose(self):
        # Un port occupé par un autre programme ne doit jamais être proposé
        # comme « instance lidar2map à rejoindre ».
        import http.server
        import threading as _threading

        class _Autre(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                corps = json.dumps({"app": "autre-chose"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(corps)

            def log_message(self, *a):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), _Autre)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        _threading.Thread(target=server.serve_forever, daemon=True).start()
        self.assertFalse(L2M._instance_existante("127.0.0.1", server.server_address[1]))

    def test_premier_port_libre_retourne_le_port_de_depart_si_libre(self):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            depart = s.getsockname()[1]
        server, port = L2M._premier_port_libre(
            "127.0.0.1", depart, "", ROOT / "gui", {}, {},
        )
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.assertEqual(port, depart)

    def test_premier_port_libre_saute_les_ports_deja_pris(self):
        import socket
        occupant = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        occupant.bind(("127.0.0.1", 0))
        occupant.listen(1)
        depart = occupant.getsockname()[1]
        self.addCleanup(occupant.close)
        try:
            server, port = L2M._premier_port_libre(
                "127.0.0.1", depart, "", ROOT / "gui", {}, {},
            )
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            self.assertNotEqual(port, depart)
            self.assertGreater(port, depart)
        finally:
            pass

    def test_premier_port_libre_rend_none_si_toute_la_plage_est_prise(self):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            depart = s.getsockname()[1]
        occupants = []
        try:
            for p in range(depart, depart + L2M.PORT_RANGE_SIZE):
                occ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                occ.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                occ.bind(("127.0.0.1", p))
                occ.listen(1)
                occupants.append(occ)
            server, port = L2M._premier_port_libre(
                "127.0.0.1", depart, "", ROOT / "gui", {}, {},
            )
            self.assertIsNone(server)
            self.assertIsNone(port)
        finally:
            for occ in occupants:
                occ.close()


class MainServeGuiRejoindreTests(unittest.TestCase):
    """main_serve_gui() : le chemin le plus sensible du prompt interactif -
    répondre « rejoindre » (Entrée seule, ou Y) ne doit surtout pas démarrer
    un second serveur, sinon les deux écriraient dans le même historique/
    cache en croyant chacun être seul. Le prompt lui-même (builtins.input)
    et sys.stdin.isatty sont mockés : aucun vrai terminal n'est nécessaire
    pour exercer cette branche en CI."""

    def setUp(self):
        self.server = _serve_web.demarrer(
            bind="127.0.0.1", port=0, trusted_host="", gui_dir=ROOT / "gui",
            api_routes={"init": L2M._api_get_init_data}, post_routes={},
        )
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.port = self.server.server_address[1]

    def test_reponse_par_defaut_rejoint_et_ne_demarre_pas_un_second_serveur(self):
        import webbrowser
        # --no-tray : sans lui, la branche "n" (nouveau serveur) atteindrait
        # _construire_tray_icon()/icon.run() et bloquerait indéfiniment sur
        # une vraie icône système en attente d'un clic qui ne viendra jamais
        # (vécu en réel le 2026-09-20 : un run de test resté accroché,
        # process tué à la main). time.sleep reste mocké ci-dessous pour la
        # branche --no-tray, qu'il redevient pertinent de traverser.
        argv = ["lidar2map.py", "--serve-gui", "--port", str(self.port), "--no-tray"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(sys.stdin, "isatty", return_value=True), \
             mock.patch("builtins.input", return_value="") as m_input, \
             mock.patch.object(webbrowser, "open") as m_open:
            L2M.main_serve_gui()  # doit retourner, pas boucler ni sys.exit

        m_input.assert_called_once()
        m_open.assert_called_once_with(f"http://127.0.0.1:{self.port}/")
        # Le port de l'instance existante répond toujours SEUL : si
        # main_serve_gui avait quand même démarré un second serveur dessus,
        # la construction du Server aurait levé OSError plus haut (déjà
        # couvert par _premier_port_libre) - ici on vérifie l'absence
        # d'ouverture sur un port voisin, signe qu'aucun second serveur n'a
        # été tenté.
        for voisin in range(self.port + 1, self.port + L2M.PORT_RANGE_SIZE):
            self.assertFalse(L2M._instance_existante("127.0.0.1", voisin))

    def test_reponse_n_ne_rejoint_pas(self):
        # --no-browser volontairement ABSENT : c'est justement la branche
        # interactive (rejoindre/nouveau) qu'on veut exercer, elle est
        # sautée quand --no-browser est présent. threading.Timer est mocké
        # (pas juste webbrowser.open) pour qu'aucun thread différé ne puisse
        # ouvrir un vrai navigateur après la fin du test, une fois le
        # correctif with-block levé.
        # --no-tray : sans lui, la branche "n" (nouveau serveur) atteindrait
        # _construire_tray_icon()/icon.run() et bloquerait indéfiniment sur
        # une vraie icône système en attente d'un clic qui ne viendra jamais
        # (vécu en réel le 2026-09-20 : un run de test resté accroché,
        # process tué à la main). time.sleep reste mocké ci-dessous pour la
        # branche --no-tray, qu'il redevient pertinent de traverser.
        argv = ["lidar2map.py", "--serve-gui", "--port", str(self.port), "--no-tray"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(sys.stdin, "isatty", return_value=True), \
             mock.patch("builtins.input", return_value="n"), \
             mock.patch.object(L2M.threading, "Timer") as m_timer, \
             mock.patch.object(L2M.time, "sleep", side_effect=KeyboardInterrupt), \
             self.assertRaises(SystemExit):
            L2M.main_serve_gui()

        # « N » : le Timer d'ouverture cible le NOUVEAU port (port+1), pas
        # l'instance existante - la branche « rejoindre » n'a pas été
        # prise. Le serveur créé pour ce port est refermé par le handler
        # KeyboardInterrupt lui-même (comportement normal d'un Ctrl+C) avant
        # que ce test ne reprenne la main, donc rien à vérifier après coup
        # sur ce port.
        m_timer.assert_called_once()
        url_programmee = m_timer.call_args.args[2][0]
        self.assertEqual(url_programmee, f"http://127.0.0.1:{self.port + 1}/")


if __name__ == "__main__":
    unittest.main()
