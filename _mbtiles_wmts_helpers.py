"""Helpers du pipeline WMTS/XYZ : grille de tuiles, URL, connexions et
téléchargement d'une tuile.

Regroupement thématique plutôt que séparation orchestrateur/algorithme : à la
différence de ``_mbtiles_wmts.py`` (7b) et ``_mbtiles_lidar.py`` (7e), qui
isolaient chacun un vrai producteur, ce module rassemble des utilitaires de
tailles et de couplages hétérogènes. La majorité (grille XYZ, validation de
bbox, contrôle des images, pool de connexions keep-alive) est pure — aucune
couture, réexportée telle quelle par ``lidar2map``. Seules
``telecharger_tuile`` et ``_lire_zoom_limites_wmts`` touchent des constantes de
configuration (endpoints, en-têtes, tentatives) et reçoivent une structure de
dépendances reconstruite à chaque appel, sur le même principe que les
producteurs MBTiles.
"""

from __future__ import annotations

import http.client
import math
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as _ET
from dataclasses import dataclass


@dataclass(frozen=True)
class _DependancesTelechargementWmts:
    """Coutures partagées par `telecharger_tuile` et `_lire_zoom_limites_wmts`.

    ``wmts_fetch`` est injecté comme callable, pas seulement paramétré par ses
    en-têtes : certaines suites remplacent `l2m._wmts_fetch` entièrement par
    une fonction factice à un seul argument (`lambda url: ...`), sans réseau.
    Un appel direct à l'implémentation colocalisée dans ce module ignorerait
    silencieusement ce remplacement, puisqu'il ne passe jamais par l'attribut
    patché sur `lidar2map`."""

    wmts_url: str
    wmts_url_pub: str
    wmts_fetch: object
    http_ua: str
    max_tentatives: int
    delai_retry: int



# Cache GetCapabilities WMTS en session : (layer_id, apikey_requis) → (zoom_min, zoom_max) | None
_wmts_caps_cache: dict = {}
_wmts_caps_lock  = threading.Lock()   # protège les lectures/écritures concurrentes


# Plafonds (zoom_min, zoom_max) pour les couches XYZ sans GetCapabilities.
# Signature recherchée dans le template d'URL → limites. USGSImageryOnly = naip.
_XYZ_ZOOM_LIMITS = (
    ("USGSImageryOnly", (0, 16)),
)


def _lire_zoom_limites_wmts(layer, apikey_requis, apikey="", *, dependances):
    """
    Interroge GetCapabilities WMTS IGN et retourne (zoom_min, zoom_max) réels
    pour la couche *layer* dans le TileMatrixSet PM.
    Résultat mis en cache pour la session ; retourne None si inaccessible.
    """
    # Couches XYZ (USGS Imagery, etc.) : pas de GetCapabilities WMTS IGN. On
    # plafonne via une table de limites connues (réutilise le clamp ci-dessous
    # comme pour l'IGN). USGSImageryOnly (naip) : LODs 0-16 au national ; au-delà
    # de z16, le cache ArcGIS renvoie des 204 → flot d'absences qui déclenche le
    # garde-fou « hors couverture » à tort. Sans limite connue → None (le 204
    # reste le filet de sécurité).
    if layer.startswith("XYZ:"):
        for _sig, _lim in _XYZ_ZOOM_LIMITS:
            if _sig in layer:
                return _lim
        return None
    cache_key = (layer, bool(apikey_requis))

    # Lecture du cache — verrou court, pas de réseau dedans
    with _wmts_caps_lock:
        if cache_key in _wmts_caps_cache:
            return _wmts_caps_cache[cache_key]

    # Requête réseau hors du verrou (évite de bloquer les autres threads)
    base = dependances.wmts_url if apikey_requis else dependances.wmts_url_pub
    url  = f"{base}?SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0"
    if apikey_requis and apikey:
        url += f"&apikey={apikey}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": dependances.http_ua})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml_bytes = r.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
        print(f"  ⚠ WMTS GetCapabilities unreachable ({type(e).__name__}: {e}) — zoom capping skipped")
        with _wmts_caps_lock:
            _wmts_caps_cache[cache_key] = None
        return None

    _NS = {
        "wmts": "http://www.opengis.net/wmts/1.0",
        "ows":  "http://www.opengis.net/ows/1.1",
    }
    try:
        root = _ET.fromstring(xml_bytes)
    except Exception as e:   # xml.etree.ElementTree.ParseError — pas importé directement
        print(f"  ⚠ GetCapabilities parsing failed ({e})")
        with _wmts_caps_lock:
            _wmts_caps_cache[cache_key] = None
        return None

    for lyr in root.findall(".//wmts:Layer", _NS):
        ident = lyr.findtext("ows:Identifier", namespaces=_NS)
        if ident != layer:
            continue
        for link in lyr.findall("wmts:TileMatrixSetLink", _NS):
            if link.findtext("wmts:TileMatrixSet", namespaces=_NS) != "PM":
                continue
            limits = link.find("wmts:TileMatrixSetLimits", _NS)
            if limits is None:
                break
            zooms = []
            for tml in limits.findall("wmts:TileMatrixLimits", _NS):
                tm = tml.findtext("wmts:TileMatrix", namespaces=_NS)
                if tm is not None:
                    try: zooms.append(int(tm))
                    except ValueError: pass
            if zooms:
                result = (min(zooms), max(zooms))
                with _wmts_caps_lock:
                    _wmts_caps_cache[cache_key] = result
                return result
        break

    with _wmts_caps_lock:
        _wmts_caps_cache[cache_key] = None
    return None


def _bbox_valide_wgs84(lon0, lat0, lon1, lat1):
    """Retourne (lon_min, lat_min, lon_max, lat_max) validée et ordonnée, ou
    message d'erreur + sys.exit(1). Rejette NaN/inf, lat hors [-90,90], lon
    hors [-180,180], bbox dégénérée. Réordonne des coins inversés (avec un
    avertissement) au lieu de produire un MBTiles vide silencieux (#12)."""
    for v in (lon0, lat0, lon1, lat1):
        if not (isinstance(v, (int, float)) and math.isfinite(v)):
            print(f"  ERROR: non-finite bbox coordinate ({v}).")
            sys.exit(1)
    if not (-90 <= lat0 <= 90 and -90 <= lat1 <= 90):
        print(f"  ERROR: latitude out of range [-90, 90] ({lat0}, {lat1}).")
        sys.exit(1)
    if not (-180 <= lon0 <= 180 and -180 <= lon1 <= 180):
        print(f"  ERROR: longitude out of range [-180, 180] ({lon0}, {lon1}).")
        sys.exit(1)
    lo0, lo1 = sorted((lon0, lon1))
    la0, la1 = sorted((lat0, lat1))
    if lo0 == lo1 or la0 == la1:
        print("  ERROR: degenerate bbox (zero width or height).")
        sys.exit(1)
    if (lo0, la0) != (lon0, lat0):
        print("  ⚠ bbox corners were reordered to W,S,E,N.")
    return lo0, la0, lo1, la1


def deg_to_tile(lat_deg, lon_deg, zoom):
    """Coordonnées WGS84 → tuile XYZ (convention Google/OSM, y=0 en haut)."""
    n = 2 ** zoom
    # Clamp de la latitude à la plage Web Mercator AVANT le log : au-delà de
    # ±85.0511° tan/cos explosent (math domain error / inf). L'ancien code
    # clampait x,y APRÈS coup, donc une latitude polaire plantait le log.
    lat_deg = max(-85.05112878, min(85.05112878, lat_deg))
    x = int((lon_deg + 180.0) / 360.0 * n)
    lat_r = math.radians(lat_deg)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi)
            / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def calculer_grille_xyz(lat_min, lon_min, lat_max, lon_max, zoom_min, zoom_max):
    """
    Génère toutes les tuiles (z, x, y) couvrant la bbox WGS84 pour tous les
    zooms demandés. GÉNÉRATEUR : un département en z18 représente des millions
    de tuples, la liste matérialisée coûtait des centaines de Mo de RAM avant
    la première requête. Le total est fourni par compter_tuiles_xyz (formule
    fermée, mêmes bornes).
    """
    for z in range(zoom_min, zoom_max + 1):
        x0, y0 = deg_to_tile(lat_max, lon_min, z)   # coin NW (y petit)
        x1, y1 = deg_to_tile(lat_min, lon_max, z)   # coin SE (y grand)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                yield (z, x, y)


def compter_tuiles_xyz(lat_min, lon_min, lat_max, lon_max, zoom_min, zoom_max):
    """Compte les tuiles que calculer_grille_xyz générera (mêmes bornes),
    sans matérialiser la liste."""
    total = 0
    for z in range(zoom_min, zoom_max + 1):
        x0, y0 = deg_to_tile(lat_max, lon_min, z)
        x1, y1 = deg_to_tile(lat_min, lon_max, z)
        total += (x1 - x0 + 1) * (y1 - y0 + 1)
    return total


def estimer_taille(nb_tuiles, format_img="jpeg"):
    """Estimation grossière : ~15 Ko/tuile JPEG Scan25, ~30 Ko ortho.
    Accepte "jpeg" ET "jpg" : l'appelant passe fmt_ext (= "jpg"), et le
    test strict != "jpeg" ne prenait donc JAMAIS le tarif JPEG (estimation
    2× trop haute pour toutes les couches JPEG)."""
    ko_par_tuile = 15 if format_img in ("jpeg", "jpg") else 30
    return nb_tuiles * ko_par_tuile // 1024   # Mo

# ============================================================
# CONSTRUCTION URL WMTS
# ============================================================

def construire_url_wmts(z, x, y, layer, style, fmt, apikey, apikey_requis,
                       *, wmts_url, wmts_url_pub):
    """
    Construit l'URL de tuile (z, x, y).
    - WMTS IGN : TileMatrix=z, TileCol=x, TileRow=y (XYZ standard).
    - Source XYZ (layer == "XYZ:<template>", ex. USGS Imagery / NAIP) : substitue
      {z}/{x}/{y} dans le template ArcGIS/XYZ (même schéma Mercator, y top-origine).
    """
    if layer.startswith("XYZ:"):
        tmpl = layer[4:]
        return (tmpl.replace("{z}", str(z))
                    .replace("{x}", str(x))
                    .replace("{y}", str(y)))
    base = wmts_url if apikey_requis else wmts_url_pub
    params = {
        "SERVICE":      "WMTS",
        "REQUEST":      "GetTile",
        "Version":      "1.0.0",
        "Layer":        layer,
        "Style":        style,
        "TileMatrixSet":"PM",
        "FORMAT":       fmt,
        "TileMatrix":   str(z),
        "TileCol":      str(x),
        "TileRow":      str(y),
    }
    if apikey_requis:
        params["apikey"] = apikey
    return base + "?" + urllib.parse.urlencode(params)

# ============================================================
# TÉLÉCHARGEMENT D'UNE TUILE
# ============================================================



# ── Connexions keep-alive pour le download WMTS ───────────────────────────────
# urllib.request.urlopen rouvre une connexion TCP+TLS par tuile (~90 ms de
# poignée de main perdus à chaque fois ; benchmark IGN planign : ~2x plus lent
# qu'une connexion réutilisée). Les tuiles d'un batch tapent toutes le même hôte
# (data.geopf.fr) : on garde une connexion HTTP/1.1 keep-alive par worker
# (thread-local), réutilisée d'une tuile à l'autre, avec reconnexion auto si le
# serveur ferme. Fermeture en fin de batch (generer_mbtiles_wmts).

_wmts_conn_tl    = threading.local()
_wmts_conns      = []                  # connexions ouvertes (fermées en fin de batch)
_wmts_conns_lock = threading.Lock()


def _wmts_get_conn(scheme, host):
    cache = getattr(_wmts_conn_tl, "by_host", None)
    if cache is None:
        cache = {}; _wmts_conn_tl.by_host = cache
    conn = cache.get(host)
    if conn is None:
        cls = (http.client.HTTPSConnection if scheme == "https"
               else http.client.HTTPConnection)
        conn = cls(host, timeout=15)
        cache[host] = conn
        with _wmts_conns_lock:
            _wmts_conns.append(conn)
    return conn


def _wmts_drop_conn(host):
    cache = getattr(_wmts_conn_tl, "by_host", None)
    if cache and host in cache:
        try: cache[host].close()
        except Exception: pass
        del cache[host]


def _wmts_close_all_conns():
    """À appeler en fin de batch WMTS pour libérer les sockets keep-alive."""
    with _wmts_conns_lock:
        for c in _wmts_conns:
            try: c.close()
            except Exception: pass
        _wmts_conns.clear()


def _wmts_fetch(url, *, headers):
    """GET via la connexion keep-alive thread-local (réutilisée d'une tuile à
    l'autre). Retourne (status, content_type, data). Une reconnexion si la
    connexion persistante a été fermée par le serveur.

    Suit les redirections (301/302/303/307/308) jusqu'à 3 sauts :
    http.client ne le fait pas seul (contrairement à urllib), et sans ça
    une bascule d'infra côté serveur classerait tout le batch en erreurs
    « HTTP 301 » peu parlantes."""
    for _hop in range(4):
        parts = urllib.parse.urlsplit(url)
        host  = parts.netloc
        path  = parts.path + (("?" + parts.query) if parts.query else "")
        last_exc = None
        reponse  = None
        for _essai in (1, 2):
            conn = _wmts_get_conn(parts.scheme, host)
            try:
                conn.request("GET", path, headers=headers)
                resp = conn.getresponse()
                data = resp.read()        # lecture complète = condition de réutilisation
                reponse = (resp.status, resp.headers.get("content-type", ""),
                           data, resp.headers.get("location"))
                break
            except (http.client.HTTPException, OSError) as e:
                last_exc = e
                _wmts_drop_conn(host)     # connexion morte → on en recrée une au prochain tour
        if reponse is None:
            raise last_exc if last_exc else IOError("WMTS fetch failed")
        status, ct, data, loc = reponse
        if status in (301, 302, 303, 307, 308) and loc:
            url = urllib.parse.urljoin(url, loc)
            continue
        return status, ct, data
    raise IOError(f"WMTS fetch: too many redirects ({url})")


def _est_image_valide(data):
    """True si `data` commence par une signature d'image raster connue.

    Validation par MAGIE, pas par taille (R2#16) : le jumeau des dalles valide
    déjà son contenu (`_valider_tif_dalle`, magic TIFF), mais `telecharger_tuile`
    ne se fiait qu'à un seuil `len < 500` → une tuile PNG uniforme valide (zone
    de relief plat) tombait sous le seuil et était jetée = TROU de couverture,
    tandis qu'une page d'erreur HTML/JSON >500 o servie en `image/png` passait
    pour une tuile. Couvre JPEG/PNG/GIF/WebP/TIFF (tout ce qu'un WMTS raster
    peut servir)."""
    if not data or len(data) < 4:
        return False
    if data[:3] == b'\xff\xd8\xff':                       # JPEG
        return True
    if data[:8] == b'\x89PNG\r\n\x1a\n':                  # PNG
        return True
    if data[:6] in (b'GIF87a', b'GIF89a'):               # GIF
        return True
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':     # WebP
        return True
    if data[:4] in (b'II\x2a\x00', b'MM\x00\x2a',         # TIFF / BigTIFF
                    b'II\x2b\x00', b'MM\x00\x2b'):
        return True
    return False


def telecharger_tuile(z, x, y, layer, style, fmt, apikey, apikey_requis,
                     *, dependances):
    """
    Télécharge une tuile et retourne les bytes, ou None si absente/erreur.
    Réessaie MAX_TENTATIVES fois avec délai exponentiel. Réutilise une connexion
    keep-alive par worker (cf. _wmts_fetch), ~2x plus rapide que urlopen/tuile.
    """
    url = construire_url_wmts(z, x, y, layer, style, fmt, apikey, apikey_requis,
                          wmts_url=dependances.wmts_url,
                          wmts_url_pub=dependances.wmts_url_pub)
    for tentative in range(1, dependances.max_tentatives + 1):
        try:
            status, ct, data = dependances.wmts_fetch(url)
            if status == 404:
                return None
            if not (200 <= status < 300):
                raise IOError(f"HTTP {status}")
            ct = (ct or "").lower()
            if "xml" in ct or "html" in ct:
                # Rapport d'exception WMTS/HTML servi en 200 : erreur de
                # service/auth/paramètre, PAS une tuile absente. La classer
                # "absente" contournait le circuit-breaker (revue 2026-07-10).
                raise IOError(f"server error response ({ct}): "
                              f"{bytes(data[:120] if data else b'')!r}")
            # Erreur serveur JSON déguisée en 200 (ArcGIS/XYZ, cf.
            # telecharger_dalle_directe) : IOError → retry, pas "absente".
            if data and data.lstrip()[:1] == b"{" and b'"error"' in data[:200]:
                raise IOError(f"server error payload: {data[:120]!r}")
            if not data:
                return None   # 204 / corps vide = tuile absente (mer, hors couv.)
            # Validation par magie (R2#16) : ni le seuil de taille (jetait un
            # petit PNG valide) ni le content-type (parfois image/png sur une
            # erreur). Un corps non-image = panne serveur → IOError → retry →
            # 'erreurs' (jamais 'absent' : un trou marqué complet est pire).
            if not _est_image_valide(data):
                raise IOError(f"non-image WMTS response ({len(data)} B): "
                              f"{bytes(data[:80])!r}")
            return data
        except KeyboardInterrupt:
            # Propagation au handler top-level (sys.exit(130)) qui sait
            # nettoyer (lockfile, tmp). sys.exit(0) ici tuerait juste le
            # worker, masquerait l'interruption et casserait le code retour.
            raise
        except (urllib.error.URLError, IOError, OSError, http.client.HTTPException):
            if tentative < dependances.max_tentatives:
                time.sleep(dependances.delai_retry * tentative)
            else:
                # Panne PERSISTANTE (5xx, timeout, 403 clé expirée) ≠ tuile
                # absente : propager. L'appelant (_dl → generer_mbtiles_wmts)
                # compte en 'erreurs' + circuit-breaker 30 consécutives. Avant,
                # `return None` classait ces pannes en 'absentes' : le MBTiles
                # sortait "complet" avec des trous, et le re-run disait
                # "already present" — l'artefact bloquait sa propre réparation.
                raise
    return None
