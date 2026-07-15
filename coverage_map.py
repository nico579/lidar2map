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
import glob, importlib.util, json, os, re, sys, time, urllib.parse, urllib.request

# Console Windows cp1252 : les noms natifs (Česko, Österreich…) planteraient
# les print — forcer UTF-8 (best effort).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
    ("Sverige",                ["se-lantmateriet"],  "#1e40af", (10.5, 55.0, 24.5, 69.5), None),
    ("Bayern, Deutschland",    ["de-bayern"],        "#f59e0b", None, None),
    ("Nordrhein-Westfalen",    ["de-nrw"],           "#f59e0b", None, None),
    ("Niedersachsen",          ["de-niedersachsen"], "#f59e0b", None, None),
    ("Thüringen",              ["de-thueringen"],    "#f59e0b", None, None),
    ("Hessen, Deutschland",    ["de-hessen"],        "#f59e0b", None, None),
    ("Baden-Württemberg",      ["de-bw"],            "#f59e0b", None, None),
    ("Mecklenburg-Vorpommern", ["de-mv"],            "#f59e0b", None, None),
    ("Sachsen-Anhalt",         ["de-st"],            "#f59e0b", None, None),
    ("Brandenburg",            ["de-brandenburg"],   "#f59e0b", None, None),
    ("Schleswig-Holstein",     ["de-sh"],            "#f59e0b", None, None),
    ("Berlin",                 ["de-berlin"],        "#f59e0b", (13.05, 52.32, 13.77, 52.68),
     "Berlin — DGM1 1 m (ATOM/XYZ)"),
    ("Rheinland-Pfalz",        ["de-rlp"],           "#f59e0b", None, None),
    ("Österreich",             ["at-bev", "at-tirol", "at-osttirol"], "#eab308", None,
     "Autriche — BEV 1 m (national) + Tyrol 0,5 m"),
    ("England",                ["gb-england"],       "#78350f", None, None),
    ("Wales",                  ["gb-wales"],         "#78350f", None, None),
    ("Scotland",               ["gb-scotland"],      "#78350f", (-8.8, 54.5, -0.5, 61.2), None),
    ("Vlaanderen",             ["be-flanders"],      "#a855f7", None, None),
    ("Luxembourg",             ["lu-act"],           "#fb7185", None, None),
    ("Suomi",                  ["fi-maanmittauslaitos"], "#06b6d4", (19.0, 59.0, 32.0, 70.6), None),
    ("Danmark",                ["dk-datafordeler"],  "#ec4899", (7.5, 54.4, 15.6, 58.0), None),
    ("Ireland",                ["ie-gsi"],           "#0d9488", None, None),
    ("Česko",                  ["cz-cuzk"],          "#84cc16", None, None),
    ("Slovenija",              ["si-arso"],          "#14b8a6", None, None),
    ("Eesti",                  ["ee-maaamet"],       "#d946ef", (21.5, 57.4, 28.3, 59.9), None),
    ("Latvija",                ["lv-lgia"],          "#c026d3", (20.9, 55.6, 28.3, 58.1),
     "Lettonie — DTM 1 m (LĢIA, LiDAR national)"),
    ("España",                 ["es-cnig"],          "#fb923c", (-10.0, 35.5, 4.6, 44.5), None),
    ("Euskadi, España",        ["es-euskadi"],       "#fb923c", (-3.5, 42.4, -1.7, 43.5),
     "Pays basque — MDT LiDAR 1 m"),
    ("Navarra, España",        ["es-navarra"],       "#fb923c", (-2.5, 41.9, -0.7, 43.3),
     "Navarre — MDT LiDAR 2 m"),
    ("Portugal continental",   ["pt-dgt"],           "#0ea5e9", (-9.9, 36.8, -6.0, 42.3),
     "Portugal — MDT LiDAR 50 cm (DGT)"),
    ("Emilia-Romagna, Italia", ["it-emilia-romagna"], "#7c3aed", None,
     "Italie — Émilie-Romagne (DTM 5 m)"),
    ("Sardegna, Italia",       ["it-sardegna"],      "#7c3aed", (8.1, 38.85, 9.85, 41.3),
     "Italie — Sardaigne (DTM 1 m, mosaïque à trous)"),
    ("Polska",                 ["pl-gugik"],         "#4f46e5", None, None),
    ("Northern Mariana Islands", ["us-cnmi"],        "#0891b2", (144.8, 13.2, 146.2, 15.4),
     "Mariannes du Nord (CNMI, US) — Topobathy DEM 1 m (NOAA)"),
    ("Taal Lake",              ["ph-taal"],          "#f43f5e", (120.85, 13.85, 121.15, 14.18),
     "Philippines (volcan Taal) — DTM 1 m (UP TCAGP), zone ~20 km"),
    ("New Zealand",            ["nz-linz"],          "#10b981", (165.0, -48.0, 179.5, -34.0), None),
    ("Queensland",             ["au-qld"],           "#e11d48", (137.0, -29.5, 154.5, -9.0), None),
    ("New South Wales",        ["au-nsw"],           "#0284c7", (140.0, -38.0, 154.5, -27.5), None),
]


# Source UNIQUE du compte + de la liste de pays affichés dans les READMEs.
# Ordre = ordre d'affichage ; noms (EN, FR). Un COUNTRY de provider absent d'ici
# fait échouer la génération (anti-drift, comme le garde-fou REGIONS). Ajouter un
# pays = 1 ligne ici, puis relancer ce script : les 2 READMEs se mettent à jour.
COUNTRY_NAMES = [
    ("fr", "France", "France"),
    ("gb", "UK", "Royaume-Uni"),
    ("de", "Germany", "Allemagne"),
    ("at", "Austria", "Autriche"),
    ("nl", "Netherlands", "Pays-Bas"),
    ("ch", "Switzerland", "Suisse"),
    ("no", "Norway", "Norvège"),
    ("be", "Belgium", "Belgique"),
    ("lu", "Luxembourg", "Luxembourg"),
    ("fi", "Finland", "Finlande"),
    ("dk", "Denmark", "Danemark"),
    ("se", "Sweden", "Suède"),
    ("ie", "Ireland", "Irlande"),
    ("cz", "Czechia", "Tchéquie"),
    ("si", "Slovenia", "Slovénie"),
    ("ee", "Estonia", "Estonie"),
    ("lv", "Latvia", "Lettonie"),
    ("es", "Spain", "Espagne"),
    ("pt", "Portugal", "Portugal"),
    ("it", "Italy", "Italie"),
    ("pl", "Poland", "Pologne"),
    ("us", "USA", "USA"),
    ("ca", "Canada", "Canada"),
    ("nz", "New Zealand", "Nouvelle-Zélande"),
    ("au", "Australia", "Australie"),
    ("ph", "Philippines", "Philippines"),
    ("jp", "Japan", "Japon"),
]

# READMEs et langue : les marqueurs <!--N-->…<!--/N--> (compte) et
# <!--LIST-->…<!--/LIST--> (liste) sont remplacés en place.
_README_LANG = [("README_Github.md", "en"), ("README_Github.fr.md", "fr")]


def update_readme_countries(prov):
    """Injecte le compte + la liste de pays entre les marqueurs des 2 READMEs.
    Source = COUNTRY_NAMES (ordre + noms) filtré par les pays réellement couverts
    par un provider. Retourne False (et n'écrit rien) si un pays de provider n'a
    pas de nom déclaré — garde-fou anti-drift."""
    prov_countries = {p["country"] for p in prov.values() if p["country"]}
    known = {c for c, _, _ in COUNTRY_NAMES}
    missing = sorted(prov_countries - known)
    if missing:
        print(f"  ERREUR : COUNTRY de provider sans nom dans COUNTRY_NAMES : {missing}")
        return False
    rows = [(c, en, fr) for c, en, fr in COUNTRY_NAMES if c in prov_countries]
    n = len(rows)
    liste = {"en": ", ".join(en for _, en, _ in rows),
             "fr": ", ".join(fr for _, _, fr in rows)}
    for fname, lang in _README_LANG:
        path = os.path.join(HERE, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            txt = f.read()
        txt = re.sub(r"<!--N-->.*?<!--/N-->", f"<!--N-->{n}<!--/N-->", txt, flags=re.S)
        txt = re.sub(r"<!--LIST-->.*?<!--/LIST-->",
                     f"<!--LIST-->{liste[lang]}<!--/LIST-->", txt, flags=re.S)
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
    print(f"  READMEs : {n} pays injectés (compte + liste)")
    return True


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
            name = getattr(m, "NAME", None) or code
            # Résolution apposée si absente du nom officiel — même règle que le
            # sélecteur GUI (buildProviders/hasRes dans gui/app.js) : les NAME
            # ne portent plus la résolution descriptive, elle vient de
            # RESOLUTION_M. Garder les deux affichages alignés.
            res = getattr(m, "RESOLUTION_M", None)
            if res and not re.search(r"\d[\d.,]*\s?(m|cm)\b", name, re.I):
                name = f"{name} ({res:g} m)"
            prov[code] = {"name":    name,
                          "country": getattr(m, "COUNTRY", "") or ""}
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


def render_png(features, out_png, n_pays=None, lang="fr"):
    """Carte PNG colorée : Europe (principal) + encart Nouvelle-Zélande + légende.
    Optionnel — nécessite matplotlib (outil dev `pip install matplotlib`, PAS le
    bundle app). Les polygones geojson EUX-MÊMES sont les contours des pays
    (Nominatim) → pas besoin de fond de carte/coastline."""
    try:
        import math
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"  (PNG non généré — matplotlib absent : {e})")
        return
    EU = (-11, 31, 35.5, 71.5)      # lon_min, lon_max, lat_min, lat_max
    NZ = (137.0, 180.0, -47.5, -9.0)  # Océanie : Australie (est) + Nouvelle-Zélande

    def cen_lon(geom):
        ring = (geom["coordinates"][0][0] if geom["type"] == "MultiPolygon"
                else geom["coordinates"][0])
        return sum(p[0] for p in ring) / len(ring)

    def draw(ax, feats):
        for ft in feats:
            g = ft["geometry"]; col = ft["properties"]["fill"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                ext = poly[0]
                ax.fill([p[0] for p in ext], [p[1] for p in ext],
                        facecolor=col, edgecolor=col, alpha=0.55, linewidth=0.5)

    eu = [f for f in features if cen_lon(f["geometry"]) < 100]
    nz = [f for f in features if cen_lon(f["geometry"]) >= 100]

    # Carte seule, sans bloc-légende (la liste des pays vit en texte dans le
    # README, sous l'image). On étiquette juste les grands pays directement sur
    # la carte (les petits du cluster Europe centrale restent identifiés par
    # leur forme + la liste texte).
    BIG = {"fr-ign", "no-kartverket", "fi-maanmittauslaitos", "es-cnig",
           "pl-gugik", "gb-england", "gb-scotland", "se-lantmateriet"}
    fig = plt.figure(figsize=(8.5, 9.2), dpi=120)
    fig.patch.set_facecolor("#f8fafc")
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.93]); ax.set_facecolor("#eaf2fb")
    draw(ax, eu)
    for ft in eu:
        codes = set(ft["properties"].get("providers", []))
        if codes & BIG:
            g = ft["geometry"]
            ring = (g["coordinates"][0][0] if g["type"] == "MultiPolygon"
                    else g["coordinates"][0])
            cx = sum(p[0] for p in ring) / len(ring)
            cy = sum(p[1] for p in ring) / len(ring)
            ax.text(cx, cy, ft["properties"].get("label", ""), fontsize=8,
                    ha="center", va="center", color="#1e293b", weight="bold")
    ax.set_xlim(EU[0], EU[1]); ax.set_ylim(EU[2], EU[3])
    ax.set_aspect(1 / math.cos(math.radians(53)))
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#cbd5e1")
    # Deux images par langue (coverage.png = EN pour README.md,
    # coverage.fr.png = FR pour README.fr.md). Compte de pays calculé depuis
    # REGIONS (anti-drift, plus de "16" en dur).
    if lang == "en":
        _pays = f"{n_pays} countries" if n_pays else "multi-country"
        titre = (f"lidar2map — bare-earth LiDAR coverage\n"
                 f"({len(features)} zones, {_pays} + USA · Canada · Japan project-based)")
    else:
        _pays = f"{n_pays} pays" if n_pays else "multi-pays"
        titre = (f"lidar2map — couverture LiDAR sol-nu\n"
                 f"({len(features)} zones, {_pays} + USA · Canada · Japon par projet)")
    ax.set_title(titre, fontsize=11, weight="bold")
    if nz:
        axn = ax.inset_axes([0.58, 0.0, 0.41, 0.40]); axn.set_facecolor("#eaf2fb")
        draw(axn, nz)
        axn.set_xlim(NZ[0], NZ[1]); axn.set_ylim(NZ[2], NZ[3])
        axn.set_aspect(1 / math.cos(math.radians(28)))
        axn.set_xticks([]); axn.set_yticks([])
        axn.set_title("Oceania — AU (QLD·NSW) + NZ" if lang == "en"
                      else "Océanie — AU (QLD·NSW) + NZ", fontsize=6.5)
    fig.savefig(out_png, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"{os.path.basename(out_png)} : {os.path.getsize(out_png) // 1024} Ko")


def main():
    prov = load_providers()
    # Compte + liste de pays des READMEs (indépendant de Nominatim/la carte).
    if not update_readme_countries(prov):
        return 1
    # Garde-fou : tout code de REGIONS doit exister comme provider (anti-drift).
    codes = {c for r in REGIONS for c in r[1]}
    missing = sorted(c for c in codes if c not in prov)
    if missing:
        print(f"  ERREUR : codes provider introuvables dans providers/ : {missing}")
        return 1

    # Pays distincts couverts par la carte (anti-drift du titre)
    n_pays = len({prov[c]["country"] for c in codes if prov[c]["country"]})

    features = []
    for query, region_codes, color, clip, group in REGIONS:
        title = group or (prov[region_codes[0]]["name"] if len(region_codes) == 1
                          else " + ".join(prov[c]["name"] for c in region_codes))
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
                "label": group or query,
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
    render_png(features, os.path.join(HERE, "coverage.png"),    n_pays=n_pays, lang="en")
    render_png(features, os.path.join(HERE, "coverage.fr.png"), n_pays=n_pays, lang="fr")
    return 0 if len(features) == len(REGIONS) else 1


if __name__ == "__main__":
    sys.exit(main())
