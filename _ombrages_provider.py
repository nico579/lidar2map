"""Ombrages précalculés fournisseur (WCS) et composites avancés (VAT, MSTP).

Deux familles distinctes colocalisées : le téléchargement/désencapsulation
d'ombrages précalculés que certains providers exposent via WCS (évite de
recalculer localement — cf. ``_fetch_provider_shadings``), et les composites
qui blendent plusieurs couches déjà produites par ``_ombrages_pures``
(``_vat_compose``, ``_mstp_chunked``, ``_e4mstp_compose``).

Contrairement à ``_ombrages_pures`` (couche sans dépendance applicative),
ce module touche ``PROVIDER`` (WCS_URL, post_fetch, SSL) et la publication
atomique (``_chemin_part``, ``_creer_fichier``) : ses trois points d'entrée
côté provider (``_extraire_tiff_multipart``, ``_post_fetch_si_besoin``,
``_fetch_provider_shadings``) reçoivent leurs coutures par injection, sur le
même principe que les producteurs MBTiles (7b/7e). ``_extraire_tiff_multipart``
est injecté à l'intérieur même de ``_post_fetch_si_besoin``/
``_fetch_provider_shadings`` (callable, pas de bare-name interne) : des
suites remplacent `L._extraire_tiff_multipart` en bloc puis appellent
`L._fetch_provider_shadings`, et s'attendent à ce que l'appel interne route
par le nom patché — cf. le bug `_wmts_fetch` de la phase 7c, même piège.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from _ombrages_pures import _nodata_mask, _stop_event


@dataclass(frozen=True)
class _DependancesFetchProvider:
    """Coutures partagées par `_post_fetch_si_besoin` et
    `_fetch_provider_shadings` (chacune n'utilise qu'un sous-ensemble)."""

    provider: object
    extraire_tiff_multipart: Callable
    chemin_part: Callable
    creer_fichier: Callable
    formater_duree: Callable
    valider_tif: Callable
    normaliser_nom: Callable
    http_chunk_size: int


_TIFF_MAGICS = (b'II\x2a\x00', b'MM\x00\x2a', b'II\x2b\x00', b'MM\x00\x2b')


def _extraire_tiff_multipart(chemin, *, http_chunk_size):
    """Désencapsule un GeoTIFF d'une réponse WCS 2.0 multipart/related.

    Certains serveurs WCS 2.0 (MapServer : Digitaal Vlaanderen, etc.) renvoient
    GetCoverage en multipart/related : une partie GML (text/xml) puis le GeoTIFF
    binaire, séparés par une frontière MIME (--<boundary>). urllib sauve le flux
    brut tel quel → le fichier n'est pas un TIFF valide. On extrait la partie
    binaire (du magic TIFF jusqu'à la frontière suivante) et on réécrit le
    fichier en GeoTIFF pur. No-op si le fichier est déjà un TIFF brut ou n'est
    pas du multipart. Réponse OGC standard, pas un cas spécifique provider.
    """
    # R2#43 — extraction en mémoire bornée. L'ancienne version chargeait TOUT
    # le fichier (read_bytes) PUIS tranchait data[i:fin] = deux copies plein
    # cadre en RAM. Sur un GeoTIFF départemental multipart (centaines de Mo)
    # → OOM. Ici : on lit une petite fenêtre d'en-tête pour le boundary, on
    # balaye en flux (avec chevauchement) pour l'offset du magic TIFF, on lit
    # une fenêtre de QUEUE pour la frontière de clôture, puis on recopie la
    # tranche [i, fin) chunk par chunk vers un temporaire (RAM ~ HTTP_CHUNK_SIZE).
    tmp = Path(chemin).with_suffix(Path(chemin).suffix + ".mp.part")
    try:
        with open(chemin, "rb") as _f:
            entete = _f.read(2)
            if entete in (b'II', b'MM'):
                return  # déjà un TIFF brut
            if entete != b'--':
                return  # pas une frontière multipart

            # Boundary = 1re ligne (--<boundary>). Lecture bornée.
            _f.seek(0)
            tete = _f.read(8192)
            nl = tete.find(b'\n')
            if nl < 0:
                return
            boundary = tete[2:nl].strip()            # ex. b'wcs'

            taille = Path(chemin).stat().st_size
            _overlap = max(len(m) for m in _TIFF_MAGICS) - 1

            # Offset du GeoTIFF : 1re occurrence d'un magic TIFF. La partie GML
            # (text/xml) précède et ne contient pas ces octets binaires. Balayage
            # en flux, chevauchement de (len(magic)-1) pour ne pas rater un magic
            # à cheval sur deux chunks.
            i = -1
            pos = 0
            reste = b''
            _f.seek(0)
            while True:
                bloc = _f.read(http_chunk_size)
                if not bloc:
                    break
                fenetre = reste + bloc
                base = pos - len(reste)
                trouve = min((fenetre.find(m) for m in _TIFF_MAGICS
                              if m in fenetre), default=-1)
                if trouve >= 0:
                    i = base + trouve
                    break
                pos += len(bloc)
                reste = fenetre[-_overlap:]
            if i < 0:
                return  # pas de magic → fichier laissé tel quel

            # Frontière de clôture : le TIFF est la DERNIÈRE partie, donc
            # --<boundary> se trouve en toute fin de réponse. Fenêtre de queue
            # bornée (jamais tout le fichier). Repli sur EOF si introuvable.
            _TAIL = 65536
            debut_tail = max(i, taille - _TAIL)
            _f.seek(debut_tail)
            queue = _f.read()
            j = queue.find(b'--' + boundary)
            fin = (debut_tail + j) if j >= 0 else taille

            # Recopie en flux de [i, fin) vers le temporaire ; rstrip du CRLF
            # (avant la frontière) sur le dernier bloc écrit.
            with open(tmp, "wb") as _out:
                _f.seek(i)
                restant = fin - i
                while restant > 0:
                    bloc = _f.read(min(http_chunk_size, restant))
                    if not bloc:
                        break
                    restant -= len(bloc)
                    if restant <= 0:
                        bloc = bloc.rstrip(b'\r\n')
                    _out.write(bloc)
        os.replace(tmp, chemin)
    except Exception as _e_mp:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass
        print(f"  multipart {Path(chemin).name} : {type(_e_mp).__name__}: {_e_mp}",
              flush=True)


def _post_fetch_si_besoin(chemin, *, provider, extraire_tiff_multipart):
    """Prépare le fichier brut téléchargé avant la validation GeoTIFF :
      1. désencapsulation multipart/related (générique WCS 2.0) ;
      2. PROVIDER.post_fetch(chemin) si défini (LAZ/ZIP → GeoTIFF, reproject…).
    No-op si rien ne s'applique. Une erreur du hook est journalisée puis
    propagée : l'appelant doit abandonner son staging, jamais publier un fichier
    dont la transformation provider n'est pas allée au bout.
    """
    extraire_tiff_multipart(chemin)
    pf = getattr(provider, "post_fetch", None)
    if pf is None:
        return
    try:
        pf(chemin)
    except Exception as _e_pf:
        print(f"  post_fetch {chemin.name} : {type(_e_pf).__name__}: {_e_pf}",
              flush=True)
        raise


def _fetch_provider_shadings(choix, bbox_natif, dossier_ville, nom_zone,
                              ecraser_ombrages, provides_shadings, *, dependances):
    """Telecharge les ombrages precalcules fournis par le provider via WCS.
    Modifie `choix` en place : retire les cles traitees avec succes.
    provides_shadings : {cle: (coverage_id, resolution_m)} ou
                        {cle: (coverage_id, resolution_m, wcs_url)}
    """
    import urllib.request as _urlreq
    import urllib.parse   as _urlparse
    dossier_ville = Path(dossier_ville)
    dossier_ville.mkdir(parents=True, exist_ok=True)
    nom_base = dependances.normaliser_nom(nom_zone) if nom_zone else dependances.normaliser_nom(dossier_ville.name)
    _SUFFIX = {
        "svf":"svf_ombrage","multi":"multi_ombrage","slope":"slope_ombrage",
        "lrm":"lrm_ombrage","rrim":"rrim_ombrage","315":"315_ombrage",
        "045":"045_ombrage","135":"135_ombrage","225":"225_ombrage",
    }
    for cle, spec in provides_shadings.items():
        if cle not in choix:
            continue
        coverage_id  = spec[0]
        resolution_m = float(spec[1])
        wcs_url      = spec[2] if len(spec) > 2 else getattr(dependances.provider, "WCS_URL", None)
        if not wcs_url:
            continue
        nom_fichier = f"{nom_base}_{_SUFFIX.get(cle, cle+'_ombrage')}.tif"
        chemin_out  = dossier_ville / nom_fichier
        if (chemin_out.exists() and not ecraser_ombrages
                and dependances.valider_tif(chemin_out)):
            print(f"  {nom_fichier.ljust(56)} -> already present (provider pre-computed)")
            choix.remove(cle)
            continue
        x1, y1, x2, y2 = bbox_natif
        print(f"  {cle} -> provider pre-computed ({coverage_id}, {resolution_m}m)...",
              flush=True)
        t0 = time.time()
        success = False
        # Labels d'axe WCS : variables selon le serveur (x/y minuscules pour
        # MapServer Digitaal Vlaanderen, E/N ou X/Y ailleurs). On lit ceux
        # déclarés par le provider puis on tente des fallbacks courants.
        _ax_prov = getattr(dependances.provider, "WCS_AXIS_LABELS", None)
        _axes = ([tuple(_ax_prov)] if _ax_prov else []) + \
                [("x","y"),("E","N"),("X","Y")]
        for ax1, ax2 in _axes:
            params = _urlparse.urlencode({
                "service":"WCS","version":"2.0.1","request":"GetCoverage",
                "coverageId":coverage_id,"format":"image/tiff",
                "subset":f"{ax1}({x1},{x2})",
            })
            url = f"{wcs_url}?{params}&subset={ax2}({y1},{y2})"
            chemin_part = dependances.chemin_part(chemin_out)
            try:
                ssl_ctx = getattr(dependances.provider, "_SSL_CTX", None)
                req = _urlreq.Request(url, headers={"User-Agent":"lidar2map/1.0"})
                # R2#43 — écriture en flux par chunks : une réponse WCS
                # GetCoverage sur un gros département (GeoTIFF plein cadre) peut
                # peser des centaines de Mo. r.read() la chargeait ENTIÈRE en
                # RAM avant d'écrire → OOM. On copie chunk par chunk (RAM bornée
                # à dependances.http_chunk_size), comme le téléchargement de dalles.
                with _urlreq.urlopen(req, timeout=180, context=ssl_ctx) as r:
                    _headers = getattr(r, "headers", {})
                    _ct = _headers.get("content-type", "").lower()
                    if (not _ct.startswith("multipart")
                            and ("xml" in _ct or "html" in _ct)):
                        raise IOError(
                            f"server error response ({_ct or 'no content-type'})")
                    try:
                        _content_length = int(
                            _headers.get("content-length", 0))
                    except (TypeError, ValueError):
                        _content_length = 0
                    _taille_recue = 0
                    with open(chemin_part, "wb") as _out:
                        while True:
                            _chunk = r.read(dependances.http_chunk_size)
                            if not _chunk:
                                break
                            _out.write(_chunk)
                            _taille_recue += len(_chunk)
                if (_content_length > 0
                        and _taille_recue != _content_length):
                    raise IOError(
                        f"Transfert WCS tronqué : reçu {_taille_recue} octets, "
                        f"attendu {_content_length} (Content-Length)")
                # WCS 2.0 multipart/related → extraire le GeoTIFF binaire
                dependances.extraire_tiff_multipart(chemin_part)
                if not dependances.valider_tif(chemin_part):
                    chemin_part.unlink(missing_ok=True)
                    continue
                chemin_part.replace(chemin_out)
                dependances.creer_fichier(chemin_out)
                _taille = chemin_out.stat().st_size
                print(f"  {nom_fichier} ({_taille/1e6:.1f} Mo,"
                      f" {dependances.formater_duree(time.time()-t0)})",flush=True)
                choix.remove(cle)
                success = True
                break
            except KeyboardInterrupt:
                chemin_part.unlink(missing_ok=True)
                raise
            except Exception:
                chemin_part.unlink(missing_ok=True)
                continue
        if not success:
            print(f"  {cle}: provider pre-computed failed -> normal computation from DEM",
                  flush=True)

# Opacités du composite VAT (cf. _vat_compose). Tunables : ce sont les seuls
# réglages "esthétiques" du mélange, exposés en constantes pour calage facile.
VAT_OPOS_OPACITY  = 0.5   # overlay openness positif (renforce le micro-relief convexe)
VAT_SLOPE_OPACITY = 0.5   # assombrissement par la pente (contraste des talus/scarps)


def _vat_compose(svf_path, opos_path, slope_path, dst_path,
                 gamma=1.0, opos_opacity=VAT_OPOS_OPACITY,
                 slope_opacity=VAT_SLOPE_OPACITY):
    """Composite VAT-style (Visualization for Archaeological Topography), niveaux
    de gris, à partir de 3 couches uint8 déjà calculées et pixel-alignées :
        base   = Sky-View Factor (micro-relief : fossés sombres, surfaces claires)
        + overlay openness positif  (accentue crêtes / tertres / convexités)
        × assombrissement par la pente (donne du contraste aux talus et scarps)
    C'est l'esprit du défaut archéo du Relief Visualization Toolbox (ZRC SAZU) :
    une seule image qui révèle creux ET bosses sans choisir une méthode. Les
    poids sont dans VAT_*_OPACITY (à calibrer à l'œil / contre RVT).

    Blend par fenêtres 2048² (uint8, RAM bornée). Retourne True/False."""
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  VAT compose: missing import ({_ie})", flush=True)
        return False

    CHUNK = 2048
    with _rio.open(str(svf_path)) as s0:
        H, W = s0.height, s0.width
        profile = s0.profile.copy()
    # Les 3 couches viennent du même DEM donc devraient être alignées ; on le
    # vérifie quand même (cf. _rrim_chunked) : sinon les lectures fenêtrées se
    # désaligneraient silencieusement. En cas d'écart, on annule proprement.
    for _other in (opos_path, slope_path):
        with _rio.open(str(_other)) as _so:
            if (_so.width, _so.height) != (W, H):
                print(f"  VAT compose : {Path(_other).name} {_so.width}×{_so.height}"
                      f" != SVF {W}×{H}, composite aborted", flush=True)
                return False
    for _k in ("BIGTIFF", "bigtiff", "NODATA", "nodata"):
        profile.pop(_k, None)
    profile.update(driver="GTiff", dtype="uint8", count=1,
                   compress="deflate", predictor=2, tiled=True,
                   blockxsize=512, blockysize=512, nodata=None, bigtiff="IF_SAFER")

    def _overlay(b, t):
        return np.where(b < 0.5, 2 * b * t, 1.0 - 2.0 * (1.0 - b) * (1.0 - t))

    with _rio.open(str(svf_path)) as s, _rio.open(str(opos_path)) as o, \
         _rio.open(str(slope_path)) as sl, \
         _rio.open(str(dst_path), "w", **profile) as dst:
        for r in range(0, H, CHUNK):
            for c in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("VAT compose interrompu")
                win = Window(c, r, min(CHUNK, W - c), min(CHUNK, H - r))
                a_u8 = s.read(1, window=win)
                a = a_u8.astype(np.float32) / 255.0
                b = o.read(1, window=win).astype(np.float32) / 255.0
                d = sl.read(1, window=win).astype(np.float32) / 255.0
                v = a * (1.0 - opos_opacity) + _overlay(a, b) * opos_opacity
                v = v * (1.0 - slope_opacity * d)      # pente raide → plus sombre
                if gamma and gamma != 1.0:
                    v = np.clip(v, 0, 1) ** gamma
                out = (np.clip(v, 0, 1) * 255.0).astype(np.uint8)
                out[a_u8 == 0] = 0                     # nodata SVF (= 0) → noir
                dst.write(out, 1, window=win)
    return True


def _mstp_chunked(src_path, dst_path, scales_m=None, res=0.5,
                  lightness=0.85, k=2.2):
    """Approximation gaussienne interne du MSTP, chunkée → GeoTIFF RGB uint8.

    DEV(σ) = (z − moyenne_σ) / écart-type_σ : déviation d'altitude standardisée
    (≈ slope-invariant), calculée sur 3 bandes d'échelle (local/méso/large).
    Chaque bande = moyenne du DEV sur ses sous-échelles ; les 3 vont dans
    R/G/B, donc la COULEUR encode l'échelle dominante d'une structure. Clip
    symétrique ±k (unités d'écart-type) → [0,1], gamma `lightness`.

    Échelles en MÈTRES (indépendantes de la résolution du MNT), converties en
    px via `res`. RAM bornée : blocs 2048² + halo = 4·σ_max (comme le LRM).
    Nodata → noir. Retourne True/False (import manquant)."""
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
        from scipy.ndimage import gaussian_filter as _gf
    except ImportError as _ie:
        print(f"  MSTP chunked: missing import ({_ie})", flush=True)
        return False
    if scales_m is None:
        # local (micro-relief), méso (talus/parcellaire), large (versant)
        scales_m = [(1.5, 5.0), (12.0, 27.0), (55.0, 100.0)]
    scales_px = [tuple(max(1.0, s / res) for s in band) for band in scales_m]
    sig_max = max(s for band in scales_px for s in band)
    CHUNK  = 2048
    MARGIN = int(max(4 * sig_max, 64))

    def _dev(z, s):
        mu = _gf(z, s)
        sd = np.sqrt(np.maximum(_gf(z * z, s) - mu * mu, 0.0))
        return (z - mu) / (sd + 1e-3)

    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata
    out_profile = profile.copy()
    for _dk in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_dk, None)
    out_profile.update(driver="GTiff", dtype="uint8", count=3,
                       compress="deflate", predictor=2, tiled=True,
                       blockxsize=512, blockysize=512, bigtiff="YES", nodata=None)

    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n = 0
    with _rio.open(str(src_path)) as src, \
         _rio.open(str(dst_path), "w", **out_profile) as dst:
        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("MSTP chunked interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)
                r0 = max(0, row_off - MARGIN); c0 = max(0, col_off - MARGIN)
                r1 = min(H, row_end + MARGIN); c1 = min(W, col_end + MARGIN)
                block = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(np.float32)
                nd = _nodata_mask(block, nodata)
                if nd.any():
                    _mv = float(block[~nd].mean()) if (~nd).any() else 0.0
                    block = np.where(nd, _mv, block)
                bands = []
                for band in scales_px:
                    d = np.mean([_dev(block, s) for s in band], axis=0)
                    bands.append(np.clip((d + k) / (2 * k), 0.0, 1.0))
                rgb = (np.stack(bands, axis=0).astype(np.float32)) ** lightness
                dr0 = row_off - r0; dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off); dc1 = dc0 + (col_end - col_off)
                nd_c = nd[dr0:dr1, dc0:dc1]
                out = (np.clip(rgb[:, dr0:dr1, dc0:dc1], 0, 1) * 255.0).astype(np.uint8)
                out[:, nd_c] = 0
                dst.write(out, window=Window(col_off, row_off,
                                             col_end - col_off, row_end - row_off))
                n += 1
                print(f"\r  MSTP chunked: {n * 100 // total:3d}% "
                      f"({n}/{total} blocks)   ", end="", flush=True)
    print(f"\r  MSTP chunked: done ({total} blocks)                    ")
    return True


def _e4mstp_compose(mstp_path, svf_path, opos_path, oneg_path, slope_path,
                    slrm_fine_path, slrm_path_path, dst_path, gamma=1.0):
    """Variante lidar2map inspirée de l'e4MSTP → GeoTIFF RGB uint8.

    Ce composite ne reproduit pas la recette RVT de référence (Kokalj 2025) :
    il emploie un SVF et deux SLRM, sans dominance locale, ainsi qu'une
    approximation gaussienne interne du MSTP.

    Combine la couleur multi-échelle du MSTP et la netteté type-VAT du SVF :
      base   = relief coloré (openness positive = crêtes claires, négative =
               creux sombres) teinté chaud par la pente (≈ CRIM) ;
      × SVF   (multiply)  → assombrit les concavités, crispness ;
      + MSTP  (overlay)   → couleur d'échelle ;
      + SLRM fin (screen) → micro-relief ;
      + SLRM échelle-chemin (soft-light) → isole les linéaires (façon LRM).
    Toutes les couches sont déjà calculées et pixel-alignées. Blend par blocs
    2048² (RAM bornée). Retourne True/False."""
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  e4MSTP compose: missing import ({_ie})", flush=True)
        return False
    CHUNK = 2048
    with _rio.open(str(mstp_path)) as m0:
        H, W = m0.height, m0.width
        profile = m0.profile.copy()
    for _o in (svf_path, opos_path, oneg_path, slope_path,
               slrm_fine_path, slrm_path_path):
        with _rio.open(str(_o)) as _so:
            if (_so.width, _so.height) != (W, H):
                print(f"  e4MSTP: {Path(_o).name} {_so.width}×{_so.height}"
                      f" != MSTP {W}×{H}, composite aborted", flush=True)
                return False
    for _pk in ("BIGTIFF", "bigtiff", "NODATA", "nodata"):
        profile.pop(_pk, None)
    profile.update(driver="GTiff", dtype="uint8", count=3, compress="deflate",
                   predictor=2, tiled=True, blockxsize=512, blockysize=512,
                   nodata=None, bigtiff="IF_SAFER")

    def _overlay(a, b): return np.where(a < 0.5, 2 * a * b, 1 - 2 * (1 - a) * (1 - b))
    def _screen(a, b):  return 1 - (1 - a) * (1 - b)

    def _soft(a, b):
        d = np.where(a <= 0.25, ((16 * a - 12) * a + 4) * a, np.sqrt(np.clip(a, 0, 1)))
        return np.where(b <= 0.5, a - (1 - 2 * b) * a * (1 - a), a + (2 * b - 1) * (d - a))

    with _rio.open(str(mstp_path)) as m, _rio.open(str(svf_path)) as sv, \
         _rio.open(str(opos_path)) as op, _rio.open(str(oneg_path)) as on, \
         _rio.open(str(slope_path)) as sl, _rio.open(str(slrm_fine_path)) as lf, \
         _rio.open(str(slrm_path_path)) as lp, \
         _rio.open(str(dst_path), "w", **profile) as dst:
        for r in range(0, H, CHUNK):
            for c in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("e4MSTP compose interrompu")
                win = Window(c, r, min(CHUNK, W - c), min(CHUNK, H - r))
                mstp   = np.moveaxis(m.read(window=win), 0, -1).astype(np.float32) / 255.0
                svf    = sv.read(1, window=win).astype(np.float32) / 255.0
                opos_u = op.read(1, window=win)
                opos   = opos_u.astype(np.float32) / 255.0
                oneg   = on.read(1, window=win).astype(np.float32) / 255.0
                sl_u8  = sl.read(1, window=win)
                slope_deg = np.clip(sl_u8.astype(np.float32) - 1, 0, None) * (90.0 / 254.0)
                s = np.clip(slope_deg / 45.0, 0, 1)
                slf = lf.read(1, window=win).astype(np.float32) / 255.0
                slp = lp.read(1, window=win).astype(np.float32) / 255.0
                # Relief openness pos/neg : crêtes claires (opos), creux/fossés
                # assombris (oneg bas dans les creux → facteur < 1).
                L = opos * (0.40 + 0.60 * oneg)
                crim = np.stack([np.clip(L + 0.32 * s, 0, 1),
                                 np.clip(L * (1 - 0.32 * s), 0, 1),
                                 np.clip(L * (1 - 0.65 * s), 0, 1)], axis=-1)
                svf3 = svf[..., None]
                e = crim * 0.62 + (crim * svf3) * 0.38        # SVF multiply
                e = e * 0.28 + _overlay(e, mstp) * 0.72       # MSTP overlay
                slf3 = slf[..., None]; slp3 = slp[..., None]
                e = e * 0.80 + _screen(e, slf3) * 0.20        # micro-relief fin
                e = e * 0.65 + _soft(e, slp3) * 0.35          # isolation chemin
                if gamma and gamma != 1.0:
                    e = np.clip(e, 0, 1) ** gamma
                out = (np.clip(e, 0, 1) * 255.0).astype(np.uint8)
                out[opos_u == 0] = 0                          # nodata → noir
                dst.write(np.moveaxis(out, -1, 0), window=win)
    return True