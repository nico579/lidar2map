# Tests de régression des calculs scientifiques de lidar2map.py
# (kernels Horn, nodata, LRM, SVF, openness, RRIM, passe multi-sorties).
# Usage : python Tests/_test_corrections.py  (depuis n'importe quel cwd)
import sys, math, tempfile, importlib.util
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

# Importer lidar2map sans déclencher main() : on charge le module par spec.
# lidar2map n'exécute main() que sous __main__, l'import est sûr — mais le
# bootstrap peut relancer pip ; on neutralise via LIDAR2MAP_BOOTSTRAP=none.
import os
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

print("== 1. Kernels Horn : nodata, halo, slope ==")
ND = -9999.0
# DEM plan incliné vers l'est (z = -x), pente atan(1/0.5? non : dz/dx = -1 par
# mètre si on met -0.5 par pixel de 0.5 m) — ici dz = -1 m / px de 0.5 m → pente 63.43°
H, W = 64, 64
xx = np.arange(W, dtype=np.float32)
dem = np.tile(-xx, (H, 1)) * 1.0   # -1 m par pixel
# Trou nodata au centre
dem_nd = dem.copy()
dem_nd[30:34, 30:34] = ND

hs = l2m._hillshade_numpy(dem, azimuth_deg=90.0, altitude_deg=45.0,
                          dx=0.5, dy=0.5, nodata=None)
# pente = atan(1/0.5) = 63.43° ; soleil est à 45° → hs = cos(45-63.43... )
# formule : cos_z*cos_s + sin_z*sin_s*cos(0) = cos(zenith - slope)
slope_rad = math.atan(1.0 / 0.5)
expected = math.cos(math.radians(45.0) - slope_rad)  # zenith=45°
v_expected = int(max(0.0, min(1.0, expected)) * 254 + 1)
check("hillshade valeur attendue (plan incliné, soleil Est)",
      abs(int(hs[32, 32]) - v_expected) <= 1, f"got {hs[32,32]} exp {v_expected}")

hs_nd = l2m._hillshade_numpy(dem_nd, azimuth_deg=90.0, altitude_deg=45.0,
                             dx=0.5, dy=0.5, nodata=ND)
check("hillshade nodata centre → 0", np.all(hs_nd[30:34, 30:34] == 0))
# Halo : les pixels ADJACENTS au trou restent proches de la valeur du plan
# (la convention voisin→centre divise le gradient par 2 au bord : écart modéré
# attendu). Avant fix, le voisin -9999 basculait l'aspect → valeurs ~1.
ref = int(hs[10, 10])
ring = [hs_nd[29, 31], hs_nd[35, 31], hs_nd[31, 29], hs_nd[31, 35]]
check("hillshade pas de halo autour du nodata",
      all(abs(int(v) - ref) <= 20 for v in ring), f"ring={ring} ref={ref}")
# Loin du trou, identique au DEM sans trou
check("hillshade inchangé loin du nodata", hs_nd[10, 10] == hs[10, 10])

sl = l2m._slope_numpy(dem, dx=0.5, dy=0.5, nodata=None)
exp_slope = int(math.degrees(slope_rad) * 254.0 / 90.0 + 1.0)
check("slope étalé 1-255", abs(int(sl[32, 32]) - exp_slope) <= 1,
      f"got {sl[32,32]} exp {exp_slope}")
sl_flat = l2m._slope_numpy(np.zeros((16, 16), np.float32), dx=0.5, dy=0.5)
check("slope plat = 1 (0 réservé nodata)", np.all(sl_flat == 1))

# z_factor + nodata : la détection nodata doit survivre au scaling
hs_z = l2m._hillshade_numpy(dem_nd, 90.0, 45.0, z_factor=2.0,
                            dx=0.5, dy=0.5, nodata=ND)
check("z_factor=2 : nodata toujours détecté", np.all(hs_z[30:34, 30:34] == 0))

print("== 2. multi : cohérence numba vs fallback numpy ==")
rng = np.random.default_rng(42)
dem_r = np.cumsum(rng.normal(0, 0.3, (96, 96)), axis=1).astype(np.float32)
multi_nb = l2m._hillshade_multi_numpy(dem_r, altitude_deg=25.0, dx=0.5, dy=0.5)
# Forcer le fallback numpy en vidant le cache kernels
saved = dict(l2m._NUMBA_KERNELS_CACHE)
l2m._NUMBA_KERNELS_CACHE["horn"] = None
multi_np = l2m._hillshade_multi_numpy(dem_r, altitude_deg=25.0, dx=0.5, dy=0.5)
hs_np    = l2m._hillshade_numpy(dem_r, 315.0, 25.0, dx=0.5, dy=0.5)
l2m._NUMBA_KERNELS_CACHE.update(saved)
hs_nb    = l2m._hillshade_numpy(dem_r, 315.0, 25.0, dx=0.5, dy=0.5)
d_multi = np.abs(multi_nb.astype(int) - multi_np.astype(int))
d_hs    = np.abs(hs_nb.astype(int) - hs_np.astype(int))
check("multi numba == numpy (±1)", d_multi.max() <= 1, f"max diff {d_multi.max()}")
check("hillshade numba == numpy (±1)", d_hs.max() <= 1, f"max diff {d_hs.max()}")

print("== 3. _nodata_mask unifié ==")
a = np.array([1.0, -9999.0, 50000.0, np.nan, 0.0], dtype=np.float32)
m = l2m._nodata_mask(a, nodata=None)
check("magique ±9000", list(m) == [False, True, True, False, False])
m2 = l2m._nodata_mask(a, nodata=0.0)
check("nodata déclaré 0.0", list(m2) == [False, True, True, False, True])
m3 = l2m._nodata_mask(a, nodata=float("nan"))
check("nodata déclaré NaN", list(m3) == [False, True, True, True, False])

print("== 4. LRM chunked : grille 3x3 + pas de couture ==")
tmp = Path(tempfile.mkdtemp())
def write_tif(path, arr, nodata=None, count=1):
    prof = dict(driver="GTiff", dtype=str(arr.dtype), count=count,
                height=arr.shape[-2], width=arr.shape[-1],
                crs="EPSG:2154", transform=from_origin(900000, 6250000, 0.5, 0.5),
                nodata=nodata)
    with rasterio.open(str(path), "w", **prof) as ds:
        if count == 1:
            ds.write(arr, 1)
        else:
            ds.write(arr)

# Terrain : sinusoïde + bosse uniquement dans le coin SE (le coin NW est PLAT).
# Avec l'ancien échantillonnage (coin NW seul), p5≈p95≈0 → return False.
HH, WW = 3000, 3000
yy2, xx2 = np.mgrid[0:HH, 0:WW].astype(np.float32)
dem_big = np.where((yy2 > 1500) & (xx2 > 1500),
                   3.0 * np.sin(xx2 / 8.0) * np.sin(yy2 / 8.0),
                   0.0).astype(np.float32)
src_tif = tmp / "dem.tif"; dst_tif = tmp / "lrm.tif"
write_tif(src_tif, dem_big, nodata=ND)
ok = l2m._lrm_chunked(src_tif, dst_tif, sigma_px=15,
                      gdal_translate_exe=None, env_dem=None)
check("LRM chunked réussit avec coin NW plat (grille 3x3)", ok)
if ok:
    with rasterio.open(str(dst_tif)) as ds:
        lrm_out = ds.read(1)
    se = lrm_out[2000:2500, 2000:2500]
    check("LRM contraste présent dans le coin SE",
          se.min() < 100 and se.max() > 200, f"min {se.min()} max {se.max()}")

print("== 5. SVF chunked : pool sans nodata ==")
# DEM avec moitié ouest nodata : avant fix, les 0.0 nodata des fenêtres
# d'échantillon polluaient p2.
dem_svf = (2.0 * np.sin(xx2[:1024, :1024] / 6.0) * np.sin(yy2[:1024, :1024] / 6.0)).astype(np.float32)
dem_svf[:, :512] = ND
src_svf = tmp / "dem_svf.tif"; dst_svf = tmp / "svf.tif"
write_tif(src_svf, dem_svf, nodata=ND)
ok = l2m._svf_chunked(src_svf, dst_svf, max_dist_px=20, n_directions=8,
                      resolution=0.5, gamma=2.0, use_sweep=False, conv=0)
check("SVF chunked réussit", ok)
if ok:
    with rasterio.open(str(dst_svf)) as ds:
        svf_out = ds.read(1)
    check("SVF nodata → 0", np.all(svf_out[:, :500] == 0))
    east = svf_out[100:900, 600:1000]
    # p2/p98 calculés sur les seules valeurs valides → la moitié Est doit
    # utiliser toute la dynamique (médiane pas écrasée vers 255)
    check("SVF stretch non délavé (médiane Est < 250)",
          np.median(east) < 250, f"médiane {np.median(east)}")

print("== 6. RRIM chunked ==")
src_d = tmp / "dem_rrim.tif"
dem_rr = (5.0 * np.sin(xx2[:1024, :1024] / 20.0) * np.sin(yy2[:1024, :1024] / 20.0)).astype(np.float32)
dem_rr[0:64, 0:64] = ND
write_tif(src_d, dem_rr, nodata=ND)
slope_t = tmp / "slope.tif"
ok = l2m._hillshade_chunked(src_d, slope_t, "slope", {}, dx=0.5, dy=0.5)
check("slope chunked (entrée RRIM)", ok)
rrim_t = tmp / "rrim.tif"
ok = l2m._rrim_chunked(src_d, slope_t, rrim_t, sigma_px=15)
check("RRIM chunked réussit", ok)
if ok:
    with rasterio.open(str(rrim_t)) as ds:
        rrim = ds.read()
    check("RRIM 3 bandes", rrim.shape[0] == 3)
    check("RRIM G == B", np.array_equal(rrim[1], rrim[2]))
    check("RRIM nodata noir", np.all(rrim[:, 10:50, 10:50] == 0))
    interior = rrim[:, 200:800, 200:800]
    check("RRIM R et G actifs", interior[0].max() > 30 and interior[1].max() > 200,
          f"Rmax {interior[0].max()} Gmax {interior[1].max()}")

print("== 7. Passe multi-sorties hillshade ==")
o1, o2, o3 = tmp / "h315.tif", tmp / "hmulti.tif", tmp / "hslope.tif"
jobs = [("hillshade", {"azimuth_deg": 315.0, "altitude_deg": 25.0}, o1),
        ("hillshade_multi", {"altitude_deg": 25.0}, o2),
        ("slope", {}, o3)]
ok = l2m._hillshade_chunked_multi(src_d, jobs, dx=0.5, dy=0.5)
check("multi-sorties réussit", ok)
if ok:
    # Référence : passes individuelles
    r1 = tmp / "ref315.tif"
    l2m._hillshade_chunked(src_d, r1, "hillshade",
                           {"azimuth_deg": 315.0, "altitude_deg": 25.0},
                           dx=0.5, dy=0.5)
    with rasterio.open(str(o1)) as a_, rasterio.open(str(r1)) as b_:
        check("multi-sorties == passe individuelle",
              np.array_equal(a_.read(1), b_.read(1)))

print("== 8. deg_to_tile clamp + bounds ==")
x_, y_ = l2m.deg_to_tile(45.0, 180.0, 10)
check("deg_to_tile x clampé", x_ == 1023, f"x={x_}")

print("== 9. Openness positive/négative (Yokoyama 2002) ==")
# Cas analytiques : cône à 45° (tan = 1 le long de chaque rayon).
#   cuvette → β = δ = 45°  → opos = oneg = 0.5 − atan(1)/π = 0.25 (sombre)
#   plat    → β = δ = 0°   → opos = oneg = 0.5
#   sommet  → β = δ = −45° → opos = oneg = 0.75 (clair)
NN = 81; cc = NN // 2
yyo, xxo = np.mgrid[0:NN, 0:NN].astype(np.float32)
dist_px = np.sqrt((xxo - cc) ** 2 + (yyo - cc) ** 2).astype(np.float32)
bowl = dist_px * 0.5          # cuvette : monte de 0.5 m / px de 0.5 m
peak = -dist_px * 0.5         # sommet
flat = np.zeros((NN, NN), np.float32)

op_flat = l2m._svf_numpy(flat, 10, 8, 0.5, conv=2)
on_flat = l2m._svf_numpy(flat, 10, 8, 0.5, conv=3)
op_bowl = l2m._svf_numpy(bowl, 10, 8, 0.5, conv=2)
on_bowl = l2m._svf_numpy(bowl, 10, 8, 0.5, conv=3)
op_peak = l2m._svf_numpy(peak, 10, 8, 0.5, conv=2)
on_peak = l2m._svf_numpy(peak, 10, 8, 0.5, conv=3)
check("opos plat = 0.5",    abs(op_flat[cc, cc] - 0.5) < 0.01, f"{op_flat[cc,cc]:.3f}")
check("oneg plat = 0.5",    abs(on_flat[cc, cc] - 0.5) < 0.01, f"{on_flat[cc,cc]:.3f}")
check("opos cuvette ≈ 0.25", abs(op_bowl[cc, cc] - 0.25) < 0.03, f"{op_bowl[cc,cc]:.3f}")
check("oneg cuvette sombre ≈ 0.25", abs(on_bowl[cc, cc] - 0.25) < 0.03, f"{on_bowl[cc,cc]:.3f}")
check("opos sommet ≈ 0.75", abs(op_peak[cc, cc] - 0.75) < 0.03, f"{op_peak[cc,cc]:.3f}")
check("oneg sommet clair ≈ 0.75", abs(on_peak[cc, cc] - 0.75) < 0.03, f"{on_peak[cc,cc]:.3f}")

# Cohérence numba vs fallback numpy (zone centrale, hors effets de bord)
saved_svf = l2m._NUMBA_KERNELS_CACHE.get("svf")
l2m._NUMBA_KERNELS_CACHE["svf"] = None
op_bowl_np = l2m._svf_numpy(bowl, 10, 8, 0.5, conv=2)
on_bowl_np = l2m._svf_numpy(bowl, 10, 8, 0.5, conv=3)
l2m._NUMBA_KERNELS_CACHE["svf"] = saved_svf
sl_c = slice(cc - 20, cc + 20)
d_op = np.abs(op_bowl[sl_c, sl_c] - op_bowl_np[sl_c, sl_c]).max()
d_on = np.abs(on_bowl[sl_c, sl_c] - on_bowl_np[sl_c, sl_c]).max()
check("opos numba == numpy (±0.02)", d_op < 0.02, f"max diff {d_op:.4f}")
check("oneg numba == numpy (±0.02)", d_on < 0.02, f"max diff {d_on:.4f}")

# Chunked + garde sweep : use_sweep=True doit être ignoré pour l'openness
dst_on = tmp / "oneg.tif"
ok = l2m._svf_chunked(src_svf, dst_on, max_dist_px=20, n_directions=8,
                      resolution=0.5, gamma=2.0, use_sweep=True, conv=3)
check("openness chunked (sweep forcé off) réussit", ok)

# Gamma miroir oneg : le fond doit rester CLAIR (le x^γ direct donnait une
# image globalement sombre — médiane fond ~68/255 au lieu de ~195).
dem_g = (2.0 * np.sin(xx2[:1024, :1024] / 15.0) * np.sin(yy2[:1024, :1024] / 15.0)
         + 0.1 * np.sin(xx2[:1024, :1024] * 2.1)).astype(np.float32)
dem_g[:, 500:506] -= 1.5    # fossé N-S
src_g = tmp / "dem_oneg_gamma.tif"; dst_g = tmp / "oneg_gamma.tif"
write_tif(src_g, dem_g, nodata=ND)
ok = l2m._svf_chunked(src_g, dst_g, max_dist_px=40, n_directions=16,
                      resolution=0.5, gamma=2.0, use_sweep=False, conv=3)
check("oneg gamma miroir : calcul réussit", ok)
if ok:
    with rasterio.open(str(dst_g)) as ds:
        on_arr = ds.read(1)
    fond_med  = float(np.median(on_arr[100:900, 100:450]))
    fosse_med = float(np.median(on_arr[100:900, 500:506]))
    check("oneg fond clair (médiane > 150)", fond_med > 150, f"{fond_med:.0f}")
    check("oneg fossé plus sombre que le fond (Δ > 30)",
          fond_med - fosse_med > 30, f"Δ={fond_med - fosse_med:.0f}")

print("== 10. Instances d'ombrages paramétrées (--shading) ==")
# Parser de specs
assert l2m.parser_shading_spec("svf:dist=10,gamma=1.5,conv=rvt") == \
    ("svf", {"dist": 10.0, "gamma": 1.5, "conv": "rvt"})
assert l2m.parser_shading_spec("oneg") == ("oneg", {})
assert l2m.parser_shading_spec("315:elevation=35") == ("315", {"elevation": 35.0})
assert l2m.parser_shading_spec("lrm:sigma=5") == ("lrm", {"sigma": 5.0})
assert l2m.parser_shading_spec("svf:sweep=0") == ("svf", {"sweep": 0.0})
for bad in ("foo", "svf:bidule=1", "svf:conv=xx", "svf:dist=abc"):
    try:
        l2m.parser_shading_spec(bad)
        check(f"spec invalide rejetée : {bad}", False)
    except ValueError:
        pass
check("parser_shading_spec : specs valides + rejets", True)

# Moteur : deux instances du même type + noms taggés seulement si explicites
dem_i = (3.0 * np.sin(xx2[:512, :512] / 12.0)
         * np.sin(yy2[:512, :512] / 12.0)).astype(np.float32)
src_i = tmp / "dem_inst.tif"
write_tif(src_i, dem_i, nodata=ND)
inst = [l2m.parser_shading_spec(s) for s in
        ("svf:dist=10,gamma=1.0", "svf:dist=20,gamma=1.0",
         "315:elevation=35", "lrm:sigma=5")]
dossier_i = tmp / "inst"
dossier_i.mkdir()
l2m.generer_ombrages([src_i], dossier_i, choix=["multi"], nom_zone="zz",
                     instances=inst, bbox_natif=None)
produits = {f.name for f in dossier_i.glob("zz_*.tif")}
attendus = {"zz_multi_ombrage.tif",            # legacy : nom historique
            "zz_svf_flux_10m_g1p0_ombrage.tif",
            "zz_svf_flux_20m_g1p0_ombrage.tif",  # 2 instances du même type
            "zz_315_e35_ombrage.tif",            # élévation explicite → taggée
            "zz_lrm_s5m_ombrage.tif"}            # sigma explicite → taggé
check("instances : fichiers attendus produits", produits == attendus,
      f"écart : {produits ^ attendus}")

print("== 11. Provider gb-scotland : encodage OS National Grid ==")
_SCT = Path(__file__).resolve().parent.parent / "providers" / "gb_scotland.py"
_sct_spec = importlib.util.spec_from_file_location("gb_scotland", str(_SCT))
sct = importlib.util.module_from_spec(_sct_spec)
_sct_spec.loader.exec_module(sct)
# Références OS connues (coin SW) — carrés 100 km NR (E100000/N600000) et
# HY (E300000/N1000000).
check("OS ref NR5807 (E158000/N607000)",
      sct._en_vers_osref(158000, 607000) == "NR5807",
      sct._en_vers_osref(158000, 607000))
check("OS ref HY1700 (E317000/N1000000)",
      sct._en_vers_osref(317000, 1000000) == "HY1700",
      sct._en_vers_osref(317000, 1000000))
check("dalle_filename km → nom OS",
      sct.dalle_filename(158, 607) == "sct_dtm_NR5807.tif",
      sct.dalle_filename(158, 607))
check("subdir_from_name parse le carré 100 km",
      sct.subdir_from_name("sct_dtm_NR5807.tif") == "NR")
check("dalles_pour_bbox : grille 1 km (2×2)",
      len(sct.dalles_pour_bbox(158000, 607000, 160000, 609000)) == 4)
check("discover_dalles(bbox_natif=None) → {} (pas de réseau)",
      sct.discover_dalles(None, None, tmp / "sct_cache.json") == {})

print("== 12. Provider lu-act : COG national fenêtré ==")
_LU = Path(__file__).resolve().parent.parent / "providers" / "lu_act.py"
_lu_spec = importlib.util.spec_from_file_location("lu_act", str(_LU))
lu = importlib.util.module_from_spec(_lu_spec)
_lu_spec.loader.exec_module(lu)
check("COG_WINDOWED activé", getattr(lu, "COG_WINDOWED", False) is True)
check("CRS natif EPSG:2169", lu.CRS_NATIF == "EPSG:2169")
_lu_in = lu.discover_dalles(None, (76000, 75000, 76500, 75500), None)
check("discover : 1 fenêtre dans la bbox LU", len(_lu_in) == 1)
check("nom encode la bbox zone (rejoue → même nom)",
      next(iter(_lu_in)) == "lu_mnt2024_76000_75000_76500_75500.tif",
      next(iter(_lu_in)))
check("URL = COG unique (toutes zones)", next(iter(_lu_in.values())) == lu.COG_URL)
check("subdir_from_name : bande 10 km easting",
      lu.subdir_from_name("lu_mnt2024_76000_75000_76500_75500.tif") == "7")
check("discover hors étendue LU → {}",
      lu.discover_dalles(None, (0, 0, 1000, 1000), None) == {})

print("== 13. Provider au-ga : grille WCS + reproject 3857 ==")
_GA = Path(__file__).resolve().parent.parent / "providers" / "au_ga.py"
_ga_spec = importlib.util.spec_from_file_location("au_ga", str(_GA))
ga = importlib.util.module_from_spec(_ga_spec)
_ga_spec.loader.exec_module(ga)
check("CRS natif (travail) EPSG:3857", ga.CRS_NATIF == "EPSG:3857")
check("dalle_filename signé", ga.dalle_filename(1542, -416) == "au_ga5m_+01542_-00416.tif",
      ga.dalle_filename(1542, -416))
check("subdir_from_name round-trip",
      ga.subdir_from_name("au_ga5m_+01542_-00416.tif") == "+01542")
# grille 10 km (pyproj-free) : 20×20 km → 4 dalles
_g = ga.dalles_pour_bbox(15420000, -4160000, 15440000, -4140000)
check("dalles_pour_bbox : grille 10 km (2×2)", len(_g) == 4, str(len(_g)))
try:
    import pyproj  # noqa: F401
    _u = ga.dalle_url(1542, -416)
    check("dalle_url : WCS 1.0.0 natif 4283 GeoTIFF",
          "VERSION=1.0.0" in _u and "CRS=EPSG:4283" in _u and "FORMAT=GeoTIFF" in _u)
except ImportError:
    print("  [skip] dalle_url (pyproj absent)")

print("== 14. Provider de-thueringen : grille + ATOM (offline) ==")
_TH = Path(__file__).resolve().parent.parent / "providers" / "de_thueringen.py"
_th_spec = importlib.util.spec_from_file_location("de_thueringen", str(_TH))
th = importlib.util.module_from_spec(_th_spec)
_th_spec.loader.exec_module(th)
check("CRS natif EPSG:25832", th.CRS_NATIF == "EPSG:25832")
check("dalle_filename km", th.dalle_filename(642, 5650) == "th_dgm_642_5650.tif",
      th.dalle_filename(642, 5650))
check("subdir_from_name round-trip", th.subdir_from_name("th_dgm_642_5650.tif") == "642")
check("dalles_pour_bbox : grille 1 km (2×2)",
      len(th.dalles_pour_bbox(642000, 5650000, 644000, 5652000)) == 4)
check("discover(bbox_natif=None) → {} (pas de réseau)",
      th.discover_dalles(None, None, tmp / "th_cache.json") == {})

print("== 15. Provider es-icgc : COG Catalogne 50 cm fenêtré ==")
_IC = Path(__file__).resolve().parent.parent / "providers" / "es_icgc.py"
_ic_spec = importlib.util.spec_from_file_location("es_icgc", str(_IC))
ic = importlib.util.module_from_spec(_ic_spec)
_ic_spec.loader.exec_module(ic)
check("COG_WINDOWED activé", getattr(ic, "COG_WINDOWED", False) is True)
check("CRS natif EPSG:25831", ic.CRS_NATIF == "EPSG:25831")
check("résolution 0,5 m", ic.RESOLUTION_M == 0.5)
_ic_in = ic.discover_dalles(None, (430000, 4580000, 430500, 4580500), None)
check("discover : 1 fenêtre dans la bbox Catalogne", len(_ic_in) == 1)
check("nom encode la bbox zone",
      next(iter(_ic_in)) == "icgc_met50cm_430000_4580000_430500_4580500.tif",
      next(iter(_ic_in)))
check("URL = COG unique datacloud", next(iter(_ic_in.values())) == ic.COG_URL)
check("subdir bande 10 km", ic.subdir_from_name(next(iter(_ic_in))) == "43")
check("discover hors étendue → {}",
      ic.discover_dalles(None, (0, 0, 1000, 1000), None) == {})

print("== 16. Provider jp-gsi : tuiles XYZ DEM5A → 3857 (offline) ==")
_JP = Path(__file__).resolve().parent.parent / "providers" / "jp_gsi.py"
_jp_spec = importlib.util.spec_from_file_location("jp_gsi", str(_JP))
jp = importlib.util.module_from_spec(_jp_spec)
_jp_spec.loader.exec_module(jp)
check("CRS de travail EPSG:3857", jp.CRS_NATIF == "EPSG:3857")
check("dalle_filename z/x/y", jp.dalle_filename(15, 29105, 12902) == "jp_dem5a_15_29105_12902.tif",
      jp.dalle_filename(15, 29105, 12902))
check("subdir_from_name", jp.subdir_from_name("jp_dem5a_15_29105_12902.tif") == f"{29105 // 64}")
# Tokyo-area bbox EPSG:3857 (math de tuiles pure, sans réseau)
_jp_d = jp.discover_dalles(None, (15556000, 4257000, 15557200, 4258200), None)
check("discover : tuiles z15 dans la bbox Tokyo", len(_jp_d) >= 1, str(len(_jp_d)))
check("noms bien formés", all(n.startswith("jp_dem5a_15_") and n.endswith(".tif")
                               for n in _jp_d))
_l, _b, _r, _t = jp._tile_bounds(15, 29105, 12902)
check("tile_bounds : ~1223 m de côté", abs((_r - _l) - jp._STEP) < 1 and _t > _b)
check("discover(bbox_natif=None) → {}", jp.discover_dalles(None, None, None) == {})

print()
print("TOUS OK" if ok_all else "ÉCHECS DÉTECTÉS")
sys.exit(0 if ok_all else 1)
