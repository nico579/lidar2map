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
_css = (_ROOT / "gui" / "style.css").read_text(encoding="utf-8")
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

        # Chemin ZIP de DfmProvider (swisstopo .las.zip = PK) : le download est
        # un ZIP enveloppant le nuage, écrit sous un nom .tif ; post_fetch doit
        # dézipper (anti zip-slip) → nuage caché → GeoTIFF. Testé avec un
        # provider jetable zipped=True (le mur synthétique zippé).
        import zipfile as _zf
        _Pz = _common.DfmProvider(
            prefix="zz_laz", crs_epsg=2154, resolution=0.5,
            socle_possible=(2, 9, 66),
            defaults=(0.4, 2.5, (1, 2, 3, 4, 9, 66), "classes"),
            bounds_fn=None, discover_fn=None, zipped=True)
        _tile = _dd / _Pz.dalle_filename(0, 0)          # zz_laz_dfm_0_0.tif
        with _zf.ZipFile(_tile, "w", _zf.ZIP_DEFLATED) as z:
            z.write(_dd / "syn.las", arcname="cloud.las")
        _Pz.post_fetch(_tile)                            # PK détecté → dézip
        check("ZIP path : nuage caché extrait (zz_laz_0_0.laz)",
              (_dd / "zz_laz_0_0.laz").exists())
        check("ZIP path : GeoTIFF DFM produit (plus un ZIP)",
              _tile.exists() and _tile.read_bytes()[:2] != b"PK")
        with _rio.open(_tile) as ds:
            _rw, _cw = ds.index(19.0, 20.0)
            check("ZIP path : mur reconstruit depuis le nuage dézippé (z≈101,5)",
                  abs(float(ds.read(1)[_rw, _cw]) - 101.5) < 0.3)
        # Garde CRS/unités (revue LAZ 2026-07-18) : un nuage dont le header
        # déclare un EPSG/unité incompatible avec le provider est REFUSÉ, au
        # lieu d'être converti comme si c'était des mètres (sortie silencieusement
        # fausse, cas USGS ftUS). Lenient sinon : syn.las (sans CRS) passe déjà
        # ci-dessus.
        try:
            import laspy as _lp
            from pyproj import CRS as _pcrs
            _hft = _lp.LasHeader(version="1.4", point_format=6)
            _hft.add_crs(_pcrs.from_epsg(2229))       # California 5, US survey foot
            _lft = _lp.LasData(_hft)
            _lft.x = _np.array([0.0, 1.0]); _lft.y = _np.array([0.0, 1.0])
            _lft.z = _np.array([0.0, 0.0])
            _lft.classification = _np.array([2, 2], dtype=_np.uint8)
            _lft.write(str(_dd / "ft.las"))
            _refuse = False
            try:
                _common.las_to_dfm(_dd / "ft.las", _dd / "ft.tif", crs_epsg=2154,
                                   resolution=0.5, bounds=(0, 0, 40, 40))
            except ValueError:
                _refuse = True
            check("garde CRS : nuage ftUS/EPSG≠provider → REFUSÉ (pas de sortie fausse)",
                  _refuse)
        except ImportError:
            print("  [SKIP] pyproj absent (garde CRS non testé)")
except ImportError as _e_dfm:
    print(f"  [SKIP] laspy/rasterio absents ({_e_dfm})")

print("== 9b. fr-ign-dfm : réglages encodés dans le nom (pattern ombrages) ==")
_dfm = provs.get("fr-ign-dfm")
if _dfm is None:
    # le scan de la section 7 saute *_dfm ? Non : il liste tout module à CODE.
    import importlib as _il
    _dfm = _il.import_module("providers.fr_ign_dfm")
# NOUVEAU nommage 2026-07-17 : préfixe fr_laz05 (laz = source nuage), token de
# MÉTHODE toujours présent dans la dalle (dfm_ = classes, csf_ = tissu),
# variant_tag = laz_dfm / laz_csf (le MNT défaut reste sans marqueur).
check("défauts classes → token dfm_ (fr_laz05_dfm_)",
      _dfm.dalle_filename(932, 6257) == "fr_laz05_dfm_932_6257.tif",
      detail=_dfm.dalle_filename(932, 6257))
check("variant_tag classes défaut = laz_dfm", _dfm.variant_tag() == "laz_dfm")
check("method_label classes = LAZ_DFM (log ≠ 'DFM' figé)",
      _dfm.method_label() == "LAZ_DFM")
check("DOWNLOAD_WORKERS_MAX exposé et < 8 (cap download LAZ)",
      isinstance(getattr(_dfm, "DOWNLOAD_WORKERS_MAX", None), int)
      and _dfm.DOWNLOAD_WORKERS_MAX < 8)
_dfm.set_dfm_params(hmin=0.3, hmax=3.0)
_nom = _dfm.dalle_filename(932, 6257)
check("réglages ≠ défauts → suffixe dfm_h03-30", _nom == "fr_laz05_dfm_h03-30_932_6257.tif",
      detail=_nom)
check("subdir_from_name reconnaît le nom suffixé", _dfm.subdir_from_name(_nom) == "932")
check("variant_tag classes réglé = laz_dfm_h03-30",
      _dfm.variant_tag() == "laz_dfm_h03-30")
check("le nuage caché reste SANS token de méthode (partagé dfm/csf)",
      _dfm._laz_filename(932, 6257) == "fr_laz05_932_6257.laz")
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
check("reset défauts → nom dfm_ nu", _dfm.dalle_filename(932, 6257) == "fr_laz05_dfm_932_6257.tif")
check("socle/réinjectées dérivés du même ensemble",
      _dfm._socle() == (2, 9, 66) and _dfm._reinjectees() == (1, 3, 4))
# Socle CSF : suffixe 'csf_' + réglages du tissu ≠ défauts (ordre fixe t/r/g) ;
# hmin/hmax/classes sont ignorés par le tissu, les encoder créerait des caches
# distincts pour des sorties identiques.
_dfm.set_dfm_params(ground="csf")
_nom = _dfm.dalle_filename(932, 6257)
check("ground=csf défauts → suffixe csf_ seul", _nom == "fr_laz05_csf_932_6257.tif",
      detail=_nom)
check("subdir_from_name reconnaît le nom csf", _dfm.subdir_from_name(_nom) == "932")
check("variant_tag csf → projet laz_csf", _dfm.variant_tag() == "laz_csf")
check("method_label csf = LAZ_CSF (le log dit CSF, pas DFM)",
      _dfm.method_label() == "LAZ_CSF")
_dfm.set_dfm_params(hmin=0.3)          # ignoré par le tissu : nom inchangé
check("csf : hmin/classes non encodés (ignorés par le tissu)",
      _dfm.dalle_filename(932, 6257) == "fr_laz05_csf_932_6257.tif")
check("csf : le nuage caché reste partagé (sans token)",
      _dfm._laz_filename(932, 6257) == "fr_laz05_932_6257.laz")
# Réglages du tissu (surface CloudCompare) encodés injectifs + reconnus.
_dfm.set_dfm_params(csf_threshold=0.8, csf_rigidness=2)
_nom = _dfm.dalle_filename(932, 6257)
check("csf t=0.8 g=2 → suffixe csf_t08_g2_",
      _nom == "fr_laz05_csf_t08_g2_932_6257.tif", detail=_nom)
check("subdir_from_name reconnaît le nom csf paramétré",
      _dfm.subdir_from_name(_nom) == "932")
check("variant_tag csf paramétré → projet laz_csf_t08_g2",
      _dfm.variant_tag() == "laz_csf_t08_g2")
_dfm.set_dfm_params(csf_threshold=0.5, csf_rigidness=1, csf_resolution=1.0)
check("csf r=1.0 seul → suffixe csf_r10_",
      _dfm.dalle_filename(932, 6257) == "fr_laz05_csf_r10_932_6257.tif",
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
check("reset ground=classes → nom dfm_ nu",
      _dfm.dalle_filename(932, 6257) == "fr_laz05_dfm_932_6257.tif")

print("== 9b-bis. ch-swisstopo-dfm : jumeau STAC, socle csf par défaut ==")
_chdfm = provs.get("ch-swisstopo-dfm")
if _chdfm is None:
    import importlib as _il
    _chdfm = _il.import_module("providers.ch_swisstopo_dfm")
check("ch défaut ground=csf (schéma de classes suisse non garanti)",
      _chdfm.DFM_GROUND == "csf")
check("ch défauts → nom ch_laz05_csf_",
      _chdfm.dalle_filename(2600, 1198) == "ch_laz05_csf_2600_1198.tif",
      detail=_chdfm.dalle_filename(2600, 1198))
check("ch bornes = COIN SW (≠ convention Ymax de l'IGN)",
      _chdfm._bounds_nominaux(2600, 1198) == (2600000, 1198000, 2601000, 1199000))
check("ch variant_tag défaut = laz_csf", _chdfm.variant_tag() == "laz_csf")
check("ch method_label défaut = LAZ_CSF", _chdfm.method_label() == "LAZ_CSF")
check("ch DOWNLOAD_WORKERS_MAX exposé et < 8",
      isinstance(getattr(_chdfm, "DOWNLOAD_WORKERS_MAX", None), int)
      and _chdfm.DOWNLOAD_WORKERS_MAX < 8)
check("ch subdir_from_name reconnaît le nom ch",
      _chdfm.subdir_from_name(_chdfm.dalle_filename(2600, 1198)) == "2600")
_chdfm.set_dfm_params(ground="classes")
check("ch mode classes : socle ASPRS (2,9), réinjectées (1,3,4)",
      _chdfm._socle() == (2, 9) and _chdfm._reinjectees() == (1, 3, 4))
_chdfm.set_dfm_params(ground="csf")   # reset au défaut CH

print("== 9b-ter. fr-craig-dfm : 3e jumeau (CRAIG, découverte shapefile) ==")
import importlib as _il2
_cg = _il2.import_module("providers.fr_craig_dfm")
_cgr = _il2.import_module("providers.fr_craig")
check("craig défaut ground=csf (schéma classes CRAIG ≠ IGN)", _cg.DFM_GROUND == "csf")
check("craig défauts → nom fr_craig05_csf_",
      _cg.dalle_filename(7172, 65066) == "fr_craig05_csf_7172_65066.tif",
      detail=_cg.dalle_filename(7172, 65066))
check("craig variant_tag défaut = laz_csf", _cg.variant_tag() == "laz_csf")
check("craig method_label défaut = LAZ_CSF", _cg.method_label() == "LAZ_CSF")
_cg.set_dfm_params(ground="classes")
check("craig mode classes : socle (2), réinjectées bâtiment 6 incluses (3,4,6)",
      _cg._socle() == (2,) and _cg._reinjectees() == (3, 4, 6))
_cg.set_dfm_params(ground="csf")
check("craig registre : campagnes cloud (2019+2021) + MNT (2019) config-as-data",
      len(_common.CRAIG_CLOUD_CAMPAIGNS) >= 2 and len(_common.CRAIG_MNT_CAMPAIGNS) >= 1)
check("craig bounds_fn = lookup (None hors découverte, pas de crash)",
      _cg._bounds_nominaux(1, 1) is None)
check("craig parent fr-craig : post_fetch .asc→GeoTIFF exposé, pas de bounds fig",
      hasattr(_cgr, "post_fetch") and _cgr.CODE == "fr-craig")

print("== 9c. DFM : jumeaux GUI × pipeline ==")
# Le sélecteur de surface + réglages existent dans le HTML ; app.js les câble ;
# _build_cmd les traduit en flags ; le dropdown n'expose PAS le jumeau et porte
# les défauts du module (source de vérité unique).
# Depuis 2026-07-20 le contrôle est une liste MNT/LAZ (f-surface) et non plus
# une case f-dfm : plus précis, et il conditionne CHRONOLOGIQUEMENT la liste des
# providers (LAZ ne propose que les sources DFM-capables). Le contrat de config
# reste le booléen `dfm` → --dfm.
check("HTML : liste de surface MNT/LAZ + 7 réglages",
      all(k in _html for k in ('id="f-surface"', 'value="mnt"', 'value="laz"',
                               'id="f-dfm-hmin"',
                               'id="f-dfm-hmax"', 'id="f-dfm-classes"',
                               'id="f-dfm-ground"', 'id="f-dfm-csf-threshold"',
                               'id="f-dfm-csf-resolution"',
                               'id="f-dfm-csf-rigidness"'))
      and 'id="f-dfm"' not in _html
      and 'name="surface"' not in _html)
# Surface et provider se lisent ensemble (l'un filtre l'autre) : même ligne,
# sans mention annexe qui la surcharge.
_i_surf = _html.find('id="f-surface"')
check("surface et provider sur la même ligne, sans détails annexes",
      0 < _i_surf < _html.find('id="f-provider"')
      and '<div class="row"' not in _html[_i_surf:_html.find('id="f-provider"')]
      and 'id="dfm-source"' not in _html and 'id="surface-hint"' not in _html
      and '"f.src.mnt"' not in _appjs and '"f.surf.hint.mnt"' not in _appjs)
check("app.js : la surface pilote la liste des providers (lazActif/onSurfaceChange)",
      "function lazActif()" in _appjs and "function onSurfaceChange()" in _appjs
      and "dfm: lazActif()" in _appjs
      # tokens essentiels du filtre (pays × surface), pas l'expression exacte
      and "_allProviders.filter" in _appjs
      and "duPays(p)" in _appjs and "p.dfm" in _appjs)
# Le bloc Source vit dans l'onglet LiDAR, AVANT le cadre « 1 — Télécharger »,
# et le cadre ne nomme plus un provider en particulier.
_i_src = _html.find('data-i18n="sec.source"')
_i_dl  = _html.find('id="body-tel"')
check("HTML : bloc Source dans l'onglet LiDAR, avant le cadre Télécharger",
      _html.find('<div id="sec-lidar">') < _i_src < _i_dl and _i_src > 0)
# Le cadre 1 porte le même libellé sur tous les onglets : plus de mention d'un
# fournisseur ni du type d'artefact téléchargé.
check("HTML : cadre 1 identique partout (clé `dl`, plus de `dl.lidar`)",
      "Télécharger les dalles" not in _html and '"dl.lidar"' not in _appjs
      and "Download IGN LiDAR HD tiles" not in _appjs
      # LiDAR + Raster + les deux sources de l'onglet Vectoriel (IGN et OSM)
      and _html.count('data-i18n="dl"') == 4)
check("app.js : applyProviderDfm + payloads dfm_hmin/dfm_ground/dfm_csf_*",
      "applyProviderDfm" in _appjs and "dfm_hmin" in _appjs
      and "dfm_ground" in _appjs and "dfm_csf_threshold" in _appjs)
_src = (_ROOT / "lidar2map.py").read_text(encoding="utf-8")
check("_build_cmd traduit --dfm/--dfm-hmin/--dfm-ground/--dfm-csf-threshold",
      '"--dfm"' in _src and '"--dfm-hmin"' in _src and '"--dfm-ground"' in _src
      and '"--dfm-csf-threshold"' in _src)
# --download-overwrite = VRAI re-download de la source (choix Nico) : le hook
# pre_download (reconstruction depuis le LAZ caché) est SAUTÉ si ecraser, et les
# deux flags overwrite convergent (_force_dl) dans le download de zone. Sans ça,
# un overwrite reconstruisait du cache sans jamais re-tirer le nuage.
check("overwrite → pre_download sauté si ecraser (bypass cache LAZ)",
      "tentative == 1 and not ecraser" in _src)
check("overwrite → les 2 flags convergent (_force_dl) dans le download de zone",
      "_force_dl" in _src
      and "args.telechargement_forcer or args.telechargement_ecraser" in _src)
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
# Le cap de download LAZ remonte du provider (source unique) jusqu'au front :
# entrée registre -> note HTML #dfm-workers-note -> lecture app.js (aucun '3'
# codé en dur côté GUI).
check("dropdown : fr-ign porte le cap de download LAZ (source unique)",
      _fr.get("dfm", {}).get("download_workers_max") == _dfm.DOWNLOAD_WORKERS_MAX
      and _dfm.DOWNLOAD_WORKERS_MAX > 0)
# Le cap borne le champ Workers ; le motif est dans l'infobulle du champ, plus
# dans une mention qui encombrait la ligne (même traitement que le cap de zoom).
check("GUI reflète le cap : borne le champ Workers (pas de 3 en dur)",
      'id="dfm-workers-note"' not in _html
      and "download_workers_max" in _appjs and '"f.dlcap"' in _appjs
      and "wl.title" in _appjs
      and "preLaz" in _appjs and "f-workers-l" in _appjs)
# 2e provider DFM : ch-swisstopo porte la capacité (jumeau détecté), défaut csf,
# et son jumeau ch-swisstopo-dfm est aussi masqué du dropdown.
_ch = next((p for p in _provs_gui if p["code"] == "ch-swisstopo"), None)
check("dropdown : ch-swisstopo porte la capacité dfm (défaut ground=csf)",
      _ch is not None and _ch.get("dfm", {}).get("ground") == "csf")
check("dropdown : le jumeau ch-swisstopo-dfm n'y est PAS",
      all(p["code"] != "ch-swisstopo-dfm" for p in _provs_gui))
# 3e provider DFM : fr-craig (parent raster MNT) porte la capacité (jumeau
# fr-craig-dfm détecté, défaut csf), et le jumeau est masqué du dropdown.
_cgp = next((p for p in _provs_gui if p["code"] == "fr-craig"), None)
check("dropdown : fr-craig porte la capacité dfm (défaut ground=csf)",
      _cgp is not None and _cgp.get("dfm", {}).get("ground") == "csf")
check("dropdown : le jumeau fr-craig-dfm n'y est PAS",
      all(p["code"] != "fr-craig-dfm" for p in _provs_gui))

print("== 9d. Découplage raster / tri pays / zoom natif / cleanup file ==")
# Le pays de CHAQUE provider est résolu depuis la table unique
# providers.common.COUNTRY_NAMES (même ordre que READMEs + carte). Un provider
# sans nom de pays déclaré sortirait au rang 9999 : c'est le drift qu'on guette.
_sans_nom = [p["code"] for p in _provs_gui if p.get("country_rank", 9999) >= 9999]
check("providers : tous les pays ont un nom + un rang (table unique)",
      not _sans_nom, detail=f"sans nom={_sans_nom}")
check("providers : country_fr/country_en remontent au front",
      _fr.get("country_fr") == "France" and _fr.get("country_en") == "France")
check("COUNTRY_NAMES : une seule table (coverage_map l'importe de common)",
      _common.COUNTRY_NAMES is __import__("coverage_map").COUNTRY_NAMES)
check("app.js : dropdown providers groupée par pays, triée par rang",
      "_providerOptionsHtml" in _appjs and "<optgroup" in _appjs
      and "country_rank" in _appjs)
# Découplage : le provider LiDAR ne filtre plus les couches raster ni les
# onglets FR-only. Le pipeline raster résout sa zone en WGS84 pur, il n'a jamais
# eu besoin du provider — le couplage était un artefact GUI.
check("app.js : filterCouchesByCountry supprimé (raster découplé du provider)",
      "filterCouchesByCountry" not in _appjs and "_RASTER_TAB_LABEL" not in _appjs)
check("app.js : couches raster groupées par propriétaire (IGN / USGS)",
      "_RASTER_OWNER" in _appjs and "createElement('optgroup')" in _appjs)
check("raster : main_wmts résout la zone en WGS84, sans PROVIDER",
      "_resoudre_zone_wgs84(args)" in _src
      and "CRS_NATIF" not in _src[_src.find("def _resoudre_zone_wgs84"):
                                  _src.find("def _resoudre_zone_wgs84") + 4000])
# Zoom natif : premier zoom Web Mercator au moins aussi fin que la source.
# 0,5 m → z18 aux latitudes métropolitaines ; au-delà = agrandissement pur.
check("app.js : zoomNatif + bornage du champ Zoom max (miroir du cap raster)",
      "function zoomNatif(" in _appjs and "function applyZoomCap(" in _appjs
      and "156543.033928" in _appjs and "preCap" in _appjs
      # Le bridage est porté par le `max` du champ ; l'explication est dans
      # l'infobulle, pas dans une mention qui encombrait la ligne.
      and 'id="zoom-cap-note"' not in _html
      and "zl.title" in _appjs and '"f.zoomcap"' in _appjs)
# « Générer la carte » (LiDAR) : zoom, format image, qualité et formats de
# fichier tiennent sur une seule ligne.
for _nom, _debut, _fin, _champs in (
        ("LiDAR", 'id="body-mbt"', '<div id="sec-scan"',
         ('id="f-zoom-min-l"', 'id="f-qualite-l"', 'id="f-mbtiles"', 'id="f-sqlitedb"')),
        ("Raster", 'id="body-tuil-s"', '<div id="sec-vecteur"',
         ('id="f-zoom-min-s"', 'id="f-qualite-s"', 'id="f-mbtiles-s"', 'id="f-sqlitedb-s"'))):
    _b = _html[_html.find(_debut):_html.find(_fin)]
    check("générer la carte %s : tous les champs sur une seule ligne" % _nom,
          _b.count('<div class="row">') == 1 and all(k in _b for k in _champs))
# --cleanup-keep-tiles : le nettoyage inter-chunk reste actif, seules les dalles
# du cache partagé sont épargnées, et uniquement si une tâche ULTÉRIEURE de la
# file retélécharge exactement les mêmes (même provider × surface × zone).
check("CLI : --cleanup-keep-tiles déclaré et câblé au nettoyage",
      "--cleanup-keep-tiles" in _src and "nettoyage_garder_dalles" in _src
      and "def _supprimer_fichiers(" in _src and "dossier_dalles=None" in _src)
check("_build_cmd émet --cleanup-keep-tiles depuis cleanup_keep_tiles",
      'cfg.get("cleanup_keep_tiles")' in _src)
check("app.js : la file ne garde les dalles que pour un groupe réutilisé",
      "_signatureDalles" in _appjs and "cleanup_keep_tiles" in _appjs
      and "_signatureDalles(it.cfg)" in _appjs)   # comparaison de signature dans la file

# _supprimer_fichiers : comportement réel sur un cache de dalles + un intermédiaire.
import tempfile as _tf
with _tf.TemporaryDirectory() as _d:
    _cache = Path(_d) / "cache" / "lidar" / "fr"
    _cache.mkdir(parents=True)
    _dalle = _cache / "fr_dalle_0932_6257.tif"; _dalle.write_bytes(b"x")
    _inter = Path(_d) / "ombrage.tif";          _inter.write_bytes(b"y")
    l2m._supprimer_fichiers([str(_dalle), str(_inter)], _cache)
    check("keep-tiles : dalle du cache épargnée, intermédiaire supprimé",
          _dalle.exists() and not _inter.exists())
    _inter.write_bytes(b"y")
    l2m._supprimer_fichiers([str(_dalle), str(_inter)], None)
    check("sans keep-tiles : tout est supprimé (comportement historique)",
          not _dalle.exists() and not _inter.exists())

print("== 9e. Uniformité « Source des données » sur les 4 onglets ==")
# Chaque onglet producteur de carte expose D'ABORD sa source (quoi + d'où),
# PUIS un cadre « 1 — Télécharger » qui ne garde que la mécanique du transfert
# (workers, compression, cache). Avant 2026-07-20 : LiDAR et Raster avaient un
# bloc dédié, mais OSM et IGN Vecteur enterraient leur sélecteur DANS le cadre
# de téléchargement — décocher « Télécharger » masquait donc la sélection, qui
# sert encore à l'étape suivante.
_ONGLETS = [
    ("LiDAR",     '<div id="sec-lidar">',                 "body-tel",     "f-provider"),
    ("Raster",    '<div id="sec-scan" class="hidden">',    "body-tel-s",   "f-couche"),
    ("Vectoriel", '<div id="sec-vecteur" class="hidden">', "body-tel-v",   "wfs-dispo"),
]
for _nom, _ancre, _corps_dl, _selecteur in _ONGLETS:
    _i0 = _html.find(_ancre)
    _fin = min([x for x in (_html.find('<div id="sec-', _i0 + 10), len(_html)) if x > 0])
    _bloc = _html[_i0:_fin]
    _i_src = _bloc.find('data-i18n="sec.source"')
    _i_sel = _bloc.find('id="%s"' % _selecteur)
    _i_dl  = _bloc.find('id="%s"' % _corps_dl)
    check("onglet %s : Source, puis sélecteur, puis Télécharger" % _nom,
          0 <= _i_src < _i_sel < _i_dl,
          detail="source=%d sel=%d dl=%d" % (_i_src, _i_sel, _i_dl))
check("chaque onglet nomme son service amont (WMTS raster, WFS/PBF vecteur)",
      all(k in _appjs for k in ('"svc.wmts.fr"', '"svc.wmts.us"',
                                '"vsrc.ign"', '"vsrc.osm"'))
      and 'data-i18n="vsrc.ign"' in _html and 'data-i18n="vsrc.osm"' in _html)

print("== 9f. Onglets vecteur fusionnés (IGN WFS + OSM Geofabrik) ==")
# Les deux onglets avaient le même squelette et les mêmes livrables : un seul
# onglet « Vectoriel » avec un sélecteur de source. Le CONTRAT ne bouge pas —
# cfg.type vaut toujours 'vecteur' ou 'osm', donc _build_cmd est inchangé.
check("un seul onglet vecteur : le radio t-osm a disparu",
      'id="t-osm"' not in _html and 'id="sec-osm"' not in _html
      and 'id="t-vecteur"' in _html and '"t.vect":"Vectoriel"' in _appjs)
check("sélecteur de source aux valeurs du contrat ('vecteur' | 'osm')",
      'name="vsrc"' in _html
      and 'id="v-ign" value="vecteur"' in _html
      and 'id="v-osm" value="osm"' in _html)
check("getConfig dérive le type de la source",
      "_vecteurSource()" in _appjs and "type === 'vecteur'" in _appjs
      and "function _vecteurSource()" in _appjs)
check("loadConfig : une config 'osm' d'avant la fusion se recharge",
      "sr('type', 'vecteur');" in _appjs and "sr('vsrc', cfg.type);" in _appjs)
# Sélection des couches/thèmes : shuttle « disponibles ↔ choisis », même idiome
# que la liste d'ombrages. 17 couches WFS en cases à cocher demandaient de
# balayer plusieurs lignes pour lire l'ensemble retenu. Pas de panneau de
# réglages : contrairement aux ombrages, ces entrées n'ont pas de paramètres.
check("vecteur : couches et thèmes en shuttle, plus en cases à cocher",
      all(k in _html for k in ('id="wfs-dispo"', 'id="wfs-liste"',
                               'id="osm-dispo"', 'id="osm-liste"'))
      and 'id="wfs-checks"' not in _html and 'id="osm-tag-checks"' not in _html
      and "name=wfs" not in _appjs and "name=osm_tag" not in _appjs)
check("shuttle : état unique re-rendu, pas de déplacement d'<option>",
      "_shuttleData" in _appjs and "function shuttleRender(" in _appjs
      and "function listeAdd(" in _appjs and "function listeDel(" in _appjs
      and "shuttleValeurs('osm')" in _appjs and "shuttleValeurs('wfs')" in _appjs)
check("shuttle : restauration tolérante (liste ou chaîne espacée héritée)",
      ".split(' ')" in _appjs   # accepte la chaîne espacée héritée du CLI
      and "shuttleSet('osm', cfg.osm_tags_sel)" in _appjs
      and "shuttleSet('wfs', cfg.wfs_couches_sel)" in _appjs)
# La source ne recolore plus l'onglet : IGN et OSM sont deux sources du même
# onglet depuis la fusion, pas deux contextes.
# Même ORDRE de formats partout où l'on produit du vecteur : données brutes,
# dérivé raster, carte vecteur. Fusion et IGN l'appliquaient déjà, OSM plaçait
# Mapsforge en tête.
_ORDRE = ["geojson", "geojson-raw", "transparent", "map"]
for _nom, _ids in (
        ("IGN",    ["f-fusion-gz", "f-fusion-gz-raw", "f-vec-transparent", "f-tuiles-v"]),
        ("OSM",    ["f-osm-geojson", "f-osm-geojson-raw", "f-osm-transparent", "f-map"]),
        ("Fusion", ["f-fusion-gz2", "f-fusion-gz2-raw", "f-fusion-transparent", "f-fusion-map"])):
    _pos = [_html.find('id="%s"' % i) for i in _ids]
    check("formats %s : ordre commun (brut, transparent, Mapsforge)" % _nom,
          all(p > 0 for p in _pos) and _pos == sorted(_pos),
          detail=" < ".join(_ids))
# --workers est unique en CLI, la GUI a un champ par type : ne le reporter que
# sur le type réellement lancé. Sinon un run LiDAR `--workers 8` repeuplait le
# champ vecteur (plafonné à 4) au rechargement de l'historique. Les jumeaux
# osm_tags_sel / wfs_couches_sel du même dict avaient déjà ce conditionnement.
check("cfg depuis argv : --workers ne va qu'au champ du type lancé",
      # CONTRAT : chaque workers_* est conditionné au type lancé (tokens du gate)
      all(k in _src for k in ('if t == "lidar" else 8',
                              'if t == "scan" else 8',
                              'if t == "osm" else 4')))
check("vecteur : workers plafonné à 4 dans le champ ET à la relecture",
      'id="f-workers-v" value="4" min="1" max="4"' in _html
      and 'min(_arg_int("--workers", default=4), 4) if t == "vecteur"' in _src
      and '"max4"' not in _appjs and '"pbfpar"' not in _appjs)
check("row-simplif-fusion : plus de double attribut class",
      '<div class="row hidden" id="row-simplif-fusion"' in _html
      and 'id="row-simplif-fusion" class="hidden"' not in _html)
check("vecteur : pas de recoloration selon la source",
      "type-osm" not in _css and "type-osm" not in _appjs
      and ".v-osm .section-hd" not in _css
      and ".section.v-osm" not in _css)
check("les contrôles des 2 sources gardent leurs ids (contrat intact)",
      all(k in _html for k in ('id="f-tel-osm"', 'id="f-workers-osm"',
                               'id="f-tuiles-osm"', 'id="f-map"',
                               'id="f-osm-geojson"', 'id="f-osm-transparent"',
                               'id="f-tel-v"', 'id="f-workers-v"',
                               'id="f-fusion-gz"', 'id="f-vec-transparent"',
                               'id="f-tuiles-v"', 'id="f-simplif-v"')))
check("blocs .v-ign / .v-osm échangés par onVecteurSource",
      "function onVecteurSource()" in _appjs
      and "#sec-vecteur .v-ign" in _appjs and "#sec-vecteur .v-osm" in _appjs
      and _html.count('class="section v-osm hidden"') == 2
      and _html.count('class="section v-ign"') == 2)
check("applyType ne cherche plus de section 'osm'",
      "['lidar','scan','vecteur','fusion','decoupe']" in _appjs)
# _build_cmd doit rester capable de traiter les deux types, inchangé.
check("_build_cmd : les 2 branches vecteur/osm intactes",
      'elif t == "osm":' in _src and 'elif t == "vecteur":' in _src
      and 'cmd.append("--osm")' in _src and 'cmd.append("--vector")' in _src)
check("raster : le service suit la couche, plus le provider LiDAR",
      "svc.wmts.us" in _appjs and "getElementById('hd-couche')" in _appjs)
# Pays : déclaré dans la ZONE (partagée par tous les onglets), plus déduit du
# provider LiDAR. Il cadre le géocodage des villes, la liste des providers et
# les couches raster. Entrée « Tous » indispensable : OSM est mondial.
check("zone : sélecteur de pays alimenté par les providers",
      'id="f-pays"' in _html and "function buildPays(" in _appjs
      and "country_rank" in _appjs)
# lidar2map est un outil LiDAR : OSM et raster y sont des compléments du LiDAR.
# Un pays sans provider LiDAR est donc hors périmètre — pas d'entrée « tous
# pays », et pas de chemin de géocodage mondial à maintenir pour elle.
# Zone : liste déroulante au lieu de 5 radios, et tous les champs du mode sur
# la même ligne que Pays + Zone. Les libellés par mode sont supprimés (la liste
# et le placeholder les portent) ; les aides longues (dep/region) restent hors
# ligne, affichées par applyMode.
check("zone : mode en liste déroulante, plus en radios",
      'id="f-mode"' in _html and 'name="mode"' not in _html
      and "function _modeActif()" in _appjs
      and "input[name=mode]" not in _appjs)
check("zone : pays, mode et champs sur la même ligne",
      _html.count('class="z-zone"') + _html.count('class="z-zone hidden"') == 5
      and _html.find('id="f-pays"') < _html.find('id="f-mode"')
                                    < _html.find('id="z-ville"')
      and ".z-zone{display:inline-flex" in _css)
check("zone : aides dep/region hors ligne, pilotées par applyMode",
      'id="z-dep-hint"' in _html and 'id="z-region-hint"' in _html
      and "['dep','z-dep-hint']" in _appjs)
# Department et Région sont des découpages FRANÇAIS (_GEOFABRIK = codes INSEE,
# geocoder_* rend du Lambert 93). Il n'existe pas d'équivalent ailleurs : la
# liste des régions ne pouvait pas « suivre le pays », il faut retirer les modes.
check("zone : Department/Région désactivés hors de France",
      "_MODES_FR" in _appjs and "function _majModesDisponibles()" in _appjs
      and '"mode.fronly"' in _appjs
      and "_majModesDisponibles();" in _appjs)
check("les régions restent une notion française (aucune donnée étrangère)",
      "return sorted(set(_GEOFABRIK.values()))" in _src)
# Garde-fou OSM : le téléchargement auto est franco-centré (Lambert 93 +
# geo.api.gouv.fr + table INSEE + URL .../europe/france). Hors de France on
# refuse, au lieu de tirer 4 Go de PBF français pour un overlay vide. --source
# reste ouvert à tous les pays → le garde est sur la branche AUTO uniquement.
# Vérifié à l'exécution (provider ch → refus sans download) ; ici on ancre que
# le garde est bien conditionné au pays et laisse --source passer.
check("OSM auto-download refusé hors de France (--source épargné)",
      'elif (getattr(PROVIDER, "COUNTRY", "fr") or "fr").lower() != "fr":' in _src
      and "OSM auto-download is France-only" in _src
      and "--source <file>.pbf" in _src)
# --zone-bbox est WGS84 (W,S,E,N) sur TOUS les modes. main() (lidar/osm) le lisait
# comme du Lambert 93 en mètres — franco-centré et cassé pour la GUI (champ unique
# en degrés) et hors de France. Conversion WGS84→CRS natif au parse, comme le mode
# Département. Vérifié à l'exécution : fr-ign→EPSG:2154, ch→EPSG:2056.
check("--zone-bbox lu en WGS84 puis converti au CRS natif du provider",
      'lon1, lat1, lon2, lat2 = parts' in _src          # parse en degrés WGS84
      and "_wgs84_vers_natif, lon1, lat1, lon2, lat2" in _src   # → CRS natif
      and '"Lambert 93 bbox in metres' not in _src)
# Config vs code : le CRS cible vient du PROVIDER, jamais écrit en dur. Un seul
# helper _wgs84_vers_natif / _natif_vers_wgs84 ; le repli pur-Python (formules
# Lambert 93) est BORNÉ à la France, il lève pour tout autre CRS au lieu de
# rendre des coordonnées françaises fausses. Plus de blocs try/except dupliqués.
check("conversion WGS84<->natif centralisée + repli France borné",
      "def _wgs84_vers_natif(" in _src
      and "def _natif_vers_wgs84(" in _src
      and "def _exiger_pyproj_hors_france(" in _src
      and 'if crs != "EPSG:2154":' in _src)   # le garde France = CONTRAT du repli
check("les sites de zone routés sur les helpers (plus de try/except dupliqués)",
      # geocoder_ville, gps, dept, region, bbox : tous via _wgs84_vers_natif ;
      # l'ancien nom trompeur _lamb93_to_wgs84_safe a disparu. On compte les
      # appels (≥ 5 sites) plutôt que d'épingler chaque site au caractère près.
      _src.count("_wgs84_vers_natif") >= 6   # 1 def + ≥5 appels
      and "_lamb93_to_wgs84_safe" not in _src
      and "_lamb93_to_merc" not in _src)
check("--zone-bbox : metavar/help WGS84 sur tous les modes (plus de X1,Y1)",
      'bbox_metavar="W,S,E,N"' in _src
      and 'bbox_metavar="X1,Y1,X2,Y2"' not in _src
      and "WGS84 bbox in degrees" in _src)
check("--zone-bbox : centre natif calculé (détection dept OSM en mode bbox)",
      "cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2" in _src)
# --cache-dir : racine UNIQUE de tous les caches, déplaçable d'un geste (12 sites
# repointés depuis DOSSIER_CACHE au lieu de DOSSIER_TRAVAIL/"cache" en dur). Posé
# tôt dans chaque main via _appliquer_cache_dir. Vérifié à l'exécution :
# dalles → <cd>/lidar/fr, WMTS → <cd>/ign_raster. --tiles-dir reste le réglage
# fin des seules dalles LiDAR (prioritaire), CLI-only.
check("--cache-dir : racine de cache unique et déplaçable",
      "DOSSIER_CACHE = DOSSIER_TRAVAIL / \"cache\"" in _src
      and "def _appliquer_cache_dir(args):" in _src
      and 'parser.add_argument("--cache-dir", "--dossier-cache"' in _src
      # une SEULE occurrence du motif en dur = la définition de DOSSIER_CACHE ;
      # tous les sites d'accès passent désormais par DOSSIER_CACHE.
      and _src.count('DOSSIER_TRAVAIL / "cache"') == 1)
check("--cache-dir : appliqué au début des 3 mains zone-based",
      _src.count("_appliquer_cache_dir(args)") >= 3)
# GUI : le champ cache est global (Projet, à côté de « Dossier sortie »), plus
# dans le cadre Télécharger. « Compresser » reste LiDAR-only. --tiles-dir n'a
# plus de champ GUI (réglage fin CLI).
_i_out = _html.find('id="f-dossier"')
_i_cd  = _html.find('id="f-cache-dir"')
check("GUI : champ Dossier cache dans Projet, à côté de Dossier sortie",
      0 < _i_out < _i_cd < _html.find('<div id="sec-lidar">')
      and 'id="f-dossier-dalles"' not in _html
      and 'data-i18n="extcache"' not in _html)
check("GUI : cache_dir sauvé/restauré + émis par _build_cmd (tous types)",
      # champ lu ET restauré (tokens, pas l'expression exacte) + CONTRAT CLI émis
      "'f-cache-dir'" in _appjs and "cfg.cache_dir" in _appjs
      and '"--cache-dir"' in _src)
check("pas d'entrée « tous pays » (hors périmètre d'un outil LiDAR)",
      '"z.pays.tous"' not in _appjs
      and '<option value="">' not in _appjs
      and 'country = (country or "fr").lower()' in _src)
check("géocodage : scopé par le pays de la zone, plus par le provider",
      "const country = _paysActif();" in _appjs
      and "psel.dataset.country) || 'fr'" not in _appjs)
check("pays : filtre providers ET couches raster",
      "function onPaysChange()" in _appjs
      and "function filtrerCouchesParPays()" in _appjs
      and "filtrerCouchesParPays();" in _appjs)
# Pays sans provider DFM : la combinaison pays × LAZ serait vide → l'option LAZ
# est désactivée et porte son motif dans son propre libellé (plus de mention
# séparée sur la ligne, plus de liste de providers vide).
check("pays sans source LAZ : l'option LAZ est désactivée, motif dans le libellé",
      "optLaz.disabled" in _appjs and '"f.surf.nolaz"' in _appjs
      and "optLaz.textContent" in _appjs)
check("cfg : le pays est sauvegardé et restauré AVANT le provider",
      # champ lu (token) + INVARIANT d'ordre : pays restauré avant provider
      # (sinon il refiltre la liste et efface le provider sauvé).
      "g('f-pays')" in _appjs
      and 0 <= _appjs.find("if (cfg.pays !== undefined)") < _appjs.find("if (cfg.provider) {"))
# Chaque pays proposé a au moins un provider (la liste EN vient) : aucune
# sélection ne peut produire une liste de providers vide.
_pays_dispo = {p["country"] for p in _provs_gui if p["country"]}
check("tout pays proposé a au moins un provider",
      all(any(p["country"] == c for p in _provs_gui) for c in _pays_dispo),
      detail=f"{len(_pays_dispo)} pays")
# Le découpage à priori dépend du VOLUME, donc de la source : il vient après
# elle sur les deux onglets qui l'exposent (LiDAR et Raster). Le raster l'avait
# en premier, avant même de savoir quelle couche on tire.
for _nom, _ancre in (("LiDAR", '<div id="sec-lidar">'),
                     ("Raster", '<div id="sec-scan" class="hidden">')):
    _i0 = _html.find(_ancre)
    _fin = min([x for x in (_html.find('<div id="sec-', _i0 + 10), len(_html)) if x > 0])
    _bloc = _html[_i0:_fin]
    check("onglet %s : découpage à priori APRÈS la source" % _nom,
          0 <= _bloc.find('data-i18n="sec.source"') < _bloc.find('data-i18n="split0"'))
# L'onglet couvre MNT ET LAZ depuis le sélecteur de surface : « LiDAR MNT » ne
# décrivait plus que la moitié de ce qu'il fait.
check("onglet LiDAR : libellé sans 'MNT' (il traite aussi le LAZ)",
      '"t.lidar":"LiDAR"' in _appjs
      and "LiDAR MNT" not in _appjs and "LiDAR MNT" not in _html
      and "LiDAR DEM" not in _appjs)
# Un seul nom pour l'étape de production. « Calculer les tuiles » n'était exact
# que pour les sorties raster : OSM et IGN Vecteur produisent un .map Mapsforge
# et du GeoJSON, pas des tuiles.
# NB : on teste les VALEURS i18n et les libellés du HTML, pas le texte brut du
# .js — un commentaire qui documente l'ancien nom est légitime et ne doit pas
# faire échouer le test.
check("étape de production : un seul nom « Générer la carte » partout",
      '"map2":"2 — Générer la carte"' in _appjs and '"map3"' in _appjs
      and '"2 — Calculer les tuiles"' not in _appjs
      and '"3 — Calculer les tuiles"' not in _appjs
      and '"2 — Compute tiles"' not in _appjs
      and "Calculer les tuiles" not in _html
      and '"gen.map"' not in _appjs and 'data-i18n="gen.map"' not in _html
      and _html.count('data-i18n="map2"') == 3)   # raster + osm + vecteur
# IGN Vecteur : répartition des formats calquée sur le pipeline, pas sur
# l'apparence. .geojson.gz/.geojson sont ÉCRITS par telecharger_wfs (étape 1,
# écrasement --download-overwrite) ; .map et transparent-raster en dérivent
# (étape 2, écrasement --tiles-overwrite). Les mettre tous en étape 2 aurait
# décorrélé les GeoJSON de leur case Écraser.
_i_v = _html.find('<div id="sec-vecteur" class="hidden">')
_bloc_v = _html[_i_v:]
_i_tel_v = _bloc_v.find('id="body-tel-v"')
_i_map_v = _bloc_v.find('id="body-map-v"')
check("vecteur : TOUS les formats regroupés dans « Générer la carte »",
      _i_map_v < _bloc_v.find('id="f-fusion-gz"')
      and _i_map_v < _bloc_v.find('id="f-vec-transparent"')
      and _i_map_v < _bloc_v.find('id="f-tuiles-v"')
      and _i_tel_v < _i_map_v)
# Les GeoJSON sont écrits PAR le téléchargement : marqués « natif » plutôt que
# grisés — le choix compressé/non compressé reste libre, seul le fait qu'au
# moins un des deux sorte est imposé, et l'UI tient cet invariant.
check("vecteur : GeoJSON marqués natifs, invariant « au moins un » tenu",
      _html.count('data-i18n="fmt.natif"') == 2
      and "function _garantirGeojson(" in _appjs
      and 'onchange="_garantirGeojson(this)"' in _html
      and 'if (not fmts)' not in _appjs)
check("vecteur : le fallback backend existe toujours (miroir de l'UI)",
      'if not fmts: fmts = ["gz"]' in _src)
check("vecteur : Mapsforge est un format, plus un cadre séparé",
      'data-i18n="fmt.mapsforge"' in _html
      and "'map-v-detail'" in _appjs
      and "'row-simplif-v'" not in _appjs)
# Les gates de _build_cmd doivent rester ceux du pipeline : gz/geojson
# inconditionnels, map et overwrite gatés sur tuiles_v.
check("_build_cmd vecteur : GeoJSON toujours émis, dérivés gatés par la case",
      # CONTRAT (tokens) : gz inconditionnel, map gaté sur carte_v+tuiles_v.
      'fmts.append("gz")' in _src and 'fmts.append("map")' in _src
      and '_carte_v' in _src and '"carte_v"' in _src)

print("== 9g. Cases d'activation uniformes sur tous les cadres ==")
# Les cadres « 0 — Découpage » (LiDAR + Raster) et « 2 — Générer la carte »
# (vecteur IGN) n'avaient pas de case, contrairement à tous les autres.
check("découpage à priori : case + corps repliable sur les 2 onglets",
      'id="f-priori"' in _html and 'id="body-priori"' in _html
      and 'id="f-priori-s"' in _html and 'id="body-priori-s"' in _html
      # câblage toggle (tokens présents), pas l'espacement exact du tableau
      and "'f-priori'" in _appjs and "'body-priori'" in _appjs
      and "'f-priori-s'" in _appjs and "'body-priori-s'" in _appjs)
# La case est la source UNIQUE de l'état on/off : décochée, aucun --split-*
# n'est émis même si des valeurs traînent dans les champs.
check("découpage : la case gouverne l'émission, pas les valeurs saisies",
      # la case decoupe/decoupe_s conditionne l'émission des --split-* (tokens)
      'cfg.get("decoupe"' in _src and 'cfg.get("decoupe_s"' in _src)
check("vecteur : case sur « Générer la carte », défaut coché",
      'id="f-carte-v" checked' in _html          # attribut HTML = stable
      and "'f-carte-v'" in _appjs and "'body-map-v'" in _appjs
      and "carte_v" in _appjs)
check("les 3 cases se sauvegardent et se restaurent",
      # lues dans getConfig + restaurées dans loadConfig (tokens, pas l'espacement)
      "f-priori'" in _appjs and "cfg.decoupe" in _appjs
      and "'f-carte-v'" in _appjs and "cfg.carte_v" in _appjs)

print("== 9h. Masquages selon le pays + bouton Aide ==")
# Onglet Raster masqué si le pays n'a aucune couche (ni IGN ni USGS) : on cache
# le radio + le libellé, et on bascule sur LiDAR si l'onglet était actif.
check("onglet Raster masqué quand le pays n'a pas de couche raster",
      "getElementById('lbl-raster')" in _appjs
      and "getElementById('t-scan')" in _appjs
      and "premiere !== null" in _appjs
      and 't-lidar' in _appjs)
# Source IGN (WFS) masquée hors de France ; il ne reste qu'OSM.
check("vecteur : source IGN masquée hors de France",
      "function _majSourcesVecteur()" in _appjs
      and "label[for=\"v-ign\"]" in _appjs
      and "_paysActif() === 'fr'" in _appjs
      # appelée au changement de pays ET au chargement/init
      and _appjs.count("_majSourcesVecteur()") >= 3)
# Les vestiges des notes remplacées par le masquage ont disparu.
check("notes remplacées par le masquage : vestiges retirés",
      "vsrc-note" not in _html and '"vsrc.ignfr"' not in _appjs
      and "pays-note" not in _html and '"z.pays.noraster"' not in _appjs)
# Bouton Aide : UNE seule source = get_help() (docstring du module). Aucun texte
# d'aide en dur dans la GUI ; le modal est peuplé au runtime.
check("bouton Aide : source unique get_help() (docstring module)",
      'id="btn-help"' in _html and 'id="help-modal"' in _html
      and 'id="help-text"' in _html
      and "function afficherAide()" in _appjs
      and "pywebview.api.get_help()" in _appjs
      and "def get_help(self):" in _src
      and "__name__].__doc__" in _src)

print("== 9i. Séparation cache/production + onglet Usage ==")
_common = (_ROOT / "providers" / "common.py").read_text(encoding="utf-8")
# Règle Nico : le .tif LAZ/DFM est un PRODUIT (calculé du nuage) → production ;
# le .tif MNT et le nuage .laz sont des downloads → cache. Le routage du dossier
# des .tif vit dans _dossier_dalles_actif.
check("dalles : MNT→cache, LAZ/DFM→production (routage par nature)",
      "def _dossier_dalles_actif" in _src
      and 'PROVIDER.CODE.endswith("-dfm")' in _src
      and "DOSSIER_PRODUCTION / LIDAR_SUBDIR" in _src
      and "DOSSIER_CACHE / LIDAR_SUBDIR" in _src)
# Le nuage .laz reste au cache même quand le .tif descend en production.
check("nuage .laz : reste au cache indépendamment du .tif produit",
      "def set_cloud_cache_dir" in _common
      and "def _cloud_path" in _common
      and "self.cloud_cache_dir" in _common
      and all("set_cloud_cache_dir = _P.set_cloud_cache_dir"
              in (_ROOT / "providers" / f"{p}.py").read_text(encoding="utf-8")
              for p in ("fr_ign_dfm", "ch_swisstopo_dfm", "fr_craig_dfm")))
check("cœur : cloud_cache_dir posé (cache) sauf --dossier-dalles forcé",
      "def _configurer_cloud_cache" in _src
      and "_configurer_cloud_cache(args)" in _src
      and "None if args.dossier_dalles else DOSSIER_CACHE / LIDAR_SUBDIR" in _src)
check("--production-dir : flag + défaut + émission GUI + relecture argv",
      'DOSSIER_PRODUCTION = DOSSIER_TRAVAIL / "production"' in _src
      and '"--production-dir", "--dossier-production"' in _src
      and 'cmd += ["--production-dir"' in _src
      and '"production_dir": _arg("--production-dir"' in _src)
# cache et production peuvent être sur des volumes différents (--production-dir) :
# le déplacement du nuage tombe en cross-device (EXDEV), fallback shutil.move.
check("relocation nuage : fallback cross-device (shutil.move)",
      "shutil.move(str(chemin), str(cloud))" in _common)
# GUI : champ production dans Projet, sur la ligne des racines (sortie/cache/
# production = les 3 tiers de l'onglet Usage). Placé juste après le dossier cache.
check("GUI : champ production (Projet, à côté du cache), sauvé/restauré",
      'id="f-production-dir"' in _html
      and "ouvrirDossier('f-production-dir','production')" in _html
      and "production_dir: g('f-production-dir')" in _appjs
      and "s('f-production-dir'" in _appjs
      # dans le cadre Projet : après le cache, avant la section Zone
      and _html.find('id="f-cache-dir"') < _html.find('id="f-production-dir"')
                                         < _html.find('data-i18n="sec.zone"'))
# Bouton « … » des 3 dossiers : ouvre le dossier correspondant dans l'explorateur
# (champ vide → racine par défaut du tier), réutilise open_folder.
check("bouton « … » : ouvre le dossier correspondant (explorateur)",
      "ouvrirDossier('f-dossier','output')" in _html
      and "ouvrirDossier('f-cache-dir','cache')" in _html
      and "ouvrirDossier('f-production-dir','production')" in _html
      and "function ouvrirDossier(" in _appjs
      and "pywebview.api.open_dir(" in _appjs
      and "def open_dir(self" in _src
      and "self.open_folder(p)" in _src)
# CORRECTION à la note : --cleanup-keep-tiles est GARDÉ. La séparation le rend
# inutile en mode LAZ (le .laz reconvertit sans re-download) mais PAS en MNT, où
# le .tif téléchargé est évincé par --cleanup → une tâche +file re-téléchargerait.
check("--cleanup-keep-tiles conservé (nécessaire en mode MNT)",
      '"--cleanup-keep-tiles"' in _src)
# Onglet Usage : LECTURE SEULE. get_usage marche les 3 tiers ; open_folder réutilisé.
check("onglet Usage : lecture seule, 3 tiers, open_folder",
      'id="btn-usage"' in _html and 'id="usage-modal"' in _html
      and "function afficherUsage()" in _appjs
      and "pywebview.api.get_usage(" in _appjs
      and "def get_usage(self" in _src
      and "pywebview.api.open_folder" in _appjs)

print()
print("TOUS OK" if ok_all else "ÉCHECS — voir ci-dessus")
sys.exit(0 if ok_all else 1)
