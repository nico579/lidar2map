# Tests de robustesse réseau/pagination/cache de lidar2map.py — SANS RÉSEAU.
# Couvre les correctifs de la revue externe du 2026-07-10 :
#   1. telecharger_tuile : 404/petit = absent (None), panne persistante = raise,
#      XML/HTML en 200 = raise (plus classé absent).
#   2. generer_mbtiles_wmts : erreurs > 0 → .part jeté + RuntimeError (jamais de
#      MBTiles troué publié) ; zone 100% hors couverture → ZoneHorsCouvertureWMTS.
#   3. telecharger_wfs : serveur qui plafonne sa page sous COUNT → complet quand
#      numberMatched est connu ; échec mi-pagination → sortie JETÉE (None) ;
#      troncature vs numberMatched → jetée ; collision de noms hors BDTOPO.
#   4. _telecharger_bdtopo_gpkg : sélection du membre EXACT de l'archive (un
#      .gpkg d'un autre département en cache ne doit être ni pris ni détruit) ;
#      validation taille avant promotion.
#   5. _bbox_sqlite_tiles : mbtiles multi-zoom sans metadata, sqlitedb
#      tilenumbering 'simple' multi-zoom (régression bbox fausse).
# Seams : monkeypatch des globals (_wmts_fetch, _urlopen, urllib.request.urlopen,
# sys.modules['py7zr']) — aucun refactor de production requis.
# Usage : python tests/_test_robustesse.py  (depuis n'importe quel cwd)
import gzip
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.parse
from pathlib import Path

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
_APP = Path(__file__).resolve().parent.parent / "lidar2map.py"
spec = importlib.util.spec_from_file_location("l2m", str(_APP))
l2m = importlib.util.module_from_spec(spec)
sys.modules["l2m"] = l2m
spec.loader.exec_module(l2m)

ok_all = True
def check(name, cond, detail=""):
    global ok_all
    status = "OK " if cond else "FAIL"
    print(f"  [{status}] {name} {detail}")
    if not cond:
        ok_all = False

tmp = Path(tempfile.mkdtemp())

# Accélérer les retries (les délais réels sont exponentiels) et neutraliser
# les sleeps de pagination. time.sleep est global au process de test : OK.
l2m.DELAI_RETRY = 0
_real_sleep = time.sleep
time.sleep = lambda *_a, **_k: None

# Un JPEG factice plausible (> 500 octets pour passer le seuil "tuile vide").
_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 700

print("== 1. telecharger_tuile : classification absent / erreur ==")
_saved_fetch = l2m._wmts_fetch

def _tuile(reponse):
    """Appelle telecharger_tuile avec _wmts_fetch mocké → (data | exception)."""
    l2m._wmts_fetch = lambda url: reponse
    try:
        return l2m.telecharger_tuile(10, 1, 2, "TEST", "normal",
                                     "image/jpeg", "", False)
    finally:
        l2m._wmts_fetch = _saved_fetch

check("200 image → bytes", _tuile((200, "image/jpeg", _JPEG)) == _JPEG)
check("404 → None (absent)", _tuile((404, "", b"")) is None)
check("204/petit payload → None (absent)", _tuile((204, "", b"")) is None)
try:
    _tuile((503, "", b""))
    check("503 persistant → raise", False)
except (IOError, OSError):
    check("503 persistant → raise", True)
try:
    _tuile((200, "application/xml", b"<ServiceExceptionReport/>"))
    check("XML en 200 → raise (erreur de service)", False)
except (IOError, OSError):
    check("XML en 200 → raise (erreur de service)", True)
try:
    _tuile((200, "image/tiff", b'{"error":{"code":400}}' + b" " * 600))
    check("payload JSON erreur en 200 → raise", False)
except (IOError, OSError):
    check("payload JSON erreur en 200 → raise", True)


print("== 2. generer_mbtiles_wmts : jamais de MBTiles troué publié ==")
def _mbtiles(scenario, nom):
    """scenario : {(z,x,y): reponse_wmts}. Retourne (exc|None, chemin)."""
    chemin = tmp / f"{nom}.mbtiles"
    tuiles = list(scenario.keys())
    l2m._wmts_fetch = lambda url: _reponse_pour(url, scenario)
    try:
        l2m.generer_mbtiles_wmts(
            chemin=chemin, tuiles_iter=iter(tuiles), total=len(tuiles),
            nom_zone=nom, fmt_ext="jpg", zoom_min=10, zoom_max=10,
            layer="TEST", style="normal", img_fmt="image/jpeg",
            apikey="", apikey_requis=False, workers=2,
            bbox_wgs84=(5.0, 43.0, 6.0, 44.0))
        return None, chemin
    except BaseException as e:
        return e, chemin
    finally:
        l2m._wmts_fetch = _saved_fetch

def _reponse_pour(url, scenario):
    # Retrouver (z,x,y) dans l'URL WMTS (TILEROW/TILECOL/TILEMATRIX).
    try:
        q = {k.lower(): v for k, v in
             urllib.parse.parse_qs(urllib.parse.urlparse(url).query).items()}
        # Clés WMTS en CamelCase (TileMatrix/TileCol/TileRow) → lookup insensible.
        z = int(q["tilematrix"][0])
        x = int(q["tilecol"][0])
        y = int(q["tilerow"][0])
        return scenario[(z, x, y)]
    except Exception as e:
        print(f"  [MOCK FAIL] {type(e).__name__}: {e}  url={url[:160]}")
        raise

_OKT = (200, "image/jpeg", _JPEG)
exc, chemin = _mbtiles({(10, 1, 1): _OKT, (10, 1, 2): _OKT, (10, 2, 1): _OKT}, "m_ok")
check("tout OK → publié sans exception", exc is None and chemin.exists())
if chemin.exists():
    con = sqlite3.connect(str(chemin))
    n = con.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
    con.close()
    check("tout OK → 3 tuiles dans le MBTiles", n == 3, f"n={n}")

exc, chemin = _mbtiles({(10, 1, 1): _OKT, (10, 1, 2): (503, "", b""),
                        (10, 2, 1): _OKT}, "m_err")
check("1 tuile en panne persistante → RuntimeError (pas de publication)",
      isinstance(exc, RuntimeError) and not chemin.exists()
      and not l2m._chemin_part(chemin).exists(),
      type(exc).__name__)

exc, chemin = _mbtiles({(10, 1, 1): (204, "", b""), (10, 1, 2): (204, "", b""),
                        (10, 2, 1): (204, "", b"")}, "m_mer")
check("zone 100% hors couverture → ZoneHorsCouvertureWMTS",
      isinstance(exc, l2m.ZoneHorsCouvertureWMTS) and not chemin.exists(),
      type(exc).__name__)


print("== 3. telecharger_wfs : pagination pilotée par numberMatched ==")
_real_urlopen = l2m.urllib.request.urlopen

class _FakeResp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode("utf-8")
    def read(self):
        return self._b
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

def _feat(i):
    return {"type": "Feature", "properties": {"i": i},
            "geometry": {"type": "Point", "coordinates": [6.0 + i * 1e-4, 43.0]}}

def _serveur_wfs(total, page_cap, fail_at=None, stop_at=None):
    """Serveur WFS factice : plafonne sa page à page_cap quel que soit COUNT.
    fail_at : STARTINDEX qui lève URLError (panne). stop_at : n'envoie plus
    rien au-delà (troncature silencieuse vs numberMatched)."""
    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if q.get("RESULTTYPE", [""])[0] == "hits":
            return _FakeResp({"numberMatched": total})
        start = int(q.get("STARTINDEX", ["0"])[0])
        if fail_at is not None and start >= fail_at:
            raise urllib.error.URLError("panne simulée")
        fin = min(start + page_cap, stop_at if stop_at is not None else total, total)
        return _FakeResp({"type": "FeatureCollection",
                          "numberMatched": total,
                          "features": [_feat(i) for i in range(start, fin)]})
    return fake_urlopen

def _wfs(nom, typename="BDTOPO_V3:test_couche", **kw):
    # WFS_URL est un re-export du provider (None pour fr-ign importé hors
    # main) : poser une URL factice, le faux urlopen ne la contacte jamais.
    _saved_wfs_url = l2m.WFS_URL
    l2m.WFS_URL = "https://wfs.fake/ows"
    l2m.urllib.request.urlopen = _serveur_wfs(**kw)
    try:
        return l2m.telecharger_wfs(typename, 5.0, 43.0, 6.0, 44.0,
                                   nom, tmp / f"wfs_{nom}")
    finally:
        l2m.urllib.request.urlopen = _real_urlopen
        l2m.WFS_URL = _saved_wfs_url

# a) serveur plafonné à 10/page (on demande 1000) : 25 features attendues.
#    L'ancien code s'arrêtait à la 1re page courte → 10 features publiées.
p = _wfs("cap", total=25, page_cap=10)
if p and p.exists():
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        nb = len(json.load(fh)["features"])
    check("page plafonnée sous COUNT → complet via numberMatched",
          nb == 25, f"features={nb}")
else:
    check("page plafonnée sous COUNT → complet via numberMatched", False, "None")

# b) panne à la 2e page : sortie JETÉE, pas de fichier final ni de tmp.
p = _wfs("panne", total=25, page_cap=10, fail_at=10)
d = tmp / "wfs_panne"
check("panne mi-pagination → None + aucun fichier",
      p is None and not list(d.glob("*.geojson*")) if d.exists() else p is None,
      str(p))

# c) troncature silencieuse (serveur s'arrête à 20/25) : sortie JETÉE.
p = _wfs("tronque", total=25, page_cap=10, stop_at=20)
d = tmp / "wfs_tronque"
check("troncature vs numberMatched → None + aucun fichier",
      p is None and (not d.exists() or not list(d.glob("*.geojson*"))), str(p))

# d) collision de noms : deux typenames hors BDTOPO qui se normalisent pareil.
p1 = _wfs("ns1", typename="NS_X:a-b", total=1, page_cap=10)
p2 = _wfs("ns1b", typename="NS_X:a_b", total=1, page_cap=10)
check("ns:a-b et ns:a_b → noms de fichiers distincts (hash)",
      p1 is not None and p2 is not None and p1.name != p2.name,
      f"{getattr(p1, 'name', None)} vs {getattr(p2, 'name', None)}")
# e) BDTOPO_V3 garde le nom court historique (cache utilisateurs préservé).
p3 = _wfs("bd", typename="BDTOPO_V3:cours_d_eau", total=1, page_cap=10)
check("BDTOPO_V3 → nom court inchangé",
      p3 is not None and p3.name == "bd_ign_cours_d_eau.geojson.gz",
      getattr(p3, "name", None))


print("== 4. _telecharger_bdtopo_gpkg : membre exact, cache voisin intact ==")
def _mk_gpkg_bytes(marqueur, taille_min=11_000_000):
    """Fabrique un vrai fichier SQLite ≥ taille_min avec un marqueur lisible."""
    f = tmp / f"_mk_{marqueur}.sqlite"
    f.unlink(missing_ok=True)
    con = sqlite3.connect(str(f))
    con.execute("CREATE TABLE marque (v TEXT)")
    con.execute("INSERT INTO marque VALUES (?)", (marqueur,))
    con.execute("CREATE TABLE bourrage (b BLOB)")
    con.execute("INSERT INTO bourrage VALUES (?)", (b"\0" * taille_min,))
    con.commit(); con.close()
    data = f.read_bytes()
    f.unlink()
    return data

class _FakeUrlopen:
    """Réponse de téléchargement vide : le .7z n'est pas lu par le faux py7zr."""
    headers = {"content-length": "0"}
    def read(self, n=-1):
        return b""
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    # compat resp.headers.get(...)
    class _H(dict):
        pass

class _FakePy7zr:
    """Module py7zr factice : SevenZipFile 'extrait' un GPKG contrôlé."""
    class SevenZipFile:
        membre  = "BDTOPO/1_DONNEES/D083_test.gpkg"
        contenu = b""
        def __init__(self, path, mode="r"):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def getnames(self):
            return [self.membre]
        def extract(self, targets, path):
            dest = Path(path) / self.membre
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(self.contenu)

def _gpkg(nom_ressource, contenu):
    _saved_travail = l2m.DOSSIER_TRAVAIL
    _saved_urlopen = l2m._urlopen
    _saved_mod = sys.modules.get("py7zr")
    l2m.DOSSIER_TRAVAIL = tmp / "travail"
    l2m._urlopen = lambda url, timeout=None: _FakeUrlopen()
    _FakePy7zr.SevenZipFile.contenu = contenu
    sys.modules["py7zr"] = _FakePy7zr
    try:
        return l2m._telecharger_bdtopo_gpkg("83", "https://fake/archive.7z",
                                            nom_ressource)
    finally:
        l2m.DOSSIER_TRAVAIL = _saved_travail
        l2m._urlopen = _saved_urlopen
        if _saved_mod is not None:
            sys.modules["py7zr"] = _saved_mod
        else:
            sys.modules.pop("py7zr", None)

# Décor : le gpkg d'un AUTRE département déjà en cache (l'ancien bug le
# renommait à la place du bon).
_cache = tmp / "travail" / "cache" / "bdtopo"
_cache.mkdir(parents=True, exist_ok=True)
_decoy = _cache / "BDTOPO_TEST_D084.gpkg"
_decoy_bytes = _mk_gpkg_bytes("D084")
_decoy.write_bytes(_decoy_bytes)

_bon = _mk_gpkg_bytes("D083")
res = _gpkg("BDTOPO_TEST_D083", _bon)
check("extraction → gpkg promu au nom demandé",
      res is not None and res.name == "BDTOPO_TEST_D083.gpkg" and res.exists(),
      str(res))
if res and res.exists():
    con = sqlite3.connect(f"file:{res}?mode=ro", uri=True)
    v = con.execute("SELECT v FROM marque").fetchone()[0]
    con.close()
    check("le contenu est le membre extrait (pas le voisin)", v == "D083", v)
check("le gpkg de l'autre département est INTACT",
      _decoy.exists() and _decoy.read_bytes() == _decoy_bytes)
check("dossier d'extraction temporaire nettoyé",
      not list(_cache.glob("_extract_*")))

# Validation taille : un gpkg trop petit ne doit pas entrer au cache.
res2 = _gpkg("BDTOPO_TEST_D000", b"trop petit")
check("gpkg < 10 Mo rejeté (pas de promotion)",
      res2 is None and not (_cache / "BDTOPO_TEST_D000.gpkg").exists())


print("== 5. _bbox_sqlite_tiles : multi-zoom (régression bbox fausse) ==")
def _mk_mbtiles_multizoom(path):
    con = sqlite3.connect(str(path))
    con.executescript("""
        CREATE TABLE metadata (name TEXT, value TEXT);
        CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER,
                            tile_row INTEGER, tile_data BLOB);
    """)
    # PAS de metadata bounds → force le fallback sur l'étendue des tuiles.
    # z12 : colonnes basses ; z14 : colonnes hautes. L'ancien agrégat mélangé
    # donnait min(col)@z12 interprété à z14 → bbox aberrante vers l'ouest.
    for (z, x, y) in [(12, 2115, 2570), (14, 8465, 10290), (14, 8466, 10291)]:
        y_tms = (1 << z) - 1 - y
        con.execute("INSERT INTO tiles VALUES (?,?,?,?)", (z, x, y_tms, b"d"))
    con.commit(); con.close()

mb = tmp / "multi.mbtiles"
_mk_mbtiles_multizoom(mb)
bbox = l2m._bbox_sqlite_tiles(mb, rmaps=False)
# Attendu : étendue des seules tuiles z14 (8465-8466 / 10290-10291)
tl = l2m._tile_to_geo(8465, 10290, 14)
br = l2m._tile_to_geo(8466, 10291, 14)
att = (tl[0], br[1], br[2], tl[3])
check("mbtiles multi-zoom sans bounds → bbox du zoom max seul",
      bbox is not None and all(abs(a - b) < 1e-6 for a, b in zip(bbox, att)),
      f"{bbox}")

def _mk_sqlitedb_simple(path):
    con = sqlite3.connect(str(path))
    con.executescript("""
        CREATE TABLE tiles (x INT, y INT, z INT, s INT, image BLOB);
        CREATE TABLE info (minzoom INT, maxzoom INT, tilenumbering TEXT);
    """)
    con.execute("INSERT INTO info VALUES (?,?,?)", (12, 14, "simple"))
    for (z, x, y) in [(12, 2115, 1525), (14, 8465, 6093), (14, 8466, 6094)]:
        con.execute("INSERT INTO tiles VALUES (?,?,?,0,?)", (x, y, z, b"d"))
    con.commit(); con.close()

sq = tmp / "simple.sqlitedb"
_mk_sqlitedb_simple(sq)
bbox = l2m._bbox_sqlite_tiles(sq, rmaps=True)
tl = l2m._tile_to_geo(8465, 6093, 14)
br = l2m._tile_to_geo(8466, 6094, 14)
att = (tl[0], br[1], br[2], tl[3])
check("sqlitedb 'simple' multi-zoom → bbox du zoom max, z NON inversé",
      bbox is not None and all(abs(a - b) < 1e-6 for a, b in zip(bbox, att)),
      f"{bbox}")

time.sleep = _real_sleep
print()
print("TOUS OK" if ok_all else "ÉCHECS DÉTECTÉS")
sys.exit(0 if ok_all else 1)
