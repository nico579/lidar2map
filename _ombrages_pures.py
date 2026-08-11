"""Couche pure du pipeline d'ombrages : IO raster, kernels numba et
algorithmes de calcul par type (hillshade, SVF, LRM, RRIM).

Regroupe la partie scientifique du bloc « ASSEMBLAGE COG » qui n'a pas de
dépendance applicative (pas de ``PROVIDER``, pas d'``args`` CLI) : chaque
fonction prend des chemins/arrays en entrée et produit des chemins/arrays en
sortie. L'orchestrateur (``generer_ombrages``, presets, VAT/MSTP, fetch
provider) reste dans ``lidar2map.py`` pour l'instant (sous-phases 9c/9d).

``_stop_event`` a son foyer canonique ici plutôt que dans ``lidar2map.py`` :
plusieurs fonctions de ce module (``_hillshade_chunked_multi``, `_svf_chunked`,
``_svf_opos_chunked``, ``_svf_numpy``, ``_rrim_chunked``) le lisent en
variable libre et sont appelées DIRECTEMENT par les suites de tests
(`_test_corrections.py`), sans passer par une façade — les y injecter aurait
cassé des dizaines d'appels positionnels existants. `lidar2map.py` réexporte
ce nom (``from _ombrages_pures import _stop_event``) : c'est le MÊME objet
partout (mutation via ``.set()``/``.clear()``, jamais de réaffectation), donc
le handler SIGINT de `lidar2map.py` continue de piloter l'annulation ici
correctement. ``SVF_GAMMA`` suit la même logique (valeur par défaut liée à la
signature de ``_svf_chunked`` à la définition, pas à l'appel).
"""

from __future__ import annotations

import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading


# Gamma appliqué au SVF après stretch percentile (p2→p98) avant ×255.
# <1 éclaircit (√), 1 = linéaire, >1 assombrit. Le SVF flux cos²γ est tassé
# près de 1 : gamma 2.0 assombrit les midtones et fait ressortir le contraste
# (rendu jugé meilleur à l'œil que la variante RVT 1−sin γ). Surchargeable
# via --svf-gamma ou le champ γ du GUI.
SVF_GAMMA = 2.0

# Événement d'arrêt propre — positionné par Ctrl+C en mode CLI (handler dans
# lidar2map.py). Vérifié dans les boucles longues de ce module pour
# interrompre entre deux itérations sans laisser de thread zombie.
_stop_event = threading.Event()


def _sauver_array_georef(arr, src_tif, dst_tif, *, formater_duree):
    """
    Sauvegarde un numpy array uint8 (2D niveaux de gris ou 3D RGB) en GeoTIFF
    en copiant le géoréférencement de src_tif via rasterio.

    arr   : numpy uint8 shape (H,W) pour L, (H,W,3) pour RGB
    """
    import numpy as np
    import rasterio

    n_bands = 1 if arr.ndim == 2 else arr.shape[2]

    with rasterio.open(str(src_tif)) as src:
        profile = src.profile.copy()

    # La destination peut finir par ``.part`` pendant une publication
    # atomique : ne pas laisser GDAL déduire le format depuis l'extension, ni
    # hériter du driver VRT quand ``src_tif`` est la mosaïque virtuelle.
    for k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        profile.pop(k, None)
    profile.update(
        driver    = "GTiff",
        dtype     = "uint8",
        count     = n_bands,
        compress  = "deflate",
        predictor = 2,
        tiled     = True,
        blockxsize = 512,
        blockysize = 512,
        bigtiff   = "IF_SAFER",
        nodata    = None,
    )

    _t0 = time.time()
    with rasterio.open(str(dst_tif), "w", **profile) as dst:
        if arr.ndim == 2:
            dst.write(arr.astype(np.uint8), 1)
        else:
            for b in range(n_bands):
                dst.write(arr[:, :, b].astype(np.uint8), b + 1)
    print(f"  rasterio write OK  ({formater_duree(time.time()-_t0)})", flush=True)


def _publier_tif_atomique(chemin_part, chemin_final, *, valider_tif):
    """Valide un GeoTIFF fermé puis le publie par remplacement atomique.

    ``chemin_final`` n'est jamais supprimé au préalable : si l'écriture ou la
    validation de ``chemin_part`` échoue, l'éventuelle version complète déjà
    présente reste intacte.
    """
    chemin_part = Path(chemin_part)
    chemin_final = Path(chemin_final)
    if not valider_tif(chemin_part):
        raise RuntimeError(
            f"GeoTIFF temporaire invalide ou incomplet: {chemin_part.name}"
        )
    os.replace(chemin_part, chemin_final)


# ── Helpers lecture DEM ───────────────────────────────────────────────────────

def _lire_dem_rasterio(src_path):
    """
    Lit un GeoTIFF DEM (bande 1) et retourne un numpy float32.

    Utilise rasterio en priorité (gestion native du nodata, DEFLATE, BigTIFF).
    Fallback PIL si rasterio absent.

    Retourne : (arr_float32, nodata_value | None)
    """
    import numpy as np
    try:
        import rasterio as _rio
        with _rio.open(str(src_path)) as src:
            arr = src.read(1).astype(np.float32)
            nodata = src.nodata
        return arr, nodata
    except ImportError:
        pass
    except Exception as e_rio:
        print(f"  WARNING rasterio read ({e_rio}) — repli PIL", flush=True)

    from PIL import Image as _Img
    return np.array(_Img.open(str(src_path)), dtype=np.float32), None


def _nodata_mask(arr, nodata=None):
    """Masque nodata unifié : sentinelles hors plage altimétrique (|z| > 9000 m,
    couvre le -9999 IGN comme les ±3.4e38) + valeur nodata déclarée du raster.

    Convention unique partagée par hillshade/SVF/LRM/RRIM — avant ce helper,
    les trois fonctions chunked utilisaient chacune une variante différente
    (magique seul, déclaré seul, ou les deux), donc un provider avec un nodata
    déclaré dans [-9000, 9000] passait au travers du SVF mais pas du LRM.
    """
    import numpy as np
    mask = (arr < -9000) | (arr > 9000)
    # NaN est TOUJOURS invalide (bords de reprojection, trous provider), quel que
    # soit le nodata déclaré (R2#21). Avant, np.isnan(arr) n'était ajouté QUE si
    # nodata était lui-même NaN : un DEM à NaN bruts mais nodata -9999/None (ou
    # nodata absent) laissait filer les NaN jusqu'à astype(uint8) → pixels
    # noirs/garbage dans l'ombrage. NaN échappe aussi aux comparaisons de la
    # bande sentinelle (NaN < -9000 = False). Garde de dtype : np.isnan lève sur
    # un array entier (arr peut être un MNT int selon le provider).
    if np.issubdtype(arr.dtype, np.floating):
        mask |= np.isnan(arr)
    if nodata is not None and not np.isnan(nodata):
        mask |= (arr == nodata)
    return mask


def _source_a_des_donnees(source, max_dim=512):
    """True si `source` contient au moins un pixel d'altitude valide.

    Lecture décimée (overview <= max_dim px) : rapide même sur une zone
    départementale. Garde-fou avant les ombrages : une zone entièrement nodata
    (dalles IGN non encore publiées = placeholders -9999, ou index TMS
    indisponible au download → fallback grille qui rapatrie des dalles vides)
    ne doit ni planter le SVF (percentile sur tableau vide) ni produire un
    MBTiles vide silencieux. En cas de doute (lecture impossible), on renvoie
    True pour ne pas bloquer le pipeline.
    """
    try:
        import rasterio
        with rasterio.open(str(source)) as ds:
            h, w = ds.height, ds.width
            scale = max(1, int(max(h, w) / max_dim))
            arr = ds.read(1, out_shape=(max(1, h // scale), max(1, w // scale)))
            nd = ds.nodata
        return bool((~_nodata_mask(arr, nd)).any())
    except Exception:
        return True


def _percentiles_grille(src_path, halo, calc_block, p_lo, p_hi):
    """Percentiles globaux estimés sur une grille 3×3 de fenêtres réparties
    sur toute l'étendue du raster (fractions 0.2/0.5/0.8 en x et y).

    calc_block : fenêtre float32 (avec halo) → array de valeurs, NaN aux
    pixels invalides (nodata) — OU tuple d'arrays pour un calcul
    multi-sorties en un seul passage (ex. kernel fusionné SVF+openness du
    VAT : sans ça, la passe d'échantillonnage scannait deux fois les mêmes
    fenêtres). Les valeurs finies de toutes les fenêtres sont mises en
    commun avant le calcul des percentiles.

    Un crop unique rendrait le stretch dépendant de ce que contient ce crop
    (même terrain → rendu différent selon le cadrage) — régression de rendu
    silencieuse déjà rencontrée sur le SVF, d'où la grille. Partagé par
    SVF / LRM / RRIM / VAT.

    Retourne (lo, hi, n_valides) ou None si trop peu de pixels valides ;
    en multi-sorties, une liste avec une entrée (ou None) par sortie.
    """
    import numpy as np
    import rasterio as _rio
    from rasterio.windows import Window
    SAMPLE = 192
    s_half = SAMPLE // 2
    _fracs = (0.2, 0.5, 0.8)
    pools = None
    multi = False
    with _rio.open(str(src_path)) as src:
        H, W = src.height, src.width
        for _fy in _fracs:
            cy = int(H * _fy)
            for _fx in _fracs:
                cx = int(W * _fx)
                r0 = max(0, cy - s_half - halo)
                c0 = max(0, cx - s_half - halo)
                r1 = min(H, cy + s_half + halo)
                c1 = min(W, cx + s_half + halo)
                if r1 - r0 < 8 or c1 - c0 < 8:
                    continue
                win = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(np.float32)
                vals = calc_block(win)
                multi = isinstance(vals, tuple)
                outs = vals if multi else (vals,)
                if pools is None:
                    pools = [[] for _ in outs]
                for k, v in enumerate(outs):
                    pools[k].append(v[np.isfinite(v)])
    if pools is None:
        return None

    def _stats(pool):
        valid = np.concatenate(pool) if pool else np.empty(0, dtype=np.float32)
        if len(valid) < 100:
            return None
        return (float(np.percentile(valid, p_lo)),
                float(np.percentile(valid, p_hi)),
                len(valid))

    res = [_stats(p) for p in pools]
    return res if multi else res[0]


# ── Hillshade et slope numpy (remplacent gdaldem CLI) ─────────────────────────

# Cache des kernels Numba (compilation paresseuse au 1er appel, partagée entre
# tous les modes — évite la double compilation entre _svf_numpy et _svf_chunked,
# et entre les variantes hillshade/multi/slope).
_NUMBA_KERNELS_CACHE = {}


def _ensure_numba():
    """Garantit que numba est importable, en l'installant à la demande si absent.

    numba accélère hillshade/slope/SVF/openness de ×15 à ×50 (JIT LLVM). Il est
    normalement posé par le bootstrap venv, mais un venv ancien ou un install
    optionnel qui a échoué peut le laisser manquant. On l'installe alors ici, au
    moment où un ombrage numba est réellement demandé (même logique que
    laspy/lazrs pour le LAZ dans providers.common._check_deps).

    PAS de repli numpy silencieux : si l'install échoue, on lève une erreur
    claire plutôt que de dégrader d'un facteur 15-50 sans le dire. Le binaire
    PyInstaller embarque déjà numba, donc ce chemin ne concerne que la source.
    """
    import importlib
    try:
        return importlib.import_module("numba")
    except ImportError:
        pass
    import subprocess
    print("  numba: installing (one-time, speeds up SVF/hillshade x15-50)...",
          flush=True)
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "numba"],
                       check=True)
        importlib.invalidate_caches()
        return importlib.import_module("numba")
    except Exception as _e:
        raise RuntimeError(
            "numba est requis pour cet ombrage (hillshade/slope/SVF/openness) et "
            "son installation automatique a échoué : pip install numba"
        ) from _e


def _get_numba_horn_kernels():
    """Compile et cache les kernels Numba pour Horn (hillshade, multi, slope).

    Une seule passe sur le DEM par kernel : gradient Horn 3x3 + projection
    solaire + écriture uint8 directement, sans buffers intermédiaires float32
    (slope, aspect, dz_dx, dz_dy, pad). Edge replication via clamp d'indices.

    Retourne (hillshade_kernel, multi_kernel, slope_kernel) ou None si numba
    indisponible.
    """
    if "horn" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["horn"]
    _ensure_numba()  # installe numba à la demande ou lève (pas de repli silencieux)
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _hillshade_kernel(dem, dx, dy, az_math_rad, zen_rad, nodata, has_nodata):
            h, w = dem.shape
            out = _np.empty((h, w), dtype=_np.uint8)
            cos_z = _math.cos(zen_rad)
            sin_z = _math.sin(zen_rad)
            cos_a = _math.cos(az_math_rad)
            sin_a = _math.sin(az_math_rad)
            inv_8dx = 1.0 / (8.0 * dx)
            inv_8dy = 1.0 / (8.0 * dy)
            for row in _nb.prange(h):
                rm = row - 1 if row > 0 else 0
                rp = row + 1 if row < h - 1 else h - 1
                for col in range(w):
                    z0 = dem[row, col]
                    if has_nodata and z0 == nodata:
                        out[row, col] = 0
                        continue
                    cm = col - 1 if col > 0 else 0
                    cp = col + 1 if col < w - 1 else w - 1
                    a = dem[rm, cm]; b = dem[rm, col]; c = dem[rm, cp]
                    d = dem[row, cm];                  f = dem[row, cp]
                    g = dem[rp, cm]; hv = dem[rp, col]; i = dem[rp, cp]
                    if has_nodata:
                        # Voisin nodata remplacé par la valeur centrale
                        # (convention gdaldem) : sans ça, un voisin à -9999
                        # produit un gradient énorme → halo noir/blanc d'1 px
                        # autour des zones hors couverture.
                        if a  == nodata: a  = z0
                        if b  == nodata: b  = z0
                        if c  == nodata: c  = z0
                        if d  == nodata: d  = z0
                        if f  == nodata: f  = z0
                        if g  == nodata: g  = z0
                        if hv == nodata: hv = z0
                        if i  == nodata: i  = z0
                    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) * inv_8dx
                    dz_dy = ((g + 2.0 * hv + i) - (a + 2.0 * b + c)) * inv_8dy
                    g2 = dz_dx * dz_dx + dz_dy * dz_dy
                    # Forme analytique évitant atan/atan2 :
                    # cos(slope)=1/sqrt(1+g²), sin(slope)*cos(aspect)=-dz_dx/sqrt(1+g²),
                    # sin(slope)*sin(aspect)=dz_dy/sqrt(1+g²)
                    # → hs = (cos_z + sin_z * (-cos_a * dz_dx + sin_a * dz_dy)) / sqrt(1+g²)
                    inv_sqrt = 1.0 / _math.sqrt(1.0 + g2)
                    hs = (cos_z + sin_z * (-cos_a * dz_dx + sin_a * dz_dy)) * inv_sqrt
                    if hs < 0.0:
                        hs = 0.0
                    elif hs > 1.0:
                        hs = 1.0
                    out[row, col] = int(hs * 254.0 + 1.0)
            return out

        @_nb.njit(parallel=True, fastmath=True)
        def _multi_kernel(dem, dx, dy, zen_rad, nodata, has_nodata):
            h, w = dem.shape
            out = _np.empty((h, w), dtype=_np.uint8)
            cos_z = _math.cos(zen_rad)
            sin_z = _math.sin(zen_rad)
            inv_8dx = 1.0 / (8.0 * dx)
            inv_8dy = 1.0 / (8.0 * dy)
            # Azimuts GDAL : 225, 270, 315, 360 → az_math = 360 - az + 90
            # → 225, 180, 135, 90
            az0_c = _math.cos(_math.radians(225.0)); az0_s = _math.sin(_math.radians(225.0))
            az1_c = _math.cos(_math.radians(180.0)); az1_s = _math.sin(_math.radians(180.0))
            az2_c = _math.cos(_math.radians(135.0)); az2_s = _math.sin(_math.radians(135.0))
            az3_c = _math.cos(_math.radians( 90.0)); az3_s = _math.sin(_math.radians( 90.0))
            for row in _nb.prange(h):
                rm = row - 1 if row > 0 else 0
                rp = row + 1 if row < h - 1 else h - 1
                for col in range(w):
                    z0 = dem[row, col]
                    if has_nodata and z0 == nodata:
                        out[row, col] = 0
                        continue
                    cm = col - 1 if col > 0 else 0
                    cp = col + 1 if col < w - 1 else w - 1
                    a = dem[rm, cm]; b = dem[rm, col]; c = dem[rm, cp]
                    d = dem[row, cm];                  f = dem[row, cp]
                    g = dem[rp, cm]; hv = dem[rp, col]; i = dem[rp, cp]
                    if has_nodata:
                        # Voisin nodata → valeur centrale (cf. _hillshade_kernel)
                        if a  == nodata: a  = z0
                        if b  == nodata: b  = z0
                        if c  == nodata: c  = z0
                        if d  == nodata: d  = z0
                        if f  == nodata: f  = z0
                        if g  == nodata: g  = z0
                        if hv == nodata: hv = z0
                        if i  == nodata: i  = z0
                    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) * inv_8dx
                    dz_dy = ((g + 2.0 * hv + i) - (a + 2.0 * b + c)) * inv_8dy
                    g2 = dz_dx * dz_dx + dz_dy * dz_dy
                    g_len = _math.sqrt(g2)
                    inv_sqrt = 1.0 / _math.sqrt(1.0 + g2)
                    cos_s = inv_sqrt
                    sin_s = g_len * inv_sqrt
                    if g_len > 1e-12:
                        cos_asp = -dz_dx / g_len
                        sin_asp =  dz_dy / g_len
                    else:
                        cos_asp = 1.0
                        sin_asp = 0.0
                    hs_sum = 0.0
                    w_sum  = 0.0
                    # 4 azimuts déroulés
                    for k in range(4):
                        if k == 0:
                            cAz = az0_c; sAz = az0_s
                        elif k == 1:
                            cAz = az1_c; sAz = az1_s
                        elif k == 2:
                            cAz = az2_c; sAz = az2_s
                        else:
                            cAz = az3_c; sAz = az3_s
                        cos_d = cAz * cos_asp + sAz * sin_asp
                        sin_d = sAz * cos_asp - cAz * sin_asp
                        hs = cos_z * cos_s + sin_z * sin_s * cos_d
                        if hs < 0.0:
                            hs = 0.0
                        elif hs > 1.0:
                            hs = 1.0
                        wi = sin_d * sin_d
                        hs_sum += hs * wi
                        w_sum  += wi
                    if w_sum < 1e-6:
                        w_sum = 1e-6
                    hs_avg = hs_sum / w_sum
                    if hs_avg < 0.0:
                        hs_avg = 0.0
                    elif hs_avg > 1.0:
                        hs_avg = 1.0
                    out[row, col] = int(hs_avg * 254.0 + 1.0)
            return out

        @_nb.njit(parallel=True, fastmath=True)
        def _slope_kernel(dem, dx, dy, nodata, has_nodata):
            h, w = dem.shape
            out = _np.empty((h, w), dtype=_np.uint8)
            inv_8dx = 1.0 / (8.0 * dx)
            inv_8dy = 1.0 / (8.0 * dy)
            for row in _nb.prange(h):
                rm = row - 1 if row > 0 else 0
                rp = row + 1 if row < h - 1 else h - 1
                for col in range(w):
                    z0 = dem[row, col]
                    if has_nodata and z0 == nodata:
                        out[row, col] = 0
                        continue
                    cm = col - 1 if col > 0 else 0
                    cp = col + 1 if col < w - 1 else w - 1
                    a = dem[rm, cm]; b = dem[rm, col]; c = dem[rm, cp]
                    d = dem[row, cm];                  f = dem[row, cp]
                    g = dem[rp, cm]; hv = dem[rp, col]; i = dem[rp, cp]
                    if has_nodata:
                        # Voisin nodata → valeur centrale (cf. _hillshade_kernel)
                        if a  == nodata: a  = z0
                        if b  == nodata: b  = z0
                        if c  == nodata: c  = z0
                        if d  == nodata: d  = z0
                        if f  == nodata: f  = z0
                        if g  == nodata: g  = z0
                        if hv == nodata: hv = z0
                        if i  == nodata: i  = z0
                    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) * inv_8dx
                    dz_dy = ((g + 2.0 * hv + i) - (a + 2.0 * b + c)) * inv_8dy
                    slope_deg = _math.degrees(_math.atan(_math.sqrt(dz_dx * dz_dx + dz_dy * dz_dy)))
                    if slope_deg < 0.0:
                        slope_deg = 0.0
                    elif slope_deg > 90.0:
                        slope_deg = 90.0
                    # Étalement 0–90° → 1–255 (0 réservé nodata, comme les
                    # hillshades). Sans ça, le TIF stocke des degrés bruts
                    # (max 90/255) → tuiles quasi noires.
                    out[row, col] = int(slope_deg * (254.0 / 90.0) + 1.0)
            return out

        kernels = (_hillshade_kernel, _multi_kernel, _slope_kernel)
        _NUMBA_KERNELS_CACHE["horn"] = kernels
        return kernels
    except Exception as _e:
        print(f"  Numba kernels Horn : erreur compilation ({_e}) — fallback numpy", flush=True)
        _NUMBA_KERNELS_CACHE["horn"] = None
        return None


def _get_numba_svf_kernel():
    """Compile et cache le kernel Numba SVF (ray-casting horizon avec interp
    bilinéaire). Réutilisé par _svf_numpy et _svf_chunked — évite la double
    compilation initiale (~20 s × 2).
    """
    if "svf" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["svf"]
    _ensure_numba()  # installe numba à la demande ou lève (pas de repli silencieux)
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _svf_kernel(dem, n_dir, max_r, res, conv):
            # conv : 0 = SVF flux cos²γ (contraste) ; 1 = SVF RVT 1−sin γ ;
            #        2 = openness positive (Yokoyama 2002) : φ/π, φ = π/2 − β
            #            où β = angle d'horizon max (NON clampé : négatif sur
            #            crête) — crêtes claires ;
            #        3 = openness négative INVERSÉE : (π/2 − δ)/π, δ = angle
            #            min (vue la plus descendante) — fossés/chemins creux
            #            sombres, lecture alignée sur le SVF.
            # Argument runtime → une seule compilation gère les 4 variantes.
            h, w = dem.shape
            PI2 = 2.0 * _math.pi
            out = _np.zeros((h, w), dtype=_np.float32)
            for row in _nb.prange(h):
                for col in range(w):
                    z0 = dem[row, col]
                    svf_sum = 0.0
                    for k in range(n_dir):
                        angle = k * PI2 / n_dir
                        ddx =  _math.sin(angle)
                        ddy = -_math.cos(angle)
                        max_tan = -1e38
                        min_tan =  1e38
                        for r in range(1, max_r + 1):
                            rr = row + ddy * r
                            cc = col + ddx * r
                            # floor calculé une seule fois (réutilisé pour
                            # l'indice entier ET la partie fractionnaire).
                            rr_fl = _math.floor(rr)
                            cc_fl = _math.floor(cc)
                            r0i = int(rr_fl)
                            c0i = int(cc_fl)
                            r1i = r0i + 1
                            c1i = c0i + 1
                            if r0i < 0:       r0i = 0
                            elif r0i > h - 1: r0i = h - 1
                            if r1i < 0:       r1i = 0
                            elif r1i > h - 1: r1i = h - 1
                            if c0i < 0:       c0i = 0
                            elif c0i > w - 1: c0i = w - 1
                            if c1i < 0:       c1i = 0
                            elif c1i > w - 1: c1i = w - 1
                            fr = rr - rr_fl
                            fc = cc - cc_fl
                            zn = (dem[r0i, c0i] * (1 - fr) * (1 - fc) +
                                  dem[r0i, c1i] * (1 - fr) *      fc  +
                                  dem[r1i, c0i] *      fr  * (1 - fc) +
                                  dem[r1i, c1i] *      fr  *      fc)
                            dist_m = r * res
                            tan_a  = (zn - z0) / dist_m
                            if tan_a > max_tan:
                                max_tan = tan_a
                            if tan_a < min_tan:
                                min_tan = tan_a
                        if conv == 0:
                            # SVF flux : cos²γ = 1/(1+tan²γ) — contraste
                            mt = max_tan if max_tan > 0.0 else 0.0
                            svf_sum += 1.0 / (1.0 + mt * mt)
                        elif conv == 1:
                            # SVF RVT (Kokalj/Hesse) : 1 − sin γ (archéo)
                            mt = max_tan if max_tan > 0.0 else 0.0
                            svf_sum += 1.0 - mt / _math.sqrt(1.0 + mt * mt)
                        elif conv == 2:
                            # Openness positive : φ/π ∈ (0,1)
                            svf_sum += 0.5 - _math.atan(max_tan) / _math.pi
                        else:
                            # Openness négative inversée : (π/2 − δ)/π
                            svf_sum += 0.5 - _math.atan(min_tan) / _math.pi
                    out[row, col] = svf_sum / n_dir
            return out

        _NUMBA_KERNELS_CACHE["svf"] = _svf_kernel
        return _svf_kernel
    except Exception as _e:
        print(f"  Numba kernel SVF : erreur compilation ({_e}) — fallback numpy", flush=True)
        _NUMBA_KERNELS_CACHE["svf"] = None
        return None


def _get_numba_svf_opos_kernel():
    """Kernel FUSIONNÉ SVF flux (conv=0) + openness positif (conv=2) : un seul
    scan d'horizon produit les DEUX réductions (toutes deux dérivées de max_tan).
    Sert au composite VAT, qui sinon refait le scan coûteux deux fois. Le scan et
    les deux formules sont identiques à ceux de _svf_kernel (conv 0 et 2), donc
    sorties numériquement identiques (min_tan, utile au seul oneg, est omis)."""
    if "svf_opos" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["svf_opos"]
    _ensure_numba()  # installe numba à la demande ou lève (pas de repli silencieux)
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _svf_opos_kernel(dem, n_dir, max_r, res):
            h, w = dem.shape
            PI2 = 2.0 * _math.pi
            svf  = _np.zeros((h, w), dtype=_np.float32)
            opos = _np.zeros((h, w), dtype=_np.float32)
            for row in _nb.prange(h):
                for col in range(w):
                    z0 = dem[row, col]
                    svf_sum  = 0.0
                    opos_sum = 0.0
                    for k in range(n_dir):
                        angle = k * PI2 / n_dir
                        ddx =  _math.sin(angle)
                        ddy = -_math.cos(angle)
                        max_tan = -1e38
                        for r in range(1, max_r + 1):
                            rr = row + ddy * r
                            cc = col + ddx * r
                            rr_fl = _math.floor(rr)
                            cc_fl = _math.floor(cc)
                            r0i = int(rr_fl)
                            c0i = int(cc_fl)
                            r1i = r0i + 1
                            c1i = c0i + 1
                            if r0i < 0:       r0i = 0
                            elif r0i > h - 1: r0i = h - 1
                            if r1i < 0:       r1i = 0
                            elif r1i > h - 1: r1i = h - 1
                            if c0i < 0:       c0i = 0
                            elif c0i > w - 1: c0i = w - 1
                            if c1i < 0:       c1i = 0
                            elif c1i > w - 1: c1i = w - 1
                            fr = rr - rr_fl
                            fc = cc - cc_fl
                            zn = (dem[r0i, c0i] * (1 - fr) * (1 - fc) +
                                  dem[r0i, c1i] * (1 - fr) *      fc  +
                                  dem[r1i, c0i] *      fr  * (1 - fc) +
                                  dem[r1i, c1i] *      fr  *      fc)
                            dist_m = r * res
                            tan_a  = (zn - z0) / dist_m
                            if tan_a > max_tan:
                                max_tan = tan_a
                        # SVF flux : cos²γ = 1/(1+tan²γ), tan clampé >= 0
                        mt = max_tan if max_tan > 0.0 else 0.0
                        svf_sum  += 1.0 / (1.0 + mt * mt)
                        # Openness positive : 0.5 − atan(max_tan)/π (NON clampé)
                        opos_sum += 0.5 - _math.atan(max_tan) / _math.pi
                    svf[row, col]  = svf_sum  / n_dir
                    opos[row, col] = opos_sum / n_dir
            return svf, opos

        _NUMBA_KERNELS_CACHE["svf_opos"] = _svf_opos_kernel
        return _svf_opos_kernel
    except Exception as _e:
        print(f"  Numba kernel SVF+opos : erreur compilation ({_e})", flush=True)
        _NUMBA_KERNELS_CACHE["svf_opos"] = None
        return None


def _get_numba_svf_sweep_kernel():
    """Sweep-horizon SVF avec running max sur deque (upper convex hull).

    Algorithme :
    - Pour chaque direction θ, balayage de lignes parallèles grid-aligned
      à travers la grille
    - Chaque pixel visité exactement une fois par direction
    - Maintient une deque des points "skyline" passés (upper convex hull)
    - Pop arrière les points dominés à l'ajout (préserve la propriété de hull)
    - Pop avant les points hors fenêtre max_r (cap distance)
    - Horizon angle = scan du hull, query en O(hull_size) amorti

    Complexité : O(W·H·N·hull_size_moyen) — la query re-scanne tout le hull à
    chaque pixel. hull_size reste petit (~5-10 en terrain naturel), d'où le
    gain massif vs O(W·H·N·max_r) du ray-cast classique.

    Pour terrain naturel (hull_size ~5-10), speedup vs ray-cast bilinéaire :
        max_r=40    (SVF 20m)   → ~×5-15
        max_r=200   (SVF 100m)  → ~×30-50
        max_r=40000 (SVF 20km)  → ~×500+

    Trade-off : nearest-neighbor pixel access le long de la scan-line (pas
    d'interp bilinéaire sub-pixel). Aliasing négligeable pour structures
    > 1-2 px sur DEM 0.5 m/px.

    ⚠ Sémantique des directions : ce kernel balaie en direction (ddx, ddy) et
    accumule l'horizon depuis les pixels passés sur la scan-line, qui sont
    donc en direction -θ par rapport au pixel courant. Pour SVF la somme sur
    N directions équi-réparties est invariante par cette permutation (-θ_k
    ≡ θ_{N-k} mod 2π) — résultat numérique correct. À NE PAS réutiliser tel
    quel pour un calcul asymétrique single-direction (ex: horizon à un
    azimut donné, ombre solaire) : inverser le sens du balayage ou
    réinterpréter k.
    """
    if "svf_sweep" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["svf_sweep"]
    _ensure_numba()  # installe numba à la demande ou lève (pas de repli silencieux)
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _svf_sweep_kernel(dem, n_dir, max_r, res, conv):
            # conv : 0 = flux cos²γ ; 1 = RVT 1−sin γ ; 2 = openness+ ; 3 =
            # openness− (min sur le même deque plutôt qu'un hull séparé, cf.
            # commentaire "max_tan porte l'extremum..." dans la requête plus
            # bas). Formules identiques à _svf_kernel.
            h, w = dem.shape
            PI2 = 2.0 * _math.pi
            out = _np.zeros((h, w), dtype=_np.float32)
            # Capacité deque : max_r + petite marge pour gérer push avant pop
            DEQ_CAP = max_r + 8

            for k_dir in range(n_dir):
                angle = k_dir * PI2 / n_dir
                ddx =  _math.sin(angle)
                ddy = -_math.cos(angle)
                abs_dx = abs(ddx)
                abs_dy = abs(ddy)

                if abs_dx >= abs_dy:
                    # ── Direction x-dominante : scan-lines balaient en x ──────
                    sx = 1 if ddx > 0 else -1
                    slope_y = ddy / abs_dx  # |slope_y| <= 1
                    step_dist = res * _math.sqrt(1.0 + slope_y * slope_y)
                    # max_steps = nombre max de steps scan-line correspondant à max_r px le long du rayon
                    max_steps_back = int(max_r / _math.sqrt(1.0 + slope_y * slope_y) + 0.5)
                    if max_steps_back < 1:
                        max_steps_back = 1
                    # slope appliqué dans le sens du balayage
                    slope_y_signed = slope_y if sx > 0 else -slope_y
                    # Couverture des seed_y0 : chaque pixel (r, c) est sur seed_y0 = round(r - c_progress * slope)
                    # où c_progress = c si sx>0 sinon (w-1-c). Etendre la plage pour couvrir tout.
                    extra = int(_math.ceil(abs(slope_y) * w)) + 2
                    y0_min = -extra
                    y0_max = h + extra

                    for seed_y0 in _nb.prange(y0_min, y0_max + 1):
                        # Buffers deque (per-scan-line, alloués par numba dans la prange)
                        deque_step = _np.empty(DEQ_CAP, dtype=_np.int32)
                        deque_z    = _np.empty(DEQ_CAP, dtype=_np.float32)
                        head = 0
                        tail = 0

                        # Itération en x dans le sens sx
                        if sx > 0:
                            c_start = 0
                            c_step = 1
                            c_n = w
                        else:
                            c_start = w - 1
                            c_step = -1
                            c_n = w

                        for step_idx in range(c_n):
                            c = c_start + step_idx * c_step
                            y_real = seed_y0 + step_idx * slope_y_signed
                            r = int(y_real + 0.5) if y_real >= 0.0 else int(y_real - 0.5)

                            if r < 0 or r >= h:
                                continue
                            z_curr = dem[r, c]

                            # Pop avant : points hors fenêtre max_r
                            while head != tail and (step_idx - deque_step[head]) > max_steps_back:
                                head = (head + 1) % DEQ_CAP

                            # Query : max slope du hull vers (step_idx, z_curr)
                            # max_tan porte l'extremum utile à conv (nom
                            # conservé du cas SVF pour ne pas tout renommer) :
                            # conv 3 (openness-) veut le MIN (angle le plus
                            # descendant, hull du dessous) ; conv 2 (openness+)
                            # veut le MAX non clampé (peut être négatif sur une
                            # crête) ; 0/1 (SVF) veulent le MAX clampé >= 0
                            # (obstruction), d'où l'init à 0.0 sinon. Même
                            # deque pour les deux sens : seuls la direction de
                            # l'extremum ici et le sens du pop arrière plus
                            # bas changent (cf. commentaire associé).
                            max_tan = 1e38 if conv == 3 else (-1e38 if conv == 2 else 0.0)
                            idx = head
                            while idx != tail:
                                past_step = deque_step[idx]
                                past_z    = deque_z[idx]
                                dist = (step_idx - past_step) * step_dist
                                if dist > 0.0:
                                    tan_a = (past_z - z_curr) / dist
                                    if conv == 3:
                                        if tan_a < max_tan:
                                            max_tan = tan_a
                                    else:
                                        if tan_a > max_tan:
                                            max_tan = tan_a
                                idx = (idx + 1) % DEQ_CAP

                            # Pop arrière : maintien upper convex hull
                            # Tant qu'on a >= 2 points en queue, vérifier si l'avant-dernier
                            # est sous la droite (avant-avant-dernier → new). Si oui, pop.
                            while True:
                                # Taille deque
                                sz = (tail - head + DEQ_CAP) % DEQ_CAP
                                if sz < 2:
                                    break
                                tm1 = (tail - 1) % DEQ_CAP
                                tm2 = (tail - 2) % DEQ_CAP
                                s2 = deque_step[tm1]; z2 = deque_z[tm1]
                                s1 = deque_step[tm2]; z1 = deque_z[tm2]
                                # Upper hull (conv != 3) : s2 doit être au-DESSUS
                                # de la droite (s1,z1)→(step_idx,z_curr), sinon
                                # dominé (pop). Lower hull (conv == 3) : même
                                # test, sens inversé (s2 doit être EN DESSOUS).
                                lhs = (z2 - z1) * (step_idx - s1)
                                rhs = (s2 - s1) * (z_curr - z1)
                                if conv == 3:
                                    if lhs >= rhs:
                                        tail = tm1
                                    else:
                                        break
                                else:
                                    if lhs <= rhs:
                                        tail = tm1
                                    else:
                                        break

                            # Push (step_idx, z_curr)
                            deque_step[tail] = step_idx
                            deque_z[tail]    = z_curr
                            tail = (tail + 1) % DEQ_CAP

                            # Accumulation SVF
                            # conv 0 = flux cos²γ ; conv 1 = RVT 1−sin γ (max_tan
                            # = tan γ ≥ 0) ; conv 2/3 = openness +/- (Yokoyama
                            # 2002), même formule appliquée à max_tan (extremum
                            # déjà orienté max/min par la requête du hull plus
                            # haut) — identique à _get_numba_svf_kernel.
                            if conv == 0:
                                out[r, c] += 1.0 / (1.0 + max_tan * max_tan)
                            elif conv == 1:
                                out[r, c] += 1.0 - max_tan / _math.sqrt(1.0 + max_tan * max_tan)
                            else:
                                out[r, c] += 0.5 - _math.atan(max_tan) / _math.pi
                else:
                    # ── Direction y-dominante : scan-lines balaient en y ──────
                    sy = 1 if ddy > 0 else -1
                    slope_x = ddx / abs_dy  # |slope_x| <= 1
                    step_dist = res * _math.sqrt(1.0 + slope_x * slope_x)
                    max_steps_back = int(max_r / _math.sqrt(1.0 + slope_x * slope_x) + 0.5)
                    if max_steps_back < 1:
                        max_steps_back = 1
                    slope_x_signed = slope_x if sy > 0 else -slope_x

                    extra = int(_math.ceil(abs(slope_x) * h)) + 2
                    x0_min = -extra
                    x0_max = w + extra

                    for seed_x0 in _nb.prange(x0_min, x0_max + 1):
                        deque_step = _np.empty(DEQ_CAP, dtype=_np.int32)
                        deque_z    = _np.empty(DEQ_CAP, dtype=_np.float32)
                        head = 0
                        tail = 0

                        if sy > 0:
                            r_start = 0
                            r_step = 1
                            r_n = h
                        else:
                            r_start = h - 1
                            r_step = -1
                            r_n = h

                        for step_idx in range(r_n):
                            r = r_start + step_idx * r_step
                            x_real = seed_x0 + step_idx * slope_x_signed
                            c = int(x_real + 0.5) if x_real >= 0.0 else int(x_real - 0.5)

                            if c < 0 or c >= w:
                                continue
                            z_curr = dem[r, c]

                            while head != tail and (step_idx - deque_step[head]) > max_steps_back:
                                head = (head + 1) % DEQ_CAP

                            # max_tan porte l'extremum utile à conv (nom
                            # conservé du cas SVF pour ne pas tout renommer) :
                            # conv 3 (openness-) veut le MIN (angle le plus
                            # descendant, hull du dessous) ; conv 2 (openness+)
                            # veut le MAX non clampé (peut être négatif sur une
                            # crête) ; 0/1 (SVF) veulent le MAX clampé >= 0
                            # (obstruction), d'où l'init à 0.0 sinon. Même
                            # deque pour les deux sens : seuls la direction de
                            # l'extremum ici et le sens du pop arrière plus
                            # bas changent (cf. commentaire associé).
                            max_tan = 1e38 if conv == 3 else (-1e38 if conv == 2 else 0.0)
                            idx = head
                            while idx != tail:
                                past_step = deque_step[idx]
                                past_z    = deque_z[idx]
                                dist = (step_idx - past_step) * step_dist
                                if dist > 0.0:
                                    tan_a = (past_z - z_curr) / dist
                                    if conv == 3:
                                        if tan_a < max_tan:
                                            max_tan = tan_a
                                    else:
                                        if tan_a > max_tan:
                                            max_tan = tan_a
                                idx = (idx + 1) % DEQ_CAP

                            while True:
                                sz = (tail - head + DEQ_CAP) % DEQ_CAP
                                if sz < 2:
                                    break
                                tm1 = (tail - 1) % DEQ_CAP
                                tm2 = (tail - 2) % DEQ_CAP
                                s2 = deque_step[tm1]; z2 = deque_z[tm1]
                                s1 = deque_step[tm2]; z1 = deque_z[tm2]
                                # cf. branche x-dominante : hull inversé si conv == 3.
                                lhs = (z2 - z1) * (step_idx - s1)
                                rhs = (s2 - s1) * (z_curr - z1)
                                if conv == 3:
                                    if lhs >= rhs:
                                        tail = tm1
                                    else:
                                        break
                                else:
                                    if lhs <= rhs:
                                        tail = tm1
                                    else:
                                        break

                            deque_step[tail] = step_idx
                            deque_z[tail]    = z_curr
                            tail = (tail + 1) % DEQ_CAP

                            # conv 0 = flux cos²γ ; conv 1 = RVT 1−sin γ (max_tan
                            # = tan γ ≥ 0) ; conv 2/3 = openness +/- (Yokoyama
                            # 2002), même formule appliquée à max_tan (extremum
                            # déjà orienté max/min par la requête du hull plus
                            # haut) — identique à _get_numba_svf_kernel.
                            if conv == 0:
                                out[r, c] += 1.0 / (1.0 + max_tan * max_tan)
                            elif conv == 1:
                                out[r, c] += 1.0 - max_tan / _math.sqrt(1.0 + max_tan * max_tan)
                            else:
                                out[r, c] += 0.5 - _math.atan(max_tan) / _math.pi

            # Normalisation : moyenne sur n_dir
            inv_n = 1.0 / n_dir
            for r in _nb.prange(h):
                for c in range(w):
                    out[r, c] *= inv_n
            return out

        _NUMBA_KERNELS_CACHE["svf_sweep"] = _svf_sweep_kernel
        return _svf_sweep_kernel
    except Exception as _e:
        print(f"  Numba kernel SVF sweep : erreur compilation ({_e})", flush=True)
        _NUMBA_KERNELS_CACHE["svf_sweep"] = None
        return None


def _appliquer_z_factor(dem_f, z_factor, nodata):
    """Multiplie le DEM par z_factor en préservant les valeurs nodata.

    Sans cette précaution, nodata × z ≠ nodata et la détection nodata des
    kernels (comparaison d'égalité) échoue silencieusement dès que z ≠ 1.
    """
    import numpy as np
    if z_factor == 1.0:
        return dem_f
    if nodata is None:
        return dem_f * np.float32(z_factor)
    m = _nodata_mask(dem_f, nodata)
    out = dem_f * np.float32(z_factor)
    out[m] = dem_f[m]
    return out


def _remplir_nodata_moyenne(dem_f, nodata):
    """(fallback numpy sans numba) Remplit les nodata par la moyenne des
    pixels valides avant le calcul de gradient Horn — supprime le halo
    noir/blanc d'1 px autour des trous de couverture (les kernels Numba
    appliquent la convention gdaldem exacte : voisin nodata → centre).

    Retourne (dem_rempli, mask_nodata).
    """
    m = _nodata_mask(dem_f, nodata)
    if not m.any():
        return dem_f, m
    valid = dem_f[~m]
    fill = float(valid.mean()) if valid.size else 0.0
    out = dem_f.copy()
    out[m] = fill
    return out, m


def _calc_slope_aspect(dem, dx=0.5, dy=0.5):
    """Calcule slope (radians) et aspect (radians) d'un DEM via la formule Horn 1981.

    Horn 1981 utilise une fenêtre 3x3 avec pondération centrale 2× pour
    limiter le bruit. C'est la formule par défaut de gdaldem.

    dx, dy : taille du pixel en mètres (X et Y, identiques pour LiDAR)

    Retourne (slope_rad, aspect_rad) en arrays float32 même shape que dem.
    """
    import numpy as np

    # Convolution 3x3 manuelle via padding + slicing — beaucoup plus rapide
    # que scipy.ndimage.convolve sur ces matrices simples
    dem = dem.astype(np.float32)
    pad = np.pad(dem, 1, mode="edge")  # edge replication (compat GDAL)
    a = pad[0:-2, 0:-2]; b = pad[0:-2, 1:-1]; c = pad[0:-2, 2:  ]
    d = pad[1:-1, 0:-2];                       f = pad[1:-1, 2:  ]
    g = pad[2:  , 0:-2]; h = pad[2:  , 1:-1]; i = pad[2:  , 2:  ]

    # dz/dx (Horn) : ((c + 2f + i) - (a + 2d + g)) / (8 * dx)
    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) / (8.0 * dx)
    # dz/dy (Horn) : ((g + 2h + i) - (a + 2b + c)) / (8 * dy)
    # Note : dans GDAL, l'axe Y est inversé (origine en haut-gauche), donc le
    # signe de dy peut différer selon les conventions. On garde la convention
    # Horn standard ici.
    dz_dy = ((g + 2.0 * h + i) - (a + 2.0 * b + c)) / (8.0 * dy)

    # Slope (radians) : atan(sqrt(dz_dx² + dz_dy²))
    slope = np.arctan(np.sqrt(dz_dx * dz_dx + dz_dy * dz_dy))

    # Aspect (radians) : atan2(dz_dy, -dz_dx)
    # Convention GDAL : aspect = 0 vers le Nord (Y+ haut), augmente sens horaire
    aspect = np.arctan2(dz_dy, -dz_dx)

    return slope.astype(np.float32), aspect.astype(np.float32)


def _hillshade_numpy(dem, azimuth_deg, altitude_deg, z_factor=1.0, dx=0.5, dy=0.5,
                     nodata=None):
    """Hillshade directionnel — formule GDAL standard.

    Reproduit la formule de gdaldem hillshade (-alt -az) :
        hillshade = 255 * (cos(zenith) * cos(slope)
                         + sin(zenith) * sin(slope) * cos(azimuth - aspect))

    azimuth_deg : direction du soleil en degrés (0=N, 90=E, 180=S, 270=W)
    altitude_deg : hauteur du soleil au-dessus de l'horizon, en degrés
    z_factor : multiplicateur d'exagération verticale (1.0 = pas d'exagération)

    Moteur Numba (1 passe, uint8 direct) si dispo, sinon fallback numpy.
    Retourne un array uint8 (0-255) même shape que dem.
    """
    import numpy as np

    dem_f = dem.astype(np.float32, copy=False)
    dem_f = _appliquer_z_factor(dem_f, z_factor, nodata)

    zenith_rad  = math.radians(90.0 - altitude_deg)
    az_math_rad = math.radians(360.0 - azimuth_deg + 90.0)

    kernels = _get_numba_horn_kernels()
    if kernels is not None:
        hs_kernel, _, _ = kernels
        nd_val = float(nodata) if nodata is not None else 0.0
        return hs_kernel(dem_f, float(dx), float(dy),
                         az_math_rad, zenith_rad, nd_val, nodata is not None)

    # ── Fallback numpy ───────────────────────────────────────────────────────
    dem_calc, nd_m = _remplir_nodata_moyenne(dem_f, nodata)
    slope, aspect = _calc_slope_aspect(dem_calc, dx, dy)
    hs = (np.cos(zenith_rad) * np.cos(slope)
          + np.sin(zenith_rad) * np.sin(slope) * np.cos(az_math_rad - aspect))
    hs = np.clip(hs, 0.0, 1.0)
    hs_u8 = (hs * 254.0 + 1.0).astype(np.uint8)
    hs_u8[nd_m] = 0
    return hs_u8


def _hillshade_multi_numpy(dem, altitude_deg=45.0, z_factor=1.0, dx=0.5, dy=0.5,
                           nodata=None):
    """Hillshade multidirectionnel — formule GDAL `-multidirectional`.

    Calcule 4 hillshades à 225°, 270°, 315°, 360° et combine via une moyenne
    pondérée par sin²(diff) pour éviter les "stripes" du hillshade simple.

    C'est la méthode "Multidirectional Hillshade" de Mark 1992 / Tait 2010
    qu'utilise GDAL avec --multidirectional.

    Moteur Numba (1 passe, 4 azimuts déroulés) si dispo, sinon fallback numpy.
    """
    import numpy as np

    dem_f = dem.astype(np.float32, copy=False)
    dem_f = _appliquer_z_factor(dem_f, z_factor, nodata)

    zenith_rad = math.radians(90.0 - altitude_deg)

    kernels = _get_numba_horn_kernels()
    if kernels is not None:
        _, multi_kernel, _ = kernels
        nd_val = float(nodata) if nodata is not None else 0.0
        return multi_kernel(dem_f, float(dx), float(dy),
                            zenith_rad, nd_val, nodata is not None)

    # ── Fallback numpy ───────────────────────────────────────────────────────
    dem_calc, nd_m = _remplir_nodata_moyenne(dem_f, nodata)
    slope, aspect = _calc_slope_aspect(dem_calc, dx, dy)
    cos_z = np.cos(zenith_rad)
    sin_z = np.sin(zenith_rad)
    azimuths = [225.0, 270.0, 315.0, 360.0]
    hs_sum     = np.zeros_like(slope)
    weight_sum = np.zeros_like(slope)
    for az in azimuths:
        az_math_rad = np.radians(360.0 - az + 90.0)
        diff = az_math_rad - aspect
        w = np.sin(diff) ** 2
        hs = (cos_z * np.cos(slope)
              + sin_z * np.sin(slope) * np.cos(diff))
        hs = np.clip(hs, 0.0, 1.0)
        hs_sum     += hs * w
        weight_sum += w
    weight_sum = np.where(weight_sum < 1e-6, 1e-6, weight_sum)
    hs_avg = hs_sum / weight_sum
    hs_u8  = (hs_avg * 254.0 + 1.0).astype(np.uint8)
    hs_u8[nd_m] = 0
    return hs_u8


def _slope_numpy(dem, z_factor=1.0, dx=0.5, dy=0.5, scale=1.0, nodata=None):
    """Slope — formule GDAL standard (Horn 1981), encodage visuel.

    Renvoie un array uint8 : pente 0–90° étalée linéairement sur 1–255
    (0 réservé au nodata, même convention que les hillshades).
    Décodage : degrés = (v − 1) × 90 / 254.

    Moteur Numba (1 passe, uint8 direct) si dispo, sinon fallback numpy.
    """
    import numpy as np

    dem_f = dem.astype(np.float32, copy=False)
    dem_f = _appliquer_z_factor(dem_f, z_factor, nodata)

    kernels = _get_numba_horn_kernels()
    if kernels is not None:
        _, _, slope_kernel = kernels
        nd_val = float(nodata) if nodata is not None else 0.0
        return slope_kernel(dem_f, float(dx), float(dy),
                            nd_val, nodata is not None)

    # ── Fallback numpy ───────────────────────────────────────────────────────
    dem_calc, nd_m = _remplir_nodata_moyenne(dem_f, nodata)
    slope, _ = _calc_slope_aspect(dem_calc, dx, dy)
    slope_deg = np.degrees(slope)
    slope_u8 = (np.clip(slope_deg, 0.0, 90.0) * (254.0 / 90.0) + 1.0).astype(np.uint8)
    slope_u8[nd_m] = 0
    return slope_u8


def _build_vrt_xml(cogs, vrt_path, target_res, *, ecrire_texte_atomique):
    """
    Construit un VRT GDAL (XML) référençant N dalles GeoTIFF, sans matérialiser
    de mosaïque physique. Le fichier produit est de l'ordre de quelques 100 Ko
    (≈ 200 octets/dalle) et la construction prend < 1 s même pour 10 000 dalles.

    Rasterio lit le VRT transparemment : pour chaque fenêtre demandée, libgdal
    dispatche les reads aux dalles concernées. Les calculs chunked en aval
    (_hillshade_chunked, _svf_chunked) fonctionnent à l'identique.

    Hypothèses : toutes les dalles partagent le même CRS, dtype, nodata, et
    sont alignées sur une grille (cas standard des dalles IGN LiDAR HD).
    """
    import rasterio as _rio

    if not cogs:
        raise ValueError("Aucune dalle source pour la construction du VRT")

    xmin = ymin = float("inf")
    xmax = ymax = float("-inf")
    crs_wkt = None
    nodata  = None
    dtype   = None
    src_info = []

    for src_path in cogs:
        with _rio.open(str(src_path)) as ds:
            b = ds.bounds
            src_info.append({
                "path":   str(src_path),
                "bounds": (b.left, b.bottom, b.right, b.top),
                "width":  ds.width,
                "height": ds.height,
            })
            if b.left   < xmin: xmin = b.left
            if b.right  > xmax: xmax = b.right
            if b.bottom < ymin: ymin = b.bottom
            if b.top    > ymax: ymax = b.top
            if crs_wkt is None:
                crs_wkt = ds.crs.to_wkt() if ds.crs else ""
                nodata  = ds.nodata
                dtype   = str(ds.dtypes[0])

    vrt_w = int(round((xmax - xmin) / target_res))
    vrt_h = int(round((ymax - ymin) / target_res))

    DTYPE_MAP = {
        "uint8":   "Byte",    "uint16": "UInt16",  "int16":  "Int16",
        "uint32":  "UInt32",  "int32":  "Int32",
        "float32": "Float32", "float64": "Float64",
    }
    gdal_dtype = DTYPE_MAP.get(dtype, "Float32")

    def _esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                       .replace(">", "&gt;"))

    lines = []
    lines.append(f'<VRTDataset rasterXSize="{vrt_w}" rasterYSize="{vrt_h}">')
    if crs_wkt:
        lines.append(f'  <SRS>{_esc(crs_wkt)}</SRS>')
    lines.append(f'  <GeoTransform>{xmin}, {target_res}, 0.0, {ymax}, 0.0, {-target_res}</GeoTransform>')
    lines.append(f'  <VRTRasterBand dataType="{gdal_dtype}" band="1">')
    if nodata is not None:
        lines.append(f'    <NoDataValue>{nodata}</NoDataValue>')

    for info in src_info:
        sb = info["bounds"]
        x_dest = int(round((sb[0] - xmin) / target_res))
        y_dest = int(round((ymax - sb[3]) / target_res))
        w_dest = int(round((sb[2] - sb[0]) / target_res))
        h_dest = int(round((sb[3] - sb[1]) / target_res))
        lines.append('    <SimpleSource>')
        lines.append(f'      <SourceFilename relativeToVRT="0">{_esc(info["path"])}</SourceFilename>')
        lines.append('      <SourceBand>1</SourceBand>')
        lines.append(f'      <SrcRect xOff="0" yOff="0" xSize="{info["width"]}" ySize="{info["height"]}"/>')
        lines.append(f'      <DstRect xOff="{x_dest}" yOff="{y_dest}" xSize="{w_dest}" ySize="{h_dest}"/>')
        lines.append('    </SimpleSource>')

    lines.append('  </VRTRasterBand>')
    lines.append('</VRTDataset>')

    ecrire_texte_atomique(vrt_path, "\n".join(lines))


def _lrm_chunked(src_path, dst_path, sigma_px):
    """
    Local Relief Model calculé par blocs avec overlap pour éviter les artefacts
    de bord gaussien et borner la RAM indépendamment de la taille du raster.

    Stratégie :
      - Taille de chunk : 2048 × 2048 px
      - Overlap (marge) : 4 × sigma_px (≈ 4σ garantit que l'erreur de bord < 0.1 %)
      - Chaque bloc est lu depuis le disque, filtré, puis la zone centrale
        (sans la marge) est écrite dans le TIF de sortie.
      - La normalisation percentile est calculée en deux passes :
          passe 1 (échantillon)  → p5 / p95 globaux sur grille 3×3
                                   (_percentiles_grille — même garde-fou que le
                                   SVF : un crop unique rend le stretch dépendant
                                   du cadrage, régression de rendu silencieuse)
          passe 2 (traitement)   → applique la normalisation bloc par bloc

    Retourne True si succès, False si fallback requis (ex: rasterio absent).
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
        from scipy.ndimage import gaussian_filter as _gf
    except ImportError as _ie:
        print(f"  LRM chunked: missing import ({_ie}) — fallback to full memory", flush=True)
        return False

    CHUNK  = 2048
    MARGIN = max(4 * sigma_px, 64)   # au moins 64 px pour les petits sigma

    with _rio.open(str(src_path)) as src:
        H, W   = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    # ── Passe 1 : percentiles p5/p95 globaux sur grille 3×3 ─────────────────
    # On accumule aussi somme/effectif des altitudes valides : la moyenne
    # globale sert de valeur de remplissage nodata UNIQUE en passe 2 (un
    # remplissage par moyenne de bloc créait une couture dans la gaussienne
    # quand du nodata se trouve à < 4σ d'une frontière de bloc).
    _acc = [0.0, 0]   # [somme, n]
    def _lrm_vals(win):
        nd = _nodata_mask(win, nodata)
        v = win[~nd]
        if v.size:
            _acc[0] += float(v.sum()); _acc[1] += v.size
        fill = float(v.mean()) if v.size else 0.0
        lrm = win - _gf(np.where(nd, fill, win), sigma=sigma_px)
        lrm[nd] = np.nan
        return lrm

    _pcts = _percentiles_grille(src_path, MARGIN, _lrm_vals, 5, 95)
    if _pcts is None:
        return False  # raster trop petit / vide
    p5_g, p95_g, _n_valid = _pcts
    mean_g = _acc[0] / _acc[1] if _acc[1] else 0.0
    if p95_g <= p5_g:
        return False  # relief dégénéré (tout plat / tout nodata)
    print(f"  LRM chunked: p5={p5_g:.2f} m  p95={p95_g:.2f} m (3×3 grid)",
          flush=True)

    # ── Profil de sortie ────────────────────────────────────────────────────
    out_profile = profile.copy()
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver     = "GTiff",
        dtype      = "uint8",
        count      = 1,
        compress   = "deflate",
        predictor  = 2,
        tiled      = True,
        blockxsize = 512,
        blockysize = 512,
        bigtiff    = "YES",
        nodata     = None,
    )

    # ── Passe 2 : traitement bloc par bloc, CALCUL parallélisé ──────────────
    # Les blocs sont indépendants (chacun lit sa fenêtre + marge 4σ) et
    # gaussian_filter relâche le GIL en C → on parallélise le CALCUL sur un pool
    # de threads (~×Ncœurs quand σ est grand). MAIS les datasets GDAL/rasterio ne
    # sont PAS thread-safe en accès concurrent : src.read et dst.write RESTENT sur
    # le thread principal (I/O rapide), seul le gaussien tourne en parallèle. En
    # vol : au plus ~2×workers blocs (RAM bornée, indépendante de la taille du
    # raster). Sortie BIT-IDENTIQUE au séquentiel (même math, même ordre d'écriture).
    total_chunks = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n_done = 0
    _nw = max(1, min(os.cpu_count() or 4, 16))

    def _compute_bloc(block, crop):
        """Pur calcul (relâche le GIL dans _gf) : LRM + normalisation + crop marge."""
        _dr0, _dc0, _dr1, _dc1 = crop
        nd = _nodata_mask(block, nodata)
        # Remplissage par la moyenne GLOBALE (passe 1), pas celle du bloc (couture).
        smooth = _gf(np.where(nd, mean_g, block), sigma=sigma_px)
        lrm_block = block - smooth
        lrm_block[nd] = np.nan
        arr_f  = np.clip((lrm_block - p5_g) / (p95_g - p5_g), 0.0, 1.0) * 255.0
        arr_u8 = np.nan_to_num(arr_f, nan=128.0).astype(np.uint8)
        arr_u8[nd] = 128   # valeur neutre pour les nodata
        return arr_u8[_dr0:_dr1, _dc0:_dc1]   # zone centrale (marge enlevée)

    with _rio.open(str(src_path)) as src, \
         _rio.open(str(dst_path), "w", **out_profile) as dst, \
         ThreadPoolExecutor(max_workers=_nw) as _ex:
        _pending = []   # (future, win_write) dans l'ordre de soumission

        def _ecrire(fut, win_write):
            nonlocal n_done
            dst.write(fut.result()[np.newaxis, :, :], window=win_write)
            n_done += 1
            pct = n_done * 100 // total_chunks
            print(f"\r  LRM chunked: {pct:3d}% ({n_done}/{total_chunks} blocks,"
                  f" {_nw} threads)   ", end="", flush=True)

        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)
                r0 = max(0, row_off - MARGIN); c0 = max(0, col_off - MARGIN)
                r1 = min(H, row_end + MARGIN); c1 = min(W, col_end + MARGIN)

                block = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)
                                 ).astype(np.float32)
                crop  = (row_off - r0, col_off - c0,
                         (row_off - r0) + (row_end - row_off),
                         (col_off - c0) + (col_end - col_off))
                win_write = Window(col_off, row_off, col_end - col_off, row_end - row_off)

                _pending.append((_ex.submit(_compute_bloc, block, crop), win_write))
                if len(_pending) >= _nw * 2:      # borne RAM : ~2×workers en vol
                    _f, _w = _pending.pop(0); _ecrire(_f, _w)

        for _f, _w in _pending:                    # drain final, dans l'ordre
            _ecrire(_f, _w)

    print(f"\r  LRM chunked: done ({total_chunks} blocks, σ={sigma_px} px,"
          f" {_nw} threads)          ")
    return True


def _lrm_array(dem, nodata_val, sigma_px):
    """Local Relief Model brut (float) : DEM − gaussienne(σ), pleine mémoire.

    Centralise le calcul partagé par le LRM standalone (fallback pleine
    mémoire) et le composite RRIM, qui divergeaient cosmétiquement (l'un
    posait nan avant nanmean, l'autre masquait directement) pour un résultat
    identique. Le trou nodata est rempli par la moyenne des pixels valides
    avant le flou — sinon la gaussienne propagerait le nodata dans le relief.

    dem        : array float (lu via _lire_dem_rasterio).
    nodata_val : valeur nodata du raster source, ou None.
    sigma_px   : écart-type gaussien en pixels.

    Retourne (lrm, nodata_mask) ; lrm vaut np.nan sur les nodata.
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter as _gf
    nodata_mask = _nodata_mask(dem, nodata_val)
    mean_val = float(np.nanmean(dem[~nodata_mask])) if (~nodata_mask).any() else 0.0
    dem_fill = np.where(nodata_mask, mean_val, dem)
    lrm = dem - _gf(dem_fill, sigma=sigma_px)
    lrm[nodata_mask] = np.nan
    return lrm, nodata_mask


def _hillshade_chunked_multi(src_path, jobs, dx=0.5, dy=0.5):
    """
    Hillshade / hillshade-multi / slope par fenêtres avec halo = 1 px (Horn 3x3)
    — N sorties calculées en UNE seule passe de lecture.

    jobs : liste de (mode, params, dst_path)
        mode   : "hillshade" | "hillshade_multi" | "slope"
        params : dict — clés selon le mode
            hillshade        : {"azimuth_deg": float, "altitude_deg": float}
            hillshade_multi  : {"altitude_deg": float}
            slope            : {} (vide)

    Sur une grande zone, le coût dominant est l'I/O + la décompression deflate
    des dalles derrière le VRT, pas les kernels Horn : lire chaque bloc une
    fois pour tous les types demandés divise le temps total par ~le nombre de
    types (vs une passe complète par type).

    Borne la RAM indépendamment de la taille du raster (chunks 2048×2048 px).
    Retourne True si succès, False si import manquant.
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  Hillshade chunked: missing import ({_ie})", flush=True)
        return False

    CHUNK = 2048
    HALO  = 1

    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    out_profile = profile.copy()
    # Purger les clés héritées qui pourraient interférer :
    #  - driver : la source peut être un VRT, on veut écrire un GeoTIFF
    #  - BIGTIFF/bigtiff doublons : casse différente, GDAL choisirait au hasard
    #  - NODATA/nodata : on désactive nodata sur la sortie uint8
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver="GTiff",
        dtype="uint8", count=1, compress="deflate", predictor=2,
        tiled=True, blockxsize=512, blockysize=512,
        bigtiff="YES", nodata=None)

    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n = 0
    lbl = "+".join(m for m, _, _ in jobs)

    src_ds = _rio.open(str(src_path))
    dsts = []
    try:
        for _mode, _params, _dst_path in jobs:
            dsts.append(_rio.open(str(_dst_path), "w", **out_profile))

        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt(f"{lbl} chunked interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)

                r0 = max(0, row_off - HALO)
                c0 = max(0, col_off - HALO)
                r1 = min(H, row_end + HALO)
                c1 = min(W, col_end + HALO)

                win_read = Window(c0, r0, c1 - c0, r1 - r0)
                block = src_ds.read(1, window=win_read).astype(np.float32)

                # Canonicalisation nodata : sentinelles magiques ET nodata
                # déclaré ramenés à une seule valeur connue des kernels.
                nd_mask = _nodata_mask(block, nodata)
                if nd_mask.any():
                    block[nd_mask] = np.float32(-9999.0)
                    nd_eff = -9999.0
                else:
                    nd_eff = None

                dr0 = row_off - r0
                dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off)
                dc1 = dc0 + (col_end - col_off)
                win_write = Window(col_off, row_off,
                                   col_end - col_off, row_end - row_off)

                for (mode, params, _dst_path), dst in zip(jobs, dsts):
                    if mode == "hillshade":
                        out = _hillshade_numpy(
                            block, params["azimuth_deg"], params["altitude_deg"],
                            z_factor=1.0, dx=dx, dy=dy, nodata=nd_eff)
                    elif mode == "hillshade_multi":
                        out = _hillshade_multi_numpy(
                            block, altitude_deg=params["altitude_deg"],
                            z_factor=1.0, dx=dx, dy=dy, nodata=nd_eff)
                    elif mode == "slope":
                        out = _slope_numpy(
                            block, z_factor=1.0, dx=dx, dy=dy, nodata=nd_eff)
                    else:
                        raise ValueError(f"Mode hillshade inconnu : {mode}")

                    centre = out[dr0:dr1, dc0:dc1]
                    dst.write(centre[np.newaxis, :, :], window=win_write)

                n += 1
                pct = n * 100 // total
                print(f"\r  {lbl} chunked: {pct:3d}% ({n}/{total} blocks)   ",
                      end="", flush=True)
    finally:
        src_ds.close()
        for dst in dsts:
            dst.close()
    print(f"\r  {lbl} chunked: done ({total} blocks)                     ")
    return True


def _hillshade_chunked(src_path, dst_path, mode, params, dx=0.5, dy=0.5):
    """Wrapper mono-sortie de _hillshade_chunked_multi (compat appels existants)."""
    return _hillshade_chunked_multi(src_path, [(mode, params, dst_path)],
                                    dx=dx, dy=dy)


def _svf_chunked(src_path, dst_path, max_dist_px, n_directions=16,
                 resolution=0.5, gamma=SVF_GAMMA, use_sweep=False, conv=0):
    """
    Sky-View Factor par fenêtres avec halo = max_dist_px (rayons SVF).

    use_sweep=True : utilise le kernel sweep (nearest-neighbor, ~2-3× plus
    rapide, léger aliasing aux faibles gradients).

    Stratégie 2 passes :
      1. Échantillon central → percentiles p2/p98 globaux
      2. Traitement bloc par bloc → stretch + gamma + uint8

    Borne la RAM à ~(2048+2*max_dist_px)² × 4 octets ≈ 25 MB pour SVF100.
    Retourne True si succès, False si import manquant.
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  SVF chunked: missing import ({_ie})", flush=True)
        return False

    CHUNK = 2048
    HALO  = max_dist_px

    # Kernel SVF mutualisé entre _svf_numpy et _svf_chunked (factory + cache).
    # Évite la double compilation Numba (~20 s × 2 au premier appel).
    # Si use_sweep : variante nearest-neighbor sans bilinéaire (~×2-3 plus rapide).
    # Openness +/- (conv == 2/3) : géré par le sweep désormais (hull non
    # clampé pour +, lower hull/min pour -, même deque, cf. _svf_sweep_kernel).
    # Plus aucun gate ray-cast forcé ici.
    _kernel = _get_numba_svf_sweep_kernel() if use_sweep else _get_numba_svf_kernel()
    if _kernel is None:
        print("  numba missing - SVF chunked unavailable", flush=True)
        return False
    if use_sweep:
        print("  SVF chunked: sweep-horizon kernel (deque/upper-hull)", flush=True)

    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    def _svf_block(block, nd_to=0.0):
        # nd_to : valeur posée sur les pixels nodata — 0.0 pour la sortie
        # (noir), NaN pour l'échantillonnage percentile (un 0.0 dans le pool
        # tirerait p2 vers 0 → stretch délavé dès qu'une fenêtre d'échantillon
        # chevauche du nodata).
        nd_mask = _nodata_mask(block, nodata)
        block_f = block.astype(np.float32, copy=True)
        if nd_mask.any():
            mean_val = float(np.nanmean(block_f[~nd_mask])) if (~nd_mask).any() else 0.0
            block_f[nd_mask] = mean_val
        svf = _kernel(block_f, n_directions, max_dist_px, resolution, conv)
        svf[nd_mask] = nd_to
        return svf

    # ── Passe 1 : compilation Numba + percentiles globaux (grille 3×3) ──────
    # Les p2/p98 calibrent le stretch (point noir/blanc) appliqué à TOUTE
    # l'image — échantillonnage réparti via _percentiles_grille (helper
    # partagé SVF/LRM/RRIM).
    print("  SVF chunked: Numba compilation + percentiles (grid)...", flush=True)
    _pcts = _percentiles_grille(src_path, HALO,
                                lambda w: _svf_block(w, nd_to=np.nan), 2, 98)
    if _pcts is None:
        return False
    p2_g, p98_g, _n_valid = _pcts
    if p98_g <= p2_g:
        p2_g, p98_g = 0.0, 1.0
    print(f"  SVF chunked: p2={p2_g:.3f}  p98={p98_g:.3f} (3×3 grid)", flush=True)

    out_profile = profile.copy()
    # Purger les clés héritées qui pourraient interférer :
    #  - driver : la source peut être un VRT, on veut écrire un GeoTIFF
    #  - BIGTIFF/bigtiff doublons : casse différente, GDAL choisirait au hasard
    #  - NODATA/nodata : on désactive nodata sur la sortie uint8
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver="GTiff",
        dtype="uint8", count=1, compress="deflate", predictor=2,
        tiled=True, blockxsize=512, blockysize=512,
        bigtiff="YES", nodata=None)

    # ── Passe 2 : traitement bloc par bloc ──────────────────────────────────
    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n = 0
    with _rio.open(str(src_path)) as src, \
         _rio.open(str(dst_path), "w", **out_profile) as dst:
        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("SVF chunked interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)

                r0 = max(0, row_off - HALO)
                c0 = max(0, col_off - HALO)
                r1 = min(H, row_end + HALO)
                c1 = min(W, col_end + HALO)

                win_read = Window(c0, r0, c1 - c0, r1 - r0)
                block = src.read(1, window=win_read).astype(np.float32)
                svf   = _svf_block(block)

                svf_stretched = np.clip((svf - p2_g) / (p98_g - p2_g), 0.0, 1.0)
                if conv == 3:
                    # Openness négative inversée : les features (fossés, chemins
                    # creux) sont les valeurs BASSES, le fond est clair — gamma
                    # en miroir 1−(1−x)^γ : renforce les creux SANS assombrir le
                    # fond. Le x^γ direct (γ=2) assombrissait toute l'image
                    # (fond ~0.5 → 0.27, rendu « très sombre »).
                    arr_u8 = ((1.0 - (1.0 - svf_stretched) ** gamma)
                              * 255.0).astype(np.uint8)
                else:
                    arr_u8 = (svf_stretched ** gamma * 255.0).astype(np.uint8)

                dr0 = row_off - r0
                dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off)
                dc1 = dc0 + (col_end - col_off)
                centre = arr_u8[dr0:dr1, dc0:dc1]

                win_write = Window(col_off, row_off, col_end - col_off, row_end - row_off)
                dst.write(centre[np.newaxis, :, :], window=win_write)

                n += 1
                pct = n * 100 // total
                print(f"\r  SVF chunked: {pct:3d}% ({n}/{total} blocks)   ",
                      end="", flush=True)
    print(f"\r  SVF chunked: done ({total} blocks, halo={HALO} px)        ")
    return True


def _svf_opos_chunked(src_path, svf_dst, opos_dst, max_dist_px, n_directions=16,
                      resolution=0.5, gamma=1.0):
    """SVF flux + openness positif en UN seul scan d'horizon (kernel fusionné),
    écrits dans svf_dst et opos_dst. Utilisé par le composite VAT pour éviter de
    refaire le scan deux fois (~moitié du temps des deux passes SVF/openness).
    Mêmes 2 passes (percentiles puis blocs), même stretch/gamma que _svf_chunked
    en conv=0 / conv=2 : sorties identiques, une seule traversée. True/False."""
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  SVF+opos chunked: missing import ({_ie})", flush=True)
        return False
    _kernel = _get_numba_svf_opos_kernel()
    if _kernel is None:
        print("  numba missing - VAT SVF+opos unavailable", flush=True)
        return False

    CHUNK = 2048
    HALO  = max_dist_px
    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    def _blocks(block):
        """(svf, opos, nd_mask) — float, nodata rempli par la moyenne du bloc."""
        nd_mask = _nodata_mask(block, nodata)
        bf = block.astype(np.float32, copy=True)
        if nd_mask.any():
            mv = float(np.nanmean(bf[~nd_mask])) if (~nd_mask).any() else 0.0
            bf[nd_mask] = mv
        svf, opos = _kernel(bf, n_directions, max_dist_px, resolution)
        return svf, opos, nd_mask

    # ── Passe 1 : percentiles p2/p98 des DEUX sorties en un seul scan ───────
    # (calc_block multi-sorties de _percentiles_grille — l'ancien code
    # appelait la grille une fois par sortie et refaisait donc le scan
    # d'horizon fusionné deux fois sur les mêmes fenêtres.)
    print("  VAT SVF+opos chunked: Numba compilation + percentiles (grid)...", flush=True)
    def _samp(win):
        svf, opos, nd = _blocks(win)
        return (np.where(nd, np.nan, svf), np.where(nd, np.nan, opos))
    _pcs = _percentiles_grille(src_path, HALO, _samp, 2, 98)
    if _pcs is None or _pcs[0] is None or _pcs[1] is None:
        return False
    p2s, p98s, _ = _pcs[0]
    p2o, p98o, _ = _pcs[1]
    if p98s <= p2s: p2s, p98s = 0.0, 1.0
    if p98o <= p2o: p2o, p98o = 0.0, 1.0
    print(f"  VAT SVF+opos: svf p2={p2s:.3f}/p98={p98s:.3f}, "
          f"opos p2={p2o:.3f}/p98={p98o:.3f}", flush=True)

    op = profile.copy()
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        op.pop(_k, None)
    op.update(driver="GTiff", dtype="uint8", count=1, compress="deflate",
              predictor=2, tiled=True, blockxsize=512, blockysize=512,
              bigtiff="YES", nodata=None)

    # ── Passe 2 : un seul scan par bloc → stretch des deux sorties → écriture ──
    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    nblk = 0
    with _rio.open(str(src_path)) as src, \
         _rio.open(str(svf_dst), "w", **op) as dsv, \
         _rio.open(str(opos_dst), "w", **op) as dop:
        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("VAT SVF+opos interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)
                r0 = max(0, row_off - HALO); c0 = max(0, col_off - HALO)
                r1 = min(H, row_end + HALO); c1 = min(W, col_end + HALO)
                block = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(np.float32)
                svf, opos, nd = _blocks(block)
                svf[nd] = 0.0; opos[nd] = 0.0
                su8 = (np.clip((svf - p2s) / (p98s - p2s), 0.0, 1.0) ** gamma
                       * 255.0).astype(np.uint8)
                ou8 = (np.clip((opos - p2o) / (p98o - p2o), 0.0, 1.0) ** gamma
                       * 255.0).astype(np.uint8)
                dr0 = row_off - r0; dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off); dc1 = dc0 + (col_end - col_off)
                ww = Window(col_off, row_off, col_end - col_off, row_end - row_off)
                dsv.write(su8[dr0:dr1, dc0:dc1][np.newaxis, :, :], window=ww)
                dop.write(ou8[dr0:dr1, dc0:dc1][np.newaxis, :, :], window=ww)
                nblk += 1
                print(f"\r  VAT SVF+opos: {nblk * 100 // total:3d}% "
                      f"({nblk}/{total} blocks)   ", end="", flush=True)
    print(f"\r  VAT SVF+opos: done ({total} blocks, halo={HALO} px)        ")
    return True


def _svf_numpy(dem, max_dist_px, n_directions=16, resolution=0.5, use_sweep=False,
               conv=0, nodata=None):
    """
    Sky-View Factor — pixel-level ray casting.

    SVF(p) = (1/N) × Σ_k cos²(γ_k),  γ_k = angle d'horizon dans la direction k

    Convention flux : cos²γ = 1/(1+tan²γ), avec tan γ = max(pente_horizon, 0).
    C'est la fraction de ciel hémisphérique pondérée par le cosinus (radiance).
    Préférée ici à la variante archéo RVT 1−sin γ : la distribution tassée près
    de 1 (terrain ouvert) donne, après stretch percentile + gamma 2.0, un
    contraste plus marqué jugé meilleur à l'œil sur ce relief.

    Moteurs disponibles par ordre de préférence :
      1. Numba njit + prange  → ×15-50 vs numpy pur, compilation ~20s au 1er appel
      2. numpy vectorisé      → fallback si numba absent

    use_sweep=True : utilise le kernel sweep (nearest-neighbor, ~×2-3 plus rapide,
    léger aliasing aux faibles gradients).

    SVF faible (sombre) = creux (fossé, fond de vallée)
    SVF élevé (clair)   = ouvert (sommet, plateau)
    """
    import numpy as np

    h, w = dem.shape
    nodata_mask = _nodata_mask(dem, nodata)
    dem_f = dem.astype(np.float32)
    if nodata_mask.any():
        mean_val = float(np.nanmean(dem_f[~nodata_mask])) if (~nodata_mask).any() else 0.0
        dem_f[nodata_mask] = mean_val

    # ── Tentative Numba ──────────────────────────────────────────────────────
    # Kernel mutualisé via _get_numba_svf_kernel() — partagé avec _svf_chunked
    # pour éviter la double compilation (~20 s × 2 au premier appel).
    # Openness +/- (conv == 2/3) : géré par le sweep désormais, cf. _svf_chunked.
    _numba_ok = False
    _svf_kernel = _get_numba_svf_sweep_kernel() if use_sweep else _get_numba_svf_kernel()
    if _svf_kernel is not None:
        try:
            print("  SVF Numba JIT: compiling on first call (~20s)...", flush=True)
            svf = _svf_kernel(dem_f, n_directions, max_dist_px, resolution, conv)
            _numba_ok = True
            print(f"\r  SVF Numba JIT - done{' ' * 30}")
        except Exception as e_nb:
            print(f"  numba erreur ({e_nb}) — fallback numpy", flush=True)
    else:
        print("  numba missing - vectorised numpy fallback", flush=True)

    # ── Fallback numpy ───────────────────────────────────────────────────────
    if not _numba_ok:
        try:
            from scipy.ndimage import shift as _shift
            _use_scipy = True
        except ImportError:
            _use_scipy = False

        # Check précoce : si l'utilisateur a déjà fait Ctrl+C avant qu'on arrive
        # ici (ex. pendant l'init Numba), on n'enchaîne pas le fallback.
        if _stop_event.is_set():
            raise KeyboardInterrupt("SVF interrompu avant traitement")

        def _process_direction(k):
            angle   = k * 2.0 * np.pi / n_directions
            dx      =  np.sin(angle)
            dy      = -np.cos(angle)
            # conv 3 (openness négative) suit le MIN des angles le long du
            # rayon ; les autres conventions suivent le MAX (horizon).
            need_min = (conv == 3)
            fill = np.inf if need_min else -np.inf
            ext_tan = np.full((h, w), fill, dtype=np.float32)

            for r in range(1, max_dist_px + 1):
                # Check au sein du rayon : sur dept-scale, max_dist_px peut
                # atteindre 200+ et chaque shift scipy prend 1-3s → permet
                # l'interruption en quelques secondes max.
                if _stop_event.is_set():
                    return None
                dist_m = r * resolution
                if _use_scipy:
                    neighbor  = _shift(dem_f, [dy * r, dx * r],
                                       mode='nearest', order=1, prefilter=False)
                    tan_angle = (neighbor - dem_f) / dist_m
                else:
                    rs = int(round(dy * r)); cs = int(round(dx * r))
                    r_s0 = max(0, -rs); r_s1 = min(h, h - rs)
                    c_s0 = max(0, -cs); c_s1 = min(w, w - cs)
                    r_d0 = max(0,  rs); r_d1 = min(h, h + rs)
                    c_d0 = max(0,  cs); c_d1 = min(w, w + cs)
                    if r_s1 <= r_s0 or c_s1 <= c_s0:
                        continue
                    tan_angle = np.full((h, w), fill, dtype=np.float32)
                    tan_angle[r_d0:r_d1, c_d0:c_d1] = (
                        dem_f[r_s0:r_s1, c_s0:c_s1] -
                        dem_f[r_d0:r_d1, c_d0:c_d1]
                    ) / dist_m
                if need_min:
                    np.minimum(ext_tan, tan_angle, out=ext_tan)
                else:
                    np.maximum(ext_tan, tan_angle, out=ext_tan)

            if conv == 0:
                # SVF flux : cos²γ = 1/(1+tan²γ) — contraste
                mt = np.maximum(ext_tan, 0.0)
                return (1.0 / (1.0 + mt * mt)).astype(np.float32)
            if conv == 1:
                # SVF RVT (Kokalj/Hesse) : 1 − sin γ — archéo
                mt = np.maximum(ext_tan, 0.0)
                return (1.0 - mt / np.sqrt(1.0 + mt * mt)).astype(np.float32)
            # Openness (Yokoyama 2002) — conv 2 : φ/π depuis le max β ;
            # conv 3 : négative inversée (π/2 − δ)/π depuis le min δ.
            return (0.5 - np.arctan(ext_tan) / np.pi).astype(np.float32)

        n_workers = min(n_directions, max(1, os.cpu_count() or 4))
        svf_sum   = np.zeros((h, w), dtype=np.float32)
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(_process_direction, k): k
                       for k in range(n_directions)}
            done = 0
            try:
                for fut in as_completed(futures):
                    if _stop_event.is_set():
                        # Annuler les futures non encore démarrées (les autres
                        # finiront leur direction courante mais retourneront None).
                        for f in futures:
                            f.cancel()
                        # On ne raise pas tout de suite — on laisse les workers
                        # actifs se terminer avant de quitter le with-block,
                        # sinon ThreadPoolExecutor.__exit__ va attendre quand même.
                        break
                    res = fut.result()
                    if res is None:
                        # Worker a vu _stop_event en interne et a retourné None
                        break
                    svf_sum += res
                    done += 1
                    pct_svf = done * 100 // max(n_directions, 1)
                    print(f"\r  SVF directions : {pct_svf:3d}%  {done}/{n_directions}",
                          end="", flush=True)
            except KeyboardInterrupt:
                # Signal arrivé pendant l'attente du future — annuler ce qu'on peut
                for f in futures:
                    f.cancel()
                raise
        print()
        # Si l'utilisateur a interrompu, propager l'arrêt à l'appelant.
        # Le résultat partiel n'est pas utilisable (sommation incomplète sur
        # n_directions). KeyboardInterrupt = standard Python, ne sera pas
        # capturé par les `except Exception:` en aval.
        if _stop_event.is_set():
            raise KeyboardInterrupt("SVF interrompu en cours de calcul")
        svf = svf_sum / n_directions

    svf[nodata_mask] = 0.0
    return svf


def _rrim_chunked(src_path, slope_path, dst_path, sigma_px):
    """
    Red Relief Image Map par blocs — RAM bornée (c'était le dernier ombrage
    qui chargeait encore le DEM entier en mémoire : OOM garanti à l'échelle
    d'un département).

    R     = pente décodée du TIF slope (uint8 1–255 → 0–90°), rampe ABSOLUE
            0–45° + gamma 0.7. Rampe fixe (Chiba et al. 2008) et non stretch
            percentile : deux zones adjacentes gardent le même rouge — l'ancien
            code cumulait clip(slope/45) PUIS stretch percentile, le second
            annulant le premier et rendant le rouge relatif au dataset.
    G = B = LRM (DEM − gaussienne σ) normalisé p5–p95 globaux (grille 3×3,
            cf. _percentiles_grille), gamma 0.8.
    Nodata → pixel noir (0,0,0).

    slope_path : TIF slope uint8 produit par _hillshade_chunked (même grille
    que le DEM source). Retourne True si succès, False si fallback requis.
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
        from scipy.ndimage import gaussian_filter as _gf
    except ImportError as _ie:
        print(f"  RRIM chunked: missing import ({_ie}), fallback to full memory",
              flush=True)
        return False

    CHUNK  = 2048
    MARGIN = max(4 * sigma_px, 64)

    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata
    with _rio.open(str(slope_path)) as srcsl_chk:
        if (srcsl_chk.width, srcsl_chk.height) != (W, H):
            print(f"  RRIM chunked: slope {srcsl_chk.width}×{srcsl_chk.height}"
                  f" != DEM {W}×{H}, fallback to full memory", flush=True)
            return False

    # ── Passe 1 : percentiles LRM p5/p95 + moyenne de remplissage globale ───
    _acc = [0.0, 0]
    def _lrm_vals(win):
        nd = _nodata_mask(win, nodata)
        v = win[~nd]
        if v.size:
            _acc[0] += float(v.sum()); _acc[1] += v.size
        fill = float(v.mean()) if v.size else 0.0
        lrm = win - _gf(np.where(nd, fill, win), sigma=sigma_px)
        lrm[nd] = np.nan
        return lrm

    _pcts = _percentiles_grille(src_path, MARGIN, _lrm_vals, 5, 95)
    if _pcts is None:
        return False
    p5_g, p95_g, _n_valid = _pcts
    mean_g = _acc[0] / _acc[1] if _acc[1] else 0.0
    if p95_g <= p5_g:
        return False
    print(f"  RRIM chunked: LRM p5={p5_g:.2f} m  p95={p95_g:.2f} m (3×3 grid)",
          flush=True)

    out_profile = profile.copy()
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver="GTiff",
        dtype="uint8", count=3, compress="deflate", predictor=2,
        tiled=True, blockxsize=512, blockysize=512,
        bigtiff="YES", nodata=None)

    # ── Passe 2 : traitement bloc par bloc ──────────────────────────────────
    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n = 0
    with _rio.open(str(src_path)) as src, \
         _rio.open(str(slope_path)) as srcsl, \
         _rio.open(str(dst_path), "w", **out_profile) as dst:
        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("RRIM chunked interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)

                r0 = max(0, row_off - MARGIN)
                c0 = max(0, col_off - MARGIN)
                r1 = min(H, row_end + MARGIN)
                c1 = min(W, col_end + MARGIN)

                win_read = Window(c0, r0, c1 - c0, r1 - r0)
                block = src.read(1, window=win_read).astype(np.float32)

                nd_mask    = _nodata_mask(block, nodata)
                block_fill = np.where(nd_mask, mean_g, block)
                lrm_block  = block - _gf(block_fill, sigma=sigma_px)

                dr0 = row_off - r0
                dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off)
                dc1 = dc0 + (col_end - col_off)
                lrm_c = lrm_block[dr0:dr1, dc0:dc1]
                nd_c  = nd_mask[dr0:dr1, dc0:dc1]

                win_write = Window(col_off, row_off,
                                   col_end - col_off, row_end - row_off)

                # R : pente décodée (1–255 → 0–90°), rampe absolue 0–45°
                sl_enc = srcsl.read(1, window=win_write).astype(np.float32)
                slope_deg = np.clip(sl_enc - 1.0, 0.0, None) * (90.0 / 254.0)
                r_chan = (np.clip(slope_deg / 45.0, 0.0, 1.0) ** 0.7
                          * 255.0).astype(np.uint8)

                # G = B : LRM normalisé p5–p95 globaux
                lrm_n = np.clip((lrm_c - p5_g) / (p95_g - p5_g), 0.0, 1.0)
                gb_chan = (np.nan_to_num(lrm_n) ** 0.8 * 255.0).astype(np.uint8)

                r_chan[nd_c]  = 0
                gb_chan[nd_c] = 0
                r_chan[sl_enc == 0] = 0   # nodata du slope

                rgb = np.stack([r_chan, gb_chan, gb_chan], axis=0)
                dst.write(rgb, window=win_write)

                n += 1
                pct = n * 100 // total
                print(f"\r  RRIM chunked: {pct:3d}% ({n}/{total} blocks)   ",
                      end="", flush=True)
    print(f"\r  RRIM chunked: done ({total} blocks, σ={sigma_px} px)          ")
    return True