# Tests d'INTERACTION de lidar2map.py — SANS RÉSEAU.
#
# Cible : les chemins où les bugs de cette base se sont systématiquement nichés
# (leçon des passes d'audit 2026-07) — cache×flag, gate×état, overwrite×manifeste,
# jumeaux désalignés. Chaque section garde un invariant qui a DÉJÀ cassé une fois :
#   1. Manifeste : debut_morceau remet termine=False (relance overwrite qui échoue
#      mi-chunk ne repasse pas pour faite) ; manifeste corrompu = reset propre.
#   2. _run_split_priori : chunk fait sauté SANS overwrite, rejoué AVEC ;
#      échec mi-run → chunk non marqué, la relance ne rejoue QUE lui ;
#      ZoneHorsCouvertureWMTS = marqué fait, pas fatal.
#   3. _mbtiles_a_regenerer : fraîcheur make-like (TIF plus récent → régénère ;
#      mbtiles vide/corrompu → régénère ; valide + source plus vieille → skip).
#   4. _warped_3857_valide : cache de warp (CRS≠3857 ou fichier tronqué → False).
#   5. _cog_cache_couvre : fragment COG caché d'une AUTRE zone → re-download
#      (audit providers #1) ; corrompu → False.
#   6. Cache WMTS × couche : namespace par (endpoint,layer,style,format) — deux
#      couches même z/x/y ne partagent JAMAIS un fichier de cache (8e passe #5) ;
#      re-run même couche = servi du cache (0 fetch).
#   7. Providers jumeaux : cache STAC par-bbox (ca-nrcan, audit #4 : même
#      cache_path, 2 bboxes → 2 caches, pas de poisoning) ; disjonction des
#      nommages intra-pays (invariant de la purge hors-zone scopée, audit #2).
# Seams : monkeypatch des globals (_wmts_fetch, urllib.request.urlopen,
# _planche_depuis_dossier) — aucun refactor de production requis.
# Usage : python Tests/_test_interactions.py  (depuis n'importe quel cwd)
import glob as _glob
import importlib.util
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
import types
import urllib.request
from pathlib import Path

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
_ROOT = Path(__file__).resolve().parent.parent
_APP = _ROOT / "lidar2map.py"
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
l2m.DELAI_RETRY = 0
time.sleep = lambda *_a, **_k: None            # neutraliser les retries/sleeps


# ══ 1. Manifeste : gate × état ════════════════════════════════════════════════
print("== 1. Manifeste : debut remet termine=False ; corrompu = reset propre ==")
mpath = tmp / "m1" / "manifeste.json"
mpath.parent.mkdir(parents=True)
m = l2m.Manifeste(mpath)
check("chunk inconnu → pas fait", not m.deja_traite("001x001"))
m.debut_morceau("001x001", "z_001x001")
m.fin_morceau("001x001", 5)
check("fin_morceau → fait", m.deja_traite("001x001"))
# Relance avec écrasement qui démarre puis MEURT avant fin_morceau : l'ancien
# termine=True ne doit PAS rester actif (fix #6, 8e passe).
m2 = l2m.Manifeste(mpath)
m2.debut_morceau("001x001", "z_001x001")
m3 = l2m.Manifeste(mpath)          # relecture disque = état après le crash
check("debut_morceau sur chunk fait → termine=False persisté",
      not m3.deja_traite("001x001"))
# Manifeste corrompu : reset propre, pas d'exception.
mpath.write_text("{corrompu:::", encoding="utf-8")
m4 = l2m.Manifeste(mpath)
check("manifeste corrompu → reset sans lever", not m4.deja_traite("001x001"))
# enregistrer_fichiers : lot dédoublonné
m4.enregistrer_fichiers([tmp / "a.tif", tmp / "a.tif", tmp / "b.tif"], "001x001")
check("enregistrer_fichiers dédoublonne", len(m4.fichiers_morceau("001x001")) == 2)


# ══ 2. _run_split_priori : manifeste × overwrite ══════════════════════════════
print("== 2. Split a-priori : skip/percement/reprise après échec ==")
_planche_orig = l2m._planche_depuis_dossier
l2m._planche_depuis_dossier = lambda *a, **k: None   # best-effort → no-op (réseau)
args_ns = types.SimpleNamespace(min_free_gb=0.0, nettoyage=False)
sous_zones = [(0, 0, 1.0, 2.0, 3.0, 4.0), (0, 1, 5.0, 6.0, 7.0, 8.0)]

def _run(racine, overwrite, fail_on=None, hors_couv=None):
    """Lance _run_split_priori avec un callback traceur. Retourne (calls, exc)."""
    calls = []
    def traiter(coords, nom_z, cle, manifeste):
        calls.append(cle)
        if fail_on == cle:
            raise ValueError(f"panne simulée {cle}")
        if hors_couv == cle:
            raise l2m.ZoneHorsCouvertureWMTS(f"mer {cle}")
    exc = None
    try:
        l2m._run_split_priori(args_ns, sous_zones, "test", "ztest", racine,
                              overwrite, lambda c: f"bbox {c}", traiter,
                              time.time())
    except Exception as e:
        exc = e
    return calls, exc

r1 = tmp / "split1"; (r1 / "ztest").mkdir(parents=True)
calls, exc = _run(r1, overwrite=False)
check("run 1 : 2 chunks traités", calls == ["001x001", "001x002"] and exc is None)
calls, exc = _run(r1, overwrite=False)
check("run 2 sans overwrite : 0 rejoué (already done)", calls == [] and exc is None)
calls, exc = _run(r1, overwrite=True)
check("run 3 avec overwrite : manifeste percé, 2 rejoués",
      calls == ["001x001", "001x002"] and exc is None)

r2 = tmp / "split2"; (r2 / "ztest").mkdir(parents=True)
calls, exc = _run(r2, overwrite=False, fail_on="001x002")
check("échec chunk 2 → exception remonte (fail-fast)",
      isinstance(exc, ValueError) and calls == ["001x001", "001x002"])
man = l2m.Manifeste(r2 / "ztest" / "manifeste.json")
check("chunk 1 fait, chunk 2 PAS fait après le crash",
      man.deja_traite("001x001") and not man.deja_traite("001x002"))
calls, exc = _run(r2, overwrite=False)
check("relance : SEUL le chunk 2 rejoué", calls == ["001x002"] and exc is None)

r3 = tmp / "split3"; (r3 / "ztest").mkdir(parents=True)
calls, exc = _run(r3, overwrite=False, hors_couv="001x001")
check("ZoneHorsCouverture : pas fatal, chunk marqué fait",
      exc is None and calls == ["001x001", "001x002"]
      and l2m.Manifeste(r3 / "ztest" / "manifeste.json").deja_traite("001x001"))
l2m._planche_depuis_dossier = _planche_orig


# ══ 3. _mbtiles_a_regenerer : fraîcheur make-like ═════════════════════════════
print("== 3. Fraîcheur make-like mbtiles ← TIF source ==")
def _mk_mbtiles(path, n_tuiles=1):
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE tiles (zoom_level INT, tile_column INT, "
                  "tile_row INT, tile_data BLOB)")
        for i in range(n_tuiles):
            c.execute("INSERT INTO tiles VALUES (10, ?, 0, x'ff')", (i,))

mbt = tmp / "z.mbtiles"; tif = tmp / "z_src.tif"
check("mbtiles absent → régénère", l2m._mbtiles_a_regenerer(mbt, False))
_mk_mbtiles(mbt)
check("mbtiles valide, ecraser=True → régénère", l2m._mbtiles_a_regenerer(mbt, True))
tif.write_bytes(b"x")
os.utime(tif, (time.time() - 3600, time.time() - 3600))   # source PLUS VIEILLE
check("source plus vieille → skip (réutilise)",
      not l2m._mbtiles_a_regenerer(mbt, False, source=tif))
os.utime(tif, None)                                        # source PLUS RÉCENTE
os.utime(mbt, (time.time() - 3600, time.time() - 3600))
check("source plus récente → régénère (shadings-overwrite sans tiles-overwrite)",
      l2m._mbtiles_a_regenerer(mbt, False, source=tif))
mbt2 = tmp / "vide.mbtiles"; _mk_mbtiles(mbt2, n_tuiles=0)
check("mbtiles 0 tuiles (run interrompu) → régénère",
      l2m._mbtiles_a_regenerer(mbt2, False))
mbt3 = tmp / "corrompu.mbtiles"; mbt3.write_text("pas du sqlite", encoding="utf-8")
check("mbtiles corrompu → régénère", l2m._mbtiles_a_regenerer(mbt3, False))


# ══ 4/5. Caches raster : warp 3857 et fragment COG fenêtré ═══════════════════
print("== 4. Cache de warp : _warped_3857_valide ==")
import numpy as np
import rasterio
from rasterio.transform import from_bounds

def _mk_tif(path, epsg, bounds=(500000, 5000000, 501000, 5001000), size=64):
    data = np.arange(size * size, dtype=np.float32).reshape(size, size)
    tr = from_bounds(*bounds, size, size)
    with rasterio.open(path, "w", driver="GTiff", height=size, width=size,
                       count=1, dtype="float32", crs=f"EPSG:{epsg}",
                       transform=tr, nodata=-9999) as d:
        d.write(data, 1)

w_ok = tmp / "w3857.tif"; _mk_tif(w_ok, 3857)
w_bad = tmp / "w2154.tif"; _mk_tif(w_bad, 2154)
w_tronque = tmp / "wtronque.tif"
w_tronque.write_bytes(w_ok.read_bytes()[:200])   # header TIFF coupé
check("GeoTIFF 3857 lisible → True", l2m._warped_3857_valide(w_ok))
check("CRS 2154 (pas 3857) → False (pas réutilisé)",
      not l2m._warped_3857_valide(w_bad))
check("fichier tronqué → False (pas réutilisé)",
      not l2m._warped_3857_valide(w_tronque))
check("fichier absent → False", not l2m._warped_3857_valide(tmp / "absent.tif"))

print("== 5. Fragment COG caché : _cog_cache_couvre (audit providers #1) ==")
# PROVIDER par défaut = fr-ign (CRS_NATIF 2154) → tif de test en 2154 (identité).
frag = tmp / "frag.tif"
_mk_tif(frag, 2154, bounds=(900000, 6200000, 902000, 6202000))
check("bbox couverte par le fragment → skip (True)",
      l2m._cog_cache_couvre(frag, (900500, 6200500, 901500, 6201500)))
check("bbox d'une AUTRE zone du même COG → re-download (False)",
      not l2m._cog_cache_couvre(frag, (950000, 6250000, 951000, 6251000)))
check("bbox débordant du fragment → re-download (False)",
      not l2m._cog_cache_couvre(frag, (901000, 6201000, 903000, 6203000)))
frag2 = tmp / "frag_corrompu.tif"; frag2.write_text("x", encoding="utf-8")
check("fragment illisible → False (conservateur)",
      not l2m._cog_cache_couvre(frag2, (0, 0, 1, 1)))


# ══ 6. Cache WMTS × couche : namespace par (endpoint,layer,style,format) ══════
print("== 6. Cache disque WMTS : deux couches ne se croisent jamais ==")
_JPEG_A = b"\xff\xd8\xff\xe0" + b"A" * 700
_JPEG_B = b"\xff\xd8\xff\xe0" + b"B" * 700
_fetches = []
_payload = {"data": _JPEG_A}
_saved_fetch = l2m._wmts_fetch
l2m._wmts_fetch = lambda url: (_fetches.append(url) or (200, "image/jpeg", _payload["data"]))

cache_dir = tmp / "wmts_cache"
def _gen(nom, layer):
    chemin = tmp / f"{nom}.mbtiles"
    l2m.generer_mbtiles_wmts(
        chemin=chemin, tuiles_iter=iter([(10, 1, 2)]), total=1,
        nom_zone=nom, fmt_ext="jpg", zoom_min=10, zoom_max=10,
        layer=layer, style="normal", img_fmt="image/jpeg",
        apikey="", apikey_requis=False, workers=1,
        dossier_cache=cache_dir)
    with sqlite3.connect(chemin) as c:
        return c.execute("SELECT tile_data FROM tiles").fetchone()[0]

d1 = _gen("wa1", "LAYA")
check("couche A run 1 : 1 fetch, payload A", len(_fetches) == 1 and bytes(d1) == _JPEG_A)
d2 = _gen("wa2", "LAYA")
check("couche A run 2 : 0 fetch (servi du cache), payload A",
      len(_fetches) == 1 and bytes(d2) == _JPEG_A)
_payload["data"] = _JPEG_B
d3 = _gen("wb1", "LAYB")
check("couche B même z/x/y : re-fetch (pas le cache de A), payload B",
      len(_fetches) == 2 and bytes(d3) == _JPEG_B)
ns_dirs = [p.name for p in cache_dir.iterdir() if p.is_dir()]
check("2 namespaces de cache distincts", len(ns_dirs) == 2, detail=str(ns_dirs))
l2m._wmts_fetch = _saved_fetch


# ══ 7. Providers jumeaux : cache STAC par-bbox + disjonction des nommages ═════
print("== 7a. ca-nrcan : cache STAC par-bbox (audit #4, pas de poisoning) ==")
def _load_provider_module(fname):
    p = _ROOT / "providers" / fname
    s = importlib.util.spec_from_file_location(fname[:-3], str(p))
    mod = importlib.util.module_from_spec(s)
    s.loader.exec_module(mod)
    return mod

ca = _load_provider_module("ca_nrcan.py")
_stac_fetches = []

def _fake_urlopen(req, timeout=None, **_kw):
    url = req.full_url if hasattr(req, "full_url") else str(req)
    _stac_fetches.append(url)
    import urllib.parse as _up
    q = _up.parse_qs(_up.urlparse(url).query)
    bbox = q.get("bbox", [""])[0]
    tag = "A" if bbox.startswith("-75") else "B"
    feats = [{"id": f"Survey{tag}{i}-1m",
              "assets": {"dtm": {
                  "href": f"https://x/Survey{tag}{i}-1m-dtm.tif",
                  "type": "image/tiff; application=geotiff"}},
              "bbox": [0, 0, 1, 1]} for i in (1, 2)]
    body = json.dumps({"type": "FeatureCollection", "features": feats,
                       "links": []}).encode()
    return io.BytesIO(body)

_saved_urlopen = urllib.request.urlopen
urllib.request.urlopen = _fake_urlopen
try:
    ncache = tmp / "nrcan" / "discover.json"
    A = (-75.75, 45.35, -75.65, 45.45)
    B = (-123.20, 49.20, -123.10, 49.30)
    dA = ca.discover_dalles(A, None, str(ncache))
    check("bbox A : 1 requête STAC, 2 surveys",
          len(_stac_fetches) == 1 and len(dA) == 2)
    dA2 = ca.discover_dalles(A, None, str(ncache))
    check("bbox A re-run : 0 requête (cache par-bbox relu), même résultat",
          len(_stac_fetches) == 1 and dA2 == dA)
    dB = ca.discover_dalles(B, None, str(ncache))
    check("bbox B (même cache_path) : re-requête, résultat DISJOINT de A",
          len(_stac_fetches) == 2 and not (set(dA) & set(dB)))
    n_caches = len(list((tmp / "nrcan").glob("discover_*.json")))
    check("2 fichiers de cache par-bbox", n_caches == 2)
finally:
    urllib.request.urlopen = _saved_urlopen

print("== 7b. Disjonction des nommages intra-pays (invariant purge, audit #2) ==")
# La purge hors-zone ne supprime que les dalles que PROVIDER.subdir_from_name
# reconnaît. Sûr ssi, dans un même pays (cache lidar/<pays> partagé), le nom
# d'une dalle de X n'est JAMAIS reconnu par le subdir_from_name d'un autre Y.
provs = {}
for f in sorted(_glob.glob(str(_ROOT / "providers" / "*.py"))):
    base = os.path.basename(f)
    if base.startswith("_") or base == "common.py":
        continue
    try:
        mod = _load_provider_module(base)
    except Exception:
        continue
    if hasattr(mod, "CODE"):
        provs[mod.CODE] = mod

def _sample_name(mod):
    # Providers à nommage-formule : on synthétise via dalle_filename.
    for a in [(500, 4500), (15, 29105, 12902), ("sample-survey-1m",)]:
        try:
            nom = mod.dalle_filename(*a)
            if nom:
                return nom
        except NotImplementedError:
            break                  # nommage non-formule (index/COG distant)
        except Exception:
            continue
    # Providers à nommage-index (dalle_filename lève / renvoie None) : ils étaient
    # AUTREFOIS silencieusement sautés, ce qui masquait la collision de-nrw ×
    # de-niedersachsen (même préfixe fédéral dgm1_32_). Ils exposent désormais un
    # SAMPLE_DALLE (vrai nom exemple) pour que la disjonction soit vraiment testée.
    return getattr(mod, "SAMPLE_DALLE", None)

by_country = {}
for code, mod in provs.items():
    by_country.setdefault(getattr(mod, "COUNTRY", ""), []).append(code)

n_paires, n_croisees = 0, 0
for country, codes in sorted(by_country.items()):
    if len(codes) < 2:
        continue
    for cx in codes:
        nom = _sample_name(provs[cx])
        if not nom:
            continue
        for cy in codes:
            if cy == cx:
                continue
            n_paires += 1
            try:
                rec = provs[cy].subdir_from_name(nom)
            except Exception:
                rec = None
            if rec is not None:
                n_croisees += 1
                print(f"    !! {cy} reconnaît une dalle de {cx} : {nom}")
check(f"aucune reconnaissance croisée intra-pays ({n_paires} paires testées)",
      n_paires > 0 and n_croisees == 0)
# Garde-fou inverse du resserrement gb-scotland : ses 3 formats de réf OS
# (1 km, 10 km, 5 km quadrant) doivent TOUJOURS être auto-reconnus.
sc = provs.get("gb-scotland")
check("gb-scotland auto-reconnaît ses 3 formats OS (NR5807/HY20/NS16NE)",
      sc is not None and sc.subdir_from_name("NR5807.tif") == "NR"
      and sc.subdir_from_name("HY20.tif") == "HY"
      and sc.subdir_from_name("NS16NE.tif") == "NS"
      and sc.subdir_from_name("dtm_england_500_4500.tif") is None)

print("== 7c. jp-gsi : géométrie tuile alignée sur le VRT (résolution z15) ==")
jp = provs.get("jp-gsi")
check("largeur tuile / RESOLUTION_M = 256 px exactement",
      jp is not None and abs(jp._STEP / jp.RESOLUTION_M - 256.0) < 1e-9
      and jp.PX_PAR_DALLE == 256)


# ══ 8. GUI × pipeline : jumeaux des types d'ombrage ═══════════════════════════
print("== 8. Ombrages : <select> HTML = OMB_DEFS (app.js) = _SHADING_TYPES ==")
# Trois listes jumelles qui ont DÉJÀ dérivé (e4mstp présent dans OMB_DEFS et le
# pipeline mais absent du <select id='omb-dispo'> → inajoutable depuis le GUI,
# 2026-07-14). On les compare par regex, sans parseur JS/HTML (suffisant : les
# structures sont plates et régulières).
_html = (_ROOT / "gui" / "index.html").read_text(encoding="utf-8")
_mdis = re.search(r'<select id="omb-dispo".*?</select>', _html, re.S)
opts_html = set(re.findall(r'<option value="([^"]+)"', _mdis.group(0))) if _mdis else set()

_appjs = (_ROOT / "gui" / "app.js").read_text(encoding="utf-8")
_mdefs = re.search(r"const OMB_DEFS = \{(.*?)\n\};", _appjs, re.S)
types_js = set(re.findall(r"^\s*'?([a-z0-9]+)'?\s*:\s*\{label:", _mdefs.group(1), re.M)) \
           if _mdefs else set()

types_pipe = set(l2m._SHADING_TYPES)
check("les 3 listes existent",
      bool(opts_html) and bool(types_js) and bool(types_pipe),
      detail=f"html={len(opts_html)} js={len(types_js)} pipe={len(types_pipe)}")
check("HTML == OMB_DEFS", opts_html == types_js,
      detail=f"diff={sorted(opts_html ^ types_js)}")
check("OMB_DEFS == _SHADING_TYPES", types_js == types_pipe,
      detail=f"diff={sorted(types_js ^ types_pipe)}")
# Défaut gamma e4mstp : le GUI SÈME ses defs dans les params émis → doit valoir
# 0.8 (défaut pipeline du composite), pas 2.0 (svf_gamma) qui assombrit tout.
_me4 = re.search(r"e4mstp:\{label:.*?gamma:\{[^}]*def:([\d.]+)", _appjs, re.S)
check("def gamma e4mstp du GUI = 0.8 (aligné pipeline)",
      _me4 is not None and float(_me4.group(1)) == 0.8)

# ══ 9. DFM (mode structures debout) : mécanique + jumeaux GUI ═════════════════
# En prod, le répertoire de lidar2map.py est dans sys.path (script principal) ;
# ici le test charge tout par chemin de fichier → l'ajouter pour que
# `import providers.common` et _discover_providers fonctionnent comme en prod.
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

print("== 9a. las_to_dfm : mur synthétique (classes 1+4) dans un trou de sol ==")
# Le cas des ruines du Var : le mur n'a AUCUN point sol (classe 2) sous lui ;
# ses points sont classés « végétation » (3/4, mesuré ~70% sur le site test)
# et/ou « non classé » (1 — la spec IGN le prévoit pour les murs « plus hauts
# que larges », observé dans QGIS). On mélange 1 et 4 ici pour couvrir les
# deux réalités. Le DTM (classe 2 seule) doit interpoler À PLAT ; le DFM doit
# faire APPARAÎTRE le mur. NB : ~30% des points de la tranche murs sont en
# classe 5 sur le site test → hors défaut (1,3,4), réglable via --dfm-classes.
try:
    import laspy as _laspy
    import numpy as _np
    import rasterio as _rio

    def _laz_synthetique(path):
        # sol plat z=100 sur 40×40 m (pas 0,5 m), TROU sous le mur ;
        # mur : bande x∈[18,20[, y∈[10,30[, points classe 4 à z=101,5 ;
        # butte à RAMPE (pour le socle CSF) : pyramide 6×6 m centrée (31,31),
        # crête 1,5 m, pente 0,5 m/m, classe 1, SANS sol dessous (cas ruine).
        xs, ys, zs, cl = [], [], [], []
        for i in range(80):
            for j in range(80):
                x, y = i * 0.5, j * 0.5
                if 18 <= x < 20 and 10 <= y < 30:
                    continue                      # pas de sol sous le mur
                if 28 <= x <= 34 and 28 <= y <= 34:
                    continue                      # pas de sol sous la butte
                xs.append(x); ys.append(y); zs.append(100.0); cl.append(2)
        for i in range(18 * 2, 20 * 2):
            for j in range(10 * 2, 30 * 2):
                xs.append(i * 0.5); ys.append(j * 0.5)
                zs.append(101.5)
                cl.append(1 if (i + j) % 2 else 4)   # mur : mélange « non classé »
                                                     # + « végétation » (cas réels)
        for i in range(28 * 2, 34 * 2 + 1):
            for j in range(28 * 2, 34 * 2 + 1):
                x, y = i * 0.5, j * 0.5
                xs.append(x); ys.append(y)
                zs.append(100.0 + max(0.0, 1.5 - 0.5 * max(abs(x - 31), abs(y - 31))))
                cl.append(1)
        h = _laspy.LasHeader(point_format=0, version="1.2")
        h.offsets = [0, 0, 0]; h.scales = [0.01, 0.01, 0.01]
        las = _laspy.LasData(h)
        las.x = _np.array(xs); las.y = _np.array(ys); las.z = _np.array(zs)
        las.classification = _np.array(cl, dtype=_np.uint8)
        las.write(str(path))

    from providers import common as _common
    with tempfile.TemporaryDirectory() as _dd:
        _dd = Path(_dd)
        _laz_synthetique(_dd / "syn.las")
        _common.las_to_dfm(_dd / "syn.las", _dd / "dfm.tif",
                           crs_epsg=2154, resolution=0.5)
        _common.las_to_dtm(_dd / "syn.las", _dd / "dtm.tif",
                           crs_epsg=2154, resolution=0.5, classes=(2,))
        # COUPE (socle vide, choix Nico : « une coupe horizontale à 1m50 du
        # sol ») : objets de la tranche seuls, fond nodata, hauteurs toujours
        # référencées à la classe 2.
        _common.las_to_dfm(_dd / "syn.las", _dd / "coupe.tif",
                           crs_epsg=2154, resolution=0.5, classes_ground=())
        def _z_a(p, x, y):
            with _rio.open(p) as ds:
                r, c = ds.index(x, y)
                return float(ds.read(1)[r, c])
        z_dfm = _z_a(_dd / "dfm.tif", 19.0, 20.0)     # centre du mur
        z_dtm = _z_a(_dd / "dtm.tif", 19.0, 20.0)
        check("DFM : le mur apparaît (z ≈ 101,5)", abs(z_dfm - 101.5) < 0.2,
              detail=f"z_dfm={z_dfm:.2f}")
        check("DTM : le mur est gommé (z ≈ 100, interpolé)", abs(z_dtm - 100.0) < 0.2,
              detail=f"z_dtm={z_dtm:.2f}")
        z_cm = _z_a(_dd / "coupe.tif", 19.0, 20.0)    # mur : présent
        z_cf = _z_a(_dd / "coupe.tif", 5.0, 5.0)      # sol nu : nodata
        check("COUPE : mur présent, fond nodata",
              abs(z_cm - 101.5) < 0.2 and z_cf == -9999.0,
              detail=f"mur={z_cm:.2f} fond={z_cf:.0f}")
        # Grille alignée sur bornes NOMINALES (anti-couture VRT) : 40 m à
        # 0,5 m = exactement 80×80 px, origine (0,40).
        _common.las_to_dfm(_dd / "syn.las", _dd / "dfmb.tif",
                           crs_epsg=2154, resolution=0.5, bounds=(0, 0, 40, 40))
        with _rio.open(_dd / "dfmb.tif") as ds:
            check("bounds nominaux → grille exacte 80×80 alignée",
                  ds.width == 80 and ds.height == 80
                  and ds.bounds.left == 0 and ds.bounds.top == 40)
            a = ds.read(1)
            check("valeurs finies ou nodata (jamais 0 résiduel ni inf)",
                  bool(_np.isfinite(a).all())
                  and not bool((a == 0).any()))
        # Socle CSF (--dfm-ground csf) : le tissu mou doit ABSORBER la butte
        # à RAMPE continue — le bloc vertical isolé (le mur) est le cas
        # défavorable pour un tissu, on ne l'asserte pas (sur les sites réels
        # il passe : les vraies ruines ont des éboulis en pente).
        try:
            import CSF as _CSF  # noqa: F401
            _common.las_to_dfm(_dd / "syn.las", _dd / "csf.tif",
                               crs_epsg=2154, resolution=0.5,
                               ground_method="csf", bounds=(0, 0, 40, 40))
            z_bu = _z_a(_dd / "csf.tif", 31.0, 31.0)   # crête de la butte
            z_fd = _z_a(_dd / "csf.tif", 5.0, 5.0)     # sol nu
            check("CSF : butte à rampe absorbée dans le socle (z > 100,7)",
                  z_bu > 100.7, detail=f"z_butte={z_bu:.2f}")
            check("CSF : sol nu inchangé (z ≈ 100)", abs(z_fd - 100.0) < 0.2,
                  detail=f"z_fond={z_fd:.2f}")
            with _rio.open(_dd / "csf.tif") as ds:
                a = ds.read(1)
                check("CSF : grille 80×80, finie, pas de 0 résiduel",
                      ds.width == 80 and bool(_np.isfinite(a).all())
                      and not bool((a == 0).any()))
            # Réglages du tissu ≠ défauts : pass-through de bout en bout
            # (une faute de signature casserait ici, pas en prod).
            _common.las_to_dfm(_dd / "syn.las", _dd / "csf2.tif",
                               crs_epsg=2154, resolution=0.5,
                               ground_method="csf", csf_threshold=0.8,
                               csf_resolution=1.0, csf_rigidness=2,
                               bounds=(0, 0, 40, 40))
            with _rio.open(_dd / "csf2.tif") as ds:
                check("CSF paramétré (t=0.8 r=1.0 g=2) : sortie finie",
                      bool(_np.isfinite(ds.read(1)).all()))
        except ImportError:
            print("  [SKIP] cloth-simulation-filter absent (chemin csf non testé)")
except ImportError as _e_dfm:
    print(f"  [SKIP] laspy/rasterio absents ({_e_dfm})")

print("== 9b. fr-ign-dfm : réglages encodés dans le nom (pattern ombrages) ==")
_dfm = provs.get("fr-ign-dfm")
if _dfm is None:
    # le scan de la section 7 saute *_dfm ? Non : il liste tout module à CODE.
    import importlib as _il
    _dfm = _il.import_module("providers.fr_ign_dfm")
check("défauts → nom SANS suffixe", _dfm.dalle_filename(932, 6257) == "fr_dfm05_932_6257.tif")
_dfm.set_dfm_params(hmin=0.3, hmax=3.0)
_nom = _dfm.dalle_filename(932, 6257)
check("réglages ≠ défauts → suffixe h03-30", _nom == "fr_dfm05_h03-30_932_6257.tif",
      detail=_nom)
check("subdir_from_name reconnaît le nom suffixé", _dfm.subdir_from_name(_nom) == "932")
check("le LAZ persistant reste SANS suffixe (partagé entre essais)",
      _dfm._laz_filename(932, 6257) == "fr_dfm05_932_6257.laz")
_err = False
try:
    _dfm.set_dfm_params(hmin=3.0, hmax=1.0)
except ValueError:
    _err = True
check("hmin >= hmax → ValueError", _err)
# Classes = UN ensemble complet (défaut 1,2,3,4,9,66) ; encodage injectif avec
# séparateurs ; retirer la classe 2 = mode coupe (permis, plus de ValueError).
_dfm.set_dfm_params(hmin=0.4, hmax=2.5, classes=(1, 2, 3, 4, 5, 9, 66))
check("classes ≠ défaut → suffixe séparé injectif",
      "c1-2-3-4-5-9-66_" in _dfm.dalle_filename(932, 6257),
      detail=_dfm.dalle_filename(932, 6257))
_dfm.set_dfm_params(classes=(1, 3, 4))     # sans classe 2 : coupe, ne lève pas
check("socle sans classe 2 → mode coupe (réinjectées seules)",
      _dfm._socle() == () and _dfm._reinjectees() == (1, 3, 4))
_dfm.set_dfm_params(hmin=0.4, hmax=2.5, classes=(1, 2, 3, 4, 9, 66))  # défauts
check("reset défauts → nom nu", _dfm.dalle_filename(932, 6257) == "fr_dfm05_932_6257.tif")
check("socle/réinjectées dérivés du même ensemble",
      _dfm._socle() == (2, 9, 66) and _dfm._reinjectees() == (1, 3, 4))
# Socle CSF : suffixe 'csf_' + réglages du tissu ≠ défauts (ordre fixe t/r/g) ;
# hmin/hmax/classes sont ignorés par le tissu, les encoder créerait des caches
# distincts pour des sorties identiques.
_dfm.set_dfm_params(ground="csf")
_nom = _dfm.dalle_filename(932, 6257)
check("ground=csf défauts → suffixe csf_ seul", _nom == "fr_dfm05_csf_932_6257.tif",
      detail=_nom)
check("subdir_from_name reconnaît le nom csf", _dfm.subdir_from_name(_nom) == "932")
check("variant_tag csf → projet _dfm_csf", _dfm.variant_tag() == "dfm_csf")
_dfm.set_dfm_params(hmin=0.3)          # ignoré par le tissu : nom inchangé
check("csf : hmin/classes non encodés (ignorés par le tissu)",
      _dfm.dalle_filename(932, 6257) == "fr_dfm05_csf_932_6257.tif")
check("csf : le LAZ persistant reste partagé (sans suffixe)",
      _dfm._laz_filename(932, 6257) == "fr_dfm05_932_6257.laz")
# Réglages du tissu (surface CloudCompare) encodés injectifs + reconnus.
_dfm.set_dfm_params(csf_threshold=0.8, csf_rigidness=2)
_nom = _dfm.dalle_filename(932, 6257)
check("csf t=0.8 g=2 → suffixe csf_t08_g2_",
      _nom == "fr_dfm05_csf_t08_g2_932_6257.tif", detail=_nom)
check("subdir_from_name reconnaît le nom csf paramétré",
      _dfm.subdir_from_name(_nom) == "932")
check("variant_tag csf paramétré → projet _dfm_csf_t08_g2",
      _dfm.variant_tag() == "dfm_csf_t08_g2")
_dfm.set_dfm_params(csf_threshold=0.5, csf_rigidness=1, csf_resolution=1.0)
check("csf r=1.0 seul → suffixe csf_r10_",
      _dfm.dalle_filename(932, 6257) == "fr_dfm05_csf_r10_932_6257.tif",
      detail=_dfm.dalle_filename(932, 6257))
for _bad in (dict(ground="tissu"), dict(csf_rigidness=4),
             dict(csf_threshold=9.0)):
    _err = False
    try:
        _dfm.set_dfm_params(**_bad)
    except ValueError:
        _err = True
    check(f"réglage invalide {_bad} → ValueError", _err)
_dfm.set_dfm_params(ground="classes", hmin=0.4, hmax=2.5,
                    classes=(1, 2, 3, 4, 9, 66), csf_threshold=0.5,
                    csf_resolution=0.5, csf_rigidness=1)   # défauts complets
check("reset ground=classes → nom nu",
      _dfm.dalle_filename(932, 6257) == "fr_dfm05_932_6257.tif")

print("== 9c. DFM : jumeaux GUI × pipeline ==")
# La case + réglages existent dans le HTML ; app.js les câble ; _build_cmd les
# traduit en flags ; le dropdown n'expose PAS le jumeau (case seulement) et
# porte les défauts du module (source de vérité unique).
check("HTML : case f-dfm + 7 réglages",
      all(k in _html for k in ('id="f-dfm"', 'id="f-dfm-hmin"',
                               'id="f-dfm-hmax"', 'id="f-dfm-classes"',
                               'id="f-dfm-ground"', 'id="f-dfm-csf-threshold"',
                               'id="f-dfm-csf-resolution"',
                               'id="f-dfm-csf-rigidness"')))
check("app.js : applyProviderDfm + payloads dfm_hmin/dfm_ground/dfm_csf_*",
      "applyProviderDfm" in _appjs and "dfm_hmin" in _appjs
      and "dfm_ground" in _appjs and "dfm_csf_threshold" in _appjs)
_src = (_ROOT / "lidar2map.py").read_text(encoding="utf-8")
check("_build_cmd traduit --dfm/--dfm-hmin/--dfm-ground/--dfm-csf-threshold",
      '"--dfm"' in _src and '"--dfm-hmin"' in _src and '"--dfm-ground"' in _src
      and '"--dfm-csf-threshold"' in _src)
_provs_gui = l2m._discover_providers()
_fr = next((p for p in _provs_gui if p["code"] == "fr-ign"), None)
check("dropdown : fr-ign porte la capacité dfm aux défauts du module",
      _fr is not None and _fr.get("dfm", {}).get("hmin") == _dfm.DFM_HMIN
      and _fr.get("dfm", {}).get("hmax") == _dfm.DFM_HMAX
      and _fr.get("dfm", {}).get("ground") == "classes"
      and _fr.get("dfm", {}).get("csf_threshold") == _dfm.DFM_CSF_THRESHOLD
      and _fr.get("dfm", {}).get("csf_rigidness") == _dfm.DFM_CSF_RIGIDNESS)
check("dropdown : le jumeau fr-ign-dfm n'y est PAS (case, pas entrée)",
      all(p["code"] != "fr-ign-dfm" for p in _provs_gui))

print()
print("TOUS OK" if ok_all else "ÉCHECS — voir ci-dessus")
sys.exit(0 if ok_all else 1)
