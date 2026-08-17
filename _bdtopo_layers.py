"""Conversion streamée des couches GPKG BD TOPO en GeoJSON."""

from __future__ import annotations

import decimal
import gzip
import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependancesCouchesBdtopo:
    """Coutures applicatives relues par la façade à chaque appel."""

    chemin_part: object
    gunzip_vers_fichier: object
    gzip_depuis_fichier: object
    get_transformer: object
    streamer_geojson: object
    formater_duree: object


def streamer_geojson_ajout_source(
    src_geojson, dst_gz, source_name, *, chemin_part
):
    """Streame une FeatureCollection vers gzip en ajoutant la source."""

    def _enc_default(value):
        if isinstance(value, decimal.Decimal):
            return float(value)
        raise TypeError(f"Type non-sérialisable : {type(value).__name__}")

    dst_gz = Path(dst_gz)
    if not str(dst_gz).endswith((".gz", ".part")):
        dst_gz = Path(str(dst_gz) + ".gz")
    dst_gz.parent.mkdir(parents=True, exist_ok=True)
    dst_tmp = chemin_part(dst_gz)
    try:
        try:
            import ijson
        except ImportError:
            print("  ⚠ ijson missing - full RAM load (OOM risk at dept-scale)")
            with open(src_geojson, encoding="utf-8") as source:
                geojson = json.load(source)
            features = geojson.get("features", [])
            for feature in features:
                properties = feature.get("properties") or {}
                properties.setdefault("source", source_name)
                feature["properties"] = properties
            geojson["features"] = features
            data = json.dumps(
                geojson,
                ensure_ascii=False,
                separators=(",", ":"),
                default=_enc_default,
            ).encode("utf-8")
            with gzip.open(dst_tmp, "wb", compresslevel=6) as output:
                output.write(data)
            if not features:
                dst_tmp.unlink(missing_ok=True)
                return 0
            dst_tmp.replace(dst_gz)
            return len(features)

        count = 0
        crs = {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        }
        header = (
            '{"type":"FeatureCollection","name":'
            + json.dumps(source_name, ensure_ascii=False)
            + ',"crs":'
            + json.dumps(crs, ensure_ascii=False, separators=(",", ":"))
            + ',"features":['
        )
        with gzip.open(dst_tmp, "wb", compresslevel=6) as output:
            output.write(header.encode("utf-8"))
            with open(src_geojson, "rb") as source:
                for feature in ijson.items(source, "features.item"):
                    properties = feature.get("properties") or {}
                    properties.setdefault("source", source_name)
                    feature["properties"] = properties
                    if count:
                        output.write(b",")
                    output.write(
                        json.dumps(
                            feature,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            default=_enc_default,
                        ).encode("utf-8")
                    )
                    count += 1
            output.write(b"]}")
        if count == 0:
            dst_tmp.unlink(missing_ok=True)
            return 0
        dst_tmp.replace(dst_gz)
        return count
    except BaseException:
        dst_tmp.unlink(missing_ok=True)
        raise


def _publier_formats_atomiquement(paires, chemin_part):
    """Promeut plusieurs formats et restaure tous les anciens en cas d'échec."""
    sauvegardes = []
    publies = []
    try:
        for _stage, final in paires:
            if final.exists():
                sauvegarde = chemin_part(final)
                final.replace(sauvegarde)
                sauvegardes.append((sauvegarde, final))
        for stage, final in paires:
            stage.replace(final)
            publies.append(final)
    except BaseException:
        for final in reversed(publies):
            final.unlink(missing_ok=True)
        for sauvegarde, final in reversed(sauvegardes):
            if sauvegarde.exists():
                sauvegarde.replace(final)
        raise
    finally:
        for sauvegarde, _final in sauvegardes:
            sauvegarde.unlink(missing_ok=True)


def extraire_couche_bdtopo(
    gpkg_path,
    layer_name,
    sortie_gz,
    bbox_l93=None,
    ecraser=False,
    formats=None,
    *,
    dependances,
):
    """Extrait une couche GPKG vers des GeoJSON WGS84 publiés atomiquement."""
    sortie_gz = Path(sortie_gz)
    sortie_raw = (
        Path(str(sortie_gz)[:-3])
        if str(sortie_gz).endswith(".gz")
        else Path(str(sortie_gz) + ".geojson")
    )
    formats = formats or ["gz"]
    formats = [f.lower() for f in formats if f.lower() in ("gz", "geojson")]
    if not formats:
        formats = ["gz"]
    ecrire_gz = "gz" in formats
    ecrire_geojson = "geojson" in formats

    if ecraser:
        for path in (sortie_gz, sortie_raw):
            if path.exists():
                print(f"  {path.name} -> overwrite")
    if not ecraser:
        manque_gz = ecrire_gz and not sortie_gz.exists()
        manque_raw = ecrire_geojson and not sortie_raw.exists()
        if not manque_gz and not manque_raw:
            present = sortie_gz if sortie_gz.exists() else sortie_raw
            print(f"  {present.name} → already present")
            return present
        if sortie_gz.exists() or sortie_raw.exists():
            try:
                if manque_raw and sortie_gz.exists():
                    dependances.gunzip_vers_fichier(sortie_gz, sortie_raw)
                    print(f"  {sortie_raw.name} -> rebuilt from {sortie_gz.name}")
                if manque_gz and sortie_raw.exists():
                    dependances.gzip_depuis_fichier(sortie_raw, sortie_gz)
                    print(f"  {sortie_gz.name} -> rebuilt from {sortie_raw.name}")
                return sortie_gz if sortie_gz.exists() else sortie_raw
            except OSError as error:
                print(f"  ⚠ Local rebuild failed ({error}) — extraction GPKG")

    try:
        import fiona
        from fiona.transform import transform_geom
        try:
            from fiona.model import to_dict as fiona_to_dict
        except ImportError:
            def fiona_to_dict(value):
                return value
    except ImportError:
        print("  ERROR: fiona missing, run pip install fiona")
        return None

    tmp_geojson = dependances.chemin_part(
        sortie_gz.parent / sortie_gz.name.replace(".geojson.gz", ".source.geojson")
    )

    def _json_default(value):
        isoformat = getattr(value, "isoformat", None)
        if callable(isoformat):
            return isoformat()
        return fiona_to_dict(value)

    started = time.time()
    try:
        bbox_filter = tuple(bbox_l93) if bbox_l93 else None
        with fiona.open(str(gpkg_path), layer=layer_name) as source:
            source_crs = source.crs
            transformer = dependances.get_transformer(str(source_crs), "EPSG:4326")

            def _transform(coordinates):
                if not coordinates:
                    return coordinates
                if isinstance(coordinates[0], (int, float)):
                    x, y = transformer.transform(coordinates[0], coordinates[1])
                    return [x, y]
                if isinstance(coordinates[0][0], (int, float)):
                    xs, ys = transformer.transform(
                        [point[0] for point in coordinates],
                        [point[1] for point in coordinates],
                    )
                    return [[x, y] for x, y in zip(xs, ys)]
                return [_transform(element) for element in coordinates]

            count = 0
            with open(tmp_geojson, "w", encoding="utf-8") as output:
                output.write('{"type":"FeatureCollection","features":[\n')
                first = True
                iterator = source.filter(bbox=bbox_filter) if bbox_filter else source
                for feature in iterator:
                    geometry = feature["geometry"]
                    if geometry is None:
                        continue
                    geometry_dict = dict(fiona_to_dict(geometry))
                    if "coordinates" in geometry_dict:
                        geometry_dict["coordinates"] = _transform(
                            geometry_dict["coordinates"]
                        )
                    else:
                        geometry_dict = fiona_to_dict(
                            transform_geom(source_crs, "EPSG:4326", geometry)
                        )
                    properties = (
                        dict(feature["properties"])
                        if feature.get("properties")
                        else {}
                    )
                    if not first:
                        output.write(",\n")
                    first = False
                    json.dump(
                        {
                            "type": "Feature",
                            "geometry": geometry_dict,
                            "properties": properties,
                        },
                        output,
                        ensure_ascii=False,
                        default=_json_default,
                    )
                    count += 1
                    if count % 20000 == 0:
                        print(
                            f"\r  {layer_name}: {count} features...",
                            end="",
                            flush=True,
                        )
                output.write("\n]}\n")
            if count >= 20000:
                print(flush=True)
    except BaseException as error:
        print(
            f"  ERROR fiona extraction {layer_name}: "
            f"{type(error).__name__}: {error}"
        )
        tmp_geojson.unlink(missing_ok=True)
        if not isinstance(error, Exception):
            raise
        return None

    if not tmp_geojson.exists() or tmp_geojson.stat().st_size == 0 or count == 0:
        print(f"  ⚠ {layer_name}: no feature")
        tmp_geojson.unlink(missing_ok=True)
        return None

    sortie_gz_part = dependances.chemin_part(sortie_gz)
    sortie_raw_part = (
        dependances.chemin_part(sortie_raw) if ecrire_geojson else None
    )
    try:
        source_name = sortie_gz.name.replace(".geojson.gz", "")
        streamed = dependances.streamer_geojson(
            tmp_geojson, sortie_gz_part, source_name
        )
        if streamed == 0:
            print(f"  ⚠ {layer_name}: 0 features after streaming")
            return None
        if ecrire_geojson:
            dependances.gunzip_vers_fichier(sortie_gz_part, sortie_raw_part)
        if not sortie_gz_part.exists() or sortie_gz_part.stat().st_size == 0:
            raise OSError("empty staged GeoJSON gzip")
        if ecrire_geojson and (
            not sortie_raw_part.exists() or sortie_raw_part.stat().st_size == 0
        ):
            raise OSError("empty staged GeoJSON")

        publications = []
        if ecrire_geojson:
            publications.append((sortie_raw_part, sortie_raw))
        if ecrire_gz:
            publications.append((sortie_gz_part, sortie_gz))
        _publier_formats_atomiquement(publications, dependances.chemin_part)

        principal = None
        if ecrire_gz:
            print(
                f"  {sortie_gz.name} : {streamed} features  "
                f"({sortie_gz.stat().st_size // 1024} Ko)  "
                f"{dependances.formater_duree(int(time.time() - started))}",
                flush=True,
            )
            principal = sortie_gz
        if ecrire_geojson:
            print(
                f"  {sortie_raw.name} : {streamed} features  "
                f"({sortie_raw.stat().st_size // 1024} Ko)"
            )
            if principal is None:
                principal = sortie_raw
        return principal
    except BaseException as error:
        if not isinstance(error, Exception):
            raise
        print(f"  ERROR publishing {layer_name}: {type(error).__name__}: {error}")
        return None
    finally:
        tmp_geojson.unlink(missing_ok=True)
        sortie_gz_part.unlink(missing_ok=True)
        if sortie_raw_part is not None:
            sortie_raw_part.unlink(missing_ok=True)
