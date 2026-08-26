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
# R2#21 : NaN (index 3) est TOUJOURS masqué, quel que soit le nodata déclaré.
m = l2m._nodata_mask(a, nodata=None)
check("magique ±9000 + NaN (nodata None)", list(m) == [False, True, True, True, False])
m2 = l2m._nodata_mask(a, nodata=0.0)
check("nodata déclaré 0.0 + NaN toujours masqué",
      list(m2) == [False, True, True, True, True])
m3 = l2m._nodata_mask(a, nodata=float("nan"))
check("nodata déclaré NaN", list(m3) == [False, True, True, True, False])
# R2#21 : garde de dtype — np.isnan lève sur un array entier, ne doit pas planter.
ai = np.array([1, -9999, 50000, 0], dtype=np.int32)
mi = l2m._nodata_mask(ai, nodata=-9999)
check("array entier : pas de crash, sentinelle + nodata déclaré",
      list(mi) == [False, True, True, False])

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
ok = l2m._lrm_chunked(src_tif, dst_tif, sigma_px=15)
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

# Sweep vs ray-cast pour openness+ (conv=2) : même formule (0.5 - atan(max_tan)/π,
# non clampé) portée dans _svf_sweep_kernel. Le cône à 45° (bowl/peak) est un
# cas géométrique pathologique pour TOUT sweep (nearest-neighbor le long
# d'une scan-line vs ray-cast bilinéaire) : mesuré, le conv=0 (SVF) déjà en
# prod et non touché par ce fix affiche le MÊME ordre de grandeur d'écart
# sur ce cône (~0.17-0.22). Comparaison RELATIVE plutôt qu'un seuil absolu
# arbitraire : ce qui compte est que conv=2 ne soit pas significativement
# pire que conv=0 sur le même terrain, pas qu'il soit parfait dans l'absolu.
op_bowl_sw = l2m._svf_numpy(bowl, 10, 8, 0.5, use_sweep=True, conv=2)
op_peak_sw = l2m._svf_numpy(peak, 10, 8, 0.5, use_sweep=True, conv=2)
svf_bowl_rc = l2m._svf_numpy(bowl, 10, 8, 0.5, conv=0)
svf_bowl_sw = l2m._svf_numpy(bowl, 10, 8, 0.5, use_sweep=True, conv=0)
d_op_bowl_sw  = np.abs(op_bowl[sl_c, sl_c] - op_bowl_sw[sl_c, sl_c]).max()
d_op_peak_sw  = np.abs(op_peak[sl_c, sl_c] - op_peak_sw[sl_c, sl_c]).max()
d_svf_bowl_sw = np.abs(svf_bowl_rc[sl_c, sl_c] - svf_bowl_sw[sl_c, sl_c]).max()
check("opos sweep pas pire que SVF sweep sur le même cône (marge ×2)",
      d_op_bowl_sw < d_svf_bowl_sw * 2.0,
      f"opos diff={d_op_bowl_sw:.4f} vs SVF diff={d_svf_bowl_sw:.4f}")
check("opos sweep sommet : écart raisonnable (< 0.10)",
      d_op_peak_sw < 0.10, f"max diff {d_op_peak_sw:.4f}")
# Garde spécifique anti-régression du clamp : avant fix, l'init max_tan=0.0
# du sweep aurait donné 0.5 pile sur un sommet (angle négatif clampé à 0) au
# lieu de ≈0.75 (formule non clampée) — cf. bug analysé le 2026-08-05.
check("opos sweep sommet non clampé (>0.6, attendu ≈0.75)",
      op_peak_sw[cc, cc] > 0.6, f"{op_peak_sw[cc,cc]:.3f}")

# Terrain réaliste (sinusoïde douce, pas le cône pathologique ci-dessus) :
# l'écart sweep/ray-cast doit rester faible en pratique (mesuré : moyenne
# ~0.006, p95 ~0.017 sur ce terrain, contre 0.0018/0.0049 pour le SVF conv=0
# déjà en prod — même ordre de grandeur, cohérent avec une statistique
# extrémale (max_tan→atan) plus sensible qu'une moyenne/intégrale sur les
# 16 directions).
dem_doux = (3.0 * np.sin(xx2[:400, :400] / 25.0) * np.sin(yy2[:400, :400] / 25.0)).astype(np.float32)
op_doux_rc = l2m._svf_numpy(dem_doux, 40, 16, 0.5, conv=2)
op_doux_sw = l2m._svf_numpy(dem_doux, 40, 16, 0.5, use_sweep=True, conv=2)
sl_d = slice(60, 340)
d_doux = np.abs(op_doux_rc[sl_d, sl_d] - op_doux_sw[sl_d, sl_d])
check("opos sweep == ray-cast sur terrain réaliste (moyenne < 0.02)",
      d_doux.mean() < 0.02, f"moyenne {d_doux.mean():.4f}")
check("opos sweep == ray-cast sur terrain réaliste (p95 < 0.05)",
      np.percentile(d_doux, 95) < 0.05, f"p95 {np.percentile(d_doux, 95):.4f}")

# Sweep vs ray-cast pour openness- (conv=3) : même mécanisme que conv=2,
# lower hull (min) sur le MÊME deque (cf. _svf_sweep_kernel), pas de
# structure séparée. Le cône bowl/peak est dégénéré pour CE test précis :
# sur une pente radiale à tan constant, max_tan == min_tan par direction
# (pas de courbure le long d'un rayon), donc il ne peut pas à lui seul
# discriminer un bug max/min — cf. le terrain réaliste plus bas pour ça.
# Comparaison relative à conv=0 gardée pour la cohérence de grandeur.
on_bowl_sw = l2m._svf_numpy(bowl, 10, 8, 0.5, use_sweep=True, conv=3)
on_peak_sw = l2m._svf_numpy(peak, 10, 8, 0.5, use_sweep=True, conv=3)
d_on_bowl_sw = np.abs(on_bowl[sl_c, sl_c] - on_bowl_sw[sl_c, sl_c]).max()
d_on_peak_sw = np.abs(on_peak[sl_c, sl_c] - on_peak_sw[sl_c, sl_c]).max()
check("oneg sweep pas pire que SVF sweep sur le même cône (marge ×3)",
      d_on_bowl_sw < d_svf_bowl_sw * 3.0,
      f"oneg diff={d_on_bowl_sw:.4f} vs SVF diff={d_svf_bowl_sw:.4f}")
check("oneg sweep sommet : écart raisonnable (< 0.20)",
      d_on_peak_sw < 0.20, f"max diff {d_on_peak_sw:.4f}")
check("oneg sweep sommet clair (>0.6, attendu ≈0.75)",
      on_peak_sw[cc, cc] > 0.6, f"{on_peak_sw[cc,cc]:.3f}")

# Terrain réaliste (même sinusoïde que pour opos+, courbure locale réelle :
# discrimine vraiment un bug min/max, contrairement au cône ci-dessus).
on_doux_rc = l2m._svf_numpy(dem_doux, 40, 16, 0.5, conv=3)
on_doux_sw = l2m._svf_numpy(dem_doux, 40, 16, 0.5, use_sweep=True, conv=3)
d_doux_on = np.abs(on_doux_rc[sl_d, sl_d] - on_doux_sw[sl_d, sl_d])
check("oneg sweep == ray-cast sur terrain réaliste (moyenne < 0.02)",
      d_doux_on.mean() < 0.02, f"moyenne {d_doux_on.mean():.4f}")
check("oneg sweep == ray-cast sur terrain réaliste (p95 < 0.05)",
      np.percentile(d_doux_on, 95) < 0.05, f"p95 {np.percentile(d_doux_on, 95):.4f}")

# Chunked + gate ouvert : conv=3 (oneg) doit maintenant passer par le sweep
# quand use_sweep=True (plus aucun conv ne force le ray-cast désormais).
dst_on_sw = tmp / "oneg_sweep.tif"
ok = l2m._svf_chunked(src_svf, dst_on_sw, max_dist_px=20, n_directions=8,
                      resolution=0.5, gamma=1.0, use_sweep=True, conv=3)
check("oneg chunked (sweep) réussit", ok)
if ok:
    with rasterio.open(str(dst_on_sw)) as ds:
        on_sw_out = ds.read(1)
    east = on_sw_out[100:900, 600:1000]
    check("oneg chunked sweep : dynamique non délavée (médiane < 250)",
          np.median(east) < 250, f"médiane {np.median(east)}")

# Chunked + gate ouvert : conv=2 (opos) doit maintenant passer par le sweep
# quand use_sweep=True (gate restreint à conv >= 3 désormais, cf. ci-dessus).
dst_op_sw = tmp / "opos_sweep.tif"
ok = l2m._svf_chunked(src_svf, dst_op_sw, max_dist_px=20, n_directions=8,
                      resolution=0.5, gamma=1.0, use_sweep=True, conv=2)
check("opos chunked (sweep) réussit", ok)
if ok:
    with rasterio.open(str(dst_op_sw)) as ds:
        op_sw_out = ds.read(1)
    east = op_sw_out[100:900, 600:1000]
    check("opos chunked sweep : dynamique non délavée (médiane < 250)",
          np.median(east) < 250, f"médiane {np.median(east)}")

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

print("== 10a-bis. Listes d'ombrages dérivées de _SHADING_TYPES ==")
# Anti-drift : argparse choices et l'expansion "tous" doivent dériver de
# _SHADING_TYPES (sinon un nouveau type est rejeté par --shadings, cf. bug vat).
check("SHADING_TYPES_ORDRE == clés de _SHADING_TYPES (ordre préservé)",
      l2m.SHADING_TYPES_ORDRE == list(l2m._SHADING_TYPES))
check("tout type de _SHADING_TYPES est une valeur --shadings acceptée",
      all(t in l2m.SHADING_TYPES_ORDRE for t in l2m._SHADING_TYPES))
check("SHADING_TOUS = tous sauf vat/e4mstp (composites lourds exclus de 'tous')",
      l2m.SHADING_TOUS == [t for t in l2m._SHADING_TYPES if t not in ("vat", "e4mstp")]
      and "vat" not in l2m.SHADING_TOUS
      and "e4mstp" not in l2m.SHADING_TOUS)

print("== 10b. Composite VAT (_vat_compose) ==")
assert l2m.parser_shading_spec("vat") == ("vat", {})
assert l2m.parser_shading_spec("vat:dist=30,gamma=1.5") == \
    ("vat", {"dist": 30.0, "gamma": 1.5})
check("vat dans _SHADING_TYPES (dist, gamma)",
      l2m._SHADING_TYPES.get("vat") == {"dist", "gamma"})
# Blend sur 3 couches uint8 synthétiques (pas de numba ni réseau) : on vérifie
# le nodata (SVF=0 → noir) et l'assombrissement par la pente.
_vd = tmp / "vat"; _vd.mkdir()
def _mk_u8(path, arr):
    h, w = arr.shape
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=1,
                       dtype="uint8", crs="EPSG:27700",
                       transform=from_origin(0, h, 1, 1)) as d:
        d.write(arr, 1)
_svf = np.full((32, 32), 200, np.uint8); _svf[0:4, 0:4] = 0       # nodata SVF
_opos = np.full((32, 32), 128, np.uint8)
_slope = np.zeros((32, 32), np.uint8); _slope[:, 16:] = 200        # pente à droite
_mk_u8(_vd / "s.tif", _svf); _mk_u8(_vd / "o.tif", _opos); _mk_u8(_vd / "sl.tif", _slope)
assert l2m._vat_compose(_vd / "s.tif", _vd / "o.tif", _vd / "sl.tif",
                        _vd / "v.tif", gamma=1.0)
with rasterio.open(_vd / "v.tif") as _r:
    _out = _r.read(1); _bands = _r.count
check("VAT : sortie 1 bande uint8", _bands == 1 and _out.dtype == np.uint8)
check("VAT : nodata SVF → noir", int(_out[1, 1]) == 0, int(_out[1, 1]))
check("VAT : la pente assombrit (droite < gauche)",
      int(_out[20, 24]) < int(_out[20, 4]),
      f"droite={_out[20, 24]} gauche={_out[20, 4]}")

print("== 10b2. Composite e4MSTP (_mstp_chunked + _e4mstp_compose) ==")
assert l2m.parser_shading_spec("e4mstp") == ("e4mstp", {})
assert l2m.parser_shading_spec("e4mstp:dist=100,gamma=0.7") == \
    ("e4mstp", {"dist": 100.0, "gamma": 0.7})
check("e4mstp dans _SHADING_TYPES (dist, gamma)",
      l2m._SHADING_TYPES.get("e4mstp") == {"dist", "gamma"})
_ed = tmp / "e4"; _ed.mkdir()
# MSTP chunké sur un DEM synthétique (scipy seul, pas de numba).
_dem_e = (10.0 * np.sin(xx2[:256, :256] / 12.0)
          + 3.0 * np.cos(yy2[:256, :256] / 5.0)).astype(np.float32)
write_tif(_ed / "dem.tif", _dem_e, nodata=ND)
check("_mstp_chunked -> RGB uint8", l2m._mstp_chunked(_ed / "dem.tif", _ed / "mstp.tif", res=0.5))
with rasterio.open(_ed / "mstp.tif") as _r:
    check("MSTP : 3 bandes uint8", _r.count == 3 and _r.dtypes[0] == "uint8")
# _e4mstp_compose sur composantes uint8 synthétiques (numpy pur).
def _mk3(path, val):
    with rasterio.open(path, "w", driver="GTiff", height=32, width=32, count=3,
                       dtype="uint8", crs="EPSG:27700",
                       transform=from_origin(0, 32, 1, 1)) as d:
        d.write(np.full((3, 32, 32), val, np.uint8))
_mk3(_ed / "m.tif", 150)
_opos_e = np.full((32, 32), 160, np.uint8); _opos_e[0:4, 0:4] = 0   # nodata (opos=0)
for _n, _v in [("svf", 180), ("op", None), ("on", 140), ("slp", 0), ("slf", 128), ("sp", 128)]:
    _mk_u8(_ed / f"{_n}.tif", _opos_e if _n == "op" else np.full((32, 32), _v, np.uint8))
check("_e4mstp_compose -> True",
      l2m._e4mstp_compose(_ed / "m.tif", _ed / "svf.tif", _ed / "op.tif",
                          _ed / "on.tif", _ed / "slp.tif", _ed / "slf.tif",
                          _ed / "sp.tif", _ed / "e4.tif", gamma=0.8))
with rasterio.open(_ed / "e4.tif") as _r:
    _e4o = _r.read(); _e4b = _r.count
check("e4MSTP : sortie 3 bandes uint8", _e4b == 3 and _e4o.dtype == np.uint8)
check("e4MSTP : nodata (opos=0) → noir", int(_e4o[:, 1, 1].sum()) == 0, str(_e4o[:, 1, 1]))

print("== 10c. Presets de stack par resolution ==")
_pn, _pi, _pe = l2m._resoudre_preset_shading("auto", 0.5)
check("preset auto 0.5m -> micro (soleil 25)", _pn == "micro" and _pe == 25)
check("preset micro : svf/opos rayon 15 m en metres",
      dict(_pi).get("svf") == {"dist": 15.0} and dict(_pi).get("opos") == {"dist": 15.0})
_pn2, _pi2, _pe2 = l2m._resoudre_preset_shading("auto", 5.0)
check("preset auto 5m -> landscape (rayon 80 m, lrm sigma 40 m, soleil 30)",
      _pn2 == "landscape" and dict(_pi2)["lrm"] == {"sigma": 40.0} and _pe2 == 30,
      f"{_pn2} {dict(_pi2)} {_pe2}")
check("preset auto 1m -> standard",
      l2m._resoudre_preset_shading("auto", 1.0)[0] == "standard")
check("preset : types valides", all(t in l2m._SHADING_TYPES for t, _ in _pi))

print("== 10d. Fusion SVF+openness (kernel VAT) ==")
if l2m._get_numba_svf_opos_kernel() is None:
    check("fusion : numba absent -> skip", True)
else:
    import rasterio as _rio_f
    _fd = tmp / "fus"; _fd.mkdir()
    _dem_f = (4.0 * np.sin(xx2[:512, :512] / 9.0)
              * np.cos(yy2[:512, :512] / 11.0)).astype(np.float32)
    _src_f = _fd / "dem.tif"; write_tif(_src_f, _dem_f, nodata=ND)
    # 2 passes separees vs 1 passe fusionnee, memes params (dist 20px, gamma 1)
    l2m._svf_chunked(_src_f, _fd / "svf_s.tif", 20, 16, 1.0, 1.0, False, conv=0)
    l2m._svf_chunked(_src_f, _fd / "opos_s.tif", 20, 16, 1.0, 1.0, False, conv=2)
    l2m._svf_opos_chunked(_src_f, _fd / "svf_f.tif", _fd / "opos_f.tif",
                          20, 16, 1.0, 1.0)
    def _arr_f(p):
        with _rio_f.open(p) as r:
            return r.read(1)
    check("fusion SVF == _svf_chunked conv=0 (byte-identique)",
          np.array_equal(_arr_f(_fd / "svf_s.tif"), _arr_f(_fd / "svf_f.tif")))
    check("fusion openness == _svf_chunked conv=2 (byte-identique)",
          np.array_equal(_arr_f(_fd / "opos_s.tif"), _arr_f(_fd / "opos_f.tif")))

print("== 11. Provider gb-scotland : encodage OS National Grid (multi-grille) ==")
_SCT = Path(__file__).resolve().parent.parent / "providers" / "gb_scotland.py"
_sct_spec = importlib.util.spec_from_file_location("gb_scotland", str(_SCT))
sct = importlib.util.module_from_spec(_sct_spec)
_sct_spec.loader.exec_module(sct)
# Réf OS du point E158000/N607000 (carré 100 km NR, 1 km = E58/N07 km) selon les
# 3 grilles du bucket : 1 km (national/hes/orkney), 10 km (phases 1-2), 5 km
# (phases 3-6, outer-hebrides : cellule 10 km + quadrant N/S puis E/O).
check("OS ref 1 km NR5807 (E158000/N607000)",
      sct._ref_pour_grille(158000, 607000, "1km") == "NR5807",
      sct._ref_pour_grille(158000, 607000, "1km"))
check("OS ref 1 km HY1700 (E317000/N1000000)",
      sct._ref_pour_grille(317000, 1000000, "1km") == "HY1700",
      sct._ref_pour_grille(317000, 1000000, "1km"))
check("OS ref 10 km NR50 (E158000/N607000)",
      sct._ref_pour_grille(158000, 607000, "10km") == "NR50",
      sct._ref_pour_grille(158000, 607000, "10km"))
check("OS ref 5 km NR50NE (E%10=8→E, N%10=7→N)",
      sct._ref_pour_grille(158000, 607000, "5km") == "NR50NE",
      sct._ref_pour_grille(158000, 607000, "5km"))
check("dalle_filename km → nom OS 1 km",
      sct.dalle_filename(158, 607) == "NR5807.tif",
      sct.dalle_filename(158, 607))
check("subdir_from_name parse le carré 100 km (basename S3 réel)",
      sct.subdir_from_name("NR5807_50cm_DTM_ScotlandNationalLiDAR.tif") == "NR")
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

print("== 17. Sécurité (revue 2026-07-28) ==")
import ssl as _ssl

# R2#1 : allowlist des filtres --layer OSM avant l'osmosis shell (anti-injection).
_legit = ["highway=*", "boundary=administrative", "building",
          "addr:housenumber=*", "highway=residential,service,track"]
_malins = ["highway=* & calc.exe", "x=y | whoami", "a=b > C:/pwn.txt",
           "foo=%PATH%", 'q="evil"', "a=b`id`", "a;rm -rf", "a=b^c", "a=$(id)"]
def _tag_ok(tokens):
    try:
        l2m._valider_osm_tags(tokens); return True
    except SystemExit:
        return False
check("R2#1 filtres OSM légitimes acceptés", all(_tag_ok([t]) for t in _legit))
check("R2#1 injections shell bloquées", all(not _tag_ok([t]) for t in _malins),
      f"{sum(1 for t in _malins if _tag_ok([t]))} passées")

# R2#3 : traversée de chemin sur nom de dalle d'index distant.
_surs = ["LHD_FXX_0958_6279_MNT.tif", "tile.laz", "0958.copc.laz"]
_dang = ["../evil.tif", "..\\evil.tif", "/etc/passwd", "C:\\x.tif",
         "sub/dir/x.tif", "..", ".", "", "a\x00b.tif"]
check("R2#3 basenames sûrs acceptés", all(l2m._nom_dalle_sur(n) for n in _surs))
check("R2#3 noms piégés rejetés", all(not l2m._nom_dalle_sur(n) for n in _dang))
def _cd_leve(n):
    try:
        l2m.chemin_dalle(Path("/cache/dalles"), n); return False
    except ValueError:
        return True
    except Exception:
        return False
check("R2#3 chemin_dalle lève sur nom piégé", all(_cd_leve(n) for n in _dang))

# R2#2 : vérification TLS stricte rétablie (certifi présent dans l'env de test).
l2m._restaurer_tls_strict()
_ctx = _ssl._create_default_https_context()
check("R2#2 contexte TLS strict après restore",
      _ctx.verify_mode == _ssl.CERT_REQUIRED and _ctx.check_hostname)

print("== 18. R1#8 : découverte EXACTE vs GRILLE (404 indexé = erreur) ==")
# Le flag DISCOVER_EXACT distingue un index (WFS/STAC/registre : la dalle est
# PROMISE → 404 = index périmé/panne = ERREUR) d'une grille synthétique (cellule
# de bord → 404 légitime = 'absent'). Machinerie côté LazProvider + bascule côté
# telecharger_dalle_directe.
sys.path.insert(0, str(_APP.parent))            # rend le package `providers` importable
from providers import common as _common_r18

# Machinerie : le param du constructeur stocke le flag, défaut = False.
_lp_def = _common_r18.LazProvider(
    prefix="t", crs_epsg=2154, resolution=0.5, socle_possible=(2,),
    defaults=(0.4, 2.5, (2,), "classes"))
_lp_ex = _common_r18.LazProvider(
    prefix="t", crs_epsg=2154, resolution=0.5, socle_possible=(2,),
    defaults=(0.4, 2.5, (2,), "classes"), discover_exact=True)
check("R1#8 LazProvider.discover_exact défaut False", _lp_def.discover_exact is False)
check("R1#8 LazProvider discover_exact=True stocké", _lp_ex.discover_exact is True)

# Intégration : un provider index ré-exporte True, un provider grille reste False.
_fr = importlib.import_module("providers.fr_ign_laz")
_dk = importlib.import_module("providers.dk_datafordeler_laz")
check("R1#8 fr_ign_laz.DISCOVER_EXACT True (index WFS)",
      getattr(_fr, "DISCOVER_EXACT", False) is True)
check("R1#8 dk_datafordeler_laz défaut False (grille range×range)",
      getattr(_dk, "DISCOVER_EXACT", False) is False)

# Bascule : un 404 (taille 0) devient 'erreur' en mode exact, reste 'absent' sinon.
class _FakeExact:
    DISCOVER_EXACT = True
    def subdir_from_name(self, nom): return ""
class _FakeGrid:
    DISCOVER_EXACT = False
    def subdir_from_name(self, nom): return ""
_prov0, _dl0, _delai0 = l2m.PROVIDER, l2m._download_to_tmp, l2m.DELAI_RETRY
try:
    l2m.DELAI_RETRY = 0
    l2m._download_to_tmp = lambda url, tmp, timeout=60, **_kwargs: 0   # simule un 404
    with tempfile.TemporaryDirectory() as _d:
        _dos = Path(_d)
        l2m.PROVIDER = _FakeExact()
        _r_ex = l2m.telecharger_dalle_directe("tile_exact.tif", "http://x/y", _dos)
        l2m.PROVIDER = _FakeGrid()
        _r_gr = l2m.telecharger_dalle_directe("tile_grid.tif", "http://x/y", _dos)
    check("R1#8 exact + 404 -> 'erreur'", _r_ex == "erreur", f"(obtenu {_r_ex!r})")
    check("R1#8 grille + 404 -> 'absent'", _r_gr == "absent", f"(obtenu {_r_gr!r})")
finally:
    l2m.PROVIDER, l2m._download_to_tmp, l2m.DELAI_RETRY = _prov0, _dl0, _delai0

print("== 19. P1 contrats de format JPEG/PNG (R2#7 RMAP, R2#14 split) ==")
import io as _io, struct as _st, sqlite3 as _sq
from PIL import Image as _PImg

def _png(color=(200, 100, 50, 255)):
    b = _io.BytesIO(); _PImg.new("RGBA", (256, 256), color).save(b, "PNG")
    return b.getvalue()
def _jpg():
    b = _io.BytesIO(); _PImg.new("RGB", (256, 256), (10, 20, 30)).save(b, "JPEG")
    return b.getvalue()

# R2#7 : helper _blob_vers_jpeg (RMAP = JPEG uniquement).
_r = l2m._blob_vers_jpeg(_png())
check("R2#7 PNG -> JPEG (magic FFD8FF)", _r is not None and _r[:3] == b'\xff\xd8\xff')
_jb = _jpg()
check("R2#7 JPEG -> inchangé (pas de re-encodage)", l2m._blob_vers_jpeg(_jb) is _jb)
check("R2#7 blob indécodable -> None", l2m._blob_vers_jpeg(b"nope") is None)

# R2#7 : intégration RMAP depuis mbtiles PNG → la tuile stockée est du JPEG.
with tempfile.TemporaryDirectory() as _td:
    _mb = Path(_td) / "t.mbtiles"
    _c = _sq.connect(str(_mb))
    _c.executescript("CREATE TABLE metadata(name TEXT,value TEXT);"
                     "CREATE TABLE tiles(zoom_level INT,tile_column INT,"
                     "tile_row INT,tile_data BLOB);")
    _c.execute("INSERT INTO metadata VALUES('format','png')")
    _c.execute("INSERT INTO tiles VALUES(?,?,?,?)", (10, 500, 300, _png()))
    _c.commit(); _c.close()
    _rm = l2m.generer_rmap_depuis_mbtiles(_mb, ecraser=True)
    _tuile_jpeg = False
    if _rm and _rm.exists():
        _d = _rm.read_bytes()
        _o = 19 + 4*3 + 4*2 + 4*2 + 4*2 + 8 + 4       # -> nZooms
        _nz = _st.unpack_from("<i", _d, _o)[0]; _o += 4
        _z0 = _st.unpack_from("<q", _d, _o)[0]
        _p = _z0 + 4*2
        _xt = _st.unpack_from("<i", _d, _p)[0]; _yt = _st.unpack_from("<i", _d, _p+4)[0]
        _p += 8
        _t0 = _st.unpack_from("<q", _d, _p)[0]
        _tag = _st.unpack_from("<i", _d, _t0)[0]
        _ln = _st.unpack_from("<i", _d, _t0+4)[0]
        _payload = _d[_t0+8:_t0+8+_ln]
        _tuile_jpeg = (_tag == 7 and _payload[:3] == b'\xff\xd8\xff'
                       and _payload[:4] != b'\x89PNG')
    check("R2#7 tuile RMAP depuis mbtiles PNG est bien du JPEG", _tuile_jpeg)

# R2#14 : décision de format de sortie WMTS (source de vérité unique jumeaux).
_f = l2m._jpeg_quality_sortie
_matrice = [
    ("image/png",  "auto", 85,   "PNG+auto -> convert"),
    ("image/png",  "jpeg", 85,   "PNG+jpeg -> convert"),
    ("image/png",  "png",  None, "PNG+png -> garder PNG"),
    ("image/jpeg", "auto", None, "JPEG+auto -> garder JPEG"),
    ("image/jpeg", "png",  None, "JPEG+png -> garder JPEG (pas de JPEG->PNG)"),
]
check("R2#14 matrice format de sortie (split == passe simple)",
      all(_f(imf, ff, 85) == exp for imf, ff, exp, _ in _matrice),
      detail=str([(_l, _f(imf, ff, 85)) for imf, ff, exp, _l in _matrice
                  if _f(imf, ff, 85) != exp]))

print("== 20. R2#12 : découpage zooms lus + bbox N/S non inversée ==")
def _meta(path):
    _cc = _sq.connect(str(path))
    try:
        return dict(_cc.execute("SELECT name, value FROM metadata").fetchall())
    finally:
        _cc.close()

_Z = 12; _N = 2 ** _Z
with tempfile.TemporaryDirectory() as _td:
    _src = Path(_td) / "base.mbtiles"
    _c = _sq.connect(str(_src))
    # PAS de minzoom/maxzoom/bounds → force la lecture depuis les tuiles (R2#12)
    _c.executescript("CREATE TABLE metadata(name TEXT,value TEXT);"
                     "CREATE TABLE tiles(zoom_level INT,tile_column INT,"
                     "tile_row INT,tile_data BLOB);")
    _c.execute("INSERT INTO metadata VALUES('format','jpg')")
    for _col in range(2000, 2002):
        for _r in range(1000, 1006):          # 1000=sud ... 1005=nord (TMS)
            _c.execute("INSERT INTO tiles VALUES(?,?,?,?)", (_Z, _col, _r, _jpg()))
    _c.commit(); _c.close()

    _outs = l2m.decouper_mbtiles(_src, n_cols=1, n_rows=2,
                                 dossier=Path(_td) / "out", ecraser=True)
    check("R2#12 découpe 2 morceaux", len(_outs) == 2)
    def _lat(y, n):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2*y/n))))
    _nord_att = _lat(_N - 1 - 1005, _N)          # bord nord de la tuile la plus nord
    _sud_att  = _lat((_N - 1 - 1000) + 1, _N)    # bord sud de la tuile la plus sud
    _zmin = set(); _zmax = set(); _uN = -1e9; _uS = 1e9; _non_inv = True
    for _o in _outs:
        _m = _meta(_o)
        _zmin.add(int(_m["minzoom"])); _zmax.add(int(_m["maxzoom"]))
        _lo0, _la0, _lo1, _la1 = [float(v) for v in _m["bounds"].split(",")]
        _non_inv = _non_inv and (_la1 > _la0)
        _uN = max(_uN, _la1); _uS = min(_uS, _la0)
    check("R2#12 zooms LUS des tuiles (12/12, pas 0/17)", _zmin == {_Z} and _zmax == {_Z})
    check("R2#12 bounds NON inversée (lat_max > lat_min sur chaque morceau)", _non_inv)
    check("R2#12 union lat_max = bord nord réel (tuile nord, pas sud)",
          abs(_uN - _nord_att) < 1e-6, detail=f"{_uN:.5f}~{_nord_att:.5f}")
    check("R2#12 union lat_min = bord sud réel", abs(_uS - _sud_att) < 1e-6)

print("== 21. P1 formats : R2#10 nom non-ASCII, R2#16 magic, R2#19 dtype/alpha ==")

# R2#10 : nom MBTiles accentué/non-latin ne doit plus crasher la calibration RMAP.
_txt = l2m._build_map_info("forêt_Ardèche_Ⅶ.mbtiles", 512, 512,
                           2.0, 43.0, 3.0, 44.0)
check("R2#10 _build_map_info encode ASCII sans lever",
      isinstance(_txt, str) and _txt.encode("ascii") is not None)
check("R2#10 nom translittéré (accents retirés, ASCII pur)",
      "Bitmap=foret_Ardeche" in _txt)
# CJK pur : NFKD ne décompose PAS vers de l'ASCII (contrairement à Ⅶ→VII),
# donc ascii-ignore laisse une chaîne vide → repli 'map'.
_txt_vide = l2m._build_map_info("油混固", 256, 256, 0, 0, 1, 1)
check("R2#10 nom 100% non-ASCII -> repli 'map' non vide", "Bitmap=map" in _txt_vide)

# R2#16 : validation d'une tuile WMTS par MAGIE, pas par taille.
_petit_png = _io.BytesIO()
_PImg.new("RGB", (256, 256), (128, 128, 128)).save(_petit_png, "PNG", optimize=True)
_petit_png = _petit_png.getvalue()
check("R2#16 PNG uniforme accepté même si petit",
      l2m._est_image_valide(_petit_png))
check("R2#16 JPEG accepté", l2m._est_image_valide(_jpg()))
check("R2#16 HTML volumineux rejeté (page d'erreur servie en 200)",
      not l2m._est_image_valide(b"<html><body>Error 500 " + b"x" * 2000 + b"</body>"))
check("R2#16 JSON d'erreur rejeté",
      not l2m._est_image_valide(b'{"error":{"code":400,"message":"bad"}}'))
check("R2#16 corps vide rejeté", not l2m._est_image_valide(b""))
check("R2#16 GIF/WebP/TIFF reconnus",
      l2m._est_image_valide(b"GIF89a" + b"\0" * 10)
      and l2m._est_image_valide(b"RIFF\0\0\0\0WEBP" + b"\0" * 4)
      and l2m._est_image_valide(b"II\x2a\x00" + b"\0" * 8))

# R2#19 : source non-uint8 -> fail-fast (pas de tuiles tronquées en silence).
with tempfile.TemporaryDirectory() as _td19:
    _f32 = Path(_td19) / "dem_float.tif"
    _tr = from_origin(650000, 6300000, 1.0, 1.0)
    _arr32 = (np.random.rand(64, 64) * 5000).astype(np.float32)   # MNT brut
    with rasterio.open(str(_f32), "w", driver="GTiff", height=64, width=64,
                       count=1, dtype="float32", crs="EPSG:2154",
                       transform=_tr) as _d:
        _d.write(_arr32, 1)
    _res = l2m.generer_mbtiles_lidar(_f32, Path(_td19), "dem_float",
                                     zoom_min=14, zoom_max=14,
                                     bbox_natif=(650000, 6299936, 650064, 6300000))
    check("R2#19 source float32 refusée (return None, pas de mbtiles tronqué)",
          _res is None)
    check("R2#19 aucun .mbtiles produit depuis la source float",
          not list(Path(_td19).glob("*.mbtiles")))

print("== 22. R2#33 : mapsforge, anneau dégénéré (<3 sommets) écarté ==")
import json as _json, xml.etree.ElementTree as _ET
with tempfile.TemporaryDirectory() as _td33:
    _gj = Path(_td33) / "in.geojson"
    _fc = {"type": "FeatureCollection", "features": [
        # anneau dégénéré : 2 sommets distincts (a,b,a) → aire nulle → à écarter
        {"type": "Feature", "properties": {"source": "x_ign_cours_d_eau"},
         "geometry": {"type": "Polygon",
                      "coordinates": [[[2.0, 43.0], [2.001, 43.001], [2.0, 43.0]]]}},
        # triangle valide : 3 sommets distincts → 1 way fermé
        {"type": "Feature", "properties": {"source": "x_ign_cours_d_eau"},
         "geometry": {"type": "Polygon",
                      "coordinates": [[[2.01, 43.0], [2.012, 43.0],
                                       [2.011, 43.002], [2.01, 43.0]]]}},
    ]}
    _gj.write_text(_json.dumps(_fc), encoding="utf-8")
    _xml = Path(_td33) / "out.osm"
    _ok = l2m.geojson_ign_vers_osm_xml(_gj, _xml, epsilon=1e-9)
    check("R2#33 conversion OSM XML réussie", _ok is True and _xml.exists())
    if _xml.exists():
        _root = _ET.parse(str(_xml)).getroot()
        _ways = _root.findall("way")
        check("R2#33 un seul way émis (triangle valide ; dégénéré écarté)",
              len(_ways) == 1, detail=f"{len(_ways)} ways")
        if _ways:
            _nds = _ways[0].findall("nd")
            _refs = [n.get("ref") for n in _nds]
            check("R2#33 way fermé à >=4 nœuds (contour d'aire non nulle)",
                  len(_refs) >= 4 and _refs[0] == _refs[-1],
                  detail=f"{len(_refs)} nd, fermé={_refs[0]==_refs[-1]}")

print("== 22b. R2#32 : couche WFS sans 'source' → repli sur le nom de fichier ==")
with tempfile.TemporaryDirectory() as _td32:
    # Feature SANS propriété 'source' (cas mono-couche telecharger_wfs). Le nom
    # de fichier porte la clé de couche 'cours_d_eau' → tags waterway=river.
    _gj32 = Path(_td32) / "zone_ign_cours_d_eau.geojson"
    _fc32 = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"nom": "Le Caramy"},
         "geometry": {"type": "LineString",
                      "coordinates": [[6.00, 43.36], [6.002, 43.361],
                                      [6.004, 43.362]]}},
    ]}
    _gj32.write_text(_json.dumps(_fc32), encoding="utf-8")
    _xml32 = Path(_td32) / "out.osm"
    _ok32 = l2m.geojson_ign_vers_osm_xml(_gj32, _xml32, epsilon=1e-9)
    check("R2#32 conversion OSM XML réussie sans 'source'",
          _ok32 is True and _xml32.exists())
    if _xml32.exists():
        _root32 = _ET.parse(str(_xml32)).getroot()
        _tags32 = {t.get("k"): t.get("v")
                   for w in _root32.findall("way") for t in w.findall("tag")}
        check("R2#32 tag waterway=river déduit du nom de fichier (pas {'note':''})",
              _tags32.get("waterway") == "river",
              detail=str(_tags32))

print("== 22c. R2#26 : .map non demandé / mapwriter absent → GeoJSON quand même ==")
_orig_verif26 = l2m._verifier_mapwriter
_orig_gj26    = l2m.generer_geojson_osm
try:
    _calls26 = {"verif": 0, "gj": 0}
    def _fake_verif26():
        _calls26["verif"] += 1
        return False   # simule mapwriter absent
    def _fake_gj26(bbox, dossier, nom, pbf, **kw):
        _calls26["gj"] += 1
        return Path(str(dossier)) / f"{nom}_osm.geojson.gz"
    l2m._verifier_mapwriter = _fake_verif26
    l2m.generer_geojson_osm = _fake_gj26
    with tempfile.TemporaryDirectory() as _td26:
        _bb26 = (6.00, 43.36, 6.01, 43.37)
        # want_map=False → osmosis/mapwriter court-circuités, GeoJSON produit
        _r1 = l2m.generer_carte_osm(_bb26, Path(_td26), "z", Path("x.pbf"),
                                    export_geojson=True, want_map=False,
                                    geojson_formats=["gz"])
        check("R2#26 want_map=False → GeoJSON produit sans toucher mapwriter",
              _r1 is not None and _calls26["gj"] == 1 and _calls26["verif"] == 0,
              detail=str(_calls26))
        # want_map=True mais mapwriter absent + gz demandé → dégrade (pas None)
        _r2 = l2m.generer_carte_osm(_bb26, Path(_td26), "z", Path("x.pbf"),
                                    export_geojson=True, want_map=True,
                                    geojson_formats=["gz"])
        check("R2#26 mapwriter absent + gz demandé → dégrade vers GeoJSON",
              _r2 is not None and _calls26["gj"] == 2,
              detail=str(_calls26))
        # want_map=False + rien demandé → None (rien à faire)
        _r3 = l2m.generer_carte_osm(_bb26, Path(_td26), "z", Path("x.pbf"),
                                    export_geojson=False, want_map=False)
        check("R2#26 want_map=False + export_geojson=False → None", _r3 is None)
finally:
    l2m._verifier_mapwriter = _orig_verif26
    l2m.generer_geojson_osm = _orig_gj26

print("== 23. R1#4 : signature de config au manifeste (cache/fraîcheur) ==")
import types as _types
def _args4(**kw):
    _d = dict(zoom_min=13, zoom_max=18, formats_image="auto", qualite_image=85,
              shading_specs=None, shading_preset=None, svf_gamma=1.0,
              svf_conv=None, svf_dist=None, sweep_horizon=True, layer=None,
              style=None, source=None, dfm=False, dfm_ground=None,
              elevation_soleil=45)
    _d.update(kw)
    return _types.SimpleNamespace(**_d)

def _sz(x1, y1, n, step):    # n×n cellules de côté `step`, origine (x1,y1)
    return [(i, j, x1+j*step, y1+i*step, x1+(j+1)*step, y1+(i+1)*step)
            for i in range(n) for j in range(n)]

_szA = _sz(650000, 6300000, 2, 1000)
_sigA = l2m._signature_config(_args4(), _szA)
check("R1#4 signature déterministe", _sigA == l2m._signature_config(_args4(), _szA))
check("R1#4 zoom_max ≠ → signature ≠", _sigA != l2m._signature_config(_args4(zoom_max=17), _szA))
check("R1#4 format ≠ → signature ≠", _sigA != l2m._signature_config(_args4(formats_image="png"), _szA))
check("R1#4 shading ≠ → signature ≠", _sigA != l2m._signature_config(_args4(shading_specs=["svf"]), _szA))
# split-width extend : même origine + même pas, +1 rangée → signature INCHANGÉE
check("R1#4 split-width extend (même origine+pas) → signature INCHANGÉE",
      _sigA == l2m._signature_config(_args4(), _sz(650000, 6300000, 3, 1000)))
check("R1#4 origine décalée → signature ≠",
      _sigA != l2m._signature_config(_args4(), _sz(651000, 6300000, 2, 1000)))
check("R1#4 pas de cellule ≠ (grille rescale) → signature ≠",
      _sigA != l2m._signature_config(_args4(), _sz(650000, 6300000, 2, 2000)))

with tempfile.TemporaryDirectory() as _td4:
    _mp = Path(_td4) / "manifeste.json"
    _m = l2m.Manifeste(_mp)
    _first = _m.verifier_signature("sigA")            # première pose
    _m._data["morceaux"]["001x001"] = {"termine": True}
    _m._data["fichiers"]["001x001"] = ["/x.tif"]
    _m._sauver()
    check("R1#4 première pose → False (rien à invalider)", _first is False)
    _m2 = l2m.Manifeste(_mp)
    check("R1#4 même signature → False + chunk conservé",
          l2m.Manifeste(_mp).verifier_signature("sigA") is False
          and _m2.deja_traite("001x001"))
    _m3 = l2m.Manifeste(_mp)
    _chg = _m3.verifier_signature("sigB")             # config changée
    check("R1#4 signature changée → True + morceaux/fichiers vidés",
          _chg is True and not _m3.deja_traite("001x001")
          and _m3._data["fichiers"] == {})

print("== 24. Lot cache/fraîcheur : R2#13 méta, R2#22 fraîcheur, R2#30 signature OSM ==")
import os as _os24, time as _time24

# R2#13 : le découpage conserve TOUTES les métadonnées source (pas 9 clés).
with tempfile.TemporaryDirectory() as _td13:
    _src13 = Path(_td13) / "base.mbtiles"
    _c13 = _sq.connect(str(_src13))
    _c13.executescript("CREATE TABLE metadata(name TEXT,value TEXT);"
                       "CREATE TABLE tiles(zoom_level INT,tile_column INT,"
                       "tile_row INT,tile_data BLOB);")
    # Pas de 'bounds' : la bbox est calculée depuis les tuiles (cf. §20). Les
    # clés attribution/json/scheme/licence sont celles dont on teste le report.
    for _k, _v in [("name", "base"), ("format", "jpg"), ("minzoom", "12"),
                   ("maxzoom", "12"),
                   ("attribution", "© IGN"), ("json", '{"vector_layers":[]}'),
                   ("scheme", "xyz"), ("licence", "etalab-2.0")]:
        _c13.execute("INSERT INTO metadata VALUES(?,?)", (_k, _v))
    for _col in range(2000, 2004):
        for _r in range(1000, 1004):
            _c13.execute("INSERT INTO tiles VALUES(?,?,?,?)", (12, _col, _r, _jpg()))
    _c13.commit(); _c13.close()
    _o13 = l2m.decouper_mbtiles(_src13, n_cols=2, n_rows=1,
                                dossier=Path(_td13) / "out", ecraser=True)
    check("R2#13 découpe produit des morceaux", len(_o13) >= 1)
    _m13 = _meta(_o13[0])
    check("R2#13 attribution conservée", _m13.get("attribution") == "© IGN")
    check("R2#13 json (vector_layers) conservé", _m13.get("json") == '{"vector_layers":[]}')
    check("R2#13 scheme+licence conservés",
          _m13.get("scheme") == "xyz" and _m13.get("licence") == "etalab-2.0")
    check("R2#13 name surchargé (propre au morceau)", _m13.get("name") != "base")

# R2#22 : _mbtiles_a_regenerer compare la fraîcheur vs source (mécanisme forcé
# à source=tif_source y compris already-warped).
# ignore_cleanup_errors : _mbtiles_a_regenerer ouvre une connexion sqlite ro que
# le `with` ne ferme pas → sur Windows le fichier reste brièvement verrouillé au
# rmtree du tempdir (course inoffensive, hors sujet du test).
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as _td22:
    _mbt22 = Path(_td22) / "x.mbtiles"
    _c22 = _sq.connect(str(_mbt22))
    _c22.executescript("CREATE TABLE tiles(zoom_level INT,tile_column INT,"
                       "tile_row INT,tile_data BLOB);")
    _c22.execute("INSERT INTO tiles VALUES(0,0,0,?)", (_jpg(),))
    _c22.commit(); _c22.close()
    _src22 = Path(_td22) / "src.tif"; _src22.write_bytes(b"x")
    _os24.utime(_src22, (_time24.time() - 100, _time24.time() - 100))
    check("R2#22 source plus vieille → réutilise (False)",
          not l2m._mbtiles_a_regenerer(_mbt22, False, source=_src22))
    _os24.utime(_src22, (_time24.time() + 100, _time24.time() + 100))
    check("R2#22 source plus récente → régénère (True)",
          l2m._mbtiles_a_regenerer(_mbt22, False, source=_src22))

# R2#30 : signature OSM + sidecar de config.
_so = l2m._signature_osm((2.0, 43.0, 3.0, 44.0), ["highway", "waterway"],
                         "paca-latest.osm.pbf", False)
check("R2#30 signature OSM déterministe (ordre tags indifférent)",
      _so == l2m._signature_osm((2.0, 43.0, 3.0, 44.0), ["waterway", "highway"],
                                "paca-latest.osm.pbf", False))
check("R2#30 tags ≠ → signature ≠",
      _so != l2m._signature_osm((2.0, 43.0, 3.0, 44.0), ["highway"],
                                "paca-latest.osm.pbf", False))
check("R2#30 bbox ≠ → signature ≠",
      _so != l2m._signature_osm((2.0, 43.0, 3.5, 44.0), ["highway", "waterway"],
                                "paca-latest.osm.pbf", False))
check("R2#30 skip_bbox ignore la bbox (mode région)",
      l2m._signature_osm((2.0, 43.0, 3.0, 44.0), ["h"], "x.pbf", True)
      == l2m._signature_osm((9.0, 9.0, 9.9, 9.9), ["h"], "x.pbf", True))
with tempfile.TemporaryDirectory() as _td30:
    _dl = Path(_td30) / "z.map"; _dl.write_text("fake")
    check("R2#30 sidecar absent → PAS périmé (migration douce)",
          not l2m._sig_sidecar_stale(_dl, "sigA"))
    l2m._sig_sidecar_ecrire(_dl, "sigA")
    check("R2#30 sidecar identique → pas périmé", not l2m._sig_sidecar_stale(_dl, "sigA"))
    check("R2#30 sidecar différent → périmé (régénérer)", l2m._sig_sidecar_stale(_dl, "sigB"))

print("== 25. Lot ressources/OOM : R2#9 RMAP clairsemé, R2#43 multipart, "
      "R2#35 intersection segment, R1#6 workers plafond ==")

# R1#6 : _dl_workers_effectif ne dépasse JAMAIS le plafond, mais --laz-parallel
# peut monter jusqu'au plafond ; sans plafond, il monte librement.
_dwe = l2m._dl_workers_effectif
check("R1#6 cap=3 lp=1 → 3", _dwe(8, 3, 1) == 3, detail=str(_dwe(8, 3, 1)))
check("R1#6 cap=3 lp=6 → 3 (jamais > plafond : LE bug)", _dwe(8, 3, 6) == 3,
      detail=str(_dwe(8, 3, 6)))
check("R1#6 cap=3 workers=2 lp=3 → 3 (lp monte jusqu'au plafond)",
      _dwe(2, 3, 3) == 3, detail=str(_dwe(2, 3, 3)))
check("R1#6 cap=3 workers=2 lp=1 → 2", _dwe(2, 3, 1) == 2, detail=str(_dwe(2, 3, 1)))
check("R1#6 sans plafond (None) lp=8 → 8 (monte librement)", _dwe(4, None, 8) == 8)
check("R1#6 cap=0 traité comme aucun plafond", _dwe(4, 0, 1) == 4)

# R2#35 : _seg_inter_box — un segment n'est binné que dans les tuiles traversées.
_sib = l2m._seg_inter_box
check("R2#35 diagonale coupe box sur le trajet", _sib(0, 0, 100, 100, 40, 40, 60, 60))
check("R2#35 diagonale ne coupe PAS box hors trajet (bas-droit)",
      not _sib(0, 0, 100, 100, 40, 0, 60, 20))
check("R2#35 diagonale ne coupe PAS box hors trajet (haut-gauche)",
      not _sib(0, 0, 100, 100, 0, 40, 20, 60))
check("R2#35 box contenant une extrémité → True", _sib(0, 0, 100, 100, 95, 95, 105, 105))
check("R2#35 horizontale coupe box à sa hauteur", _sib(0, 50, 100, 50, 40, 45, 60, 55))
check("R2#35 horizontale ne coupe pas box au-dessus",
      not _sib(0, 50, 100, 50, 40, 0, 60, 10))
check("R2#35 point (segment dégénéré) dans la box", _sib(50, 50, 50, 50, 40, 40, 60, 60))
check("R2#35 point hors box", not _sib(50, 50, 50, 50, 0, 0, 10, 10))

# R2#43 : _extraire_tiff_multipart désencapsule le GeoTIFF en mémoire bornée.
# Corps multipart/related synthétique avec un TIFF > HTTP_CHUNK_SIZE pour
# exercer le balayage en flux (magic à cheval sur chunks) + la fenêtre de queue.
_bnd = b"wcsBoundary"
_gml = b"<?xml version='1.0'?><gml:coverage>meta</gml:coverage>"
_tiff = b"II\x2a\x00" + bytes([0xAB]) * 200000 + b"REALTIFFTAIL"   # magic II*\0
_body = (b"--" + _bnd + b"\r\nContent-Type: application/gml+xml\r\n\r\n" + _gml +
         b"\r\n--" + _bnd + b"\r\nContent-Type: image/tiff\r\n\r\n" + _tiff +
         b"\r\n--" + _bnd + b"--\r\n")
with tempfile.TemporaryDirectory() as _td43:
    _f43 = Path(_td43) / "cov.tif"
    _f43.write_bytes(_body)
    l2m._extraire_tiff_multipart(_f43)
    _got = _f43.read_bytes()
    check("R2#43 multipart → TIFF pur extrait (byte-exact)", _got == _tiff,
          detail=f"len {len(_got)} vs {len(_tiff)}, head {_got[:4]!r}")
    # No-op sur un TIFF déjà brut.
    _f43b = Path(_td43) / "raw.tif"; _f43b.write_bytes(_tiff)
    l2m._extraire_tiff_multipart(_f43b)
    check("R2#43 TIFF brut inchangé (no-op)", _f43b.read_bytes() == _tiff)
    # No-op sur une réponse non-multipart non-TIFF (JSON d'erreur).
    _f43c = Path(_td43) / "err.json"; _f43c.write_bytes(b'{"error":"nope"}')
    l2m._extraire_tiff_multipart(_f43c)
    check("R2#43 non-multipart inchangé (no-op)", _f43c.read_bytes() == b'{"error":"nope"}')

# R2#9 : RMAP refuse une couverture clairsemée (rectangle min-max énorme, quasi
# vide) au lieu de matérialiser des millions de tuiles vides.
with tempfile.TemporaryDirectory() as _td9:
    _mb9 = Path(_td9) / "sparse.mbtiles"
    _c9 = _sq.connect(str(_mb9))
    _c9.executescript("CREATE TABLE metadata(name TEXT,value TEXT);"
                      "CREATE TABLE tiles(zoom_level INT,tile_column INT,"
                      "tile_row INT,tile_data BLOB);")
    _c9.execute("INSERT INTO metadata VALUES('format','jpg')")
    # 4 coins écartés à z11 → rectangle ≈ 1501×1501 ≈ 2,25 M positions, 4 réelles.
    for _col in (0, 1500):
        for _row in (0, 1500):
            _c9.execute("INSERT INTO tiles VALUES(?,?,?,?)", (11, _col, _row, _jpg()))
    _c9.commit(); _c9.close()
    _r9 = l2m.generer_rmap_depuis_mbtiles(_mb9, ecraser=True)
    check("R2#9 couverture clairsemée → refus (None)", _r9 is None)
    check("R2#9 aucun .rmap créé sur refus",
          not (_mb9.with_suffix(".rmap")).exists())
    # Contrôle : une couverture dense (1 tuile, rectangle plein) n'est PAS refusée.
    _mb9d = Path(_td9) / "dense.mbtiles"
    _c9d = _sq.connect(str(_mb9d))
    _c9d.executescript("CREATE TABLE metadata(name TEXT,value TEXT);"
                       "CREATE TABLE tiles(zoom_level INT,tile_column INT,"
                       "tile_row INT,tile_data BLOB);")
    _c9d.execute("INSERT INTO metadata VALUES('format','jpg')")
    _c9d.execute("INSERT INTO tiles VALUES(?,?,?,?)", (10, 500, 300, _jpg()))
    _c9d.commit(); _c9d.close()
    _r9d = l2m.generer_rmap_depuis_mbtiles(_mb9d, ecraser=True)
    check("R2#9 couverture dense NON refusée (contrôle)",
          _r9d is not None and _r9d.exists())

print("== 26. Lot P2 géométrie : R2#46 densification bbox reprojetée ==")
# R2#46 : un bord reprojeté est courbe → l'extremum peut tomber au MILIEU d'un
# bord, pas à un coin. Transform à bord haut « bombé » : y_out = y + sin(x/10·π),
# nul aux coins (x=0,10) et max=1 au milieu (x=5). L'enveloppe 4-coins raterait
# ce +1 ; la version densifiée doit le capturer.
def _tf_bombe(x, y):
    return (x, y + math.sin(x / 10.0 * math.pi))

_bx0, _by0, _bx1, _by1 = l2m._bbox_enveloppe_transform(_tf_bombe, 0.0, 0.0, 10.0, 1.0)
# densify=21 n'échantillonne pas exactement x=5 → capture ~1.997 (à la résolution
# d'échantillonnage), TRÈS au-dessus du 1.0 des 4 coins : c'est bien l'extremum.
check("R2#46 densifié capture l'extremum de bord (max_y≈2, >1.99)",
      _by1 > 1.99, detail=f"max_y={_by1:.4f}")
# densify=1 = coins seuls (bornes t=0/t=1) → rate le bombement (max_y≈1).
_c0, _cy0, _c1, _cy1 = l2m._bbox_enveloppe_transform(_tf_bombe, 0.0, 0.0, 10.0, 1.0,
                                                     densify=1)
check("R2#46 contrôle : 4 coins seuls ratent l'extremum (max_y≈1)",
      abs(_cy1 - 1.0) < 1e-3, detail=f"max_y coins={_cy1:.4f}")
# Cohérence : l'enveloppe densifiée ⊇ enveloppe coins (min plus bas, max plus haut).
check("R2#46 densifié est un sur-ensemble des coins",
      _bx0 <= _c0 + 1e-9 and _by0 <= _cy0 + 1e-9
      and _bx1 >= _c1 - 1e-9 and _by1 >= _cy1 - 1e-9)
# Transform identité : bbox inchangée (pas de sur-extension parasite).
_ix0, _iy0, _ix1, _iy1 = l2m._bbox_enveloppe_transform(lambda x, y: (x, y),
                                                       2.0, 43.0, 3.0, 44.0)
check("R2#46 identité : bbox préservée",
      (_ix0, _iy0, _ix1, _iy1) == (2.0, 43.0, 3.0, 44.0))

print("== 27. R2#28 filtrage OSM : valeur, ordre déterministe, défauts ==")
# Volet 1 : "highway=path" doit filtrer SUR LA VALEUR (ne pas garder motorway).
_c, _v = l2m._osm_filtre_cles(["highway=path"])
check("R2#28 parse highway=path → clé highway, valeur {path}",
      _c == ["highway"] and _v == {"highway": {"path"}})
check("R2#28 highway=path retient highway=path",
      l2m._osm_cle_match({"highway": "path"}, _c, _v) == ("highway", "path"))
check("R2#28 highway=path REJETTE highway=motorway (le bug)",
      l2m._osm_cle_match({"highway": "motorway"}, _c, _v) == (None, None))
# Clé nue ou '*' = toutes les valeurs.
for _spec in (["highway"], ["highway=*"]):
    _c2, _v2 = l2m._osm_filtre_cles(_spec)
    check(f"R2#28 {_spec[0]} accepte toute valeur",
          _v2 == {"highway": None}
          and l2m._osm_cle_match({"highway": "motorway"}, _c2, _v2)
          == ("highway", "motorway"))
# Multi-valeur + union sur clé répétée.
_c3, _v3 = l2m._osm_filtre_cles(["highway=path,track", "highway=steps"])
check("R2#28 multi-valeur + union clé répétée",
      _v3 == {"highway": {"path", "track", "steps"}})
# Clé nue absorbe une valeur spécifique donnée après.
_c4, _v4 = l2m._osm_filtre_cles(["natural=water", "natural"])
check("R2#28 clé nue absorbe (natural=water puis natural → toutes)",
      _v4 == {"natural": None})
# Volet 2 : l'ORDRE d'apparition fixe la couche gagnante (déterministe), pas un
# set. Un objet à 2 clés thématiques → la 1re clé listée gagne, invariant sur
# l'ordre d'entrée.
_ca, _va = l2m._osm_filtre_cles(["natural=water", "waterway=river"])
_cb, _vb = l2m._osm_filtre_cles(["waterway=river", "natural=water"])
_feat2 = {"natural": "water", "waterway": "river"}
check("R2#28 ordre déterministe : 1re clé listée gagne (natural avant waterway)",
      l2m._osm_cle_match(_feat2, _ca, _va) == ("natural", "water"))
check("R2#28 ordre déterministe : entrée inversée → waterway gagne",
      l2m._osm_cle_match(_feat2, _cb, _vb) == ("waterway", "river"))
# Une clé de valeur hors filtre n'arrête pas la recherche : on continue.
_c5, _v5 = l2m._osm_filtre_cles(["highway=path", "natural=water"])
check("R2#28 clé présente hors-valeur → on continue vers la clé suivante",
      l2m._osm_cle_match({"highway": "motorway", "natural": "water"}, _c5, _v5)
      == ("natural", "water"))
# Volet 4 : les défauts incluent désormais place ET historic.
_cd, _vd = l2m._osm_filtre_cles(None)
check("R2#28 défauts incluent place et historic (volet 4)",
      "place" in _cd and "historic" in _cd
      and _vd.get("place") is None and _vd.get("historic") is None)
check("R2#28 défauts : match d'un POI historic=ruins",
      l2m._osm_cle_match({"historic": "ruins"}, _cd, _vd) == ("historic", "ruins"))
# Tokens vides/espaces ignorés proprement.
_ce, _ve = l2m._osm_filtre_cles(["  ", "highway = path "])
check("R2#28 tokens vides ignorés + espaces tolérés",
      _ce == ["highway"] and _ve == {"highway": {"path"}})

print("== 28. R2#29 emprise OSM hors métropole : conversion CRS-provider ==")
# Le chemin OSM convertissait la bbox en WGS84 via la formule Lambert 93 FRANCE
# en dur ; pour un provider hors métropole (Suisse EPSG:2056, UTM ultramarin…)
# ça sortait des coords fausses → emprise/découpage OSM décalés. Le fix route
# par _natif_vers_wgs84 (pyproj, CRS du provider). On vérifie que, PROVIDER
# suisse, le helper rend des coords en Suisse, là où la formule France dérive.
from types import SimpleNamespace
_prov_backup = getattr(l2m, "PROVIDER", None)
try:
    l2m.PROVIDER = SimpleNamespace(CRS_NATIF="EPSG:2056")
    # Berne en LV95 (E=2600000, N=1200000) ≈ (7.44°E, 46.95°N).
    _lon, _lat = l2m._natif_vers_wgs84(2600000.0, 1200000.0)
    check("R2#29 _natif_vers_wgs84 (EPSG:2056) → Suisse (lon≈7.4, lat≈47)",
          6.5 < _lon < 8.5 and 46.0 < _lat < 47.5,
          detail=f"lon={_lon:.3f} lat={_lat:.3f}")
    # La formule France en dur sur les MÊMES nombres part ailleurs (le bug).
    _lonF, _latF = l2m.lamb93_to_wgs84_approx(2600000.0, 1200000.0)
    check("R2#29 formule France en dur diverge (démontre le bug)",
          not (6.5 < _lonF < 8.5 and 46.0 < _latF < 47.5),
          detail=f"lonF={_lonF:.3f} latF={_latF:.3f}")
    # Enveloppe bbox via le helper provider : reste dans le voisinage suisse.
    _b = l2m._bbox_enveloppe_transform(l2m._natif_vers_wgs84,
                                       2590000.0, 1190000.0, 2610000.0, 1210000.0)
    check("R2#29 enveloppe bbox provider-aware cohérente (Suisse)",
          6.0 < _b[0] < 8.5 and 45.5 < _b[1] < 47.5
          and 6.0 < _b[2] < 8.5 and 45.5 < _b[3] < 47.5,
          detail=f"bbox={tuple(round(v, 2) for v in _b)}")
finally:
    l2m.PROVIDER = _prov_backup

print("== 29. R2#41/#25/#39 validation des arguments CLI ==")
def _leve(fn, s):
    try:
        fn(s); return False
    except Exception:
        return True
# R2#41 : --workers/--laz-parallel doivent être des int >= 1 (max_workers<1
# plantait ThreadPoolExecutor).
check("R2#41 _arg_int_positif accepte 8 et 1",
      l2m._arg_int_positif("8") == 8 and l2m._arg_int_positif("1") == 1)
check("R2#41 _arg_int_positif rejette 0", _leve(l2m._arg_int_positif, "0"))
check("R2#41 _arg_int_positif rejette négatif", _leve(l2m._arg_int_positif, "-3"))
check("R2#41 _arg_int_positif rejette non-entier", _leve(l2m._arg_int_positif, "abc"))
# R2#25 : les floats non finis (nan/inf) passaient float() puis neutralisaient
# silencieusement les features (nan>0 == False).
check("R2#25 _arg_float_fini accepte 1.5", l2m._arg_float_fini("1.5") == 1.5)
check("R2#25 _arg_float_fini rejette nan", _leve(l2m._arg_float_fini, "nan"))
check("R2#25 _arg_float_fini rejette inf", _leve(l2m._arg_float_fini, "inf"))
check("R2#25 _arg_float_fini rejette -inf", _leve(l2m._arg_float_fini, "-inf"))
check("R2#25 _arg_float_non_negatif accepte 0",
      l2m._arg_float_non_negatif("0") == 0.0)
check("R2#25 _arg_float_non_negatif rejette négatif",
      _leve(l2m._arg_float_non_negatif, "-1"))
check("R2#25 _arg_float_non_negatif rejette nan (split-width/min-free-gb)",
      _leve(l2m._arg_float_non_negatif, "nan"))
check("R2#25 _arg_float_positif accepte 0.5",
      l2m._arg_float_positif("0.5") == 0.5)
check("R2#25 _arg_float_positif rejette 0", _leve(l2m._arg_float_positif, "0"))
check("R2#25 _arg_float_positif rejette inf", _leve(l2m._arg_float_positif, "inf"))
# R2#39 : le pré-parser manuel n'avale plus `--` ni un flag comme valeur.
check("R2#39 valeur normale prise",
      l2m._pre_valeur_suivante(["--provider", "us-tnm"], 0) == "us-tnm")
check("R2#39 séparateur -- non avalé (le bug)",
      l2m._pre_valeur_suivante(["--provider", "--"], 0) is None)
check("R2#39 flag suivant non avalé",
      l2m._pre_valeur_suivante(["--provider", "--laz"], 0) is None)
check("R2#39 valeur manquante en fin d'argv",
      l2m._pre_valeur_suivante(["--provider"], 0) is None)
check("R2#39 nombre négatif reste une valeur (--laz-hmin -0.5)",
      l2m._pre_valeur_suivante(["--laz-hmin", "-0.5"], 0) == "-0.5")

print("== 30. R2#24 : collision de noms d'ombrages (warn au lieu d'abandon muet) ==")
# Le suffixe encode dist en mètres entiers et gamma à une décimale : deux
# réglages distincts peuvent retomber sur le même nom. Avant : le 2e était
# abandonné en silence (« doublon exact » mensonger). Après : warning explicite,
# et un vrai doublon (mêmes params) reste silencieux.
import io, contextlib
_dc = tmp / "collide"; _dc.mkdir()
# dist 30.4 et 30.1 -> tous deux 30 m ; gamma 0.92 et 0.88 -> tous deux 0.9.
_inst_col = [l2m.parser_shading_spec(s) for s in
             ("svf:dist=30.4,gamma=0.92", "svf:dist=30.1,gamma=0.88")]
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    l2m.generer_ombrages([src_i], _dc, choix=[], nom_zone="zc",
                         instances=_inst_col, bbox_natif=None)
_out = _buf.getvalue()
_files_col = {f.name for f in _dc.glob("zc_*.tif")}
check("R2#24 collision distincte -> un seul fichier produit",
      _files_col == {"zc_svf_flux_30m_g0p9_ombrage.tif"},
      f"fichiers : {_files_col}")
check("R2#24 collision distincte -> warning émis", "collapses to the same name" in _out,
      _out.strip().splitlines()[-3:] if _out else "(vide)")
# Vrai doublon (spec identique deux fois) : silencieux, un seul fichier.
_dd = tmp / "dup"; _dd.mkdir()
_inst_dup = [l2m.parser_shading_spec("svf:dist=40,gamma=1.0")] * 2
_buf2 = io.StringIO()
with contextlib.redirect_stdout(_buf2):
    l2m.generer_ombrages([src_i], _dd, choix=[], nom_zone="zd",
                         instances=_inst_dup, bbox_natif=None)
check("R2#24 vrai doublon -> pas de warning (silencieux)",
      "collapses to the same name" not in _buf2.getvalue())
check("R2#24 vrai doublon -> un seul fichier",
      {f.name for f in _dd.glob("zd_*.tif")} == {"zd_svf_flux_40m_g1p0_ombrage.tif"})

print("== 31. R2#18 nom WMTS versionné qualité + R2#48 install transactionnelle ==")
# R2#18 #3 : le nom du MBTiles WMTS doit encoder la qualité quand une conversion
# PNG->JPEG a lieu, sinon relancer avec --image-quality différent réutilise un
# fichier obsolète de même nom.
_n_native = l2m._nom_mbtiles_wmts("zz", "ortho", 10, 16, None)
check("R2#18 natif (jpeg_q None) -> pas de segment qualité",
      _n_native == "zz_ortho_z10-16", _n_native)
_n_q75 = l2m._nom_mbtiles_wmts("zz", "planign", 10, 16, 75)
_n_q50 = l2m._nom_mbtiles_wmts("zz", "planign", 10, 16, 50)
check("R2#18 conversion -> segment _q<Q> dans le nom", _n_q75 == "zz_planign_z10-16_q75", _n_q75)
check("R2#18 qualités distinctes -> noms distincts (régénère)", _n_q75 != _n_q50)
check("R2#18 float qualité tronqué en int", l2m._nom_mbtiles_wmts("z", "c", 1, 2, 84.0)
      == "z_c_z1-2_q84")

# R2#48 : _bin_outil ne valide que si le binaire est dans un dossier bin/ ;
# _promouvoir_dossier remplace une install partielle antérieure de façon atomique.
_root = tmp / "r48"; _root.mkdir()
(_root / "lib").mkdir(); (_root / "lib" / "osmosis.jar").write_text("x")
check("R2#48 _bin_outil : binaire hors bin/ -> None (install incomplète)",
      l2m._bin_outil(_root, "osmosis") is None)
(_root / "bin").mkdir(); (_root / "bin" / "osmosis").write_text("#!/bin/sh")
_found = l2m._bin_outil(_root, "osmosis")
check("R2#48 _bin_outil : binaire dans bin/ -> trouvé",
      _found is not None and _found.name == "osmosis")

# Promotion : dest partiel (contenu obsolète) remplacé par le temp complet.
_dest48 = tmp / "dest48"; _dest48.mkdir()
(_dest48 / "vieux.txt").write_text("stale")     # install partielle antérieure
_tmp48 = tmp / "dest48.tmp-123"; _tmp48.mkdir()
(_tmp48 / "bin").mkdir(); (_tmp48 / "bin" / "java").write_text("ok")
l2m._promouvoir_dossier(_tmp48, _dest48)
check("R2#48 promotion : partiel antérieur retiré",
      not (_dest48 / "vieux.txt").exists())
check("R2#48 promotion : contenu temp en place",
      (_dest48 / "bin" / "java").exists())
check("R2#48 promotion : dossier temp consommé (renommé)", not _tmp48.exists())
# Cible inexistante : simple rename.
_dest48b = tmp / "dest48b"       # n'existe pas
_tmp48b = tmp / "dest48b.tmp-9"; _tmp48b.mkdir()
(_tmp48b / "f").write_text("y")
l2m._promouvoir_dossier(_tmp48b, _dest48b)
check("R2#48 promotion vers cible neuve", (_dest48b / "f").exists() and not _tmp48b.exists())

print("== 32. R1#10 : complétude chunk quand mbtiles intermédiaire supprimé ==")
# _chunk_livrable_complet : quand seuls rmap/sqlitedb sont demandés, le mbtiles
# intermédiaire est supprimé après conversion. La complétude doit se mesurer sur
# les livrables survivants (.rmap/.sqlitedb), pas sur le mbtiles absent, sinon un
# chunk réussi est marqué INCOMPLETE et rejoué en boucle (cleanup refusé).
def _args(**k):
    _d = {"mbtiles": False, "rmap": False, "sqlitedb": False}
    _d.update(k)
    return SimpleNamespace(**_d)
_dc = tmp / "chunk_r110"; _dc.mkdir()
# rmap-only, mbtiles ABSENT (supprimé), .rmap présent -> complet (le bug : False)
(_dc / "z_svf.rmap").write_text("rmap")
check("R1#10 rmap-only + .rmap présent (mbtiles absent) -> complet",
      l2m._chunk_livrable_complet(_dc, _args(rmap=True)) is True)
# rmap-only sans .rmap -> incomplet
_dc2 = tmp / "chunk_r110b"; _dc2.mkdir()
check("R1#10 rmap-only sans livrable -> incomplet",
      l2m._chunk_livrable_complet(_dc2, _args(rmap=True)) is False)
# sqlitedb-only + .sqlitedb présent -> complet
_dc3 = tmp / "chunk_r110c"; _dc3.mkdir()
(_dc3 / "z_svf.sqlitedb").write_text("db")
check("R1#10 sqlitedb-only + .sqlitedb présent -> complet",
      l2m._chunk_livrable_complet(_dc3, _args(sqlitedb=True)) is True)
# mbtiles demandé : on valide le CONTENU (monkeypatch _mbtiles_est_complete).
_dc4 = tmp / "chunk_r110d"; _dc4.mkdir()
(_dc4 / "z_svf.mbtiles").write_text("mbt")
_orig_est = l2m._mbtiles_est_complete
try:
    l2m._mbtiles_est_complete = lambda m: True
    check("R1#10 mbtiles+rmap demandés mais rmap absent -> incomplet",
          l2m._chunk_livrable_complet(_dc4, _args(mbtiles=True, rmap=True)) is False)
    (_dc4 / "z_svf.rmap").write_text("rmap")
    check("R1#10 mbtiles+rmap demandés et présents -> complet",
          l2m._chunk_livrable_complet(_dc4, _args(mbtiles=True, rmap=True)) is True)
    l2m._mbtiles_est_complete = lambda m: False
    check("R1#10 mbtiles demandé + contenu vide -> incomplet (contenu, pas présence)",
          l2m._chunk_livrable_complet(_dc4, _args(mbtiles=True)) is False)
finally:
    l2m._mbtiles_est_complete = _orig_est
# mbtiles absent + mbtiles demandé -> incomplet
_dc5 = tmp / "chunk_r110e"; _dc5.mkdir()
check("R1#10 mbtiles demandé mais absent -> incomplet",
      l2m._chunk_livrable_complet(_dc5, _args(mbtiles=True)) is False)

# -- R1#10 concurrence : lock CRS COPC multi-UTM -------------------------------
# telecharger_copc_fenetre pose le CRS UTM PAR TUILE sur le PROVIDER partagé
# (set_crs -> self.crs_epsg) puis convertit (post_fetch le lit). En multi-UTM,
# 2 tuiles concurrentes se corrompaient. _copc_post_fetch_crs sérialise le couple
# sous _copc_crs_lock. N threads d'EPSG distincts + fenêtre de course : chaque
# conversion doit voir SON crs (sans lock, une voisine l'écraserait pendant le
# sleep). Le PROVIDER et _post_fetch sont patchés (mêmes globals que le helper).
import threading as _th, time as _tm
_orig_prov = l2m.PROVIDER
_orig_pf = l2m._post_fetch_si_besoin
try:
    class _MockProv:
        def __init__(self):
            self.crs_epsg = 0

        def set_crs(self, e):
            self.crs_epsg = int(e)

    l2m.PROVIDER = _MockProv()
    _vus = []
    _barr = _th.Barrier(8)

    def _pf_mock(chemin_part):
        _attendu = int(str(chemin_part))   # chemin_part encode l'epsg attendu
        _tm.sleep(0.003)                   # fenêtre de course
        _vus.append((_attendu, l2m.PROVIDER.crs_epsg))

    l2m._post_fetch_si_besoin = _pf_mock

    def _work(epsg):
        _barr.wait()
        l2m._copc_post_fetch_crs(epsg, str(epsg))

    _ths = [_th.Thread(target=_work, args=(32610 + i,)) for i in range(8)]
    for _t in _ths:
        _t.start()
    for _t in _ths:
        _t.join()
    _mauvais = [(a, v) for a, v in _vus if a != v]
    check("R1#10 lock CRS COPC : 8 tuiles UTM concurrentes voient chacune leur CRS",
          len(_vus) == 8 and not _mauvais)
finally:
    l2m.PROVIDER = _orig_prov
    l2m._post_fetch_si_besoin = _orig_pf

print("== 23. Planche : emprise WFS d'un itinéraire recadrée sur la zone demandée ==")
# Un WFS IGN "itinéraires anciens" renvoie la géométrie ENTIÈRE d'un tracé qui
# traverse seulement la zone (ex. une véloroute de centaines de km pour une
# zone de quelques km) : sans recadrage, l'emprise calculée pour la planche
# dérive très loin de la zone réelle (reverse-geocoding département en échec,
# planche illisible à l'échelle du tracé entier). Reproduit avec un LineString
# dont la bbox dépasse largement la zone demandée.
import json as _json23
with tempfile.TemporaryDirectory() as _td23:
    _dossier23 = Path(_td23)
    _gj23 = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "LineString",
                # Traverse toute la côte méditerranéenne (Perpignan-Menton),
                # comme l'EV8 réel qui a déclenché le bug.
                "coordinates": [[2.8, 42.45], [4.0, 43.0], [6.05, 43.33], [7.5, 43.95]],
            },
        }],
    }
    (_dossier23 / "d_ign_itineraire.geojson").write_text(
        _json23.dumps(_gj23), encoding="utf-8")

    _zone23 = (6.0210, 43.3113, 6.0705, 43.3474)   # zone Garéoult ~4 km, réelle
    _appels_contours = []
    _appels_planche = []
    _orig_contours = l2m._planche_contours_dept
    _orig_generer = l2m._generer_planche

    def _contours_mock(bbox_wgs84, args):
        _appels_contours.append(bbox_wgs84)
        return None

    def _generer_mock(bbox_wgs84, cells, nom_zone, dossier, args, contours=None):
        _appels_planche.append(bbox_wgs84)

    l2m._planche_contours_dept = _contours_mock
    l2m._generer_planche = _generer_mock
    try:
        # Sans zone_bbox_wgs84 (comportement historique) : l'emprise reste
        # celle du tracé entier, largement hors de la zone demandée.
        l2m._planche_depuis_dossier(_dossier23, SimpleNamespace(index_map=True),
                                    nom_zone="d")
        _sans_recadrage = _appels_planche[-1]
        check("sans recadrage : emprise dérive hors zone (largeur > 1°, bug reproduit)",
              (_sans_recadrage[2] - _sans_recadrage[0]) > 1.0,
              detail=str(_sans_recadrage))

        _appels_contours.clear(); _appels_planche.clear()
        # Avec zone_bbox_wgs84 (correctif) : l'emprise doit rester bornée à la
        # zone réellement demandée.
        l2m._planche_depuis_dossier(_dossier23, SimpleNamespace(index_map=True),
                                    nom_zone="d", zone_bbox_wgs84=_zone23)
        _avec_recadrage = _appels_planche[-1]
        check("avec recadrage : emprise planche == zone demandée",
              _avec_recadrage == _zone23, detail=str(_avec_recadrage))
        check("avec recadrage : emprise passée au reverse-geocoding == zone demandée",
              _appels_contours and _appels_contours[0] == _zone23,
              detail=str(_appels_contours))
    finally:
        l2m._planche_contours_dept = _orig_contours
        l2m._generer_planche = _orig_generer

print()
print("TOUS OK" if ok_all else "ÉCHECS DÉTECTÉS")
sys.exit(0 if ok_all else 1)
