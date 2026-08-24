"""Production best-effort des planches d'assemblage et contours administratifs."""

from dataclasses import dataclass
import gzip
import json
import sqlite3
from pathlib import Path
import time
import urllib.parse
import urllib.request


def bbox_geojson_stream(fh):
    """bbox WGS84 d'un GeoJSON lu en STREAMING (ijson) : un département de
    vecteurs fait des centaines de Mo décompressés — le charger entier en RAM
    juste pour une bbox serait absurde. RAM O(1) : on ne garde que les min/max."""
    import ijson
    from decimal import Decimal   # ijson rend les nombres en Decimal
    lon0 = lat0 = float("inf"); lon1 = lat1 = float("-inf")
    def _walk(c):
        nonlocal lon0, lat0, lon1, lat1
        if isinstance(c, (list, tuple)):
            if (len(c) >= 2 and isinstance(c[0], (int, float, Decimal))
                    and isinstance(c[1], (int, float, Decimal))):
                x = float(c[0]); y = float(c[1])
                if x < lon0: lon0 = x
                if x > lon1: lon1 = x
                if y < lat0: lat0 = y
                if y > lat1: lat1 = y
            else:
                for e in c:
                    _walk(e)
    for coords in ijson.items(fh, "features.item.geometry.coordinates"):
        _walk(coords)
    return (lon0, lat0, lon1, lat1) if lon1 > lon0 else None


def bbox_sqlite_tiles(
        path, rmaps=False, *, tile_to_geo, sqlite_connect=sqlite3.connect):
    """bbox WGS84 d'un magasin de tuiles SQLite, best-effort. mbtiles : metadata
    `bounds`, sinon étendue des tuiles. sqlitedb RMaps : selon info.tilenumbering
    ('simple' = z réel + y XYZ, notre writer ; défaut BigPlanet = z stocké 17-zoom).
    IMPORTANT : l'agrégat min/max est fait À UN SEUL NIVEAU de zoom — mélanger
    les colonnes/lignes de zooms différents donnerait une bbox fausse.
    None si illisible/incohérent."""
    con = sqlite_connect(f"file:{path}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        if not rmaps:
            try:
                row = cur.execute(
                    "SELECT value FROM metadata WHERE name='bounds'").fetchone()
                if row and row[0]:
                    l, b, r, t = (float(x) for x in str(row[0]).split(","))
                    return (l, b, r, t)
            except Exception:
                pass
            zrow = cur.execute("SELECT max(zoom_level) FROM tiles").fetchone()
            if not zrow or zrow[0] is None:
                return None
            z = int(zrow[0])
            xmin, xmax, ytmin, ytmax = cur.execute(
                "SELECT min(tile_column),max(tile_column),"
                "min(tile_row),max(tile_row) FROM tiles WHERE zoom_level=?",
                (z,)).fetchone()
            ymin = (1 << z) - 1 - ytmax     # TMS -> XYZ
            ymax = (1 << z) - 1 - ytmin
        else:
            numbering = "simple"            # notre writer (tilenumbering='simple')
            try:
                row = cur.execute("SELECT tilenumbering FROM info").fetchone()
                if row and row[0]:
                    numbering = str(row[0]).lower()
            except Exception:
                numbering = ""              # pas de colonne = vieux schéma BigPlanet
            if numbering == "simple":
                zrow = cur.execute("SELECT max(z) FROM tiles").fetchone()
                if not zrow or zrow[0] is None:
                    return None
                zst = int(zrow[0]); z = zst
            else:
                zrow = cur.execute("SELECT min(z) FROM tiles").fetchone()
                if not zrow or zrow[0] is None:
                    return None
                zst = int(zrow[0]); z = 17 - zst
            if not (0 <= z <= 25):
                return None
            xmin, xmax, ymin, ymax = cur.execute(
                "SELECT min(x),max(x),min(y),max(y) FROM tiles WHERE z=?",
                (zst,)).fetchone()
        tl = tile_to_geo(xmin, ymin, z)    # coin NO : (lon_min, lat_min, lon_max, lat_max)
        br = tile_to_geo(xmax, ymax, z)    # coin SE
        bbox = (tl[0], br[1], br[2], tl[3])
        if -180 <= bbox[0] <= 180 and -85 <= bbox[1] <= 85 and bbox[2] > bbox[0]:
            return bbox
        return None
    except Exception:
        return None
    finally:
        try: con.close()
        except Exception: pass


def extraire_bbox_wgs84(
        fichier, *, bbox_sqlite_tiles, bbox_geojson_stream,
        path_factory=Path, open_file=open, gzip_open=gzip.open):
    """Emprise WGS84 (lon0,lat0,lon1,lat1) d'un livrable, ou None. Best-effort."""
    f = path_factory(fichier)
    nom = f.name.lower()
    try:
        if nom.endswith(".mbtiles"):
            return bbox_sqlite_tiles(f, rmaps=False)
        if nom.endswith(".sqlitedb"):
            return bbox_sqlite_tiles(f, rmaps=True)
        if nom.endswith(".geojson"):
            with open_file(f, "rb") as fh:
                return bbox_geojson_stream(fh)
        if nom.endswith(".geojson.gz"):
            with gzip_open(f, "rb") as fh:
                return bbox_geojson_stream(fh)
    except Exception:
        return None
    return None


@dataclass(frozen=True)
class DependancesPlanches:
    """Coutures runtime injectées par la façade historique."""

    extraire_bbox_wgs84: object
    planche_contours_dept: object
    generer_planche: object
    dossier_cache: Path
    http_ua: str
    ecrire_json_atomique: object
    request_url: object = urllib.request.Request
    ouvrir_url: object = urllib.request.urlopen
    attendre: object = time.sleep


def planche_depuis_dossier(dossier, args, nom_zone=None, zone_bbox_wgs84=None, *, dependances):
    """Balaie un dossier projet et génère UNE planche d'assemblage PAR PRODUIT
    (ombrage / couche : lrm, svf, ortho…) : sinon leurs emprises se
    superposeraient sur une même planche, illisible. Groupe par (produit, cellule
    NNNxNNN) ; le produit = le nom de fichier sans le token de cellule ni
    l'extension → le mbtiles et le sqlitedb d'un même produit restent groupés.
    Indépendant du run (mode --planche DIR). Une cellule sans fichier (mer)
    n'apparaît pas : c'est voulu.

    zone_bbox_wgs84 : bbox WGS84 effectivement demandée par l'utilisateur
    (lon_min, lat_min, lon_max, lat_max), si connue de l'appelant. Sert à
    borner l'emprise lue dans les fichiers : le WFS IGN renvoie la géométrie
    ENTIÈRE d'un itinéraire qui traverse seulement la zone (ex. un GR ou une
    véloroute de plusieurs centaines de km pour une zone de quelques km), pas
    la portion locale. Sans ce recadrage, l'emprise calculée peut dériver très
    loin de la zone réelle, faire échouer le reverse-geocoding du département
    et rendre la planche illisible (le point demandé devient invisible à
    l'échelle de l'emprise entière). Absent en mode --planche DIR autonome
    (pas de requête associée) : l'ancien comportement best-effort s'applique."""
    if not getattr(args, "index_map", True):
        return
    try:
        import re as _re

        def _clip(bbox):
            """Intersecte `bbox` avec la zone demandée, si connue. Conserve
            `bbox` tel quel en l'absence d'intersection (défensif : ne doit
            jamais produire une bbox vide ou inversée)."""
            if zone_bbox_wgs84 is None:
                return bbox
            x0 = max(bbox[0], zone_bbox_wgs84[0]); y0 = max(bbox[1], zone_bbox_wgs84[1])
            x1 = min(bbox[2], zone_bbox_wgs84[2]); y1 = min(bbox[3], zone_bbox_wgs84[3])
            return (x0, y0, x1, y1) if (x0 < x1 and y0 < y1) else bbox

        d = Path(dossier)
        if not d.is_dir():
            print(f"  (index sheet: {d} is not a folder)", flush=True)
            return
        nom_zone = nom_zone or d.name
        _SUFS = (".geojson.gz", ".mbtiles", ".sqlitedb", ".rmap", ".map", ".geojson")
        # mbtiles/geojson d'abord (emprise fiable), sqlitedb en dernier recours.
        _prio = {".mbtiles": 0, ".geojson": 1, ".gz": 2, ".sqlitedb": 3}
        fichiers = sorted(
            [p for pat in ("*.mbtiles", "*.sqlitedb", "*.geojson", "*.geojson.gz")
             for p in d.rglob(pat)],
            key=lambda p: _prio.get(p.suffix.lower(), 9))
        produits = {}   # produit -> {cle: bbox}  ('__single__' hors découpage)
        geo_bboxes = []; geo_stems = []
        for f in fichiers:
            stem = f.name
            for suf in _SUFS:
                if stem.lower().endswith(suf):
                    stem = stem[:-len(suf)]; break
            # Famille GeoJSON (vecteur IGN/OSM/fusion) : les couches d'un même
            # run décrivent la MÊME zone → UNE planche pour l'ensemble (demande
            # de Nico), pas une par couche. Collectées à part, groupées après.
            if f.name.lower().endswith((".geojson", ".geojson.gz")):
                bbox = dependances.extraire_bbox_wgs84(f)
                if bbox:
                    geo_bboxes.append(_clip(bbox)); geo_stems.append(stem)
                continue
            m = _re.search(r"(\d{3})x(\d{3})", stem)
            cle = f"{m.group(1)}x{m.group(2)}" if m else "__single__"
            produit = _re.sub(r"_?\d{3}x\d{3}", "", stem).strip("_") or nom_zone
            cells = produits.setdefault(produit, {})
            if cle in cells:
                continue
            bbox = dependances.extraire_bbox_wgs84(f)
            if bbox:
                cells[cle] = _clip(bbox)
        if geo_bboxes:
            # Emprise du groupe = INTERSECTION des couches, pas l'union : les
            # couches d'itinéraires (GR) portent des features ENTIÈRES
            # traversant la région — l'union donnerait une emprise de centaines
            # de km (et un centre potentiellement en mer, vécu). L'intersection
            # approxime la zone réellement demandée. Union en repli si vide.
            ib = (max(b[0] for b in geo_bboxes), max(b[1] for b in geo_bboxes),
                  min(b[2] for b in geo_bboxes), min(b[3] for b in geo_bboxes))
            if not (ib[0] < ib[2] and ib[1] < ib[3]):
                ib = (min(b[0] for b in geo_bboxes), min(b[1] for b in geo_bboxes),
                      max(b[2] for b in geo_bboxes), max(b[3] for b in geo_bboxes))
            import os.path as _osp
            nom_geo = _osp.commonprefix(geo_stems).strip("_") or nom_zone
            produits[nom_geo] = {"__single__": ib}
        produits = {k: v for k, v in produits.items() if v}
        if not produits:
            print("  (index sheet: no readable deliverable found)", flush=True)
            return
        # Contour(s) département : une seule requête Nominatim pour tous les
        # produits (même zone), sur l'emprise globale.
        # Contour département : viser le centre du produit le PLUS LOCAL (plus
        # petite bbox), pas l'union. Les couches d'itinéraires (GR) contiennent
        # des features ENTIÈRES traversant la région : l'union est énorme et
        # son centre peut tomber en mer (vécu : centre en Méditerranée → reverse
        # sans département → aucune planche avec contour). Repli sur l'union si
        # le produit local ne résout rien.
        def _pbbox(cells_d):
            v = list(cells_d.values())
            return (min(b[0] for b in v), min(b[1] for b in v),
                    max(b[2] for b in v), max(b[3] for b in v))
        pb_all = {k: _pbbox(v) for k, v in produits.items()}
        ref_bbox = min(pb_all.values(),
                       key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        allb = [b for v in produits.values() for b in v.values()]
        gbbox = (min(b[0] for b in allb), min(b[1] for b in allb),
                 max(b[2] for b in allb), max(b[3] for b in allb))
        contours = dependances.planche_contours_dept(ref_bbox, args)
        if not contours and gbbox != ref_bbox:
            dependances.attendre(1.1)   # Nominatim : 1 req/s
            contours = dependances.planche_contours_dept(gbbox, args)
        for produit, cells_d in sorted(produits.items()):
            cells = sorted((k, v) for k, v in cells_d.items() if k != "__single__")
            dependances.generer_planche(pb_all[produit], cells or None, produit, d, args,
                             contours=contours)
    except Exception as e:
        print(f"  (index sheet skipped: {type(e).__name__}: {e})", flush=True)


def planche_contours_dept(bbox_wgs84, args, *, dependances):
    """Contour(s) RÉEL(s) du/des département(s) couvrant la zone (polygone, pas
    la bbox), best-effort via Nominatim polygon_geojson. Retourne une liste
    d'anneaux extérieurs [(lon,lat), ...] en WGS84, ou [] si rien de résolvable
    (offline, hors FR, etc.) — la planche est alors dessinée sans fond dép."""
    lon0, lat0, lon1, lat1 = bbox_wgs84
    noms = []
    dep_arg = str(getattr(args, "zone_departement", "") or "").strip()
    if dep_arg:
        # Numéros simples séparés par des virgules : nom lu dans le cache rempli
        # par geocoder_departement pendant le run (pas de nouvel Overpass).
        try:
            _cache = json.loads((dependances.dossier_cache / "dep_bbox_cache.json")
                                .read_text(encoding="utf-8"))
        except Exception:
            _cache = {}
        for tok in dep_arg.replace(";", ",").split(","):
            n = (_cache.get(tok.strip()) or {}).get("nom")
            if n and n not in noms:
                noms.append(n)
    if not noms:
        # Reverse-geocode du centre → département (address.county en FR).
        lonc = (lon0 + lon1) / 2; latc = (lat0 + lat1) / 2
        try:
            url = ("https://nominatim.openstreetmap.org/reverse?"
                   + urllib.parse.urlencode({"lat": f"{latc:.5f}", "lon": f"{lonc:.5f}",
                                             "format": "jsonv2", "zoom": 8}))
            req = dependances.request_url(url, headers={"User-Agent": dependances.http_ua})
            with dependances.ouvrir_url(req, timeout=10) as r:
                addr = (json.load(r) or {}).get("address", {}) or {}
            n = addr.get("county") or addr.get("state_district") or addr.get("state")
            if n:
                noms.append(n)
            else:
                # Pas d'exception mais rien de résolu (centre en mer, hors
                # couverture admin...) : le dire, sinon indiagnosticable.
                print(f"  (index sheet: no department at "
                      f"{latc:.4f},{lonc:.4f} - outline skipped)", flush=True)
        except Exception as _e_rev:
            # Visible : un best-effort qui échoue en silence est indiagnosticable
            # (leçon du 2026-07-10 : la planche sortait sans département sans
            # aucun indice sur la cause).
            print(f"  (index sheet: reverse geocoding failed: "
                  f"{type(_e_rev).__name__}: {_e_rev})", flush=True)
    # Cache disque des polygones (même logique que dep_bbox_cache.json) : les
    # contours administratifs ne changent pas, les re-télécharger à chaque run
    # coûtait des requêtes Nominatim + les sleep de politesse par planche.
    _cache_path = dependances.dossier_cache / "dep_contour_cache.json"
    try:
        _cache = json.loads(_cache_path.read_text(encoding="utf-8"))
        if not isinstance(_cache, dict):
            _cache = {}
    except Exception:
        _cache = {}
    contours = []
    _cache_dirty = False
    for nom in noms[:4]:   # borne : ne pas spammer Nominatim
        if nom in _cache:
            contours.extend(_cache[nom])
            continue
        try:
            url = ("https://nominatim.openstreetmap.org/search?"
                   + urllib.parse.urlencode({"q": nom, "format": "jsonv2",
                                             "polygon_geojson": 1,
                                             "polygon_threshold": 0.005, "limit": 1}))
            req = dependances.request_url(url, headers={"User-Agent": dependances.http_ua})
            with dependances.ouvrir_url(req, timeout=15) as r:
                res = json.load(r)
            g = (res[0].get("geojson") if res else None) or {}
            rings = []
            if g.get("type") == "Polygon":
                rings.append(g["coordinates"][0])
            elif g.get("type") == "MultiPolygon":
                for poly in g["coordinates"]:
                    rings.append(poly[0])
            contours.extend(rings)
            if rings:   # ne pas cacher un résultat vide (permet de réessayer)
                _cache[nom] = rings
                _cache_dirty = True
            dependances.attendre(1.1)   # Nominatim : 1 req/s
        except Exception as _e_sea:
            print(f"  (index sheet: no outline for '{nom}': "
                  f"{type(_e_sea).__name__}: {_e_sea})", flush=True)
    if _cache_dirty:
        try:
            dependances.ecrire_json_atomique(_cache_path, _cache)
        except Exception:
            pass   # cache best-effort, jamais un point de panne
    return contours


def generer_planche(bbox_wgs84, cells, nom_zone, dossier, args, contours=None, *, dependances):
    """<zone>_planche.png : planche d'assemblage (index/key map) d'UN produit.
    Emprise (cadre) + contour(s) département réels + cellules numérotées (si
    découpage). `contours` pré-calculé (partagé entre produits) sinon récupéré
    ici. PIL seul (bundle app). Entièrement best-effort : toute erreur est
    avalée (l'artefact est un bonus, jamais un point de panne du run)."""
    if not getattr(args, "index_map", True):
        return
    try:
        import math as _m
        from PIL import Image, ImageDraw, ImageFont
        lon0, lat0, lon1, lat1 = bbox_wgs84
        if lon1 <= lon0 or lat1 <= lat0:
            return
        if contours is None:
            contours = dependances.planche_contours_dept(bbox_wgs84, args)

        # Emprise d'affichage = union(zone, contours), mais CAPÉE pour la
        # lisibilité : si l'emprise est minuscule vs le département, les cellules
        # deviennent illisibles (numéros qui se chevauchent). On limite la vue à
        # _CAP× l'emprise, centrée dessus, sans jamais exclure l'emprise. À
        # l'échelle départementale (emprise ≈ département) le cap ne mord pas :
        # tout le contour reste visible. Ratio corrigé du cos(lat) plus bas.
        lons = [lon0, lon1]; lats = [lat0, lat1]
        for ring in contours:
            lons += [p[0] for p in ring]; lats += [p[1] for p in ring]
        ulon0, ulon1 = min(lons), max(lons)
        ulat0, ulat1 = min(lats), max(lats)
        _CAP = 4.0
        ecx = (lon0 + lon1) / 2; ecy = (lat0 + lat1) / 2
        _hw = max(lon1 - lon0, 1e-6) * _CAP / 2
        _hh = max(lat1 - lat0, 1e-6) * _CAP / 2
        dlon0 = min(lon0, max(ulon0, ecx - _hw))
        dlon1 = max(lon1, min(ulon1, ecx + _hw))
        dlat0 = min(lat0, max(ulat0, ecy - _hh))
        dlat1 = max(lat1, min(ulat1, ecy + _hh))
        mlon = (dlon1 - dlon0) * 0.04 or 0.01
        mlat = (dlat1 - dlat0) * 0.04 or 0.01
        dlon0 -= mlon; dlon1 += mlon; dlat0 -= mlat; dlat1 += mlat
        lat_mid = (dlat0 + dlat1) / 2
        w_g = (dlon1 - dlon0) * _m.cos(_m.radians(lat_mid))
        h_g = (dlat1 - dlat0)
        if w_g <= 0 or h_g <= 0:
            return
        MAXPX = 1000
        if w_g >= h_g:
            W = MAXPX; H = max(1, round(MAXPX * h_g / w_g))
        else:
            H = MAXPX; W = max(1, round(MAXPX * w_g / h_g))

        def _px(lon, lat):
            return ((lon - dlon0) / (dlon1 - dlon0) * W,
                    (dlat1 - lat) / (dlat1 - dlat0) * H)

        img = Image.new("RGB", (W, H), (247, 249, 252))
        dr = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default(size=15)
        except Exception:
            font = ImageFont.load_default()

        # Département : contour RÉEL (polygone), léger fond + trait gris.
        for ring in contours:
            pts = [_px(lon, lat) for lon, lat in ring]
            if len(pts) >= 3:
                dr.polygon(pts, fill=(228, 233, 240), outline=(140, 150, 165))

        # Emprise globale des livrables (cadre bleu).
        ex0, ey0 = _px(lon0, lat1); ex1, ey1 = _px(lon1, lat0)
        dr.rectangle([ex0, ey0, ex1, ey1], outline=(37, 99, 235), width=3)

        # Cellules du découpage : rectangle + numéro centré.
        for cle, (clo0, cla0, clo1, cla1) in (cells or []):
            cx0, cy0 = _px(clo0, cla1); cx1, cy1 = _px(clo1, cla0)
            dr.rectangle([cx0, cy0, cx1, cy1], outline=(200, 70, 50), width=1)
            try:
                dr.text(((cx0 + cx1) / 2, (cy0 + cy1) / 2), cle,
                        fill=(120, 30, 20), font=font, anchor="mm")
            except TypeError:   # anchor absent (Pillow < 8) : coin haut-gauche
                dr.text((cx0 + 3, cy0 + 3), cle, fill=(120, 30, 20), font=font)

        titre = nom_zone + (f"  -  {len(cells)} zones" if cells else "")
        dr.text((8, 6), titre, fill=(30, 41, 59), font=font)

        # Carton de localisation (locator inset, standard cartes IGN papier) :
        # quand la vue principale est zoomée (cap 4× sur petite zone), le
        # contour du département est hors-champ — le fond couvre tout et la
        # planche perd son contexte. On dessine alors en coin le département
        # ENTIER avec l'emprise en rouge. Sauté quand la vue montre déjà le
        # département (run départemental : le carton serait redondant).
        if contours:
            klon0 = min(p[0] for ring in contours for p in ring)
            klon1 = max(p[0] for ring in contours for p in ring)
            klat0 = min(p[1] for ring in contours for p in ring)
            klat1 = max(p[1] for ring in contours for p in ring)
            # Test de CONFINEMENT (pas un ratio d'aires : sur un petit
            # département, une vue capée 4× peut en couvrir 30 % et un seuil
            # d'aire sautait le carton à tort) : si le département ne tient
            # pas entier dans la vue, on ajoute le carton.
            _tol = 0.02 * max(klon1 - klon0, klat1 - klat0)
            _dept_visible = (klon0 >= dlon0 - _tol and klon1 <= dlon1 + _tol
                             and klat0 >= dlat0 - _tol and klat1 <= dlat1 + _tol)
            if not _dept_visible:
                kmid = _m.cos(_m.radians((klat0 + klat1) / 2))
                kw_g = (klon1 - klon0) * kmid
                kh_g = (klat1 - klat0)
                iw = int(W * 0.30)
                ih = max(24, int(iw * kh_g / max(kw_g, 1e-9)))
                if ih > int(H * 0.38):          # borne : carton ≤ ~1/3 de haut
                    ih = int(H * 0.38)
                    iw = max(24, int(ih * kw_g / max(kh_g, 1e-9)))
                pad = 6; marge = 8
                x0i = W - iw - 2 * pad - marge
                y0i = H - ih - 2 * pad - marge   # coin bas-droit
                dr.rectangle([x0i, y0i, x0i + iw + 2 * pad, y0i + ih + 2 * pad],
                             fill=(255, 255, 255), outline=(140, 150, 165))

                def _kpx(lon, lat):
                    return (x0i + pad + (lon - klon0) / (klon1 - klon0) * iw,
                            y0i + pad + (klat1 - lat) / (klat1 - klat0) * ih)

                for ring in contours:
                    pts = [_kpx(lon, lat) for lon, lat in ring]
                    if len(pts) >= 3:
                        dr.polygon(pts, fill=(228, 233, 240),
                                   outline=(140, 150, 165))
                # Emprise en rouge, épaissie à 3 px minimum pour rester
                # visible même quand la zone est minuscule vs le département.
                kx0, ky0 = _kpx(lon0, lat1); kx1, ky1 = _kpx(lon1, lat0)
                if kx1 - kx0 < 3: kx1 = kx0 + 3
                if ky1 - ky0 < 3: ky1 = ky0 + 3
                dr.rectangle([kx0, ky0, kx1, ky1], outline=(220, 38, 38), width=2)

        out = Path(dossier) / f"{nom_zone}_planche.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        print(f"  {out.name} : index sheet ({W}x{H})", flush=True)
    except Exception as _e_pl:
        print(f"  (index sheet skipped: {type(_e_pl).__name__}: {_e_pl})", flush=True)
