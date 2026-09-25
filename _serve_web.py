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
import socket
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

    # Fetch Metadata (Chrome 76+, Firefox 90+, Safari 16.4+) : un GET simple
    # venu d'un autre site (<img src>, fetch no-cors) n'envoie pas Origin, mais
    # déclenchait les effets de bord des routes /api/* (vider la file du
    # journal, parcourir un dossier, interroger GitHub). Les clients hors
    # navigateur n'envoient pas cet en-tête et restent acceptés
    # (_instance_existante, anciennes versions). Voir preconisations S1.
    _SITES_ADMIS = ("same-origin", "none")

    def requete_inter_sites(self) -> bool:
        site = self.headers.get("Sec-Fetch-Site")
        return site is not None and site.strip().lower() not in self._SITES_ADMIS

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
        # Servi tel quel : index.html référence lui-même style.css,
        # web_bridge.js puis app.js. Les marqueurs d'inlining de l'époque
        # pywebview (__LIDAR2MAP_CSS__/__LIDAR2MAP_JS__), remplacés ici à
        # chaque requête, ont disparu du fichier.
        self.send_static(self.gui_dir / "index.html", "text/html; charset=utf-8")

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
        if self.requete_inter_sites():
            self.send_error(403)
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
        if self.requete_inter_sites():
            self.send_error(403)
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


class Server6(Server):
    address_family = socket.AF_INET6


def _classe_serveur(adresse: str):
    """Serveur IPv4 ou IPv6 selon l'adresse d'écoute (``fd7a::1``...)."""
    return Server6 if ":" in adresse else Server


def _est_boucle_locale(adresse: str) -> bool:
    try:
        return ipaddress.ip_address(adresse).is_loopback
    except ValueError:
        return adresse == "localhost"


class EcouteHoteConfiance:
    """Écoute supplémentaire sur l'adresse de l'hôte de confiance (VPN maillé
    type Tailscale/WireGuard), au même port et avec le même Handler que le
    serveur principal, qui reste sur la boucle locale.

    Sans elle, l'accès distant exigeait --bind <adresse VPN> : la page locale
    (127.0.0.1) cessait alors de répondre, et un serveur démarré à
    l'ouverture de session (sans --bind) n'était jamais joignable à distance.
    L'adresse n'existe pas toujours au démarrage (VPN pas encore connecté) :
    nouvel essai toutes les ``delai_s`` secondes, jusqu'au succès ou jusqu'à
    un changement d'hôte. Hôte = nom (MagicDNS) ou adresse : ses adresses
    résolues sont écoutées, sauf celles de la boucle locale (déjà servies)."""

    def __init__(self, port: int, delai_s: float = 30.0):
        self.port = port
        self.delai_s = delai_s
        self.etat = "inactif"          # inactif | actif | en attente
        self._verrou = threading.Lock()
        self._hote = ""
        self._serveurs = []
        self._arret = threading.Event()

    def definir(self, hote: str) -> str:
        """(Re)configure l'écoute pour ``hote`` ('' : aucune) ; rend l'état."""
        hote = (hote or "").strip()
        with self._verrou:
            self._stopper()
            self._hote = hote
            self._arret = threading.Event()
            if not hote:
                self.etat = "inactif"
            elif self._essayer(hote):
                self.etat = "actif"
            else:
                self.etat = "en attente"
                threading.Thread(target=self._reessayer, args=(hote, self._arret),
                                 daemon=True).start()
            return self.etat

    def arreter(self) -> None:
        with self._verrou:
            self._stopper()
            self._hote = ""
            self.etat = "inactif"

    def _adresses(self, hote):
        try:
            infos = socket.getaddrinfo(hote, self.port, type=socket.SOCK_STREAM)
        except (socket.gaierror, UnicodeError, OSError):
            return []
        adresses = []
        for info in infos:
            adresse = info[4][0]
            if adresse not in adresses:
                adresses.append(adresse)
        return adresses

    def _essayer(self, hote) -> bool:
        adresses = self._adresses(hote)
        if adresses and all(_est_boucle_locale(a) for a in adresses):
            return True                # déjà servi par le serveur principal
        for adresse in adresses:
            if _est_boucle_locale(adresse):
                continue
            try:
                serveur = _classe_serveur(adresse)((adresse, self.port), Handler)
            except OSError:
                continue               # adresse absente de cette machine (VPN arrêté)
            threading.Thread(target=serveur.serve_forever, daemon=True).start()
            self._serveurs.append(serveur)
        return bool(self._serveurs)

    def _reessayer(self, hote, arret) -> None:
        while not arret.wait(self.delai_s):
            with self._verrou:
                if arret.is_set() or self._hote != hote:
                    return
                if self._essayer(hote):
                    self.etat = "actif"
                    return

    def _stopper(self) -> None:
        self._arret.set()
        for serveur in self._serveurs:
            serveur.shutdown()
            serveur.server_close()
        self._serveurs = []


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
    server = _classe_serveur(bind)((bind, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
