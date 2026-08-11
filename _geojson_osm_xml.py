"""Conversion transactionnelle d'un GeoJSON IGN en OSM XML.

L'implémentation conserve le streaming et l'ordre nodes -> ways requis par
osmosis. Les coutures applicatives restent fournies par la façade
``lidar2map.py`` afin de préserver ses monkeypatches historiques.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _DependancesGeojsonOsmXml:
    """Services et valeurs relus par la façade avant chaque conversion."""

    chemin_part: Callable[[Path], Path]
    stop_event: Any
    layer_tags: Mapping[str, Mapping[str, str]]
    tags_pour_layer: Callable[[str], dict[str, str]]
    douglas_peucker: Callable[[Any, float], Any]
    epsilon_defaut: float


def geojson_ign_vers_osm_xml(
    geojson_path,
    osm_xml_path,
    epsilon=None,
    *,
    dependances: _DependancesGeojsonOsmXml,
):
    """
    Convertit un GeoJSON IGN (produit par telecharger_wfs / fusionner_geojson)
    en fichier OSM XML lisible par osmosis + mapwriter.

    Stratégie :
      - Points   → <node>
      - Lignes   → <way> avec <nd ref=…> (nœuds interpolés)
      - Polygones→ <way> fermé (outer ring uniquement pour MultiPolygon)

    Les tags OSM sont déduits du nom de couche (propriété 'source' ou nom fichier).
    Identifiants négatifs (convention OSM pour données non-officielles).

    Streaming : lit le GeoJSON via ijson (pas de json.load() qui ferait OOM
    sur 1 Go de données dept-scale). Écrit nodes et ways dans un fichier
    XML body temporaire au fil de l'eau, puis compose header + bounds + body
    + footer. Bounds calculés en passe unique (pas 4× _coords_flat).
    Format XML bit-fidèle à ElementTree (osmosis est un parseur Java strict).
    """
    from xml.sax.saxutils import escape as _xml_escape
    import decimal as _dec
    import traceback as _tb

    _chemin_part = dependances.chemin_part
    _stop_event = dependances.stop_event
    _IGN_LAYER_TAGS = dependances.layer_tags
    _tags_pour_layer = dependances.tags_pour_layer
    _douglas_peucker = dependances.douglas_peucker
    _IGN_SIMPLIFY_EPSILON = dependances.epsilon_defaut

    # Valeur d'attribut XML : délimitée par " → il faut aussi échapper les
    # guillemets doubles (saxutils.escape ne gère que & < >). Sinon un nom IGN
    # contenant " (ex: 'Circuit "le Serre Sommet"') casse le XML et osmosis
    # échoue au parsing. On échappe aussi ' par sûreté.
    def _xml_attr(s):
        return _xml_escape(str(s), {'"': "&quot;", "'": "&apos;"})

    geojson_path = Path(geojson_path)
    osm_xml_path = Path(osm_xml_path)
    _eps = epsilon if epsilon is not None else _IGN_SIMPLIFY_EPSILON
    _TS  = "1970-01-01T00:00:00Z"   # timestamp factice — requis par osmosis 0.6

    # ── Itérateur features (streaming si ijson dispo, fallback sinon) ────────
    def _iter_features():
        try:
            import ijson
        except ImportError:
            print("  ⚠ ijson missing - full RAM load of the GeoJSON")
            try:
                if geojson_path.suffix == ".gz":
                    with gzip.open(geojson_path, "rt", encoding="utf-8") as f:
                        gj = json.load(f)
                else:
                    gj = json.loads(geojson_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"  ERROR reading GeoJSON ({type(e).__name__}): {e}")
                return
            yield from gj.get("features", [])
            return

        try:
            opener = ((lambda: gzip.open(geojson_path, "rb"))
                      if geojson_path.suffix == ".gz"
                      else (lambda: open(geojson_path, "rb")))
            with opener() as f:
                yield from ijson.items(f, "features.item")
        except (OSError, ValueError) as e:
            # #10 : PROPAGER (ne pas `return`). Une erreur ijson mi-parcours
            # laissait un GeoJSON tronqué passer pour un flux terminé -> .map
            # partielle publiée. En levant, le handler de geojson_ign_vers_osm_xml
            # retourne False -> pas de .map depuis des données partielles.
            print(f"  ERROR streaming GeoJSON ({type(e).__name__}): {e}")
            raise

    # ── Helpers d'écriture XML brute (bien plus rapide qu'ElementTree) ───────
    def _f(v):
        """Convertit Decimal (ijson) → float ; passe-plat sinon."""
        return float(v) if isinstance(v, _dec.Decimal) else v

    def _emit_node(out, nid, lat, lon, tags=None):
        # Format reproduit ElementTree : ordre id/lat/lon/version/timestamp/visible,
        # self-closing avec espace avant slash, pas d'indentation.
        attrs = (f'id="{nid}" lat="{lat:.7f}" lon="{lon:.7f}" '
                 f'version="1" timestamp="{_TS}" visible="true"')
        if tags:
            out.write(f'<node {attrs}>')
            for k, v in tags.items():
                out.write(f'<tag k="{_xml_attr(k)}" v="{_xml_attr(v)}" />')
            out.write('</node>')
        else:
            out.write(f'<node {attrs} />')

    def _emit_way(out, wid, nd_refs, tags):
        out.write(f'<way id="{wid}" version="1" timestamp="{_TS}" visible="true">')
        for r in nd_refs:
            out.write(f'<nd ref="{r}" />')
        if tags:
            for k, v in tags.items():
                out.write(f'<tag k="{_xml_attr(k)}" v="{_xml_attr(v)}" />')
        out.write('</way>')

    # ── Compteurs et bounds (passe unique, sans _coords_flat × 4) ────────────
    state = {"node_id": -1, "way_id": -1, "nb_nodes": 0, "nb_ways": 0,
             "lon_min":  float("inf"),  "lon_max": float("-inf"),
             "lat_min":  float("inf"),  "lat_max": float("-inf"),
             "bounds_valid": False,
             "nb_inner_skipped": 0,   # rings intérieurs (trous) non émis
             "nb_rings_degen": 0}     # contours dégénérés (<3 sommets, R2#33)

    def _track_bounds(lon, lat):
        if lon < state["lon_min"]: state["lon_min"] = lon
        if lon > state["lon_max"]: state["lon_max"] = lon
        if lat < state["lat_min"]: state["lat_min"] = lat
        if lat > state["lat_max"]: state["lat_max"] = lat
        state["bounds_valid"] = True

    def _emit_node_track(out_nodes, lat, lon, tags=None):
        nid = state["node_id"]
        _emit_node(out_nodes, nid, lat, lon, tags)
        _track_bounds(lon, lat)
        state["nb_nodes"] += 1
        state["node_id"] -= 1
        return nid

    def _emit_linestring(out_nodes, out_ways, raw_coords, osm_tags):
        # Convertir Decimal→float : _douglas_peucker utilise math.hypot et
        # max(0.0, ...) qui ne supportent pas le mixage Decimal/float.
        coords = [(_f(c[0]), _f(c[1])) for c in raw_coords]
        coords = _douglas_peucker(coords, _eps)
        if len(coords) < 2:
            return
        nd_refs = [_emit_node_track(out_nodes, c[1], c[0]) for c in coords]
        wid = state["way_id"]
        _emit_way(out_ways, wid, nd_refs, osm_tags)
        state["nb_ways"] += 1
        state["way_id"] -= 1

    def _emit_ring(out_nodes, out_ways, raw_coords, osm_tags):
        coords = [(_f(c[0]), _f(c[1])) for c in raw_coords]
        coords = _douglas_peucker(coords, _eps)
        # Un anneau valide (aire non nulle) exige >=3 sommets DISTINCTS. Un
        # contour dégénéré — 2 sommets, ou points colinéaires réduits à 2 par la
        # simplification — donnait un "polygone" a->b->a d'aire nulle (nœud
        # dupliqué, segment nul) : mapsforge/osmosis le rejette ou le rend en
        # trait parasite (R2#33). On déduplique les sommets consécutifs, on
        # retire la fermeture pour compter, et on saute si < 3 distincts.
        dd = []
        for c in coords:
            if not dd or c != dd[-1]:
                dd.append(c)
        if len(dd) >= 2 and dd[0] == dd[-1]:
            dd.pop()                       # retirer la fermeture avant le compte
        if len(dd) < 3:
            state["nb_rings_degen"] += 1
            return
        nd_refs = [_emit_node_track(out_nodes, c[1], c[0]) for c in dd]
        nd_refs.append(nd_refs[0])         # fermeture explicite du contour
        wid = state["way_id"]
        _emit_way(out_ways, wid, nd_refs, osm_tags)
        state["nb_ways"] += 1
        state["way_id"] -= 1

    # ── Passe unique : streaming features → 2 fichiers temporaires ───────────
    # OSM XML impose strictement l'ordre nodes → ways → relations (osmosis
    # plante sinon). On écrit donc nodes et ways dans des fichiers séparés
    # puis on les concatène dans l'ordre.
    nodes_tmp = _chemin_part(
        osm_xml_path.parent / (osm_xml_path.name + ".nodes")
    )
    ways_tmp = _chemin_part(
        osm_xml_path.parent / (osm_xml_path.name + ".ways")
    )
    nodes_tmp.parent.mkdir(parents=True, exist_ok=True)

    out_nodes = None
    out_ways  = None
    # R2#32 : repli sur le nom de fichier. Une couche WFS mono-couche téléchargée
    # par telecharger_wfs n'a PAS de propriété 'source' sur ses features (seule
    # fusionner_geojson l'ajoute). Sans repli, layer_short restait "" → tags
    # {"note": ""} → mapwriter ignorait la couche (carte vide). Le nom du fichier
    # (`<zone>_ign_<layer>.geojson[.gz]`) porte la clé de couche, comme la
    # convention de fusion et comme le repli déjà présent dans _overlay_style_key.
    _src_fallback = geojson_path.name
    try:
        out_nodes = open(nodes_tmp, "w", encoding="utf-8")
        out_ways  = open(ways_tmp,  "w", encoding="utf-8")
        for feat in _iter_features():
            if _stop_event.is_set():
                raise KeyboardInterrupt("Interrompu par utilisateur")
            props = feat.get("properties") or {}
            geom  = feat.get("geometry")
            if not geom:
                continue

            # Déduire le layer depuis la propriété 'source' (ex: "gareoult_ign_cours_d_eau")
            src = props.get("source", "") or _src_fallback
            layer_short = ""
            for k in _IGN_LAYER_TAGS:
                if k in src:
                    layer_short = k
                    break
            osm_tags = _tags_pour_layer(layer_short)
            # Ajouter le nom si disponible
            for name_key in ("nom", "name", "toponyme", "libelle", "NOM"):
                if props.get(name_key):
                    osm_tags = dict(osm_tags)
                    osm_tags["name"] = str(props[name_key])
                    break

            gtype = geom.get("type", "")
            coords = geom.get("coordinates", [])

            if gtype == "Point":
                _emit_node_track(out_nodes, _f(coords[1]), _f(coords[0]), osm_tags)
            elif gtype == "MultiPoint":
                for pt in coords:
                    _emit_node_track(out_nodes, _f(pt[1]), _f(pt[0]), osm_tags)
            elif gtype == "LineString":
                _emit_linestring(out_nodes, out_ways, coords, osm_tags)
            elif gtype == "MultiLineString":
                for line in coords:
                    _emit_linestring(out_nodes, out_ways, line, osm_tags)
            elif gtype == "Polygon":
                if coords:
                    _emit_ring(out_nodes, out_ways, coords[0], osm_tags)
                    state["nb_inner_skipped"] += max(0, len(coords) - 1)
            elif gtype == "MultiPolygon":
                for poly in coords:
                    if poly:
                        _emit_ring(out_nodes, out_ways, poly[0], osm_tags)
                        state["nb_inner_skipped"] += max(0, len(poly) - 1)
            elif gtype == "GeometryCollection":
                for sub in geom.get("geometries", []):
                    sub_coords = sub.get("coordinates", [])
                    sub_type   = sub.get("type", "")
                    if sub_type == "Point":
                        _emit_node_track(out_nodes, _f(sub_coords[1]),
                                                    _f(sub_coords[0]), osm_tags)
                    elif sub_type == "LineString":
                        _emit_linestring(out_nodes, out_ways, sub_coords, osm_tags)
                    elif sub_type == "MultiLineString":
                        for line in sub_coords:
                            _emit_linestring(out_nodes, out_ways, line, osm_tags)
                    elif sub_type == "Polygon" and sub_coords:
                        _emit_ring(out_nodes, out_ways, sub_coords[0], osm_tags)
                        state["nb_inner_skipped"] += max(0, len(sub_coords) - 1)
                    elif sub_type == "MultiPolygon":
                        for poly in sub_coords:
                            if poly:
                                _emit_ring(out_nodes, out_ways, poly[0], osm_tags)
                                state["nb_inner_skipped"] += max(0, len(poly) - 1)
        out_nodes.close(); out_nodes = None
        out_ways.close();  out_ways  = None
    except KeyboardInterrupt:
        if out_nodes: out_nodes.close()
        if out_ways:  out_ways.close()
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)
        raise
    except Exception:
        print("\n  ERROR in geojson_ign_vers_osm_xml:")
        _tb.print_exc()
        if out_nodes: out_nodes.close()
        if out_ways:  out_ways.close()
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)
        return False

    if state["nb_nodes"] == 0:
        print("  Empty GeoJSON - nothing to convert.")
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)
        return False

    # ── Composition du XML final : header + bounds + nodes + ways + footer ───
    # Format reproduit fidèlement ElementTree.write(xml_declaration=True) :
    # prologue avec apostrophes simples, encoding utf-8 minuscule.
    try:
        osm_xml_part = _chemin_part(osm_xml_path)
    except BaseException:
        # La création du troisième chemin de staging intervient après l'écriture
        # des bodies. Préserver l'exception historique, sans laisser ces deux
        # fichiers temporaires orphelins.
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)
        raise
    try:
        with open(osm_xml_part, "w", encoding="utf-8") as out:
            out.write("<?xml version='1.0' encoding='utf-8'?>\n")
            out.write('<osm version="0.6" generator="lidar2map">')
            if state["bounds_valid"]:
                # <bounds> requis par mapsforge mapwriter pour initialiser le tile store
                out.write(
                    f'<bounds minlat="{state["lat_min"]:.7f}"'
                    f' minlon="{state["lon_min"]:.7f}"'
                    f' maxlat="{state["lat_max"]:.7f}"'
                    f' maxlon="{state["lon_max"]:.7f}" />'
                )
            # Concat des bodies en chunks de 64 KB (pas de read() global)
            for tmp in (nodes_tmp, ways_tmp):
                with open(tmp, "r", encoding="utf-8") as src:
                    while True:
                        chunk = src.read(1 << 16)
                        if not chunk:
                            break
                        out.write(chunk)
            out.write('</osm>')
        if osm_xml_part.stat().st_size <= 0:
            raise IOError("OSM XML staging file is empty")
        osm_xml_part.replace(osm_xml_path)
    except KeyboardInterrupt:
        osm_xml_part.unlink(missing_ok=True)
        raise
    except Exception:
        print("\n  ERROR publishing OSM XML:")
        _tb.print_exc()
        osm_xml_part.unlink(missing_ok=True)
        return False
    finally:
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)

    sz = osm_xml_path.stat().st_size / 1e6
    print(f"  OSM XML: {state['nb_nodes']} nodes, {state['nb_ways']} ways "
          f"→ {osm_xml_path.name} ({sz:.1f} MB)")
    if state["nb_inner_skipped"]:
        # Mapsforge mapwriter ne supporte pas les multi-polygones avec trous via
        # OSM XML (il faut des relations type=multipolygon, hors scope ici).
        # On documente la perte plutôt que de la cacher.
        print(f"  ⚠ {state['nb_inner_skipped']} inner ring(s) skipped "
              f"(polygon holes, not supported in .map output)")
    if state["nb_rings_degen"]:
        print(f"  ⚠ {state['nb_rings_degen']} degenerate ring(s) skipped "
              f"(< 3 distinct vertices, zero-area)")
    return True
