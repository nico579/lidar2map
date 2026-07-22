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

# ── RMAP (CompeGPS/TwoNav) : structure binaire écrite à la main ──────────────
# Header : magic + 9×int32 (10, 7, 0, w, -h, 24, 1, 256, 256), offset map info
# (int64), int32 0, n_zooms, n_zooms×int64. Par zoom : w, -h, nx, ny puis
# nx×ny offsets int64 ; chaque tuile : int32 7, int32 len, blob image.
import struct
rmap = l2m.generer_rmap_depuis_mbtiles(mbt)
assert rmap is not None and rmap.exists(), "RMAP non genere"
data = rmap.read_bytes()
MAGIC = b"CompeGPSRasterImage"
assert data.startswith(MAGIC), "magic RMAP absent"
hdr = struct.unpack_from("<9i", data, len(MAGIC))
assert hdr[0] == 10 and hdr[1] == 7, f"version RMAP {hdr[:2]}"
assert hdr[7] == 256 and hdr[8] == 256, f"taille tuile {hdr[7:9]}"
off = len(MAGIC) + 9 * 4
map_off, = struct.unpack_from("<q", data, off)
_zero, n_zooms = struct.unpack_from("<2i", data, off + 8)
assert 0 < map_off < len(data), f"map_off {map_off}"
assert n_zooms == 3, f"n_zooms {n_zooms} (attendu 3 : z15-17)"
zoffs = struct.unpack_from(f"<{n_zooms}q", data, off + 16)
assert all(0 < z < len(data) for z in zoffs), "offsets zoom hors fichier"
# Bloc MAP info : int32 1, int32 longueur, texte de calibration ASCII
one, mlen = struct.unpack_from("<2i", data, map_off)
assert one == 1 and 0 < mlen < 1_000_000, (one, mlen)
map_txt = data[map_off + 8: map_off + 8 + mlen].decode("ascii")
assert map_txt.startswith("CompeGPS MAP File"), map_txt[:40]
assert "<Calibration>" in map_txt and "Datum=WGS 84" in map_txt
# Première tuile du premier zoom : offsets cohérents + blob image décodable
zw, zh, nx_, ny_ = struct.unpack_from("<4i", data, zoffs[0])
assert zw > 0 and zh < 0 and nx_ > 0 and ny_ > 0, (zw, zh, nx_, ny_)
t_off, = struct.unpack_from("<q", data, zoffs[0] + 16)
seven, tlen = struct.unpack_from("<2i", data, t_off)
assert seven == 7 and 0 < tlen < len(data), (seven, tlen)
timg = Image.open(io.BytesIO(data[t_off + 8: t_off + 8 + tlen]))
timg.verify()
print(f"RMAP OK ({n_zooms} zooms, map info {mlen} o)")

# ── SQLiteDB (cible OsmAnd) : schéma + conversion TMS→XYZ ─────────────────────
sdb = l2m.generer_sqlitedb_depuis_mbtiles(mbt)
assert sdb is not None and sdb.exists(), "SQLiteDB non genere"
con_s = sqlite3.connect(str(sdb))
n_s = con_s.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
zmin_s, zmax_s = con_s.execute("SELECT minzoom, maxzoom FROM info").fetchone()
assert n_s == n, f"{n_s} tuiles SQLiteDB vs {n} MBTiles"
assert (zmin_s, zmax_s) == (15, 17), (zmin_s, zmax_s)
# tilenumbering='simple' : sans lui OsmAnd suppose BigPlanet (z inversé 17-z)
# et n'affiche rien ; Locus ignore la colonne (bug remonté par un user OsmAnd).
tn = con_s.execute("SELECT tilenumbering FROM info").fetchone()[0]
assert tn == "simple", f"tilenumbering={tn!r} (OsmAnd exige != 'BigPlanet')"
# Chaque (x, y, z) XYZ doit pointer le même blob que (x, y_tms) dans le MBTiles
x_s, y_s, z_s, im_s = con_s.execute(
    "SELECT x, y, z, image FROM tiles LIMIT 1").fetchone()
con_m = sqlite3.connect(str(mbt))
y_tms = (1 << z_s) - 1 - y_s
orig = con_m.execute(
    "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
    (z_s, x_s, y_tms)).fetchone()
assert orig is not None and orig[0] == im_s, "blob XYZ != blob TMS source"
con_s.close(); con_m.close()
print(f"SQLITEDB OK ({n_s} tuiles, z{zmin_s}-{zmax_s})")

# ── Migration : un sqlitedb au schéma périmé (sans tilenumbering) est régénéré ──
# Simule un fichier d'AVANT le fix OsmAnd : table info sans la colonne
# tilenumbering. Sans ecraser, generer_sqlitedb doit le détecter et le
# régénérer (sinon l'utilisateur garde un overlay vide après mise à jour).
con_stale = sqlite3.connect(str(sdb))
con_stale.executescript("DROP TABLE info; CREATE TABLE info (minzoom INT, maxzoom INT);"
                        "INSERT INTO info VALUES (15, 17);")
con_stale.commit(); con_stale.close()
assert not l2m._sqlitedb_schema_courant(sdb), "schéma périmé non détecté"
sdb2 = l2m.generer_sqlitedb_depuis_mbtiles(mbt)   # ecraser=False
assert l2m._sqlitedb_schema_courant(sdb2), "sqlitedb périmé non régénéré"
con_mig = sqlite3.connect(str(sdb2))
tn_mig = con_mig.execute("SELECT tilenumbering FROM info").fetchone()[0]
con_mig.close()
assert tn_mig == "simple", tn_mig
print("MIGRATION SQLITEDB OK (schéma périmé régénéré sans --overwrite)")

# ── transparent-raster : GeoJSON (OSM/IGN) → tuiles PNG transparentes ────────
# Un mini GeoJSON (une ligne highway + un polygone building) rasterisé en
# .sqlitedb transparent, schéma OsmAnd (tilenumbering='simple'), tuiles vides
# absentes. Couvre le pivot commun OSM/IGN du format transparent-raster.
gj = tmp / "zone_osm.geojson"
gj.write_text('{"type":"FeatureCollection","features":['
              '{"type":"Feature","properties":{"_cle":"highway","highway":"track"},'
              '"geometry":{"type":"LineString","coordinates":'
              '[[6.040,43.326],[6.045,43.330],[6.050,43.333]]}},'
              '{"type":"Feature","properties":{"_cle":"building","building":"yes"},'
              '"geometry":{"type":"Polygon","coordinates":'
              '[[[6.046,43.328],[6.047,43.328],[6.047,43.329],[6.046,43.329],[6.046,43.328]]]}}'
              ']}', encoding="utf-8")
ov = l2m.rasteriser_geojson_transparent(gj, tmp / "zone_transparent.sqlitedb",
                                        15, 17, ecraser=True)
assert ov is not None and ov.exists(), "transparent-raster non généré"
con_o = sqlite3.connect(str(ov))
zmin_o, zmax_o, tn_o = con_o.execute(
    "SELECT minzoom, maxzoom, tilenumbering FROM info").fetchone()
assert (zmin_o, zmax_o) == (15, 17), (zmin_o, zmax_o)
assert tn_o == "simple", f"tilenumbering={tn_o!r} (OsmAnd exige != 'BigPlanet')"
n_o = con_o.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
assert n_o > 0, "aucune tuile transparente écrite"
# Chaque tuile stockée doit être un PNG RGBA non entièrement transparent
png0 = con_o.execute("SELECT image FROM tiles LIMIT 1").fetchone()[0]
im0 = Image.open(io.BytesIO(png0)).convert("RGBA")
assert im0.size == (256, 256) and im0.getbbox() is not None, "tuile vide stockée"
con_o.close()
print(f"TRANSPARENT-RASTER OK ({n_o} tuiles, z{zmin_o}-{zmax_o}, {tn_o})")
