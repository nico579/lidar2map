#!/usr/bin/env python3
"""coverage_map.py — génère coverage.geojson : un polygone administratif par
zone LiDAR couverte. GitHub rend nativement ce GeoJSON en carte interactive
(page du fichier). Régénérer après ajout/retrait d'un provider.

Contours : Nominatim (OSM), polygon_geojson, simplifiés (~1 km via shapely).
Style : simplestyle-spec (fill/stroke) lu par le rendu GitHub.
"""
import json, os, sys, time, urllib.parse, urllib.request

UA = "lidar2map-coverage/1.0 (https://github.com/nico579/lidar2map)"

# (requête Nominatim, label, [providers], couleur, clip_bbox|None)
# clip_bbox (lon_min, lat_min, lon_max, lat_max) : ne garder que les sous-
# polygones dans cette emprise — drop des territoires lointains (Caraïbes
# néerlandaises, Svalbard/île Bouvet norvégiennes) qui ne sont pas couverts.
REGIONS = [
    ("France métropolitaine",  "France — IGN LiDAR HD",         ["fr-ign"],           "#3b82f6", None),
    ("Nederland",              "Pays-Bas — AHN",                ["nl-ahn"],           "#22c55e", (3.0, 50.5, 7.5, 53.8)),
    ("Schweiz",                "Suisse — swissALTI3D",          ["ch-swisstopo"],     "#ef4444", None),
    ("Norge",                  "Norvège — Kartverket",          ["no-kartverket"],    "#8b5cf6", (4.0, 57.5, 31.5, 71.5)),
    ("Bayern, Deutschland",    "Allemagne — Bavière (DGM1)",    ["de-bayern"],        "#f59e0b", None),
    ("Nordrhein-Westfalen",    "Allemagne — NRW (DGM1)",        ["de-nrw"],           "#f59e0b", None),
    ("Niedersachsen",          "Allemagne — Basse-Saxe (DGM1)", ["de-niedersachsen"], "#f59e0b", None),
    ("Tirol, Österreich",      "Autriche — Tyrol + Osttirol",   ["at-tirol", "at-osttirol"], "#14b8a6", None),
]


def clip_multipolygon(geom, clip):
    """Ne garde que les sous-polygones dont la bbox intersecte `clip`
    (drop Caraïbes NL, Svalbard/Bouvet NO). No-op si clip None ou pas un
    MultiPolygon."""
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


def fetch_polygon(query):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": query, "format": "jsonv2", "polygon_geojson": 1, "limit": 5})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        results = json.load(r)
    # 1er résultat administratif avec un (multi)polygone
    for res in results:
        g = res.get("geojson")
        if g and g.get("type") in ("Polygon", "MultiPolygon"):
            return g, res.get("display_name", query)
    return None, query


def simplify(geom, tol=0.01):
    try:
        from shapely.geometry import shape, mapping
        return mapping(shape(geom).simplify(tol, preserve_topology=True))
    except Exception as e:
        print(f"    (pas de simplif shapely: {e})")
        return geom


def main():
    features = []
    for query, label, providers, color, clip in REGIONS:
        print(f"  {query} ...", flush=True)
        g, name = fetch_polygon(query)
        if not g:
            print(f"    /!\\ pas de polygone pour {query}")
            continue
        g = clip_multipolygon(g, clip)
        g = simplify(g)
        features.append({
            "type": "Feature",
            "properties": {
                "title": label,
                "description": "Providers : " + ", ".join(providers),
                "providers": providers,
                "fill": color, "fill-opacity": 0.35,
                "stroke": color, "stroke-width": 1.5,
            },
            "geometry": g,
        })
        time.sleep(1.1)   # Nominatim : 1 req/s

    fc = {"type": "FeatureCollection", "features": features}
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coverage.geojson")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"\n{os.path.basename(out)} : {len(features)} zones, {os.path.getsize(out)//1024} Ko")
    return 0 if len(features) == len(REGIONS) else 1


if __name__ == "__main__":
    sys.exit(main())
