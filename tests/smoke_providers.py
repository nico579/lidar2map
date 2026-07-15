#!/usr/bin/env python3
"""smoke_providers.py - test de fumee reseau des providers LiDAR.

Importe lidar2map et appelle SES vraies fonctions de telechargement
(telecharger_dalle_directe / telecharger_cog_fenetre, qui enchainent
discover -> download -> _post_fetch_si_besoin (post_fetch/multipart) ->
_valider_tif_dalle -> post_download). Pour chaque provider : on bascule le
PROVIDER courant, on cible un point connu couvert, on telecharge UNE tuile et
on verifie qu'elle s'ouvre avec des altitudes plausibles. Pas de
reimplementation : c'est le pipeline reel qui est exerce. Aucun ajout cote CLI.

Statuts :
  PASS  tuile valide recuperee (z affiche)        -> exit 0
  FAIL  endpoint casse / vide / format invalide   -> le harness sort en 1
  SKIP  cle API absente, ou dependance LAZ absente (laspy/lazrs/pdal)

Usage :
  python Tests/smoke_providers.py
  python Tests/smoke_providers.py --only gb-scotland,lu-act
Reseau requis. Pense pour tourner regulierement (cron CI ou manuel).
Cles API (sinon SKIP) : OPENTOPOGRAPHY_API_KEY, DATAFORDELER_TOKEN, FI_NLS_API_KEY.
"""
import argparse
import importlib
import os
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("LIDAR2MAP_BOOTSTRAP", "none")   # pas de bootstrap/venv

ROOT = Path(__file__).resolve().parent.parent
PROV_DIR = ROOT / "providers"
sys.path.insert(0, str(ROOT))

import numpy as np
import rasterio
import lidar2map as L   # noqa: E402  (charge un PROVIDER par defaut ; on le bascule)

# Point (lon, lat WGS84) connu couvert par chaque provider.
TEST_POINTS = {
    "fr-ign": (1.444, 43.604), "nl-ahn": (4.895, 52.370),
    "ch-swisstopo": (7.447, 46.948), "no-kartverket": (10.746, 59.913),
    "de-bayern": (11.576, 48.137), "de-nrw": (6.960, 50.938),
    "de-niedersachsen": (9.732, 52.375), "de-thueringen": (11.029, 50.979),
    "at-tirol": (11.405, 47.268), "at-osttirol": (12.770, 46.829),
    "gb-england": (-1.470, 53.380), "gb-wales": (-3.179, 51.481),
    "gb-scotland": (-4.2518, 55.8642), "be-flanders": (4.401, 51.221),
    "lu-act": (6.130, 49.611), "fi-maanmittauslaitos": (24.941, 60.170),
    "dk-datafordeler": (12.568, 55.676), "ie-gsi": (-6.260, 53.349),
    "cz-cuzk": (14.418, 50.073), "si-arso": (14.506, 46.056),
    "ee-maaamet": (24.753, 59.437), "es-cnig": (-3.703, 40.417),
    "lv-lgia": (24.105, 56.949),             # Riga (LAS national -> binning classe 2)
    "es-icgc": (2.173, 41.385), "pl-gugik": (21.012, 52.230),
    "ca-nrcan": (-73.567, 45.501), "nz-linz": (174.776, -41.286),
    "au-qld": (153.026, -27.470), "au-nsw": (151.209, -33.868),
    "au-ga": (138.600, -34.920), "us-tnm": (-122.332, 47.606),
    "us-3dep": (-122.332, 47.606),
    "us-cnmi": (145.75, 15.19),              # Saipan (NOAA VRT fenêtré, topobathy 1 m)
    "se-lantmateriet": (17.639, 59.859),    # Uppsala (COG 1 m, auth Basic)
    "jp-gsi": (139.767, 35.681),
    # Ajouts 2026-07-13 — points DÉJÀ validés par download réel à l'intégration :
    "de-hessen": (8.681, 50.111),           # Francfort (WCS he_dgm1)
    "de-bw": (9.183, 48.775),               # Stuttgart (WCS DGM1 LGL)
    "de-mv": (11.415, 53.630),              # Schwerin (WCS mv_dgm)
    "de-st": (11.629, 52.120),              # Magdebourg (WCS Coverage1)
    "at-bev": (13.050, 47.800),             # Salzbourg (COG fenêtré, 412-632 m)
    "it-emilia-romagna": (11.300, 44.450),  # collines de Bologne (60-395 m)
    "it-sardegna": (9.115, 39.223),         # Cagliari (WCS DTM 1 m, 36-97 m)
    "de-brandenburg": (13.06, 52.40),       # Potsdam (WCS DGM1 1 m, 29-46 m)
    "de-berlin": (13.404, 52.520),          # Alexanderplatz (ATOM/XYZ 1 m, 21-41 m)
    "de-rlp": (8.27, 50.0),                 # Mayence (Metalink 1 m, 98-129 m)
    "es-euskadi": (-2.93, 43.26),           # Bilbao (WCS 1.0.0 MDT 1 m, 27-164 m)
    "es-navarra": (-1.64, 42.81),           # Pampelune (WCS MDT 2 m, 401-481 m)
    "pt-dgt": (-9.19, 38.73),               # Monsanto, Lisbonne (MDT 50 cm)
}
APIKEY_ENV = {"us-3dep": "OPENTOPOGRAPHY_API_KEY",
              "dk-datafordeler": "DATAFORDELER_TOKEN",
              "fi-maanmittauslaitos": "FI_NLS_API_KEY"}
# Providers à compte (user/pass en env, pas une clé unique) : SKIP si absents.
CRED_ENV = {"pt-dgt": ("DGT_USER", "DGT_PASS"),
            "se-lantmateriet": ("LANTMATERIET_USER", "LANTMATERIET_PASS")}
_DEP = ("laspy", "lazrs", "pdal", "laszip")


def _select(mod):
    """Bascule le PROVIDER courant de lidar2map + les globals derives qu'il
    pose a l'import (cf. lidar2map ~l.2337-2344). C'est tout ce dont les
    fonctions de download ont besoin."""
    L.PROVIDER = mod
    L.CRS_NATIF = mod.CRS_NATIF
    L.RESOLUTION_M = mod.RESOLUTION_M
    L.DALLE_KM = mod.DALLE_KM
    L.PX_PAR_DALLE = mod.PX_PAR_DALLE
    L.SEUIL_DALLE_VALIDE = mod.SEUIL_DALLE_VALIDE
    L.LIDAR_SUBDIR = f"lidar/{getattr(mod, 'COUNTRY', 'xx')}"


def smoke_one(code, mod, lon, lat):
    _select(mod)
    d = 0.003
    bbox_wgs = (lon - d, lat - d, lon + d, lat + d)
    tf = L._get_transformer("EPSG:4326", mod.CRS_NATIF)
    xs, ys = [], []
    for px, py in ((bbox_wgs[0], bbox_wgs[1]), (bbox_wgs[0], bbox_wgs[3]),
                   (bbox_wgs[2], bbox_wgs[1]), (bbox_wgs[2], bbox_wgs[3])):
        x, y = tf.transform(px, py); xs.append(x); ys.append(y)
    bbox_natif = (min(xs), min(ys), max(xs), max(ys))

    needs_key = getattr(mod, "APIKEY_REQUISE", False)
    if needs_key:
        key = os.environ.get(APIKEY_ENV.get(code, ""), "").strip()
        if not key:
            return "SKIP", "cle API absente"
        if hasattr(mod, "set_apikey"):
            mod.set_apikey(key)
    # Providers à compte (login user/pass) : SKIP si les env vars manquent
    # (CI sans secret) plutôt qu'un FAIL 'discover -> None'.
    if code in CRED_ENV:
        if not all(os.environ.get(e, "").strip() for e in CRED_ENV[code]):
            return "SKIP", f"identifiants absents ({'/'.join(CRED_ENV[code])})"

    try:
        with tempfile.TemporaryDirectory() as dd:
            dossier = Path(dd)
            dalles = mod.discover_dalles(bbox_wgs, bbox_natif, dossier / "disc.json")
            if dalles is None:
                return ("SKIP", "cle/None") if needs_key else ("FAIL", "discover -> None (reseau/endpoint)")
            if not dalles:
                return "FAIL", "0 dalle pour un point pourtant couvert"
            nom, url = next(iter(dalles.items()))
            if getattr(mod, "COG_WINDOWED", False):
                res = L.telecharger_cog_fenetre(nom, url, dossier, bbox_natif)
            else:
                res = L.telecharger_dalle_directe(nom, url, dossier)
            if res != "ok":
                return "FAIL", f"download={res} ({nom})"
            with rasterio.open(L.chemin_dalle(dossier, nom)) as src:
                a = src.read(1); ndv = src.nodata
                v = a[a != ndv] if ndv is not None else a
                v = v[np.isfinite(v)]
                rm = src.res[0]
                crs = src.crs
                nb = src.count
            if v.size == 0:
                return "FAIL", "tuile recuperee mais 0 pixel valide"
            # #5 (audit) : IMPOSER, pas seulement afficher.
            # (a) CRS présent : une dalle sans CRS ne peut pas être warpée en 3857.
            if crs is None:
                return "FAIL", f"pas de CRS sur la dalle ({nom})"
            # (b) résolution = celle déclarée, MAIS uniquement quand la dalle est
            #     dans son CRS natif PROJETÉ métrique. On exclut EPSG:3857 (web
            #     mercator, dont le pas diverge de la résolution-sol avec la
            #     latitude : au-*, jp-gsi) et EPSG:4326 (degrés) → sinon faux FAIL.
            try:
                exp = int(mod.CRS_NATIF.split(":")[1])
            except Exception:
                exp = None
            if (crs.to_epsg() == exp and exp not in (3857, 4326)
                    and abs(rm - mod.RESOLUTION_M) > 0.10 * mod.RESOLUTION_M):
                return "FAIL", f"res={rm:g} != {mod.RESOLUTION_M:g} m declaree ({nom})"
            return "PASS", (f"z=[{float(v.min()):.1f},{float(v.max()):.1f}] m, "
                            f"{v.size}px, {nb}b, EPSG:{crs.to_epsg()}, res={rm:g}")
    except ImportError as e:
        return "SKIP", f"dependance absente: {e}"
    except Exception as e:
        if any(h in repr(e).lower() for h in _DEP):
            return "SKIP", f"dependance LAZ absente: {type(e).__name__}"
        return "FAIL", f"{type(e).__name__}: {e}"


def _echec_reseau(detail):
    """FAIL candidat au retry : erreur de TRANSPORT (timeout, coupure, 5xx),
    pas une absence de donnee ('absent', 0 dalle : etat stable cote serveur)
    ni un bug de code. La moitie des rouges du cron hebdo sont des serveurs
    qui toussent et repassent au run suivant."""
    if detail.startswith("discover -> None"):
        return True
    if detail.startswith("download=erreur"):
        return True
    reseau = ("TimeoutError", "URLError", "RemoteDisconnected", "HTTPError",
              "ConnectionError", "ConnectionResetError", "IncompleteRead",
              "RasterioIOError", "socket.timeout")
    return any(m in detail for m in reseau)


def _discover_providers():
    """AUTO : tous les providers du dossier providers/ = source de verite (comme
    coverage_map.py). Retourne ({code: module}, [(fichier, erreur_import)])."""
    ok, errors = {}, []
    for p in sorted(PROV_DIR.glob("*.py")):
        if p.stem.startswith("_"):
            continue
        try:
            m = importlib.import_module("providers." + p.stem)
        except Exception as e:
            errors.append((p.stem, e)); continue
        code = getattr(m, "CODE", None)
        if code:
            ok[code] = m
        else:
            # Module sans CODE = helper partage (providers/common.py), pas un
            # provider — meme regle que _discover_providers de lidar2map.py
            # (jumeaux : ce scan avait derive, FAIL smoke du 2026-07-13).
            print(f"  (skip {p.stem}: module sans CODE = helper, pas un provider)")
    return ok, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="",
                    help="restreindre a ces codes (defaut : TOUS les providers du dossier)")
    ap.add_argument("--skip", default="",
                    help="codes a exclure (reportes SKIP) : faux-positifs CI "
                         "(IP throttle, auth) qui marchent depuis une IP normale")
    args = ap.parse_args()
    only = {c.strip() for c in args.only.split(",") if c.strip()}
    skip = {c.strip() for c in args.skip.split(",") if c.strip()}

    discovered, imp_errors = _discover_providers()      # lit providers/*.py
    codes = sorted(c for c in discovered if (not only or c in only))
    orphans = sorted(set(TEST_POINTS) - set(discovered))  # point sans provider

    print(f"\nSmoke providers (auto, dossier providers/) : {len(codes)} - "
          f"{time.strftime('%Y-%m-%d %H:%M')}\n")
    rows = []
    for stem, err in imp_errors:
        print(f"  [FAIL] {stem:<22}   import : {err}")
        rows.append((stem, "FAIL"))
    for code in codes:
        if code in skip:
            print(f"  [SKIP] {code:<22}   exclu via --skip (faux-positif CI connu)")
            rows.append((code, "SKIP")); continue
        if code not in TEST_POINTS:
            print(f"  [NOPT] {code:<22}   aucun point de test (ajouter dans TEST_POINTS)")
            rows.append((code, "NOPT")); continue
        t0 = time.time()
        try:
            status, detail = smoke_one(code, discovered[code], *TEST_POINTS[code])
        except Exception as e:
            status, detail = "FAIL", f"{type(e).__name__}: {e}"
        # Retry UNIQUE sur echec reseau (jamais sur 'absent'/'0 dalle') :
        # departage transitoire vs durable sans masquer les vraies pannes.
        if status == "FAIL" and _echec_reseau(detail):
            print(f"  [....] {code:<22}   echec reseau, retry unique dans 10 s "
                  f"({detail[:60]})", flush=True)
            time.sleep(10)
            try:
                status, detail = smoke_one(code, discovered[code], *TEST_POINTS[code])
            except Exception as e:
                status, detail = "FAIL", f"{type(e).__name__}: {e}"
            if status == "PASS":
                detail += "  (retry: transitoire)"
        dt = time.time() - t0
        icon = {"PASS": "OK  ", "FAIL": "FAIL", "SKIP": "SKIP"}.get(status, "????")
        print(f"  [{icon}] {code:<22} {dt:6.1f}s  {detail}", flush=True)
        rows.append((code, status))

    if orphans:
        print(f"\n  ATTENTION : point(s) de test sans provider dans le dossier : {orphans}")

    nf = sum(1 for _, s in rows if s == "FAIL")
    nnopt = sum(1 for _, s in rows if s == "NOPT")
    npass = sum(1 for _, s in rows if s == "PASS")
    nskip = sum(1 for _, s in rows if s == "SKIP")
    extra = f" - {nnopt} NOPT" if nnopt else ""
    print(f"\n{npass} PASS - {nf} FAIL{extra} - {nskip} SKIP / {len(rows)}")
    return 1 if (nf or nnopt) else 0


if __name__ == "__main__":
    sys.exit(main())
