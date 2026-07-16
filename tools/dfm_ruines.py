#!/usr/bin/env python3
"""dfm_ruines.py — prospection des ruines DEBOUT que le MNT IGN efface.

PROBLÈME (vécu, Var 2026-07) : les murs de ruines de ~1,5 m sont classés
« végétation moyenne » (classe 4) ou « non classé » (classe 1) par la chaîne
IGN_AUTO ; le MNT LiDAR HD ne garde que les classes 2/9/66 et INTERPOLE au
travers → les ruines n'existent pas dans le MNT, donc invisibles en LRM/VAT.
Paradoxe documenté par la spec IGN (DC_LiDAR_HD_1-0.pdf) : plus un mur est
haut, plus il disparaît proprement ; un muret de 40 cm reste « sol » et se voit.

SOLUTION : repartir du NUAGE CLASSÉ (COPC LAZ) et réintroduire dans le modèle
les points bas non-sol (0,4-2,5 m au-dessus du sol), qui contiennent les murs.
Le CONCEPT (modèle terrain + structures archéo = « DFM », Digital Feature
Model) vient de Štular et al. 2021 (doi:10.3390/rs13091855) ; la SÉLECTION
automatique implémentée ici (tranche de hauteur dans les lacunes de la classe
sol) est une heuristique calibrée sur 2 sites du Var — la littérature fait
cette étape par reclassification (semi-)manuelle. Le maquis revient aussi
(mouchetis) : la discrimination finale est VISUELLE, en comparant les couches —
workflow archéo standard (Kokalj & Hesse : jamais une seule visualisation).

SORTIES (GeoTIFF EPSG:2154, à draper dans QGIS sur l'orthophoto) :
  <prefix>_lrm_mnt.tif   LRM du MNT sol pur (l'existant : terrassements, enclos bas)
  <prefix>_lrm_dfm.tif   LRM du DFM (murs debout VISIBLES, + mouchetis maquis)
  <prefix>_delta.tif     DFM − MNT en mètres (que ce qui a été réintroduit ;
                         seuiller à ~0,4-1 m dans QGIS pour marquer les candidats)

USAGE :
  python tools/dfm_ruines.py --center 5.8662,43.3758 --rayon 150 --out ruine1
  python tools/dfm_ruines.py --bbox 5.860,43.373,5.870,43.378 --out zone --cache D:\\laz

  --center lon,lat + --rayon M   ou   --bbox lon1,lat1,lon2,lat2 (WGS84)
  --res 0.5        résolution du raster (m)
  --hmin/--hmax    tranche de hauteur réintroduite (défaut 0,4-2,5 m)
  --classes        classes LAS réintroduites (défaut 1,3,4 ; 6 pour bâti rasé)
  --sigma          rayon gaussien du LRM en mètres (défaut 7,5)
  --cache          dossier de cache des COPC LAZ (~205 Mo/km² ! défaut ./laz_cache)

Volumétrie : 1 dalle COPC 1 km² ≈ 205 Mo. Outil de prospection CIBLÉE (quelques
km² autour d'un site), pas un pipeline de grandes cartes. Le MNT/LRM classique
de lidar2map reste le bon outil pour les structures basses à grande échelle.

Dépendances : laspy+lazrs, rasterio, scipy, numpy, pyproj (le venv lidar2map les a).
"""
import argparse
import json
import math
import ssl
import sys
import urllib.request
import warnings
from pathlib import Path

import numpy as np

# nanmean sur un voisinage entièrement vide pendant le comblement : attendu.
warnings.filterwarnings("ignore", message="Mean of empty slice")

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _CTX = ssl.create_default_context()

UA = "lidar2map-dfm/1.0"
WFS = "https://data.geopf.fr/wfs/ows"
TN_LAZ = "IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle"


def wfs_dalles_laz(bbox_l93):
    """{nom: url} des dalles COPC LAZ intersectant la bbox EPSG:2154."""
    x1, y1, x2, y2 = bbox_l93
    q = (f"{WFS}?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES={TN_LAZ}"
         f"&SRSNAME=EPSG:2154&BBOX={x1},{y1},{x2},{y2},EPSG:2154"
         f"&COUNT=500&OUTPUTFORMAT=application/json")
    req = urllib.request.Request(q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90, context=_CTX) as r:
        gj = json.loads(r.read().decode("utf-8", "replace"))
    out = {}
    for f in gj.get("features", []):
        p = f.get("properties", {})
        url, name = p.get("url"), p.get("name_download") or p.get("name")
        if url and name:
            out[name] = url
    return out


def download(url, dest):
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    print(f"  download {dest.name} ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(req, timeout=600, context=_CTX) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    tmp.replace(dest)
    return dest


def fill_nan(G, iters=80):
    """Comblement itératif par moyenne des 8 voisins (petites lacunes)."""
    G = G.copy()
    for _ in range(iters):
        bad = ~np.isfinite(G)
        if not bad.any():
            break
        Gp = np.pad(G, 1, constant_values=np.nan)
        Gp[~np.isfinite(Gp)] = np.nan
        with np.errstate(all="ignore"):
            nb = np.nanmean(np.stack(
                [Gp[:-2, 1:-1], Gp[2:, 1:-1], Gp[1:-1, :-2], Gp[1:-1, 2:],
                 Gp[:-2, :-2], Gp[:-2, 2:], Gp[2:, :-2], Gp[2:, 2:]]), axis=0)
        G[bad] = nb[bad]
    return G


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--center", help="lon,lat WGS84")
    ap.add_argument("--rayon", type=float, default=150, help="demi-fenêtre en m (avec --center)")
    ap.add_argument("--bbox", help="lon1,lat1,lon2,lat2 WGS84")
    ap.add_argument("--out", default="dfm", help="préfixe des sorties")
    ap.add_argument("--res", type=float, default=0.5)
    ap.add_argument("--hmin", type=float, default=0.4)
    ap.add_argument("--hmax", type=float, default=2.5)
    ap.add_argument("--classes", default="1,3,4",
                    help="classes LAS réintroduites (déf. 1,3,4)")
    ap.add_argument("--sigma", type=float, default=7.5, help="LRM gaussien (m)")
    ap.add_argument("--cache", default="laz_cache", help="cache des COPC (~205 Mo/km²)")
    a = ap.parse_args()

    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    if a.center:
        lon, lat = map(float, a.center.split(","))
        cx, cy = tr.transform(lon, lat)
        bbox = (cx - a.rayon, cy - a.rayon, cx + a.rayon, cy + a.rayon)
    elif a.bbox:
        lo1, la1, lo2, la2 = map(float, a.bbox.split(","))
        x1, y1 = tr.transform(lo1, la1)
        x2, y2 = tr.transform(lo2, la2)
        bbox = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    else:
        ap.error("--center ou --bbox requis")
    classes = tuple(int(c) for c in a.classes.split(","))

    print(f"bbox L93 : {tuple(round(v) for v in bbox)}")
    dalles = wfs_dalles_laz(bbox)
    if not dalles:
        print("aucune dalle LiDAR HD ici (zone pas encore volée ?)")
        return 1
    print(f"{len(dalles)} dalle(s) COPC ({len(dalles) * 205} Mo max, cache : {a.cache})")
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)

    import laspy
    xs = []; ys = []; zs = []; cs = []
    for name, url in sorted(dalles.items()):
        p = download(url, cache / name)
        print(f"  lecture {name} ...", flush=True)
        las = laspy.read(str(p))
        X = np.asarray(las.x); Y = np.asarray(las.y)
        m = (X >= bbox[0]) & (X <= bbox[2]) & (Y >= bbox[1]) & (Y <= bbox[3])
        xs.append(X[m]); ys.append(Y[m])
        zs.append(np.asarray(las.z)[m]); cs.append(np.asarray(las.classification)[m])
    xs = np.concatenate(xs); ys = np.concatenate(ys)
    zs = np.concatenate(zs); cs = np.concatenate(cs)
    print(f"{xs.size:,} points dans la bbox")
    if xs.size < 1000:
        print("trop peu de points"); return 1

    res = a.res
    x0, y1 = bbox[0], bbox[3]
    nx = max(1, int(math.ceil((bbox[2] - bbox[0]) / res)))
    ny = max(1, int(math.ceil((bbox[3] - bbox[1]) / res)))
    ci = np.clip(((xs - x0) / res).astype(np.int64), 0, nx - 1)
    ri = np.clip(((y1 - ys) / res).astype(np.int64), 0, ny - 1)

    def binmin(mask):
        g = np.full(ny * nx, np.inf)
        np.minimum.at(g, ri[mask] * nx + ci[mask], zs[mask])
        return g.reshape(ny, nx)

    print("MNT sol (classe 2) ...")
    sol_raw = binmin(cs == 2)
    mnt = fill_nan(sol_raw)

    print(f"DFM (classes {classes}, {a.hmin}-{a.hmax} m) ...")
    h = zs - mnt[ri, ci]
    low = np.isin(cs, classes) & (h >= a.hmin) & (h <= a.hmax)
    lowmin = binmin(low)
    dfm = sol_raw.copy()
    holes = ~np.isfinite(dfm)
    dfm[holes] = lowmin[holes]
    dfm = fill_nan(dfm)

    from scipy.ndimage import gaussian_filter
    import rasterio
    from rasterio.transform import from_origin
    transform = from_origin(x0, y1, res, res)
    sig = a.sigma / res

    def save(path, arr):
        with rasterio.open(path, "w", driver="GTiff", height=ny, width=nx,
                           count=1, dtype="float32",
                           crs=rasterio.CRS.from_epsg(2154), transform=transform,
                           nodata=-9999, compress="deflate", predictor=3,
                           tiled=True) as dst:
            dst.write(arr.astype(np.float32), 1)
        print(f"  -> {path}")

    save(f"{a.out}_lrm_mnt.tif", mnt - gaussian_filter(mnt, sig))
    save(f"{a.out}_lrm_dfm.tif", dfm - gaussian_filter(dfm, sig))
    save(f"{a.out}_delta.tif", dfm - mnt)
    print("\nDans QGIS : draper *_lrm_dfm.tif (gris, -0,5..+0,5) sur l'ortho ;")
    print("*_delta.tif seuillé à 0,4-1 m = candidats murs (mouchetis = maquis,")
    print("lignes/rectangles = structures). Comparer TOUJOURS avec *_lrm_mnt.tif.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
