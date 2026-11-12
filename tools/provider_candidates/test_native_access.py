"""Tests réseau réels et bornés des MNT officiels ; aucun provider activé."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import rasterio
from pyproj import Transformer

from probe_native_sources import fetch

OUT = Path(__file__).resolve().parents[2] / "cache/native-provider-validation"


def sk_sample():
    x, y = Transformer.from_crs(4326, 3046, always_xy=True).transform(17.072, 48.2)
    left, bottom = int(x) - 200, int(y) - 200
    bounds = (left, bottom, left + 400, bottom + 400)
    query = [("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"),
             ("coverageId", "el__EL.GridCoverage"), ("format", "image/tiff"),
             ("subset", f"E({left},{left + 400})"),
             ("subset", f"N({bottom},{bottom + 400})")]
    url = "https://inspirews.skgeodesy.sk/geoserver/el/ows?" + urlencode(query)
    info, payload = fetch(url, 4_000_000)
    print("HTTP", {key: info.get(key) for key in ("url", "status", "bytes_read", "error", "truncated")})
    if payload[:4] not in (b"II*\0", b"MM\0*", b"II+\0", b"MM\0+"):
        print(payload[:3000].decode("utf-8", errors="replace"))
        return
    path = OUT / "sk_wcs_bratislava.tif"
    path.write_bytes(payload)
    with rasterio.open(path) as src:
        a = src.read(1, masked=True)
        print("RASTER", {"crs": str(src.crs), "resolution": src.res, "bounds": list(src.bounds),
                         "shape": a.shape, "dtype": src.dtypes, "nodata": src.nodata,
                         "valid_pixels": int(a.count()), "min": float(a.min()), "max": float(a.max()),
                         "expected_bounds": bounds})


def wallonia_prefix():
    url = "https://geoservices.wallonie.be/geotraitement/spwdatadownload/results/a004e570-99d6-4fe5-b83d-49b774409278/RELIEF_WALLONIE_MNT_50CM_2021_2022_GEOTIFF_3812_PROV_BRABANT_WALLON.zip"
    info, compressed = fetch(url, 33_554_432)
    pos = 1_002_460
    header = struct.unpack_from("<4s5H3I2H", compressed, pos)
    name = compressed[pos+30:pos+30+header[-2]].decode("utf-8")
    if name != "RELIEF_WALLONIE_MNT_50CM_2021_2022.tif":
        raise ValueError("Archive modifiée : membre TIFF inattendu")
    base = pos + 30 + header[-2] + header[-1]
    partial = zlib.decompressobj(-15).decompress(compressed[base:], 67_108_864)
    path = OUT / "wallonia_native_tif_prefix.bin"
    path.write_bytes(partial)
    # Lire les deux tables BigTIFF de strips ; pas de dépendance à tifffile.
    if partial[:8] != b"II+\0\x08\0\0\0":
        raise ValueError("BigTIFF Little Endian attendu")
    ifd = struct.unpack_from("<Q", partial, 8)[0]
    count = struct.unpack_from("<Q", partial, ifd)[0]
    tags = {}
    for i in range(count):
        start = ifd + 8 + 20*i
        tag, typ, length, value = struct.unpack_from("<HHQQ", partial, start)
        if tag in (273, 279):
            fmt, size = {3: ("H", 2), 4: ("I", 4), 16: ("Q", 8)}[typ]
            offset = start + 12 if length * size <= 8 else value
            tags[tag] = struct.unpack_from("<" + fmt*length, partial, offset)
    complete = 0
    for offset, length in zip(tags[273], tags[279]):
        if offset + length > len(partial):
            break
        complete += 1
    with rasterio.open(path) as src:
        rows = complete * src.block_shapes[0][0]
        print("PREFIX", len(partial), "COMPLETE_ROWS", rows, "SHAPE", src.shape, "GRID", src.res)
        # Rechercher une petite fenêtre valide dans les strips complets.
        # On lit par bandes pour éviter l'allocation de tout le haut du MNT.
        for row in range(64, rows - 256, 128):
            band = src.read(1, window=((row, row + 256), (0, src.width)))
            valid_columns = (band != src.nodata).all(axis=0)
            rolling = np.convolve(valid_columns.astype(np.int32), np.ones(256, dtype=np.int32), mode="valid")
            candidates = np.where(rolling == 256)[0]
            if not len(candidates):
                continue
            col = int(candidates[len(candidates)//2])
            window = rasterio.windows.Window(col, row, 256, 256)
            a = src.read(1, window=window)
            profile = src.profile.copy()
            profile.update(width=256, height=256, transform=src.window_transform(window),
                           tiled=True, blockxsize=256, blockysize=256, compress="deflate", predictor=3)
            dest = OUT / "be_wallonia_native_crop.tif"
            with rasterio.open(dest, "w", **profile) as dst:
                dst.write(a, 1)
                dst.update_tags(source="SPW MNT 2021-2022", access="bounded sequential ZIP prefix",
                                source_url=url, interpolation="none", partial_archive="CRC global non vérifié")
            with rasterio.open(dest) as dst:
                assert np.array_equal(dst.read(1).view("uint32"), a.view("uint32"))
            result = {"source": info, "archive_member": name, "prefix_bytes": len(partial),
                      "complete_rows": rows, "window": [col, row, 256, 256],
                      "crs": str(src.crs), "resolution": src.res, "transform": list(src.window_transform(window)),
                      "native_bounds": list(rasterio.windows.bounds(window, src.transform)),
                      "native_dtype": src.dtypes[0], "native_nodata": src.nodata,
                      "min": float(a.min()), "max": float(a.max()),
                      "crop_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                      "crop_bitwise_identical": True, "archive_crc_checked": False}
            (OUT / "be_wallonia_native_crop.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print("CROP", {k: result[k] for k in ("window", "native_bounds", "min", "max", "crop_bitwise_identical")})
            return
    raise RuntimeError("Aucune fenêtre valide trouvée dans le préfixe borné")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=["sk_sample", "wallonia_prefix"])
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.task == "sk_sample":
        sk_sample()
    else:
        wallonia_prefix()
