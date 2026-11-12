"""Étude isolée IGN LiDAR HD / Mapterhorn ; aucun provider n'est activé.

Les entrées réseau, métadonnées et résultats sont conservés dans un cache
séparé. Les fonctions de relief et le provider IGN existants sont lus tels quels.
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import urllib.request
from urllib.parse import parse_qs, urlencode, urlsplit

import mapbox_vector_tile
import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, shape
from PIL import Image
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import Window
from scipy.ndimage import distance_transform_edt

os.environ.setdefault("NUMBA_NUM_THREADS", "4")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from providers import fr_ign
from _ombrages_pures import _lrm_array, _svf_numpy
from tools.provider_candidates._mapterhorn import (
    COVERAGE_URL, HALF_WORLD, TILES_URL, tile_bounds,
)

BASE = ROOT / "cache" / "mapterhorn-comparison-ign"
UA = "lidar2map/1.0 (isolated IGN Mapterhorn comparison)"
NODATA = -9999.0
GRID_M = 0.5
CORE_M = 300
HALO_M = 50
L93 = Transformer.from_crs(4326, 2154, always_xy=True)
MERC = Transformer.from_crs(4326, 3857, always_xy=True)
SITES = [
    {"id": "var_ruine1", "label": "Var — Ruine1 (site du test existant)",
     "lon": 5.86628, "lat": 43.37579, "context": "relief et structures, secteur du test LAZ existant"},
    {"id": "mont_beuvray", "label": "Mont Beuvray", "lon": 4.0361, "lat": 46.9241,
     "context": "relief forestier"},
    {"id": "toulouse", "label": "Toulouse", "lon": 1.444, "lat": 43.604,
     "context": "contrôle en terrain peu accidenté"},
    {"id": "chambord", "label": "Secteur de Chambord", "lon": 1.516, "lat": 47.614,
     "context": "terrain peu accidenté, parc et forêt"},
]


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(path.name + ".part")
    staging.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    staging.replace(path)


def fetch(url, path, *, timeout=90):
    path = Path(path)
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(path.name + ".part")
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            start = time.monotonic()
            with urllib.request.urlopen(request, timeout=timeout) as response, staging.open("wb") as dst:
                headers = dict(response.headers)
                while block := response.read(1024 * 1024):
                    dst.write(block)
            staging.replace(path)
            save_json(path.with_name(path.name + ".http.json"), {
                "url": url, "fetched_utc": datetime.now(timezone.utc).isoformat(),
                "bytes": path.stat().st_size, "headers": headers,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "seconds": time.monotonic() - start,
            })
            return path
        except Exception:
            staging.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def xy_tile(lon, lat, zoom):
    mx, my = MERC.transform(lon, lat)
    step = 2 * HALF_WORLD / 2 ** zoom
    return math.floor((mx + HALF_WORLD) / step), math.floor((HALF_WORLD - my) / step)


def coverage_tile(x, y):
    path = BASE / "coverage" / f"14_{x}_{y}.mvt"
    fetch(COVERAGE_URL.format(z=14, x=x, y=y), path)
    return mapbox_vector_tile.decode(path.read_bytes(), default_options={"y_coord_down": True})["coverage"]


def point_coverage(lon, lat):
    x, y = xy_tile(lon, lat, 14)
    layer = coverage_tile(x, y)
    left, bottom, right, top = tile_bounds(14, x, y)
    mx, my = MERC.transform(lon, lat)
    extent = layer["extent"]
    point = Point((mx - left) / (right - left) * extent,
                  (top - my) / (top - bottom) * extent)
    matches = []
    for feature in layer["features"]:
        geom = shape(feature["geometry"])
        if geom.covers(point):
            matches.append({**feature["properties"],
                            "boundary_distance_ground_m_approx": geom.boundary.distance(point)
                            * (right - left) / extent * math.cos(math.radians(lat))})
    return matches


def wfs_metadata(site):
    x, y = L93.transform(site["lon"], site["lat"])
    url = "https://data.geopf.fr/wfs/ows?" + urlencode({
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": "IGNF_LIDAR-HD_METADONNEE:metadata", "SRSNAME": "EPSG:2154",
        "BBOX": f"{x-1},{y-1},{x+1},{y+1},EPSG:2154", "COUNT": 20,
        "OUTPUTFORMAT": "application/json", "SORTBY": "coordonnees_nw ASC",
    })
    path = BASE / site["id"] / "ign_metadata.geojson"
    fetch(url, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"matched": data.get("numberMatched"), "properties": [f["properties"] for f in data["features"]]}


def probe(site):
    result = dict(site)
    try:
        result["mapterhorn_coverage_at_center"] = point_coverage(site["lon"], site["lat"])
        result["ign_metadata"] = wfs_metadata(site)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return result


def prepare_native(site):
    properties = site["ign_metadata"]["properties"]
    if len(properties) != 1 or not properties[0].get("url_mnt"):
        raise ValueError("Une seule dalle IGN avec URL MNT est requise pour ce site.")
    props = properties[0]
    easting, northing = map(int, props["coordonnees_nw"].split("-"))
    name = fr_ign.dalle_filename(easting, northing - 1)
    provider_query = parse_qs(urlsplit(fr_ign.dalle_url(easting, northing - 1)).query)
    metadata_query = parse_qs(urlsplit(props["url_mnt"]).query)
    for key in ("BBOX", "WIDTH", "HEIGHT", "LAYERS", "CRS", "FILENAME"):
        if provider_query[key] != metadata_query[key]:
            raise ValueError(f"L'URL officielle diffère du provider IGN existant : {key}.")
    path = BASE / site["id"] / "inputs" / name
    fetch(props["url_mnt"], path)
    with rasterio.open(path) as src:
        # Le WMS restitue parfois un WKT « EPSG:2154 » sans autorité EPSG
        # reconnue. Vérifier les paramètres, conserver le fichier reçu tel quel,
        # et employer le CRS demandé par le provider pour la grille de travail.
        projection = src.crs.to_dict() if src.crs else {}
        lambert93 = (projection.get("proj") == "lcc"
                     and all(abs(float(projection.get(key, 0)) - expected) < 1e-8
                             for key, expected in (("lat_0", 46.5), ("lon_0", 3), ("lat_1", 49),
                                                   ("lat_2", 44), ("x_0", 700000), ("y_0", 6600000))))
        if not lambert93 or src.count != 1 or src.res != (GRID_M, GRID_M):
            raise ValueError("Grille IGN inattendue.")
        if src.shape != (2000, 2000):
            raise ValueError("Dalle IGN de 1 km attendue.")
        x, y = L93.transform(site["lon"], site["lat"])
        center_row, center_col = src.index(x, y)
        total_px = int((CORE_M + 2 * HALO_M) / GRID_M)
        window = Window(center_col - total_px // 2, center_row - total_px // 2, total_px, total_px)
        dem = src.read(1, window=window, boundless=True, fill_value=NODATA).astype(np.float32)
        dem[~np.isfinite(dem) | (dem == src.nodata)] = NODATA
        full = src.read(1).astype(np.float32)
        full[~np.isfinite(full) | (full == src.nodata)] = NODATA
        metadata = {
            "path": str(path.relative_to(ROOT)), "url": props["url_mnt"],
            "shape": list(src.shape), "resolution_m": list(src.res),
            "crs_reported": str(src.crs), "crs_authority_reported": src.crs.to_epsg(),
            "working_crs": "EPSG:2154 (requête IGN et paramètres Lambert-93 vérifiés)",
            "bounds": list(src.bounds),
            "transform": list(src.transform)[:6], "tags": src.tags(), "nodata": src.nodata,
            "date_acquisition_debut": props.get("date_debut_acquisition"),
            "date_acquisition_fin": props.get("date_fin_acquisition"),
            "date_edition": props.get("date_edition"), "classement": props.get("procede_classement"),
            "working_window": [window.col_off, window.row_off, window.width, window.height],
            "working_bounds": list(rasterio.windows.bounds(window, src.transform)),
        }
        return dem, src.window_transform(window), full, src.transform, metadata


def map_mosaic(target_transform, target_shape, zoom):
    height, width = target_shape
    bounds = rasterio.transform.array_bounds(height, width, target_transform)
    left, bottom, right, top = transform_bounds(2154, 3857, *bounds, densify_pts=21)
    step = 2 * HALF_WORLD / 2 ** zoom
    tx0, tx1 = math.floor((left + HALF_WORLD) / step), math.ceil((right + HALF_WORLD) / step)
    ty0, ty1 = math.floor((HALF_WORLD - top) / step), math.ceil((HALF_WORLD - bottom) / step)
    jobs = [(x, y) for y in range(ty0, ty1) for x in range(tx0, tx1)]

    def one(job):
        x, y = job
        url = TILES_URL.format(z=zoom, x=x, y=y)
        path = BASE / "mapterhorn_tiles" / f"{zoom}_{x}_{y}.webp"
        fetch(url, path)
        with Image.open(path) as image:
            if image.format != "WEBP" or image.mode != "RGB" or image.size != (512, 512):
                raise ValueError(f"WebP Terrarium inattendu : {path}")
            rgb = np.asarray(image, dtype=np.float32)
        dem = rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768
        return x, y, dem, {"z": zoom, "x": x, "y": y, "url": url,
                           "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size}

    mosaic = np.full(((ty1 - ty0) * 512, (tx1 - tx0) * 512), NODATA, np.float32)
    inputs = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for x, y, dem, meta in pool.map(one, jobs):
            r, c = (y - ty0) * 512, (x - tx0) * 512
            mosaic[r:r+512, c:c+512] = dem
            inputs.append(meta)
    b0 = tile_bounds(zoom, tx0, ty0)
    b1 = tile_bounds(zoom, tx1 - 1, ty1 - 1)
    transform = from_bounds(b0[0], b1[1], b1[2], b0[3], mosaic.shape[1], mosaic.shape[0])
    return mosaic, transform, inputs


def fine_coverage(target_transform, target_shape):
    height, width = target_shape
    bounds = rasterio.transform.array_bounds(height, width, target_transform)
    left, bottom, right, top = transform_bounds(2154, 3857, *bounds, densify_pts=21)
    step = 2 * HALF_WORLD / 2 ** 14
    tx0, tx1 = math.floor((left + HALF_WORLD) / step), math.ceil((right + HALF_WORLD) / step)
    ty0, ty1 = math.floor((HALF_WORLD - top) / step), math.ceil((HALF_WORLD - bottom) / step)
    to_l93 = Transformer.from_crs(3857, 2154, always_xy=True)
    from shapely.ops import transform as geom_transform
    shapes = []
    sources = set()
    for x in range(tx0, tx1):
        for y in range(ty0, ty1):
            layer = coverage_tile(x, y)
            extent = layer["extent"]
            bx0, by0, bx1, by1 = tile_bounds(14, x, y)

            def projected(u, v, z=None):
                return to_l93.transform(bx0 + np.asarray(u) / extent * (bx1 - bx0),
                                        by1 - np.asarray(v) / extent * (by1 - by0))

            for feature in layer["features"]:
                source = feature["properties"].get("source", "")
                if source.startswith("frhd2154"):
                    geom = geom_transform(projected, shape(feature["geometry"]))
                    shapes.append((geom, 1))
                    sources.add(source)
    mask = rasterize(shapes, out_shape=target_shape, transform=target_transform, fill=0, dtype="uint8") if shapes else np.zeros(target_shape, np.uint8)
    return mask.astype(bool), sorted(sources)


def warp(dem, src_transform, src_crs, dst_transform, dst_crs, dst_shape):
    result = np.full(dst_shape, NODATA, np.float32)
    reproject(dem, result, src_transform=src_transform, src_crs=src_crs,
              dst_transform=dst_transform, dst_crs=dst_crs, src_nodata=NODATA,
              dst_nodata=NODATA, resampling=Resampling.bilinear, num_threads=2)
    return result


def comparison_stats(reference, candidate, mask):
    a = reference[mask].astype(np.float64)
    b = candidate[mask].astype(np.float64)
    if len(a) == 0 or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("Mesures vides ou non finies.")
    delta = b - a
    std_a, std_b = a.std(), b.std()
    corr = float(np.corrcoef(a, b)[0, 1]) if std_a > 1e-10 and std_b > 1e-10 else None
    gain = float(np.dot(a - a.mean(), b - b.mean()) / np.dot(a - a.mean(), a - a.mean())) if std_a > 1e-10 else None
    return {
        "pixels": int(len(a)), "bias_median": float(np.median(delta)),
        "rmse": float(np.sqrt(np.mean(delta**2))),
        "rmse_after_median_bias_removal": float(np.sqrt(np.mean((delta - np.median(delta))**2))),
        "abs_error_p50": float(np.percentile(np.abs(delta), 50)),
        "abs_error_p95": float(np.percentile(np.abs(delta), 95)),
        "abs_error_p99": float(np.percentile(np.abs(delta), 99)),
        "abs_error_max": float(np.max(np.abs(delta))),
        "correlation": corr, "reference_std": float(std_a), "candidate_std": float(std_b),
        "amplitude_ratio_std": float(std_b / std_a) if std_a > 1e-10 else None,
        "regression_gain": gain,
        "fraction_abs_error_over_5cm": float(np.mean(np.abs(delta) > 0.05)),
        "fraction_abs_error_over_10cm": float(np.mean(np.abs(delta) > 0.1)),
    }


def alignment_diagnostic(reference, candidate, mask):
    # Diagnostic seulement : les résultats principaux conservent le géoréférencement livré.
    rows, cols = np.nonzero(mask)
    step = max(1, len(rows) // 20000)
    rows, cols = rows[::step], cols[::step]
    from scipy.ndimage import map_coordinates
    a = reference[rows, cols].astype(np.float64)
    scores = []
    for dy_m in (-0.5, -0.25, 0.0, 0.25, 0.5):
        for dx_m in (-0.5, -0.25, 0.0, 0.25, 0.5):
            b = map_coordinates(candidate, [rows - dy_m / GRID_M, cols - dx_m / GRID_M], order=1).astype(np.float64)
            d = b - a
            scores.append({"shift_east_m": dx_m, "shift_south_m": dy_m,
                           "lrm_5m_rmse_bias_removed_m": float(np.sqrt(np.mean((d - np.median(d))**2)))})
    return {"meaning": "Translation appliquée à Mapterhorn pour le diagnostic, jamais aux mesures principales.",
            "best_in_5x5_grid": min(scores, key=lambda s: s["lrm_5m_rmse_bias_removed_m"]), "scores": scores}


def save_raster(path, array, transform, **tags):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.where(np.isfinite(array), array, NODATA).astype(np.float32)
    with rasterio.open(path, "w", driver="GTiff", count=1, width=data.shape[1], height=data.shape[0],
                       dtype="float32", crs="EPSG:2154", transform=transform, nodata=NODATA,
                       tiled=True, compress="deflate", predictor=3) as dst:
        dst.write(data, 1)
        dst.update_tags(**tags)


def make_figure(site, native, candidate, control, lrm_native, lrm_candidate,
                svf_native, svf_candidate, mask, stats, zoom):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    margin = int(HALO_M / GRID_M)
    core = np.s_[margin:-margin, margin:-margin]
    ref, other = lrm_native[core], lrm_candidate[core]
    valid = mask[core]
    ref = np.where(valid, ref, np.nan)
    other = np.where(valid, other, np.nan)
    hdiff = np.where(valid, (candidate - native)[core], np.nan)
    ldiff = other - ref
    vlim = max(0.1, float(np.nanpercentile(np.abs(ref), 98)))
    dlim = max(0.03, float(np.nanpercentile(np.abs(ldiff), 98)))
    hlim = max(0.03, float(np.nanpercentile(np.abs(hdiff), 98)))
    sv_min = float(np.percentile(svf_native[mask], 2))
    sv_max = float(np.percentile(svf_native[mask], 98))
    fig, axes = plt.subplots(2, 3, figsize=(14, 9), constrained_layout=True)
    panels = [
        (ref, "IGN — LRM σ = 10 m", "RdBu_r", -vlim, vlim, "m"),
        (other, f"Mapterhorn z{zoom} — même échelle LRM", "RdBu_r", -vlim, vlim, "m"),
        (ldiff, "Écart LRM : Mapterhorn − IGN", "RdBu_r", -dlim, dlim, "m"),
        (np.where(valid, svf_native[core], np.nan), "IGN — SVF, rayon 15 m", "gray", sv_min, sv_max, "sans unité"),
        (np.where(valid, svf_candidate[core], np.nan), "Mapterhorn — même échelle SVF", "gray", sv_min, sv_max, "sans unité"),
        (hdiff, "Écart d’altitude : Mapterhorn − IGN", "RdBu_r", -hlim, hlim, "m"),
    ]
    for ax, (array, title, cmap, vmin, vmax, units) in zip(axes.flat, panels):
        im = ax.imshow(array, cmap=cmap, vmin=vmin, vmax=vmax, extent=(-150, 150, -150, 150), interpolation="nearest")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Est relatif (m)")
        ax.set_ylabel("Nord relatif (m)")
        fig.colorbar(im, ax=ax, shrink=0.75, label=units)
    fig.suptitle(f"{site['label']} · grille commune 0,5 m · {stats['height']['pixels']:,} pixels comparés\n"
                 f"RMSE altitude {stats['height']['rmse']:.3f} m · corrélation LRM {stats['lrm_sigma_10m']['correlation']:.4f}", fontsize=14)
    path = BASE / site["id"] / f"comparison_z{zoom}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return str(path.relative_to(ROOT))


def compare_site(site, zooms):
    print(f"\n{site['id']}: lecture IGN officiel", flush=True)
    native, target_transform, full_native, full_transform, native_meta = prepare_native(site)
    fine, sources = fine_coverage(target_transform, native.shape)
    base_mask = np.zeros(native.shape, bool)
    margin = int(HALO_M / GRID_M)
    base_mask[margin:-margin, margin:-margin] = True
    # Le témoin d'identité détecte un changement accidentel de grille ou de fenêtre.
    identity = warp(full_native, full_transform, 2154, target_transform, 2154, native.shape)
    identity_mask = (native != NODATA) & base_mask
    if not np.array_equal(identity[identity_mask], native[identity_mask]):
        raise AssertionError("Le témoin d'identité doit conserver exactement les pixels IGN.")
    results = []
    for zoom in zooms:
        print(f"{site['id']}: téléchargement/assemblage Mapterhorn z{zoom}", flush=True)
        mosaic, mosaic_transform, tiles = map_mosaic(target_transform, native.shape, zoom)
        candidate = warp(mosaic, mosaic_transform, 3857, target_transform, 2154, native.shape)
        valid = (native != NODATA) & (candidate != NODATA) & fine
        safe = distance_transform_edt(valid) > 40 / GRID_M
        mask = base_mask & safe
        if mask.sum() < 50000:
            raise ValueError("Moins de 50 000 pixels avec couverture LiDAR HD commune et halo sûr.")
        # Un témoin simulé isole reprojection bilinéaire + arrondi, sans changer les données livrées.
        merc_control = warp(full_native, full_transform, 2154, mosaic_transform, 3857, mosaic.shape)
        quantum = 1 / 2 ** (zoom - 11)
        control_valid = merc_control != NODATA
        merc_control[control_valid] = np.round(merc_control[control_valid] / quantum) * quantum
        control = warp(merc_control, mosaic_transform, 3857, target_transform, 2154, native.shape)
        mask &= distance_transform_edt(control != NODATA) > 40 / GRID_M
        record = {
            "site": {k: v for k, v in site.items() if k != "ign_metadata"}, "zoom": zoom,
            "grid_m": GRID_M, "core_side_m": CORE_M, "input_halo_m": HALO_M,
            "exclusion_from_nodata_or_coverage_edge_m": 40,
            "native": native_meta, "mapterhorn_sources_declared": sources,
            "coverage_mask_note": "MVT z14 généralisé ; sources superposées, priorité fine déduite du pipeline, pas provenance exacte pixel par pixel.",
            "mapterhorn_input_tiles": tiles,
            "mercator_pixel_m": float(mosaic_transform.a),
            "approx_ground_pixel_m": float(mosaic_transform.a * math.cos(math.radians(site['lat']))),
            "vertical_rounding_step_m_documented": quantum,
            "compared_fraction_of_core": float(mask.sum() / base_mask.sum()),
            "same_acquisition_confirmed": False,
            "epoch_note": "Métadonnées d'acquisition IGN enregistrées ; la campagne de chaque tuile RGB Mapterhorn n'est pas exposée.",
            "identity_control_max_abs_difference_m": 0.0,
            "height": comparison_stats(native, candidate, mask),
            "simulated_reprojection_quantization_control_height": comparison_stats(native, control, mask),
        }
        native_lrms, candidate_lrms, control_lrms = {}, {}, {}
        for sigma_m in (2, 5, 10):
            a, _ = _lrm_array(native, NODATA, sigma_m / GRID_M)
            b, _ = _lrm_array(candidate, NODATA, sigma_m / GRID_M)
            c, _ = _lrm_array(control, NODATA, sigma_m / GRID_M)
            record[f"lrm_sigma_{sigma_m}m"] = comparison_stats(a, b, mask)
            record[f"simulated_control_lrm_sigma_{sigma_m}m"] = comparison_stats(a, c, mask)
            native_lrms[sigma_m], candidate_lrms[sigma_m], control_lrms[sigma_m] = a, b, c
        print(f"{site['id']}: calculs SVF identiques (15 m / 16 directions)", flush=True)
        svf_native = _svf_numpy(native, int(15 / GRID_M), n_directions=16, resolution=GRID_M, nodata=NODATA)
        svf_candidate = _svf_numpy(candidate, int(15 / GRID_M), n_directions=16, resolution=GRID_M, nodata=NODATA)
        record["svf_radius_15m"] = comparison_stats(svf_native, svf_candidate, mask)
        record["svf_note"] = "Valeurs brutes sans stretch ni gamma ; erreurs sans unité, seuils en cm non applicables."
        for k in ("bias_median", "rmse_after_median_bias_removal", "abs_error_p50", "abs_error_p95", "abs_error_p99",
                  "fraction_abs_error_over_5cm", "fraction_abs_error_over_10cm"):
            if k.startswith("fraction"):
                record["svf_radius_15m"].pop(k, None)
        record["alignment_diagnostic"] = alignment_diagnostic(native_lrms[5], candidate_lrms[5], mask)
        out = BASE / site["id"] / f"z{zoom}"
        for label, array in (("ign_mnt", native), ("mapterhorn_mnt", candidate),
                             ("simulated_control_mnt", control), ("height_difference", candidate - native),
                             ("ign_lrm_10m", native_lrms[10]), ("mapterhorn_lrm_10m", candidate_lrms[10]),
                             ("ign_svf_15m", svf_native), ("mapterhorn_svf_15m", svf_candidate),
                             ("comparison_mask", mask.astype(np.float32))):
            save_raster(out / f"{label}.tif", np.where(mask, array, np.nan), target_transform,
                        benchmark="IGN MNT LiDAR HD vs Mapterhorn", source=label, zoom=str(zoom))
        record["figure"] = make_figure(site, native, candidate, control, native_lrms[10],
                                       candidate_lrms[10], svf_native, svf_candidate, mask, record, zoom)
        save_json(out / "results.json", record)
        print(f"{site['id']} z{zoom}: RMSE hauteur {record['height']['rmse']:.4f} m, "
              f"LRM corr {record['lrm_sigma_10m']['correlation']:.5f}, "
              f"LRM gain {record['lrm_sigma_10m']['regression_gain']:.5f}", flush=True)
        results.append(record)
    return results


def publish_report():
    """Exporte les résultats déjà calculés ; ne relance aucun téléchargement."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ordered_ids = ["var_ruine1", "toulouse", "chambord"]
    records = []
    for site_id in ordered_ids:
        for zoom in (17, 16):
            path = BASE / site_id / f"z{zoom}" / "results.json"
            item = json.loads(path.read_text(encoding="utf-8"))
            input_shapes = set()
            arrays = {}
            transforms = set()
            for kind in ("ign_mnt", "mapterhorn_mnt", "height_difference", "comparison_mask",
                         "ign_lrm_10m", "mapterhorn_lrm_10m", "ign_svf_15m", "mapterhorn_svf_15m"):
                with rasterio.open(path.parent / f"{kind}.tif") as src:
                    if src.crs.to_epsg() != 2154 or src.res != (GRID_M, GRID_M):
                        raise AssertionError("CRS/résolution d'un résultat exporté incorrects.")
                    input_shapes.add(src.shape)
                    transforms.add(tuple(src.transform))
                    arrays[kind] = src.read(1)
            if len(input_shapes) != 1 or len(transforms) != 1:
                raise AssertionError("Les GeoTIFF de comparaison doivent partager la même grille.")
            mask = arrays["comparison_mask"] == 1
            if int(mask.sum()) != item["height"]["pixels"]:
                raise AssertionError("Le nombre de pixels exportés diffère du résultat.")
            recomputed = comparison_stats(arrays["ign_mnt"], arrays["mapterhorn_mnt"], mask)
            if abs(recomputed["rmse"] - item["height"]["rmse"]) > 1e-9:
                raise AssertionError("La RMSE relue dans les GeoTIFF diffère du JSON.")
            if not np.array_equal((arrays["mapterhorn_mnt"] - arrays["ign_mnt"])[mask],
                                  arrays["height_difference"][mask]):
                raise AssertionError("L'image des différences n'est pas égale à Mapterhorn − IGN.")
            item["height"]["abs_error_max"] = recomputed["abs_error_max"]
            item["verification_exported_rasters"] = "Grilles identiques, effectifs et RMSE relus, différence pixel par pixel exacte."
            records.append(item)

    destination = ROOT / "docs" / "mapterhorn-ign-comparaison"
    destination.mkdir(parents=True, exist_ok=True)
    for item in records:
        label = f"{item['site']['id']}_z{item['zoom']}.png"
        shutil.copyfile(ROOT / item["figure"], destination / label)
        item["figure_exported"] = label
    csv_fields = ["site", "zoom", "pixels", "rmse_altitude_cm", "p95_abs_altitude_cm", "max_abs_altitude_m",
                  "correlation_lrm_10m", "amplitude_lrm_2m_ratio_std", "correlation_lrm_2m",
                  "rmse_svf_15m", "amplitude_svf_ratio_std", "rmse_simulated_control_altitude_cm"]
    with (destination / "mesures.csv").open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=csv_fields)
        writer.writeheader()
        for item in records:
            writer.writerow({
                "site": item["site"]["id"], "zoom": item["zoom"], "pixels": item["height"]["pixels"],
                "rmse_altitude_cm": item["height"]["rmse"] * 100,
                "p95_abs_altitude_cm": item["height"]["abs_error_p95"] * 100,
                "max_abs_altitude_m": item["height"]["abs_error_max"],
                "correlation_lrm_10m": item["lrm_sigma_10m"]["correlation"],
                "amplitude_lrm_2m_ratio_std": item["lrm_sigma_2m"]["amplitude_ratio_std"],
                "correlation_lrm_2m": item["lrm_sigma_2m"]["correlation"],
                "rmse_svf_15m": item["svf_radius_15m"]["rmse"],
                "amplitude_svf_ratio_std": item["svf_radius_15m"]["amplitude_ratio_std"],
                "rmse_simulated_control_altitude_cm": item["simulated_reprojection_quantization_control_height"]["rmse"] * 100,
            })
    inputs = []
    for path in sorted(BASE.rglob("*.http.json")):
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["sidecar_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
        inputs.append(metadata)
    source_paths = [ROOT / "providers" / "fr_ign.py", ROOT / "_ombrages_pures.py", Path(__file__)]
    save_json(destination / "resultats.json", {
        "study_utc": datetime.now(timezone.utc).isoformat(), "results": records,
        "http_inputs": inputs, "script_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"):
                                                   hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
        "excluded": [{"site": "mont_beuvray", "reason": "Index IGN : 0 dalle MNT HD ; Mapterhorn : RGE ALTI, aucune source frhd2154 au centre."}],
        "versions": {"python": sys.version, "numpy": np.__version__, "rasterio": rasterio.__version__},
    })

    names = ["Var — Ruine1", "Toulouse", "Chambord"]
    positions = np.arange(3)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    for zoom, offset, color in ((17, -0.19, "#287aa8"), (16, 0.19, "#df8b34")):
        selected = [next(x for x in records if x["site"]["id"] == sid and x["zoom"] == zoom) for sid in ordered_ids]
        heights = [x["height"]["rmse"] * 100 for x in selected]
        amplitudes = [x["lrm_sigma_2m"]["amplitude_ratio_std"] * 100 for x in selected]
        for ax, values, suffix in ((axes[0], heights, ""), (axes[1], amplitudes, "%")):
            bars = ax.bar(positions + offset, values, width=0.36, color=color, label=f"Mapterhorn z{zoom}")
            ax.bar_label(bars, labels=[f"{v:.1f}{suffix}" for v in values], padding=3)
    axes[0].set_title("Écart d’altitude avec l’IGN")
    axes[0].set_ylabel("RMSE (cm), sur les pixels comparables")
    axes[0].set_ylim(0, 5.2)
    axes[1].set_title("Variations fines du LRM : σ = 2 m")
    axes[1].set_ylabel("Écart-type relatif ; IGN = 100 %")
    axes[1].axhline(100, color="gray", linestyle="--", label="IGN natif")
    axes[1].set_ylim(0, 110)
    for ax in axes:
        ax.set_xticks(positions, names)
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    axes[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    fig.suptitle("IGN LiDAR HD / Mapterhorn — mêmes zones, grille Lambert-93 à 0,5 m", fontsize=13)
    fig.savefig(destination / "synthese.png", dpi=180)
    fig.savefig(destination / "synthese.svg")
    plt.close(fig)

    # Profil fixe, centré sur le point du test Ruine1, sans sélectionner un pic.
    fig, ax = plt.subplots(figsize=(11, 4), constrained_layout=True)
    for name, color, style, zoom in (("IGN natif", "black", "-", 17),
                                     ("Mapterhorn z17", "#287aa8", "-", 17),
                                     ("Mapterhorn z16", "#df8b34", "--", 16)):
        kind = "ign_mnt" if name == "IGN natif" else "mapterhorn_mnt"
        with rasterio.open(BASE / "var_ruine1" / f"z{zoom}" / f"{kind}.tif") as src:
            dem = src.read(1)
        lrm, _ = _lrm_array(dem, NODATA, 2 / GRID_M)
        row, col = dem.shape[0] // 2, dem.shape[1] // 2
        radius_px = int(40 / GRID_M)
        xs = np.arange(-radius_px, radius_px + 1) * GRID_M
        values = lrm[row, col-radius_px:col+radius_px+1]
        ax.plot(xs, values * 100, color=color, linestyle=style, linewidth=1.2, label=name)
    ax.set_title("Ruine1 — profil Est–Ouest de 80 m, LRM σ = 2 m")
    ax.set_xlabel("Distance relative au centre de la grille (m)")
    ax.set_ylabel("Relief résiduel LRM (cm)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(destination / "profil_ruine1.png", dpi=180)
    fig.savefig(destination / "profil_ruine1.svg")
    plt.close(fig)
    print(f"Résultats exportés et vérifiés : {destination}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--site", choices=[s["id"] for s in SITES])
    parser.add_argument("--zooms", nargs="+", type=int, default=[17, 16], choices=[16, 17])
    args = parser.parse_args()
    if args.report:
        publish_report()
    elif args.probe:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(probe, SITES))
        save_json(BASE / "probes.json", results)
    elif args.compare:
        probes = json.loads((BASE / "probes.json").read_text(encoding="utf-8"))
        results = []
        excluded = []
        for site in probes:
            if args.site and site["id"] != args.site:
                continue
            hd = any(s.get("source", "").startswith("frhd2154")
                     for s in site.get("mapterhorn_coverage_at_center", []))
            if not hd or not site.get("ign_metadata", {}).get("properties"):
                excluded.append({"site": site["id"], "reason": "Absence de couverture MNT IGN HD commune dans les index interrogés."})
                print(f"{site['id']}: exclu, pas de couverture IGN HD commune", flush=True)
                continue
            results.extend(compare_site(site, args.zooms))
        save_json(BASE / ("comparison_" + (args.site or "all") + ".json"), {
            "created_utc": datetime.now(timezone.utc).isoformat(), "results": results, "excluded": excluded,
            "method": "Mêmes pixels IGN Lambert-93 à 0,5 m ; Mapterhorn mosaïqué avant une unique reprojection bilinéaire ; LRM/SVF bruts du projet.",
        })
    else:
        parser.error("Utiliser --probe ou --compare.")


if __name__ == "__main__":
    main()
