# Tests de régression des calculs scientifiques de lidar2map.py
# (kernels Horn, nodata, LRM, SVF, RRIM, passe multi-sorties).
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

print()
print("TOUS OK" if ok_all else "ÉCHECS DÉTECTÉS")
sys.exit(0 if ok_all else 1)
