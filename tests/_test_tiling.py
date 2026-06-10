# Test tuilage MBTiles : PNG grayscale pour source monobande, metadata bounds.
# Usage : python Tests/_test_tiling.py  (depuis n'importe quel cwd)
import os, sys, sqlite3, tempfile, importlib.util, io
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from PIL import Image

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
_APP = Path(__file__).resolve().parent.parent / "lidar2map.py"
spec = importlib.util.spec_from_file_location("l2m", str(_APP))
l2m = importlib.util.module_from_spec(spec)
sys.modules["l2m"] = l2m
spec.loader.exec_module(l2m)

tmp = Path(tempfile.mkdtemp())
# Petit raster uint8 monobande en Lambert93 (simule un SVF) — ~512×512 px
H = W = 512
yy, xx = np.mgrid[0:H, 0:W]
arr = ((np.sin(xx / 9.0) * np.sin(yy / 9.0) * 0.5 + 0.5) * 255).astype(np.uint8)
src = tmp / "zone_svf_ombrage.tif"
bbox = (900000.0, 6250000.0 - H * 0.5, 900000.0 + W * 0.5, 6250000.0)
prof = dict(driver="GTiff", dtype="uint8", count=1, height=H, width=W,
            crs="EPSG:2154", transform=from_origin(bbox[0], bbox[3], 0.5, 0.5))
with rasterio.open(str(src), "w", **prof) as ds:
    ds.write(arr, 1)

mbt = l2m.generer_mbtiles_lidar(src, tmp, "zone_svf_ombrage",
                                zoom_min=15, zoom_max=17,
                                format_tuiles="auto", bbox_l93=bbox,
                                tile_workers=2)
ok = True
con = sqlite3.connect(str(mbt))
n = con.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
fmt = dict(con.execute("SELECT name, value FROM metadata"))["format"]
blob = con.execute("SELECT tile_data FROM tiles LIMIT 1").fetchone()[0]
img = Image.open(io.BytesIO(blob))
print(f"tiles={n} format_meta={fmt} png_mode={img.mode} taille_blob={len(blob)}")
bounds = dict(con.execute("SELECT name, value FROM metadata")).get("bounds")
print(f"bounds={bounds}")
con.close()
assert n > 0, "0 tuiles"
assert fmt == "png", fmt
assert img.format == "PNG" and img.mode == "L", (img.format, img.mode)
# bounds doit contenir la zone (~5.6E, 43.9N en gros pour ce coin L93)
b = [float(v) for v in bounds.split(",")]
assert b[0] < b[2] and b[1] < b[3]
print("TILING OK")
