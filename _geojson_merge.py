"""Fusion GeoJSON streamée et publication atomique."""

from dataclasses import dataclass
import decimal
import gzip
import json
from pathlib import Path


@dataclass(frozen=True)
class DependancesFusionGeojson:
    """Coutures applicatives relues par la façade à chaque appel."""

    chemin_part: object
    stop_event: object
    lire_geojson: object


def lire_geojson(chemin):
    """Lit un ``.geojson`` ou ``.geojson.gz`` et retourne son dictionnaire."""
    path = Path(chemin)
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding="utf-8"))


def fusionner_geojson(fichiers, sortie, fichiers_ignores=None, *, dependances):
    """Fusionne plusieurs GeoJSON en une FeatureCollection streamée.

    Retourne ``(chemin, bbox)`` ou ``(None, None)`` si aucune entité n'est
    disponible. Les sources absentes, illisibles ou tronquées sont ajoutées à
    ``fichiers_ignores`` lorsque cette liste est fournie.
    """
    try:
        import ijson

        has_ijson = True
    except ImportError:
        has_ijson = False

    sortie = Path(sortie)
    compresser = str(sortie).endswith(".gz")

    sortie_resolue = sortie.resolve()
    nombre_sources = len(fichiers)
    fichiers = [
        fichier for fichier in fichiers
        if Path(fichier).resolve() != sortie_resolue
    ]
    if len(fichiers) < nombre_sources:
        print(
            f"  (sortie exclue des sources, anti auto-fusion : {sortie.name})",
            flush=True,
        )

    sortie.parent.mkdir(parents=True, exist_ok=True)
    part = dependances.chemin_part(sortie)

    def encoder_decimal(objet):
        if isinstance(objet, decimal.Decimal):
            return float(objet)
        raise TypeError(f"Type non-sérialisable : {type(objet).__name__}")

    nom = sortie.name.replace(".geojson.gz", "").replace(".geojson", "")
    entete = (
        '{"type":"FeatureCollection","name":'
        + json.dumps(nom, ensure_ascii=False)
        + ',"crs":{"type":"name","properties":'
          '{"name":"urn:ogc:def:crs:OGC:1.3:CRS84"}}'
        + ',"features":['
    ).encode("utf-8")

    limites = {
        "lon_min": float("inf"),
        "lon_max": float("-inf"),
        "lat_min": float("inf"),
        "lat_max": float("-inf"),
        "valid": False,
    }

    def suivre(lon, lat):
        limites["lon_min"] = min(limites["lon_min"], lon)
        limites["lon_max"] = max(limites["lon_max"], lon)
        limites["lat_min"] = min(limites["lat_min"], lat)
        limites["lat_max"] = max(limites["lat_max"], lat)
        limites["valid"] = True

    def suivre_geometrie(geometrie):
        if not geometrie:
            return
        type_geometrie = geometrie.get("type", "")
        coordonnees = geometrie.get("coordinates", [])
        if type_geometrie == "Point" and coordonnees:
            suivre(float(coordonnees[0]), float(coordonnees[1]))
        elif type_geometrie in ("MultiPoint", "LineString"):
            for point in coordonnees:
                suivre(float(point[0]), float(point[1]))
        elif type_geometrie in ("MultiLineString", "Polygon"):
            for ligne in coordonnees:
                for point in ligne:
                    suivre(float(point[0]), float(point[1]))
        elif type_geometrie == "MultiPolygon":
            for polygone in coordonnees:
                for ligne in polygone:
                    for point in ligne:
                        suivre(float(point[0]), float(point[1]))
        elif type_geometrie == "GeometryCollection":
            for sous_geometrie in geometrie.get("geometries", []):
                suivre_geometrie(sous_geometrie)

    def iterer_features(path):
        source = path.stem.replace(".geojson", "")
        if has_ijson:
            ouvrir = (
                (lambda: gzip.open(path, "rb"))
                if str(path).endswith(".gz")
                else (lambda: open(path, "rb"))
            )
            nombre_emis = 0
            try:
                with ouvrir() as stream:
                    for feature in ijson.items(stream, "features.item"):
                        nombre_emis += 1
                        yield source, feature
                return
            except Exception as exc:
                if nombre_emis:
                    print(
                        f"  WARNING: {path.name} truncated after {nombre_emis} "
                        f"features ({exc}) - partial source skipped"
                    )
                    if fichiers_ignores is not None:
                        fichiers_ignores.append(path.name)
                    return
                print(
                    f"  WARNING: {path.name} streaming failed ({exc}) "
                    "- RAM fallback"
                )
        try:
            donnees = dependances.lire_geojson(path)
        except Exception as exc:
            print(f"  WARNING: {path.name} illisible ({exc}) - skipped")
            if fichiers_ignores is not None:
                fichiers_ignores.append(path.name)
            return
        for feature in donnees.get("features", []):
            yield source, feature

    total = 0
    flux_sortie = None
    try:
        if compresser:
            flux_sortie = gzip.open(part, "wb", compresslevel=6)
        else:
            flux_sortie = open(part, "wb")
        flux_sortie.write(entete)
        premiere_feature = True

        for fichier in fichiers:
            path = Path(fichier)
            if not path.exists() and not str(path).endswith(".gz"):
                path_gz = Path(str(path) + ".gz")
                if path_gz.exists():
                    path = path_gz
            if not path.exists():
                print(f"  WARNING: {path.name} not found - skipped")
                if fichiers_ignores is not None:
                    fichiers_ignores.append(path.name)
                continue

            nombre_fichier = 0
            for source, feature in iterer_features(path):
                if dependances.stop_event.is_set():
                    raise KeyboardInterrupt("Fusion interrompue")
                proprietes = feature.get("properties") or {}
                if not isinstance(proprietes, dict):
                    proprietes = {}
                proprietes.setdefault("source", source)
                feature["properties"] = proprietes
                suivre_geometrie(feature.get("geometry"))

                if not premiere_feature:
                    flux_sortie.write(b",")
                premiere_feature = False
                flux_sortie.write(json.dumps(
                    feature,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    default=encoder_decimal,
                ).encode("utf-8"))
                nombre_fichier += 1
            total += nombre_fichier
            print(f"  {path.name} : {nombre_fichier} features")

        flux_sortie.write(b"]}")
        flux_sortie.close()
        flux_sortie = None
    except BaseException:
        if flux_sortie is not None:
            try:
                flux_sortie.close()
            except Exception:
                pass
        part.unlink(missing_ok=True)
        raise

    if total == 0:
        part.unlink(missing_ok=True)
        print("  No feature to merge")
        return None, None

    try:
        part.replace(sortie)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    taille = sortie.stat().st_size // 1024
    print(f"  → {sortie.name} : {total} features  ({taille} Ko)")

    bbox = None
    if limites["valid"]:
        bbox = (
            limites["lon_min"],
            limites["lat_min"],
            limites["lon_max"],
            limites["lat_max"],
        )
    return sortie, bbox
