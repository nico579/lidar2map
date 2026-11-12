"""Validation réelle isolée : téléchargement du cœur, pixels, LRM et SVF.

Les candidats sont injectés uniquement dans CE processus de test. Rien n'est
ajouté au catalogue, aux préférences ou aux providers validés de l'utilisateur.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.parse import urlencode
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "cache/native-provider-validation"
sys.path.insert(0, str(ROOT))
os.environ.setdefault("LIDAR2MAP_BOOTSTRAP", "none")
os.environ["LIDAR2MAP_HOME"] = str(OUT / "state")
os.environ.setdefault("NUMBA_NUM_THREADS", "4")

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.merge import merge
from tools.provider_candidates import sk_ugkk as sk
from tools.provider_candidates.probe_native_sources import fetch
from tools.provider_candidates._native_zip import HTTPRangeFile
from _ombrages_pures import _lrm_array, _svf_numpy
import lidar2map as app
import coverage_map


def raster_info(path):
    with rasterio.open(path) as src:
        a = src.read(1, masked=True)
        return {"file": str(Path(path).relative_to(ROOT)), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                "shape": list(src.shape), "dtype": src.dtypes[0], "crs": str(src.crs),
                "resolution": list(src.res), "bounds": list(src.bounds), "nodata": src.nodata,
                "valid_pixels": int(a.count()), "min": float(a.min()) if a.count() else None,
                "max": float(a.max()) if a.count() else None}


def select(provider):
    app.PROVIDER = provider
    app.RESOLUTION_M = provider.RESOLUTION_M
    app.DALLE_KM = provider.DALLE_KM
    app.PX_PAR_DALLE = provider.PX_PAR_DALLE
    app.SEUIL_DALLE_VALIDE = provider.SEUIL_DALLE_VALIDE
    app.LIDAR_SUBDIR = f"lidar/{provider.COUNTRY}"


def shadings(label, cogs, provider, bounds, dem_path):
    select(provider)
    target = OUT / label / "shadings"
    target.mkdir(parents=True, exist_ok=True)
    outputs = app.generer_ombrages(cogs, target, choix=[], nom_zone=label,
                                  bbox_natif=bounds,
                                  instances=[("lrm", {"sigma": 10.0}),
                                             ("svf", {"dist": 15.0, "gamma": 1.0})])
    if len(outputs) != 2:
        raise AssertionError(f"Deux ombrages attendus, obtenu : {outputs}")
    result = []
    for path in outputs:
        info = raster_info(path)
        assert info["valid_pixels"] > 0 and info["min"] != info["max"], info
        assert info["resolution"] == [provider.RESOLUTION_M]*2, info
        result.append(info)
    with rasterio.open(dem_path) as src:
        a = src.read(1)
        res = src.res[0]
        lrm, mask = _lrm_array(a.copy(), src.nodata, 2.0/res)
        svf = _svf_numpy(a.copy(), int(15/res), n_directions=16, resolution=res, nodata=src.nodata)
        # Les statistiques évitent les bords des petits échantillons.
        halo = int(20/res)
        core = (slice(halo, -halo), slice(halo, -halo))
        assert np.isfinite(lrm[core]).all() and np.isfinite(svf[core]).all()
        stats = {"lrm_sigma2_std_m": float(lrm[core].std()),
                 "svf_min": float(svf[core].min()), "svf_max": float(svf[core].max())}
    print("SHADINGS_OK", label, stats, flush=True)
    return {"outputs": result, "raw_relief_stats": stats}


def slovakia_case(label, lon, lat):
    select(sk)
    x, y = Transformer.from_crs(4326, sk.CRS_NATIF, always_xy=True).transform(lon, lat)
    left, bottom = int(x)-200, int(y)-200
    bounds = (left, bottom, left+400, bottom+400)
    discovered = sk.discover_dalles(None, bounds, OUT / "index.json")
    folder = OUT / label
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for name, url in discovered.items():
        status = app.telecharger_dalle_directe(name, url, folder / "tiles", compresser=True)
        assert status in ("ok", "skip"), (name, status)
        path = app.chemin_dalle(folder / "tiles", name)
        sk.post_fetch(path)
        files.append(path)
        print("NATIVE_TILE_OK", name, path.stat().st_size, flush=True)
    readers = [rasterio.open(path) for path in files]
    try:
        mosaic, transform = merge(readers, bounds=bounds)
        profile = readers[0].profile.copy()
    finally:
        for src in readers:
            src.close()
    dem_path = folder / "native_crop.tif"
    profile.update(width=400, height=400, transform=transform, compress="deflate", predictor=3)
    with rasterio.open(dem_path, "w", **profile) as dst:
        dst.write(mosaic)
    # Extraction recoupée depuis le serveur : mêmes pixels Float32, bit pour bit.
    query = [("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"),
             ("coverageId", sk.COVERAGE), ("format", "image/tiff"),
             ("subset", f"E({left},{left+400})"), ("subset", f"N({bottom},{bottom+400})")]
    url = sk.WCS_URL + "?" + urlencode(query)
    info, payload = fetch(url, 4_000_000)
    assert info.get("status") == 200 and not info["truncated"]
    reference = folder / "overlap_reference.tif"
    reference.write_bytes(payload)
    with rasterio.open(reference) as src:
        assert src.transform == transform and src.shape == (400, 400)
        expected = src.read()
        assert np.array_equal(mosaic.view("uint32"), expected.view("uint32")), "Raccord/recompression altère les pixels"
    result = {"sample_center_wgs84": [lon, lat], "tiles": [raster_info(path) for path in files],
              "urls": discovered, "crop": raster_info(dem_path), "overlap_reference": info,
              "overlap_bitwise_identical": True, "core_download_success": True}
    result.update(shadings(label, files, sk, bounds, dem_path))
    return result


def original_sk_metadata():
    url = "https://opendata.skgeodesy.sk/static/INSPIRE/Elevation/DTM5_0_etrs89-tm34_h.zip"
    remote = HTTPRangeFile(url, OUT / "ranges")
    with zipfile.ZipFile(remote) as archive:
        tfw = archive.read("dtm5_0/dmr5_etrs89.tfw")
        xml = archive.read("dtm5_0/dmr5_etrs89.tif.xml")
    (OUT / "sk_original.tfw").write_bytes(tfw)
    (OUT / "sk_original.tif.xml").write_bytes(xml)
    values = list(map(float, tfw.decode().split()))
    assert values == [1, 0, 0, -1, 191148.5, 5497219.5]
    return {"url": url, "archive_bytes": remote.size, "world_file": values,
            "metadata_sha256": hashlib.sha256(xml).hexdigest(), "members_crc_checked": True,
            "http_records": remote.records, "native_grid_matches_WCS": True}


def main():
    before = coverage_map.load_providers()
    results = {"archaeological_ground_truth_tested": False,
               "slovakia_original_metadata": original_sk_metadata(), "samples": {}}
    for label, lon, lat in [("sk_bratislava", 17.072, 48.2), ("sk_banska_stiavnica", 18.907, 48.474)]:
        results["samples"][label] = slovakia_case(label, lon, lat)
    path = OUT / "be_wallonia_native_crop.tif"
    info = raster_info(path)
    provider = SimpleNamespace(COUNTRY="be", RESOLUTION_M=.5, DALLE_KM=1, PX_PAR_DALLE=2000,
                               SEUIL_DALLE_VALIDE=1024, CRS_NATIF="EPSG:3812")
    result = {"crop": info, "native_crop_bitwise_identical": True,
              "access": "Archive officielle : préfixe séquentiel borné (33 554 432 octets)",
              "automatic_provider_ready": False, "archive_crc_checked": False}
    result.update(shadings("be_wallonia", [path], provider, tuple(info["bounds"]), path))
    results["samples"]["be_wallonia"] = result
    after = coverage_map.load_providers()
    assert before == after, "Le catalogue actif a changé"
    results["active_catalogue_unchanged"] = True
    results["active_provider_count"] = len(before)
    target = ROOT / "docs/native-wallonie-slovaquie.results.json"
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("ALL_NATIVE_TESTS_PASS", target, flush=True)


if __name__ == "__main__":
    main()
