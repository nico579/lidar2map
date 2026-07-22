# providers/pt_dgt.py — Portugal continental, MDT LiDAR 50 cm via OGC-API DGT
#
# Source : Direção-Geral do Território (DGT) — Centro de Dados, levé LiDAR
#   national 2024 (10 pts/m², précision alti 10 cm). MDT (terrain) 50 cm.
#   Portail : https://cdd.dgterritorio.gov.pt/dgt-fe/catalogos
#   Datasets : dados.gov.pt « Dados LiDAR de Portugal continental » (accès livre).
#
# Paradigme : OGC-API Features/STAC-like derrière le proxy `dgt-be` (reversé
# depuis le SPA, non documenté officiellement mais stable et versionné /v1).
#   - API : https://cdd.dgterritorio.gov.pt/dgt-be/v1 — réponses ENVELOPPÉES
#     {"status":..,"message":..,"data":<payload>}.
#   - Le param bbox de GET /collections/<id>/items est IGNORÉ côté serveur ;
#     la recherche spatiale = POST /search en CQL2-JSON
#     {"filter-lang":"cql2-json","filter":{"op":"intersects",...},
#      "collections":["MDT-50cm"],"limit":N} (anonyme, pagination par lien next).
#   - Tuiles 1×1 km EPSG:3763 (PT-TM06/ETRS89), item id =
#     MDT-50cm-<feuille>-MM-YYYY ; plusieurs millésimes possibles par feuille →
#     on garde le plus récent (comme at-bev/ca-nrcan).
#   - Asset "data" = GeoTIFF float32 2000×2000 servi par
#     /dgt-be/v1/download/<token> : le download EXIGE une session (compte DGT
#     gratuit, login Keycloak). Le provider fait le login au discover (flux
#     formulaire kc-form-login, http.cookiejar stdlib) et INSTALLE un opener
#     urllib global à cookies : les téléchargements du cœur (urllib) portent
#     alors la session sans modification du pipeline. Cookies host-scopés,
#     inoffensif pour les autres providers. Chaque discover (donc chaque chunk)
#     rafraîchit la session.
#   - Identifiants : env DGT_USER / DGT_PASS (jamais en dur, jamais en config).
#   - Licence : dados abertos, « publicamente e gratuitamente, sem restrições ».
#
# Self-contained : stdlib uniquement.

import http.cookiejar
import json
import os
import re
import urllib.parse
import urllib.request


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Portugal — MDT LiDAR 50 cm (DGT, 2024)"
CODE       = "pt-dgt"
COUNTRY    = "pt"
LICENSE    = "Dados abertos — © Direção-Geral do Território"
DOC_URL    = "https://www.dgterritorio.gov.pt/Levantamento-LiDAR-de-Portugal-Continental"

# La GUI affiche un rappel credentials pour les providers à compte (cf. fi/dk).
APIKEY_REQUISE = False   # pas de clé API : env DGT_USER/DGT_PASS


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:3763"          # PT-TM06 / ETRS89 (mètres)
RESOLUTION_M       = 0.5                   # MDT 50 cm
DALLE_KM           = 1                     # tuile 1×1 km → 2000×2000 px
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # 2000
SEUIL_DALLE_VALIDE = 200_000              # float32 2000² (16 Mo brut) >> page HTML


# ── Endpoints ────────────────────────────────────────────────────────────────
API        = "https://cdd.dgterritorio.gov.pt/dgt-be/v1"
LOGIN_URL  = "https://cdd.dgterritorio.gov.pt/auth/login"
COLLECTION = "MDT-50cm"
HTTP_UA    = "lidar2map/1.0 (PT DGT MDT)"
# Étendue Portugal continental en EPSG:3763 (approx, clip grossier)
COVERAGE_EXTENT = (-120000, -310000, 165000, 280000)

_ID_RE = re.compile(rf"{COLLECTION}-(\d+)-(\d{{2}})-(\d{{4}})$")


# ── Nommage ──────────────────────────────────────────────────────────────────
def dalle_filename(feuille):
    return f"pt_mdt50_{feuille}.tif"


def subdir_from_name(nom):
    m = re.match(r"pt_mdt50_(\d+)\.tif$", nom)
    return m.group(1)[:3] if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("PT : URL via POST /search → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("PT : utiliser discover_dalles()")


# ── Session (login Keycloak, opener global à cookies) ────────────────────────
_session_prete = False


def _login():
    """Login Keycloak (formulaire kc-form-login) et installation d'un opener
    urllib GLOBAL à cookies : les downloads du cœur portent la session DGT.
    Lève RuntimeError si les identifiants manquent ou sont refusés."""
    global _session_prete
    user = os.environ.get("DGT_USER")
    pwd  = os.environ.get("DGT_PASS")
    if not user or not pwd:
        raise RuntimeError(
            "pt-dgt: set DGT_USER and DGT_PASS environment variables "
            "(free account: https://cdd.dgterritorio.gov.pt/auth/login)")
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", HTTP_UA)]
    # 1. page de login (redirige vers Keycloak, pose les cookies de flow)
    with opener.open(LOGIN_URL, timeout=60) as r:
        html = r.read().decode("utf-8", "replace")
    m = (re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', html)
         or re.search(r'<form[^>]*action="([^"]+)"[^>]*method="post"', html, re.I))
    if not m:
        raise RuntimeError("pt-dgt: Keycloak login form not found (portal changed?)")
    action = m.group(1).replace("&amp;", "&")
    # 2. POST credentials → redirigé vers l'app avec la session posée
    data = urllib.parse.urlencode({"username": user, "password": pwd,
                                   "credentialId": ""}).encode()
    with opener.open(urllib.request.Request(action, data=data), timeout=60) as r2:
        final = r2.geturl()
    if "auth.cdd" in final:
        raise RuntimeError("pt-dgt: login refused (check DGT_USER/DGT_PASS)")
    # 3. opener global : urllib.request.urlopen (le cœur) porte les cookies.
    urllib.request.install_opener(opener)
    _session_prete = True
    print("  PT DGT: authenticated session installed (Keycloak)")


# ── Découverte : POST /search CQL2 par bbox ──────────────────────────────────
def _post_search(body):
    req = urllib.request.Request(
        f"{API}/search", data=json.dumps(body).encode(),
        headers={"User-Agent": HTTP_UA, "Content-Type": "application/json",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read())
    return d.get("data", d)     # réponses enveloppées {status,message,data}


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """{pt_mdt50_<feuille>.tif: url} des tuiles MDT-50cm intersectant la zone.

    POST /search CQL2 intersects (le bbox GET est ignoré par ce serveur),
    pagination par lien 'next', millésime le plus récent par feuille. Le login
    (session download) est fait ICI : chaque chunk re-discover → session fraîche."""
    if bbox_wgs84 is None:
        return {}
    lon1, lat1, lon2, lat2 = bbox_wgs84
    poly = {"type": "Polygon", "coordinates": [[
        [lon1, lat1], [lon2, lat1], [lon2, lat2], [lon1, lat2], [lon1, lat1]]]}

    try:
        _login()
    except RuntimeError as e:
        print(f"  ERROR {e}")
        return None

    body = {"filter-lang": "cql2-json",
            "filter": {"op": "intersects",
                       "args": [{"property": "geometry"}, poly]},
            "collections": [COLLECTION], "limit": 200}
    meilleurs = {}   # feuille -> (annee, mois, href)
    n_pages = 0
    while True:
        try:
            data = _post_search(body)
        except Exception as e:
            print(f"  ERROR PT DGT search: {type(e).__name__}: {e}")
            return None
        feats = data.get("features", [])
        n_pages += 1
        for it in feats:
            m = _ID_RE.search(it.get("id", ""))
            href = ((it.get("assets") or {}).get("data") or {}).get("href")
            if not m or not href:
                continue
            feuille, mois, annee = m.group(1), int(m.group(2)), int(m.group(3))
            prev = meilleurs.get(feuille)
            if prev is None or (annee, mois) > (prev[0], prev[1]):
                meilleurs[feuille] = (annee, mois, href)
        # pagination : lien rel=next (body de POST à réémettre avec son token)
        nxt = next((ln for ln in data.get("links", [])
                    if ln.get("rel") == "next"), None)
        if not nxt or not feats:
            break
        nb = nxt.get("body") or {}
        if not nb:
            break
        body = {**body, **nb}
        if n_pages > 50:      # garde-fou anti-boucle
            break

    dalles = {dalle_filename(f): href for f, (_a, _m, href) in meilleurs.items()}
    print(f"  PT DGT (MDT 50 cm): {len(dalles)} tile(s) in the zone"
          f" ({n_pages} page(s), latest survey per sheet)")
    return dalles
