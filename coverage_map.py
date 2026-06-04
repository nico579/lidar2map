#!/usr/bin/env python3
"""coverage_map.py — génère coverage.geojson : un polygone administratif par
zone LiDAR couverte. GitHub rend nativement ce GeoJSON en carte interactive.

Le titre de chaque zone vient du NAME du provider (lu dans providers/*.py) —
MÊME source que la liste de providers de la GUI (_discover_providers) → la carte
et la GUI ne peuvent pas diverger. Garde-fou : un code de REGIONS qui ne
correspond à aucun provider fait échouer la génération. Régénérer après
ajout/retrait d'un provider.

Contours : Nominatim (OSM), polygon_geojson, simplifiés (~1 km via shapely).
Style : simplestyle-spec (fill/stroke) lu par le rendu GitHub.
"""
import glob, importlib.util, json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "lidar2map-coverage/1.0 (https://github.com/nico579/lidar2map)"

# (requête Nominatim, [codes provider], couleur, clip|None, label_groupe|None)
# label_groupe : titre quand >1 provider partagent une zone ; sinon le titre =
# NAME du provider unique (lu depuis son module).
# clip (lon_min,lat_min,lon_max,lat_max) : ne garder que les sous-polygones dans
# cette emprise — drop des territoires lointains non couverts (Caraïbes NL,
# Svalbard/Bouvet NO).
REGIONS = [
    ("France métropolitaine",  ["fr-ign"],           "#3b82f6", None, None),
    ("Nederland",              ["nl-ahn"],           "#22c55e", (3.0, 50.5, 7.5, 53.8), None),
    ("Schweiz",                ["ch-swisstopo"],     "#ef4444", None, None),
    ("Norge",                  ["no-kartverket"],    "#8b5cf6", (4.0, 57.5, 31.5, 71.5), None),
    ("Bayern, Deutschland",    ["de-bayern"],        "#f59e0b", None, None),
    ("Nordrhein-Westfalen",    ["de-nrw"],           "#f59e0b", None, None),
    ("Niedersachsen",          ["de-niedersachsen"], "#f59e0b", None, None),
    ("Tirol, Österreich",      ["at-tirol", "at-osttirol"], "#eab308", None,
     "Autriche — Tyrol (Nordtirol + Osttirol)"),
    ("England",                ["gb-england"],       "#78350f", None, None),
]


def load_providers():
    """{CODE: NAME} pour tous les providers/*.py — même source que la GUI."""
    prov = {}
    for path in sorted(glob.glob(os.path.join(HERE, "providers", "*.py"))):
        if os.path.basename(path).startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(
            "prov_" + os.path.basename(path)[:-3], path)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
        except Exception as e:
            print(f"    (skip {os.path.basename(path)}: {e})")
            continue
        code = getattr(m, "CODE", None)
        if code:
            prov[code] = getattr(m, "NAME", None) or code
    return prov


def fetch_polygon(query):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": query, "format": "jsonv2", "polygon_geojson": 1, "limit": 5})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        results = json.load(r)
    for res in results:
        g = res.get("geojson")
        if g and g.get("type") in ("Polygon", "MultiPolygon"):
            return g
    return None


def clip_multipolygon(geom, clip):
    """Ne garde que les sous-polygones dont la bbox intersecte `clip`."""
    if not clip or geom.get("type") != "MultiPolygon":
        return geom
    cx0, cy0, cx1, cy1 = clip
    kept = []
    for poly in geom["coordinates"]:
        ring = poly[0]
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        if not (max(xs) < cx0 or min(xs) > cx1 or max(ys) < cy0 or min(ys) > cy1):
            kept.append(poly)
    return {"type": "MultiPolygon", "coordinates": kept} if kept else geom


def simplify(geom, tol=0.01):
    try:
        from shapely.geometry import shape, mapping
        return mapping(shape(geom).simplify(tol, preserve_topology=True))
    except Exception as e:
        print(f"    (pas de simplif shapely: {e})")
        return geom


def main():
    prov = load_providers()
    # Garde-fou : tout code de REGIONS doit exister comme provider (anti-drift).
    codes = {c for r in REGIONS for c in r[1]}
    missing = sorted(c for c in codes if c not in prov)
    if missing:
        print(f"  ERREUR : codes provider introuvables dans providers/ : {missing}")
        return 1

    features = []
    for query, region_codes, color, clip, group in REGIONS:
        title = group or (prov[region_codes[0]] if len(region_codes) == 1
                          else " + ".join(prov[c] for c in region_codes))
        print(f"  {query}  ->  {title}", flush=True)
        g = fetch_polygon(query)
        if not g:
            print(f"    /!\\ pas de polygone pour {query}")
            continue
        g = simplify(clip_multipolygon(g, clip))
        features.append({
            "type": "Feature",
            "properties": {
                "title": title,
                "providers": region_codes,
                "description": "Provider(s) : " + ", ".join(region_codes),
                "fill": color, "fill-opacity": 0.35,
                "stroke": color, "stroke-width": 1.5,
            },
            "geometry": g,
        })
        time.sleep(1.1)   # Nominatim : 1 req/s

    fc = {"type": "FeatureCollection", "features": features}
    out = os.path.join(HERE, "coverage.geojson")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"\ncoverage.geojson : {len(features)} zones, {os.path.getsize(out)//1024} Ko")
    return 0 if len(features) == len(REGIONS) else 1


if __name__ == "__main__":
    sys.exit(main())
