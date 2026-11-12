"""Inventaire documentaire et sondages HTTP, sans enregistrer de provider.

Les sondages vérifient une source au point choisi et le décodage d'une tuile.
Ils ne mesurent ni précision absolue ni conservation du microrelief.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / "cache/mapterhorn-countries"
COUNTRIES = {
    "at", "au", "be", "ca", "ch", "cy", "cz", "de", "dk", "ee",
    "es", "fi", "fr", "is", "it", "jp", "lu", "nl", "no", "nz",
    "pl", "pt", "ro", "rw", "se", "si", "sk", "us",
}
SPECIAL = {
    "aalv": "lv", "aatw": "tw", "swissalti3d": "ch",
    "tinitaly": "it", "isr10": "il", "glo30": None,
}
POINTS = {
    "cy": ("Larnaca", 33.622, 34.921, 16),
    "ro": ("Arad", 21.31, 46.18, 16),
    "sk": ("Bratislava, forêt au nord", 17.072, 48.200, 16),
    "is": ("Reykjavík", -21.943, 64.147, 12),
    "isr10": ("Jérusalem", 35.214, 31.780, 13),
    "rw": ("Kigali", 30.060, -1.950, 13),
    "aatw": ("Taipei", 121.565, 25.033, 12),
}
SOURCE_FILES = {
    "cy": ["metadata.json", "Justfile", "file_list.txt", "create_file_list.py"],
    "ro": ["metadata.json", "Justfile", "file_list.txt", "source_unzip_ro.py"],
    "sk": ["metadata.json", "Justfile"],
    "is": ["metadata.json", "Justfile", "file_list.txt"],
    "isr10": ["metadata.json", "Justfile"],
    "rw": ["metadata.json", "Justfile", "README.md", "file_list.txt"],
    "aatw": ["metadata.json", "README.md"],
}


def fetch(url: str, name: str, refresh: bool = False) -> bytes:
    path = CACHE / name
    sidecar = path.with_name(path.name + ".http.json")
    if not refresh and path.exists() and sidecar.exists():
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() == json.loads(sidecar.read_text())["sha256"]:
            return payload
    request = urllib.request.Request(url, headers={"User-Agent": "lidar2map-documentary-audit/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(8 * 1024 * 1024 + 1)
        if len(payload) > 8 * 1024 * 1024:
            raise ValueError("Limite de téléchargement de 8 Mio dépassée")
        info = {
            "url": url, "final_url": response.url, "status": response.status,
            "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
            "headers": dict(response.headers),
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    sidecar.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def source_country(source: str) -> str | None:
    if source in SPECIAL:
        return SPECIAL[source]
    if source.startswith("uk"):
        return "gb"
    prefix = source[:2]
    if prefix not in COUNTRIES:
        raise ValueError(f"Source non classée : {source}")
    return prefix


def tile_position(lon: float, lat: float, zoom: int):
    n = 2**zoom
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return int(x), int(y), x % 1, y % 1


def probe(source: str) -> dict:
    import mapbox_vector_tile
    import numpy as np
    from PIL import Image
    from shapely.geometry import Point, shape

    label, lon, lat, zoom = POINTS[source]
    cx, cy, u, v = tile_position(lon, lat, 14)
    coverage_url = f"https://single-archive-tiles.mapterhorn.com/coverage/14/{cx}/{cy}.mvt"
    coverage = fetch(coverage_url, f"probes/{source}-coverage.mvt")
    layer = mapbox_vector_tile.decode(coverage, default_options={"y_coord_down": True}).get("coverage", {})
    point = Point(u * layer.get("extent", 4096), v * layer.get("extent", 4096))
    point_sources = sorted({
        f.get("properties", {}).get("source") for f in layer.get("features", [])
        if shape(f["geometry"]).covers(point)
    })
    x, y, _, _ = tile_position(lon, lat, zoom)
    tile_url = f"https://tiles.mapterhorn.com/{zoom}/{x}/{y}.webp"
    payload = fetch(tile_url, f"probes/{source}-z{zoom}.webp")
    array = np.asarray(Image.open(io.BytesIO(payload)).convert("RGB"), dtype=np.float64)
    heights = array[:, :, 0] * 256 + array[:, :, 1] + array[:, :, 2] / 256 - 32768
    return {
        "source": source, "label": label, "lon": lon, "lat": lat,
        "point_sources": point_sources, "expected_source_at_point": source in point_sources,
        "coverage_url": coverage_url, "tile_url": tile_url,
        "zoom": zoom, "tile_shape": list(array.shape),
        "ground_pixel_m_at_latitude": 40075016.68557849 / (2**zoom * 512) * math.cos(math.radians(lat)),
        "tile_elevation_min_m": float(heights.min()),
        "tile_elevation_max_m": float(heights.max()),
        "note": "Sondage de disponibilité, pas une mesure de qualité altimétrique.",
    }


def inspect_archive(source: str, limit: int) -> dict:
    """Lire le début seulement, même si le serveur ignore l'en-tête Range."""
    from pyproj import Geod
    from rasterio.io import MemoryFile

    path = CACHE / f"{source}-tar-prefix.bin"
    sidecar = CACHE / f"{source}-tar-prefix.http.json"
    payload = path.read_bytes() if path.exists() else b""
    info = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
    if len(payload) != limit or hashlib.sha256(payload).hexdigest() != info.get("sha256"):
        url = f"https://download.mapterhorn.com/sources/{source}.tar"
        request = urllib.request.Request(url, headers={
            "Range": f"bytes=0-{limit-1}", "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status not in (200, 206):
                raise ValueError(f"Statut HTTP inattendu : {response.status}")
            payload = response.read(limit)
            info = {
                "url": url, "status": response.status,
                "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "headers": dict(response.headers), "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "note": "Lecture bornée du début; connexion fermée sans télécharger toute l'archive.",
            }
        path.write_bytes(payload)
        sidecar.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        for entry in archive:
            if entry.name in {"metadata.json", "bounds.csv", "coverage.gpkg"} and entry.offset_data + entry.size <= len(payload):
                (CACHE / f"{source}-{entry.name}").write_bytes(archive.extractfile(entry).read())
            if entry.name.endswith(".tif"):
                with MemoryFile(payload[entry.offset_data:]) as memory:
                    with memory.open() as dataset:
                        result = {
                            "archive_member": entry.name, "crs": str(dataset.crs),
                            "resolution": list(dataset.res), "shape": list(dataset.shape),
                            "transform": list(dataset.transform), "bounds": list(dataset.bounds),
                            "nodata": dataset.nodata,
                            "note": "En-tête d'une dalle du stock Mapterhorn; pas une comparaison des altitudes au natif officiel.",
                        }
                if source == "cy":
                    lon = (result["bounds"][0] + result["bounds"][2]) / 2
                    lat = (result["bounds"][1] + result["bounds"][3]) / 2
                    geod = Geod(ellps="GRS80")
                    dx, dy = result["resolution"]
                    result["pixel_m_at_tile_center"] = [
                        geod.inv(lon, lat, lon + dx, lat)[2],
                        geod.inv(lon, lat, lon, lat + dy)[2],
                    ]
                (CACHE / f"{source}-first-tif-metadata.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                return result
    raise ValueError("En-tête GeoTIFF absent du préfixe téléchargé")


def main():
    from coverage_map import load_providers

    CACHE.mkdir(parents=True, exist_ok=True)
    attribution = json.loads(fetch("https://download.mapterhorn.com/attribution.json", "attribution.json"))
    providers = load_providers()
    active = sorted({p["country"].lower() for p in providers.values() if p["country"]})
    by_country = {}
    for record in attribution:
        country = source_country(record["source"])
        if country is not None:
            by_country.setdefault(country, []).append(record)
    absent = {c: records for c, records in sorted(by_country.items()) if c not in active}
    inventory = {
        "audit_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "active_provider_count": len(providers), "active_countries": active,
        "mapterhorn_source_count": len(attribution),
        "mapterhorn_country_count": len(by_country), "absent_countries": absent,
        "global_fallback_excluded": "glo30",
        "territories_grouped": "Greenland and Faroe Islands with DK; Dutch Caribbean with NL; overseas FR with FR",
    }
    jobs = []
    for source, files in SOURCE_FILES.items():
        for file in files:
            jobs.append((f"https://raw.githubusercontent.com/mapterhorn/mapterhorn/main/source-catalog/{source}/{file}", f"sources/{source}/{file}"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch, url, name): name for url, name in jobs}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as error:
                inventory.setdefault("input_errors", []).append({"name": name, "error": str(error)})
        futures = {pool.submit(probe, source): source for source in POINTS}
        probes = []
        for future in concurrent.futures.as_completed(futures):
            try:
                probes.append(future.result())
            except Exception as error:
                probes.append({"source": futures[future], "error": str(error)})
    inventory["probes"] = sorted(probes, key=lambda p: p["source"])
    if "--inspect-archives" in sys.argv:
        inventory["archive_headers"] = {
            source: inspect_archive(source, limit)
            for source, limit in (("ro", 16 * 1024 * 1024), ("cy", 10 * 1024 * 1024))
        }
    for source in ("ro", "cy"):
        footprint = CACHE / f"{source}-footprint.json"
        if footprint.exists():
            inventory.setdefault("archive_footprints", {})[source] = json.loads(footprint.read_text(encoding="utf-8"))
    (CACHE / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: inventory[k] for k in ("active_provider_count", "active_countries", "mapterhorn_source_count", "mapterhorn_country_count")}, ensure_ascii=False))
    print("Pays absents : " + ", ".join(absent))
    for result in inventory["probes"]:
        print(json.dumps(result, ensure_ascii=False))
    for error in inventory.get("input_errors", []):
        print(json.dumps(error, ensure_ascii=False))
    if "archive_headers" in inventory:
        print(json.dumps(inventory["archive_headers"], ensure_ascii=False))
    if inventory.get("input_errors") or any("error" in p or not p.get("expected_source_at_point") for p in probes):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
