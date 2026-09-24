"""Sert le GUI (gui/index.html + app.js + style.css) sur HTTP local, à la
place du mode pywebview (retiré, voir main_serve_gui() dans lidar2map.py).
N'importe jamais `webview` : ce module fonctionne sans pywebview/PyQt6/
QtWebEngine, jamais installés.

Même modèle de sécurité que blink2video (C:\\...\\blink\\serve.py,
hote_autorise()) : pas d'authentification de compte, seule la provenance
de la requête (Host, adresse TCP du client, Origin) est vérifiée - un
outil personnel, pas un service multi-utilisateur. Même stack que
_PartageServeur (lidar2map.py, déjà en prod pour le partage LAN des
livrables vers le téléphone) : http.server.ThreadingHTTPServer, stdlib
pur, pas de framework (Flask/FastAPI).

Dispatch : une route ``/api/<clef>`` appelle ``api_routes["<clef>"]()`` en
GET ou ``post_routes["<clef>"](payload_json)`` en POST. ``usage`` et
``autocomplete-ville`` sont spéciales (paramètres de requête plutôt qu'un
appel sans argument) : cas particuliers dans do_GET, pas dans le dispatch
générique.
"""
from __future__ import annotations

import ipaddress
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_PREFIXE_API = "/api/"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # Posés par demarrer() sur la CLASSE (une seule instance de serveur par
    # process ici, comme blink2video/serve.py) avant de démarrer.
    trusted_host: str = ""
    gui_dir: Path | None = None
    api_routes: dict = {}
    post_routes: dict = {}

    _HOTES_LOCAUX = ("127.0.0.1", "localhost", "::1")

    def log_message(self, fmt, *args):
        pass  # pas de journal d'accès, rien d'utile ici

    # ------------------------------------------------------------ sécurité

    def hote_autorise(self) -> bool:
        """Calque direct de hote_autorise() dans blink2video/serve.py : faux
        si Host (déclaré par le client) ne désigne pas cette machine, si
        l'adresse TCP réelle du client n'est ni la boucle locale ni le
        trusted_host, ou si Origin (quand le navigateur l'envoie) diffère.
        Aucune authentification de compte - seule la provenance compte,
        comme _PartageServeur juste à côté dans lidar2map.py."""
        hote_confiance = (self.trusted_host or "").strip()
        hotes_valides = self._HOTES_LOCAUX + ((hote_confiance,) if hote_confiance else ())
        hote = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        if hote not in hotes_valides:
            return False
        client = str(getattr(self, "client_address", ("127.0.0.1", 0))[0])
        try:
            boucle_locale = ipaddress.ip_address(client).is_loopback
        except ValueError:
            boucle_locale = False
        proxy_local = os.environ.get("LIDAR2MAP_TRUSTED_LOOPBACK_PROXY") == "1"
        tunnel_direct = bool(hote_confiance) and hote == hote_confiance
        if not boucle_locale and not proxy_local and not tunnel_direct:
            return False
        origine = self.headers.get("Origin")
        if origine:
            # ValueError sur une Origin manifestement invalide (IPv6 mal
            # fermée, ex. "http://[abc") : refuser plutôt que laisser
            # urlparse planter la requête (même piège déjà audité et
            # corrigé côté blink2video).
            try:
                origine_hote = urlparse(origine).hostname
            except ValueError:
                origine_hote = None
            if origine_hote not in hotes_valides:
                return False
        return True

    # ------------------------------------------------------------- réponses

    def send_json(self, data, status: int = 200) -> None:
        corps = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def send_static(self, path: Path, content_type: str) -> None:
        try:
            corps = path.read_bytes()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def send_index(self) -> None:
        try:
            html = (self.gui_dir / "index.html").read_text(encoding="utf-8")
        except OSError:
            self.send_error(404)
            return
        # index.html est écrit pour l'inlining pywebview (placeholders
        # remplacés par le contenu CSS/JS en Python avant html=..., mode
        # aujourd'hui retiré). En mode navigateur on sert de vrais fichiers
        # séparés : références externes normales à la place, jamais
        # d'inlining - index.html/app.js/style.css restent inchangés sur
        # disque, web_bridge.js est le seul fichier ajouté par ce mode.
        html = html.replace(
            "<style>/*__LIDAR2MAP_CSS__*/</style>",
            '<link rel="stylesheet" href="/style.css">')
        html = html.replace(
            "<script>//__LIDAR2MAP_JS__</script>",
            '<script src="/web_bridge.js"></script>\n'
            '<script src="/app.js"></script>')
        corps = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    # --------------------------------------------------------------- GET

    def do_GET(self) -> None:
        if not self.hote_autorise():
            self.send_error(403)
            return
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/":
            self.send_index()
            return
        if route == "/app.js":
            self.send_static(self.gui_dir / "app.js", "text/javascript; charset=utf-8")
            return
        if route == "/style.css":
            self.send_static(self.gui_dir / "style.css", "text/css; charset=utf-8")
            return
        if route == "/web_bridge.js":
            self.send_static(self.gui_dir / "web_bridge.js", "text/javascript; charset=utf-8")
            return

        if not route.startswith(_PREFIXE_API):
            self.send_error(404)
            return
        clef = route[len(_PREFIXE_API):]

        if clef == "usage":
            query = parse_qs(parsed.query)
            cfg = {}
            if query.get("cache_dir"):
                cfg["cache_dir"] = query["cache_dir"][0]
            if query.get("production_dir"):
                cfg["production_dir"] = query["production_dir"][0]
            self._repondre(self.api_routes["usage"], cfg)
            return
        if clef == "autocomplete-ville":
            query = parse_qs(parsed.query)
            prefix = (query.get("prefix") or [""])[0]
            country = (query.get("country") or ["fr"])[0]
            self._repondre(self.api_routes["autocomplete-ville"], prefix, country)
            return
        if clef == "projets":
            query = parse_qs(parsed.query)
            dossier = (query.get("dossier") or [None])[0]
            self._repondre(self.api_routes["projets"], dossier)
            return
        if clef == "browse-dir":
            query = parse_qs(parsed.query)
            path = (query.get("path") or [""])[0]
            kind = (query.get("kind") or [""])[0]
            exts_brut = (query.get("exts") or [""])[0]
            exts = [e for e in exts_brut.split(",") if e]
            mode = (query.get("mode") or [""])[0]
            self._repondre(self.api_routes["browse-dir"], path, kind, exts, mode)
            return

        gestionnaire = self.api_routes.get(clef)
        if gestionnaire is None:
            self.send_error(404)
            return
        self._repondre(gestionnaire)

    # --------------------------------------------------------------- POST

    def do_POST(self) -> None:
        if not self.hote_autorise():
            self.send_error(403)
            return
        route = urlparse(self.path).path
        if not route.startswith(_PREFIXE_API):
            self.send_error(404)
            return
        clef = route[len(_PREFIXE_API):]
        gestionnaire = self.post_routes.get(clef)
        if gestionnaire is None:
            self.send_error(404)
            return
        try:
            longueur = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.send_error(400)
            return
        if longueur < 0:
            # rfile.read(-1) lirait jusqu'à la fermeture de la connexion :
            # en keep-alive HTTP/1.1, le fil du serveur resterait bloqué.
            self.send_error(400)
            return
        try:
            payload = json.loads(self.rfile.read(longueur) or b"{}")
        except ValueError:
            # JSONDecodeError, mais aussi UnicodeDecodeError (corps non UTF-8),
            # toutes deux sous-classes de ValueError.
            self.send_json({"error": "corps JSON illisible"}, 400)
            return
        self._repondre(gestionnaire, payload)

    def _repondre(self, gestionnaire, *args) -> None:
        """Appelle la route et renvoie son résultat en JSON. Une exception
        de la route devient une réponse 500 JSON : sans ça, socketserver
        coupait la connexion sans réponse et le fetch() de web_bridge.js
        échouait en erreur réseau opaque."""
        try:
            resultat = gestionnaire(*args)
        except Exception as exc:
            self.send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
            return
        self.send_json(resultat)


class Server(ThreadingHTTPServer):
    # Comportement Windows de allow_reuse_address : voir la même désactivation
    # (et la même raison) dans blink2video/serve.py.
    allow_reuse_address = os.name != "nt"


def demarrer(*, bind: str, port: int, trusted_host: str, gui_dir: Path,
             api_routes: dict, post_routes: dict | None = None) -> Server:
    """Crée et démarre le serveur (thread daemon, s'éteint avec le process).
    Retourne l'instance pour permettre server.shutdown()/server_close() par
    l'appelant. Lève OSError si le port est déjà occupé (laissé à
    l'appelant : message adapté à son propre contexte CLI)."""
    Handler.trusted_host = trusted_host
    Handler.gui_dir = gui_dir
    Handler.api_routes = api_routes
    Handler.post_routes = post_routes or {}
    server = Server((bind, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
