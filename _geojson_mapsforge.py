"""Orchestration GeoJSON IGN vers carte Mapsforge.

Le module gère le cache signé, l'environnement Java, l'appel à osmosis et la
publication atomique du fichier ``.map``. Les coutures applicatives sont
injectées par la façade ``lidar2map.py`` à chaque appel.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _DependancesGeojsonMapsforge:
    """Services et valeurs relus par la façade avant chaque génération."""

    convertir_geojson_osm_xml: Callable[..., bool]
    preparer_osmosis: Callable[..., tuple[Any, Any]]
    run_osmosis_streaming: Callable[..., tuple[int, str]]
    chemin_part: Callable[[Path], Path]
    hash_config: Callable[[dict[str, Any]], str]
    sig_sidecar_stale: Callable[[Path, str], bool]
    sig_sidecar_ecrire: Callable[[Path, str], None]
    java_opts_extra: Callable[[], str]
    log_req: Callable[[Any], None]
    formater_duree: Callable[[float], str]
    windows: bool


def generer_map_depuis_geojson_ign(
    geojson_src,
    dossier_ville,
    nom_zone,
    bbox_wgs84,
    ecraser=False,
    epsilon=None,
    *,
    dependances: _DependancesGeojsonMapsforge,
):
    """Convertit un GeoJSON IGN en carte Mapsforge via osmosis/mapwriter."""
    geojson_ign_vers_osm_xml = dependances.convertir_geojson_osm_xml
    _preparer_osmosis = dependances.preparer_osmosis
    _run_osmosis_streaming = dependances.run_osmosis_streaming
    _chemin_part = dependances.chemin_part
    _hash_config = dependances.hash_config
    _sig_sidecar_stale = dependances.sig_sidecar_stale
    _sig_sidecar_ecrire = dependances.sig_sidecar_ecrire
    _java_opts_extra = dependances.java_opts_extra
    _log_req = dependances.log_req
    _hms = dependances.formater_duree
    WINDOWS = dependances.windows

    dossier_ville = Path(dossier_ville)
    chemin_osm_xml = dossier_ville / f"{nom_zone}_ign.osm"
    chemin_map = dossier_ville / f"{nom_zone}_ign.map"

    signature = _hash_config({
        "src": Path(geojson_src).name,
        "src_mtime": (
            round(Path(geojson_src).stat().st_mtime, 1)
            if Path(geojson_src).exists()
            else None
        ),
        "bbox": (
            [round(float(coord), 6) for coord in bbox_wgs84]
            if bbox_wgs84
            else None
        ),
        "eps": epsilon,
    })

    if chemin_map.exists() and not ecraser:
        if chemin_map.stat().st_size == 0:
            print("  IGN .map exists but empty - forced regeneration.")
        elif _sig_sidecar_stale(chemin_map, signature):
            print(
                f"  {chemin_map.name} → IGN config changed "
                "(source/bbox/eps), regenerating"
            )
        else:
            if not Path(str(chemin_map) + ".sig").exists():
                _sig_sidecar_ecrire(chemin_map, signature)
            print(f"  IGN .map already present: {chemin_map.name} - skipped")
            return chemin_map

    if chemin_map.exists() and ecraser:
        print(f"  Carte IGN .map : overwrite {chemin_map.name}")

    print("  Converting GeoJSON → OSM XML...", flush=True)
    converted = geojson_ign_vers_osm_xml(
        geojson_src,
        chemin_osm_xml,
        epsilon=epsilon,
    )
    if not converted:
        return None

    osmosis_exe, java_home = _preparer_osmosis()
    if not osmosis_exe:
        chemin_osm_xml.unlink(missing_ok=True)
        return None

    env_map = os.environ.copy()
    env_map["JAVA_HOME"] = java_home
    if "JAVA_OPTS" not in env_map:
        env_map["JAVA_OPTS"] = "-Xmx4g" + _java_opts_extra()

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    started = time.time()
    print(f"  osmosis → {chemin_map.name}...", flush=True)

    chemin_map_part = _chemin_part(chemin_map)
    command = [
        osmosis_exe,
        "--read-xml",
        f"file={chemin_osm_xml}",
        "--mapfile-writer",
        f"file={chemin_map_part}",
        f"bbox={lat_min:.6f},{lon_min:.6f},{lat_max:.6f},{lon_max:.6f}",
        "zoom-interval-conf=7,0,7,11,8,11,14,12,21",
        "tag-values=true",
        "polygon-clipping=true",
        "way-clipping=true",
        "label-position=true",
    ]

    use_shell = WINDOWS and str(osmosis_exe).endswith(".bat")
    if use_shell:
        command_string = " ".join(
            f'"{argument}"'
            if " " in str(argument) or "=" in str(argument)
            else str(argument)
            for argument in command
        )
    _log_req(command)

    try:
        return_code, stderr_diag = _run_osmosis_streaming(
            command_string if use_shell else command,
            shell=use_shell,
            env=env_map,
        )

        if (
            return_code == 0
            and chemin_map_part.exists()
            and chemin_map_part.stat().st_size > 0
        ):
            chemin_map_part.replace(chemin_map)
            _sig_sidecar_ecrire(chemin_map, signature)
            chemin_osm_xml.unlink(missing_ok=True)
            size_bytes = chemin_map.stat().st_size
            duration = _hms(time.time() - started)
            if size_bytes < 1_000_000:
                print(
                    f"  {chemin_map.name} : {size_bytes // 1024} Ko  {duration}"
                )
            else:
                print(
                    f"  {chemin_map.name} : {size_bytes / 1e6:.1f} MB  "
                    f"{duration}"
                )
            return chemin_map

        if chemin_map_part.exists() and chemin_map_part.stat().st_size == 0:
            chemin_map_part.unlink(missing_ok=True)
            print(
                f"  ⚠ {chemin_map.name} created but empty - "
                "no feature recognised by mapwriter."
            )
            print(f"  {chemin_osm_xml.name} kept for diagnostics.")
            return None

        chemin_map_part.unlink(missing_ok=True)
        print(f"  ERROR osmosis mapfile-writer IGN (code {return_code})")
        if stderr_diag:
            print(f"  {stderr_diag.strip()[:2000]}")
        print(f"  {chemin_osm_xml.name} kept - rerun osmosis after fixing.")
        return None
    except BaseException:
        chemin_map_part.unlink(missing_ok=True)
        raise
