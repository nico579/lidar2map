"""Rasterisation transactionnelle d'un GeoJSON en overlay SQLite OsmAnd.

Le rendu reste autonome et ne dépend pas du module principal. Les coutures
applicatives sont fournies par la façade ``lidar2map.py`` à chaque appel afin
de préserver les monkeypatches historiques et l'événement d'arrêt partagé.
"""

from __future__ import annotations

import gzip
import io
import json
import math
import os
import sqlite3
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _DependancesRasterGeojson:
    """Services et valeurs relus par la façade avant chaque rasterisation."""

    chemin_part: Callable[[Path], Path]
    nettoyer_sqlite_part: Callable[[Path], None]
    valider_sqlite_part: Callable[[Path, Mapping[str, int]], None]
    stop_event: Any
    deg_to_tile: Callable[..., tuple[int, int]]
    overlay_style: Mapping[str, Any]
    overlay_defaut: Any
    overlay_tile_warn: int
    overlay_style_key: Callable[..., Any]
    overlay_sequences: Callable[..., Any]
    clip_polygone_rect: Callable[..., Any]
    seg_inter_box: Callable[..., bool]


def rasteriser_geojson_transparent(
    geojson_path,
    sqlitedb_out,
    zoom_min,
    zoom_max,
    ecraser=False,
    supersample=2,
    bbox_wgs84=None,
    *,
    dependances: _DependancesRasterGeojson,
):
    """Rend un GeoJSON en tuiles PNG transparentes dans un SQLite OsmAnd.

    Le schéma RMaps utilise ``tilenumbering='simple'`` et cible OsmAnd. Seules
    les tuiles non vides sont écrites. Le Path final est retourné au succès,
    ``None`` lorsqu'aucune tuile n'est produite.
    """
    from PIL import Image as _Image, ImageDraw as _ImageDraw

    _chemin_part = dependances.chemin_part
    _nettoyer_sqlite_part = dependances.nettoyer_sqlite_part
    _valider_sqlite_part = dependances.valider_sqlite_part
    _stop_event = dependances.stop_event
    deg_to_tile = dependances.deg_to_tile
    _OVERLAY_STYLE = dependances.overlay_style
    _OVERLAY_DEFAUT = dependances.overlay_defaut
    _OVERLAY_TILE_WARN = dependances.overlay_tile_warn
    _overlay_style_key = dependances.overlay_style_key
    _overlay_sequences = dependances.overlay_sequences
    _clip_polygone_rect = dependances.clip_polygone_rect
    _seg_inter_box = dependances.seg_inter_box

    geojson_path = Path(geojson_path)
    sqlitedb_out = Path(sqlitedb_out)
    if sqlitedb_out.exists() and not ecraser:
        print(f"  {sqlitedb_out.name} -> already present")
        return sqlitedb_out
    if not geojson_path.exists():
        print(f"  ERROR: {geojson_path.name} not found")
        return None

    tile_size = 256
    supersampling = max(1, int(supersample))
    layer_hint = ""
    stem = geojson_path.name
    if "_ign_" in stem:
        layer_hint = stem.split("_ign_", 1)[1].split(".geojson", 1)[0]

    def _deg2num_f(lat, lon, zoom):
        n = 1 << zoom
        x = (lon + 180.0) / 360.0 * n
        y = (
            1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi
        ) / 2.0 * n
        return x, y

    opener = (
        (lambda: gzip.open(geojson_path, "rb"))
        if geojson_path.suffix == ".gz"
        else (lambda: open(geojson_path, "rb"))
    )

    def _iter_features():
        try:
            import ijson as _ijson

            with opener() as stream:
                yield from _ijson.items(stream, "features.item")
            return
        except ImportError:
            pass
        except (OSError, ValueError):
            pass
        with opener() as stream:
            payload = stream.read()
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")
        yield from json.loads(payload).get("features", [])

    # Une marge de 15 % garde les traits utiles aux bords sans rasteriser les
    # géométries IGN qui peuvent courir sur des centaines de kilomètres.
    clip = None
    if bbox_wgs84:
        west, south, east, north = bbox_wgs84
        margin_lon = (east - west) * 0.15 + 1e-4
        margin_lat = (north - south) * 0.15 + 1e-4
        clip = (
            west - margin_lon,
            south - margin_lat,
            east + margin_lon,
            north + margin_lat,
        )

    def _clip_seq(sequence):
        if clip is None or len(sequence) < 2:
            return [sequence] if len(sequence) >= 2 else []
        clip_west, clip_south, clip_east, clip_north = clip
        result, current = [], []
        for index in range(len(sequence) - 1):
            (x0, y0), (x1, y1) = sequence[index], sequence[index + 1]
            intersects = (
                max(x0, x1) >= clip_west
                and min(x0, x1) <= clip_east
                and max(y0, y1) >= clip_south
                and min(y0, y1) <= clip_north
            )
            if intersects:
                if not current:
                    current.append(sequence[index])
                current.append(sequence[index + 1])
            else:
                if len(current) >= 2:
                    result.append(current)
                current = []
        if len(current) >= 2:
            result.append(current)
        return result

    def _clip_poly(ring):
        if clip is None or len(ring) < 3:
            return ring
        clip_west, clip_south, clip_east, clip_north = clip
        xs = [point[0] for point in ring]
        ys = [point[1] for point in ring]
        if (
            min(xs) >= clip_west
            and max(xs) <= clip_east
            and min(ys) >= clip_south
            and max(ys) <= clip_north
        ):
            return ring
        return _clip_polygone_rect(
            ring, clip_west, clip_south, clip_east, clip_north
        )

    features = []
    lon_min = lat_min = float("inf")
    lon_max = lat_max = float("-inf")
    for feature in _iter_features():
        if _stop_event.is_set():
            raise KeyboardInterrupt("transparent-raster interrompu")
        geometry = feature.get("geometry")
        if not geometry:
            continue
        properties = feature.get("properties") or {}
        color, width, fill = _OVERLAY_STYLE.get(
            _overlay_style_key(properties, layer_hint), _OVERLAY_DEFAUT
        )
        lines, polygons = _overlay_sequences(geometry)
        if not lines and not polygons:
            continue

        lines = [
            part
            for sequence in lines
            for part in _clip_seq(
                [(float(coord[0]), float(coord[1])) for coord in sequence]
            )
        ]
        clipped_polygons = []
        for polygon in polygons:
            rings = [
                [(float(coord[0]), float(coord[1])) for coord in ring]
                for ring in polygon
            ]
            if fill:
                exterior = _clip_poly(rings[0])
                if len(exterior) < 3:
                    continue
                holes = []
                for hole in rings[1:]:
                    clipped_hole = _clip_poly(hole)
                    if len(clipped_hole) >= 3:
                        holes.append(clipped_hole)
                clipped_polygons.append((exterior, holes))
            else:
                for ring in rings:
                    for part in _clip_seq(ring):
                        clipped_polygons.append((part, []))

        if not lines and not clipped_polygons:
            continue
        for exterior, _holes in clipped_polygons:
            for lon, lat in exterior:
                if lon < lon_min:
                    lon_min = lon
                if lon > lon_max:
                    lon_max = lon
                if lat < lat_min:
                    lat_min = lat
                if lat > lat_max:
                    lat_max = lat
        for sequence in lines:
            for lon, lat in sequence:
                if lon < lon_min:
                    lon_min = lon
                if lon > lon_max:
                    lon_max = lon
                if lat < lat_min:
                    lat_min = lat
                if lat > lat_max:
                    lat_max = lat
        features.append((color, width, fill, lines, clipped_polygons))

    if not features or lon_min > lon_max:
        if bbox_wgs84:
            print(
                "  transparent-raster: no feature within the zone "
                "(features exist nearby but none cross it - try a larger --zone-width)"
            )
        else:
            print(
                f"  transparent-raster: no drawable feature in {geojson_path.name}"
            )
        return None

    if bbox_wgs84:
        west, south, east, north = bbox_wgs84
        lon_min = max(lon_min, west)
        lat_min = max(lat_min, south)
        lon_max = min(lon_max, east)
        lat_max = min(lat_max, north)
    if lon_min > lon_max or lat_min > lat_max:
        print("  transparent-raster: features outside the requested zone")
        return None

    print(
        f"  transparent-raster <- {geojson_path.name} "
        f"({len(features)} features, z{zoom_min}-{zoom_max})...",
        flush=True,
    )
    started = time.time()

    grid_total = 0
    for zoom in range(zoom_min, zoom_max + 1):
        x0, y0 = deg_to_tile(lat_max, lon_min, zoom)
        x1, y1 = deg_to_tile(lat_min, lon_max, zoom)
        grid_total += (x1 - x0 + 1) * (y1 - y0 + 1)
    if grid_total > _OVERLAY_TILE_WARN:
        print(
            f"  WARNING: large overlay ({grid_total:,} grid tiles) - this may "
            "take a while; reduce the zone or lower --zoom-max.",
            flush=True,
        )

    scale = tile_size * supersampling

    def _proj_pt(lon, lat, zoom):
        fractional_x, fractional_y = _deg2num_f(lat, lon, zoom)
        return fractional_x * scale, fractional_y * scale

    out_part = _chemin_part(sqlitedb_out)
    try:
        connection = sqlite3.connect(str(out_part))
        try:
            connection.execute("PRAGMA journal_mode=MEMORY;")
            connection.execute("PRAGMA synchronous=OFF;")
            connection.executescript(
                """
                CREATE TABLE tiles (x INT, y INT, z INT, s INT, image BLOB);
                CREATE TABLE android_metadata (locale TEXT);
                CREATE TABLE info (minzoom INT, maxzoom INT, tilenumbering TEXT);
                CREATE UNIQUE INDEX idx_tiles ON tiles (x, y, z, s);
                """
            )
            connection.execute(
                "INSERT INTO android_metadata VALUES (?)", ("fr_FR",)
            )
            connection.execute(
                "INSERT INTO info VALUES (?, ?, ?)",
                (zoom_min, zoom_max, "simple"),
            )

            total = 0
            for zoom in range(zoom_min, zoom_max + 1):
                grid_x0, grid_y0 = deg_to_tile(lat_max, lon_min, zoom)
                grid_x1, grid_y1 = deg_to_tile(lat_min, lon_max, zoom)
                buckets = {}

                def _add(tile_x, tile_y, item):
                    if (
                        grid_x0 <= tile_x <= grid_x1
                        and grid_y0 <= tile_y <= grid_y1
                    ):
                        buckets.setdefault((tile_x, tile_y), []).append(item)

                for color, width, fill, lines, polygons in features:
                    width_px = max(1, int(round(width * supersampling)))
                    margin = width_px + 2 * supersampling
                    for sequence in lines:
                        projected = [
                            _proj_pt(lon, lat, zoom) for lon, lat in sequence
                        ]
                        for index in range(len(projected) - 1):
                            point0, point1 = projected[index], projected[index + 1]
                            item = ("lin", color, width_px, point0, point1)
                            for tile_x in range(
                                int((min(point0[0], point1[0]) - margin) // scale),
                                int((max(point0[0], point1[0]) + margin) // scale)
                                + 1,
                            ):
                                box_x0 = tile_x * scale - margin
                                box_x1 = tile_x * scale + scale + margin
                                for tile_y in range(
                                    int(
                                        (min(point0[1], point1[1]) - margin)
                                        // scale
                                    ),
                                    int(
                                        (max(point0[1], point1[1]) + margin)
                                        // scale
                                    )
                                    + 1,
                                ):
                                    if _seg_inter_box(
                                        point0[0],
                                        point0[1],
                                        point1[0],
                                        point1[1],
                                        box_x0,
                                        tile_y * scale - margin,
                                        box_x1,
                                        tile_y * scale + scale + margin,
                                    ):
                                        _add(tile_x, tile_y, item)
                    for exterior, holes in polygons:
                        projected = [
                            _proj_pt(lon, lat, zoom) for lon, lat in exterior
                        ]
                        if len(projected) < 2:
                            continue
                        projected_holes = [
                            [_proj_pt(lon, lat, zoom) for lon, lat in hole]
                            for hole in holes
                        ]
                        xs = [point[0] for point in projected]
                        ys = [point[1] for point in projected]
                        item = (
                            "pol",
                            color,
                            width_px,
                            fill,
                            projected,
                            projected_holes,
                        )
                        for tile_x in range(
                            int((min(xs) - margin) // scale),
                            int((max(xs) + margin) // scale) + 1,
                        ):
                            for tile_y in range(
                                int((min(ys) - margin) // scale),
                                int((max(ys) + margin) // scale) + 1,
                            ):
                                _add(tile_x, tile_y, item)

                def _render_tile(job, current_zoom=zoom):
                    (tile_x, tile_y), items = job
                    origin_x, origin_y = tile_x * scale, tile_y * scale
                    big = _Image.new("RGBA", (scale, scale), (0, 0, 0, 0))
                    draw = _ImageDraw.Draw(big)

                    for item in items:
                        if item[0] != "pol":
                            continue
                        _, color, width_px, fill, projected, holes = item
                        points = [
                            (x - origin_x, y - origin_y) for x, y in projected
                        ]
                        if fill:
                            if holes:
                                mask = _Image.new("L", (scale, scale), 0)
                                mask_draw = _ImageDraw.Draw(mask)
                                mask_draw.polygon(points, fill=70)
                                for hole in holes:
                                    mask_draw.polygon(
                                        [
                                            (x - origin_x, y - origin_y)
                                            for x, y in hole
                                        ],
                                        fill=0,
                                    )
                                layer = _Image.new(
                                    "RGBA",
                                    (scale, scale),
                                    (color[0], color[1], color[2], 0),
                                )
                                layer.putalpha(mask)
                                big.alpha_composite(layer)
                            else:
                                draw.polygon(
                                    points,
                                    fill=(color[0], color[1], color[2], 70),
                                )
                        draw.line(points, fill=color, width=width_px, joint="curve")
                        for hole in holes:
                            draw.line(
                                [
                                    (x - origin_x, y - origin_y)
                                    for x, y in hole
                                ],
                                fill=color,
                                width=width_px,
                                joint="curve",
                            )

                    for item in items:
                        if item[0] != "lin":
                            continue
                        _, color, width_px, point0, point1 = item
                        start = (point0[0] - origin_x, point0[1] - origin_y)
                        end = (point1[0] - origin_x, point1[1] - origin_y)
                        radius = (width_px + 2 * supersampling) / 2.0
                        draw.line(
                            [start, end],
                            fill=(255, 255, 255, 210),
                            width=width_px + 2 * supersampling,
                        )
                        for center_x, center_y in (start, end):
                            draw.ellipse(
                                [
                                    center_x - radius,
                                    center_y - radius,
                                    center_x + radius,
                                    center_y + radius,
                                ],
                                fill=(255, 255, 255, 210),
                            )

                    for item in items:
                        if item[0] != "lin":
                            continue
                        _, color, width_px, point0, point1 = item
                        start = (point0[0] - origin_x, point0[1] - origin_y)
                        end = (point1[0] - origin_x, point1[1] - origin_y)
                        radius = width_px / 2.0
                        draw.line([start, end], fill=color, width=width_px)
                        for center_x, center_y in (start, end):
                            draw.ellipse(
                                [
                                    center_x - radius,
                                    center_y - radius,
                                    center_x + radius,
                                    center_y + radius,
                                ],
                                fill=color,
                            )

                    small = (
                        big.resize((tile_size, tile_size), _Image.BOX)
                        if supersampling > 1
                        else big
                    )
                    if small.getbbox() is None:
                        return None
                    buffer = io.BytesIO()
                    small.save(buffer, "PNG")
                    return (
                        tile_x,
                        tile_y,
                        current_zoom,
                        0,
                        buffer.getvalue(),
                    )

                zoom_total = 0
                batch = []
                jobs = list(buckets.items())
                worker_count = max(2, min(8, os.cpu_count() or 4))

                def _consume(result):
                    nonlocal zoom_total
                    if result is None:
                        return
                    batch.append(result)
                    zoom_total += 1
                    if len(batch) >= 500:
                        connection.executemany(
                            "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?,?)",
                            batch,
                        )
                        batch.clear()

                if len(jobs) >= 64:
                    with ThreadPoolExecutor(max_workers=worker_count) as pool:
                        for result in pool.map(_render_tile, jobs):
                            if _stop_event.is_set():
                                raise KeyboardInterrupt(
                                    "transparent-raster interrompu"
                                )
                            _consume(result)
                else:
                    for job in jobs:
                        _consume(_render_tile(job))
                if batch:
                    connection.executemany(
                        "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?,?)", batch
                    )
                    batch.clear()
                total += zoom_total
                if zoom_total:
                    print(f"    z{zoom}: {zoom_total} tiles", flush=True)
            connection.commit()
        finally:
            connection.close()

        if total == 0:
            _nettoyer_sqlite_part(out_part)
            print("  transparent-raster: no non-empty tile")
            return None

        _valider_sqlite_part(
            out_part, {"tiles": total, "android_metadata": 1, "info": 1}
        )
        out_part.replace(sqlitedb_out)
    except BaseException:
        _nettoyer_sqlite_part(out_part)
        raise

    print(
        f"  {sqlitedb_out.name} : {total} tiles  "
        f"({sqlitedb_out.stat().st_size / 1024:.0f} Ko)  "
        f"{time.time() - started:.1f}s"
    )
    return sqlitedb_out
