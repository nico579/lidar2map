"""Construction Mapsforge depuis un extrait OSM via Osmosis."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import time


@dataclass(frozen=True)
class DependancesCarteOsm:
    bundle_dir: object
    dossier_travail: object
    windows: bool
    osmosis_interessant: object
    chemin_part: object
    formater_duree: object
    java_opts_extra: object
    nettoyer_osmosis_temp: object
    preparer_osmosis: object
    sidecar_ecrire: object
    sidecar_stale: object
    signature_osm: object
    valider_osm_tags: object
    verifier_mapwriter: object
    generer_geojson: object
    journaliser_requete: object
    executer_osmosis: object
    publier_groupe_atomique: object


def generer_carte_osm(
    bbox_wgs84,
    dossier_ville,
    nom_zone,
    osm_pbf,
    osm_tags=None,
    export_geojson=True,
    ecraser_tuiles=False,
    skip_bbox=False,
    geojson_formats=None,
    want_map=True,
    *,
    dependances,
):
    """Génère une carte Mapsforge et, si demandé, ses GeoJSON OSM."""
    d = dependances
    dossier_ville = Path(dossier_ville)
    osm_pbf = Path(osm_pbf)
    if geojson_formats is None:
        geojson_formats = ["gz"]

    if not want_map:
        if not export_geojson:
            print("  OSM: neither .map nor GeoJSON requested - nothing to do.")
            return None
        return d.generer_geojson(
            bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
            osm_tags=osm_tags, ecraser_tuiles=ecraser_tuiles,
            formats=geojson_formats,
        )

    if d.windows:
        d.nettoyer_osmosis_temp(verbose=True)

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    chemin_map = dossier_ville / f"{nom_zone}.map"
    chemin_map_part = d.chemin_part(chemin_map)
    chemin_geojson_gz = dossier_ville / f"{nom_zone}_osm.geojson.gz"
    chemin_geojson_raw = dossier_ville / f"{nom_zone}_osm.geojson"
    need_gz = "gz" in geojson_formats
    need_raw = "geojson" in geojson_formats
    geojson_present = (
        (not need_gz or chemin_geojson_gz.exists())
        and (not need_raw or chemin_geojson_raw.exists())
    )
    signature = d.signature_osm(bbox_wgs84, osm_tags, osm_pbf, skip_bbox)
    signature_perimee = chemin_map.exists() and d.sidecar_stale(
        chemin_map, signature
    )
    regen_geojson = bool(ecraser_tuiles or signature_perimee)

    if chemin_map.exists() and ecraser_tuiles:
        print(f"  Carte OSM : overwrite {chemin_map.name}")
    elif signature_perimee:
        print(f"  {chemin_map.name} → OSM config changed (bbox/tags/PBF), regenerating")
    elif chemin_map.exists():
        if not Path(str(chemin_map) + ".sig").exists():
            d.sidecar_ecrire(chemin_map, signature)
        if not export_geojson or geojson_present:
            print(f"  OSM map already present: {chemin_map.name} - skipped")
            return chemin_map
        print(f"  OSM map already present: {chemin_map.name} - GeoJSON missing, exporting...")
        filtre = dossier_ville / f"{nom_zone}_filtered.pbf"
        source = filtre if filtre.exists() else osm_pbf
        if source == filtre:
            print(f"  Existing filtered PBF: {filtre.name}")
        d.generer_geojson(
            bbox_wgs84, dossier_ville, nom_zone, source,
            osm_tags=osm_tags, ecraser_tuiles=ecraser_tuiles,
            formats=geojson_formats,
        )
        return chemin_map

    if not d.verifier_mapwriter():
        print("  WARNING: mapwriter plugin missing - .map skipped.")
        if export_geojson:
            return d.generer_geojson(
                bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
                osm_tags=osm_tags, ecraser_tuiles=regen_geojson,
                formats=geojson_formats,
            )
        return None

    osmosis_exe, java_home = d.preparer_osmosis()
    if not osmosis_exe:
        return None
    env = os.environ.copy()
    env["JAVA_HOME"] = java_home
    java_extra = d.java_opts_extra()
    env["JAVA_OPTS"] = "-Xmx6g" + java_extra
    env["JAVACMD_OPTIONS"] = "-Xmx6g" + java_extra

    tagmapping = None
    for candidate in (
        Path(d.dossier_travail) / "tagmapping-min.xml",
        Path(d.bundle_dir) / "tagmapping-min.xml",
        osm_pbf.parent / "tagmapping-min.xml",
        dossier_ville / "tagmapping-min.xml",
    ):
        if candidate.exists():
            tagmapping = str(candidate)
            break
    if not tagmapping:
        print("  WARNING: tagmapping-min.xml not found - using osmosis default")

    started = time.time()
    print(f"  osmosis → {chemin_map.name}...", flush=True)
    if osm_tags is None:
        osm_tags = [
            "highway=*", "waterway=*", "boundary=administrative",
            "natural=water", "natural=coastline", "waterway=river",
            "waterway=stream", "waterway=canal",
        ]
    osm_tags = list(dict.fromkeys(osm_tags))
    d.valider_osm_tags(osm_tags)
    print(f"  Tags : {' '.join(osm_tags)}", flush=True)

    chemin_pbf_filtre = dossier_ville / f"{nom_zone}_filtered.pbf"
    chemin_pbf_part = d.chemin_part(chemin_pbf_filtre)
    chemin_ways_tmp = dossier_ville / f"{nom_zone}_ways.tmp.pbf"
    chemin_poi_tmp = dossier_ville / f"{nom_zone}_poi.tmp.pbf"
    poi_tags = [
        "place=*", "natural=*", "historic=*", "man_made=*",
        "tourism=*", "amenity=*", "leisure=*",
    ]
    d.valider_osm_tags(poi_tags)
    reader = "--read-xml" if str(osm_pbf).lower().endswith(".osm") else "--read-pbf"
    bbox_args = [] if skip_bbox else [
        "--bounding-box", f"left={lon_min:.4f}", f"right={lon_max:.4f}",
        f"top={lat_max:.4f}", f"bottom={lat_min:.4f}",
    ]
    mapwriter_args = [
        "--mapfile-writer", f"file={chemin_map_part}",
        "zoom-interval-conf=7,0,7,11,8,11,14,12,21", "tag-values=true",
        "polygon-clipping=true", "way-clipping=true", "label-position=true",
        "type=hd",
    ]
    if tagmapping:
        mapwriter_args.append(f"tag-conf-file={tagmapping}")

    cmd_p1 = (
        [osmosis_exe, reader, f"file={osm_pbf}"] + bbox_args
        + ["--tf", "accept-ways"] + osm_tags
        + ["--used-node", "--write-pbf", f"file={chemin_ways_tmp}"]
    )
    cmd_p2 = (
        [osmosis_exe, reader, f"file={osm_pbf}"] + bbox_args
        + ["--tf", "accept-nodes"] + poi_tags
        + ["--tf", "reject-ways", "--tf", "reject-relations",
           "--write-pbf", f"file={chemin_poi_tmp}"]
    )
    cmd_p3 = (
        [osmosis_exe, "--read-pbf", f"file={chemin_ways_tmp}",
         "--read-pbf", f"file={chemin_poi_tmp}", "--merge", "--tee", "2"]
        + mapwriter_args + ["--write-pbf", f"file={chemin_pbf_part}"]
    )
    shell = d.windows and str(osmosis_exe).endswith(".bat")

    def lancer(command):
        if shell:
            executable = " ".join(
                f'"{arg}"' if (" " in str(arg) or "=" in str(arg)) else str(arg)
                for arg in command
            )
        else:
            executable = command
        d.journaliser_requete(command)
        return d.executer_osmosis(executable, shell=shell, env=env)

    rc, stderr_diag = 0, ""
    try:
        for index, command in enumerate((cmd_p1, cmd_p2, cmd_p3), 1):
            print(f"  osmosis pass {index}/3...", flush=True)
            rc, stderr_diag = lancer(command)
            if rc != 0:
                break
    except BaseException:
        chemin_map_part.unlink(missing_ok=True)
        chemin_pbf_part.unlink(missing_ok=True)
        raise
    finally:
        chemin_ways_tmp.unlink(missing_ok=True)
        chemin_poi_tmp.unlink(missing_ok=True)

    sorties_valides = (
        rc == 0
        and chemin_map_part.exists() and chemin_map_part.stat().st_size > 0
        and chemin_pbf_part.exists() and chemin_pbf_part.stat().st_size > 0
    )
    if not sorties_valides:
        chemin_map_part.unlink(missing_ok=True)
        chemin_pbf_part.unlink(missing_ok=True)
        print(f"  ERROR osmosis mapfile-writer (code {rc})")
        if stderr_diag:
            lignes = [
                line for line in stderr_diag.splitlines()
                if any(token in line for token in d.osmosis_interessant)
            ]
            if lignes:
                print("  osmosis detail:")
                for line in lignes[:20]:
                    print(f"    {line}")
            else:
                print(f"  {stderr_diag.strip()[-600:]}")
        return None

    # Le .map reste le dernier marqueur publié, mais les deux anciens finals
    # sont restaurés ensemble si l'une des promotions échoue.
    try:
        d.publier_groupe_atomique((
            (chemin_pbf_part, chemin_pbf_filtre),
            (chemin_map_part, chemin_map),
        ))
    except BaseException:
        chemin_pbf_part.unlink(missing_ok=True)
        chemin_map_part.unlink(missing_ok=True)
        raise
    d.sidecar_ecrire(chemin_map, signature)
    taille = chemin_map.stat().st_size
    if taille < 1_000_000:
        print(f"  {chemin_map.name} : {taille // 1024} Ko  {d.formater_duree(time.time()-started)}")
    else:
        print(f"  {chemin_map.name} : {taille / 1e6:.1f} MB  {d.formater_duree(time.time()-started)}")
    if export_geojson:
        source = chemin_pbf_filtre if chemin_pbf_filtre.exists() else osm_pbf
        d.generer_geojson(
            bbox_wgs84, dossier_ville, nom_zone, source,
            osm_tags=osm_tags, ecraser_tuiles=regen_geojson,
            formats=geojson_formats,
        )
    return chemin_map
