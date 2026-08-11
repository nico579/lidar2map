"""Spécifications et algorithmes géométriques purs du domaine GeoJSON.

Le module ne réalise aucune entrée/sortie. Le convertisseur OSM XML, le
rasteriseur et l'orchestrateur Mapsforge extraits consomment ces briques via les
dépendances reconstruites par la façade historique de ``lidar2map.py``.
"""

from __future__ import annotations

import math


# Correspondance typename WFS IGN -> tags OSM pour mapwriter.
_IGN_LAYER_TAGS = {
    # hydrographie — rendu bleu natif dans tous les thèmes
    "cours_d_eau": {"waterway": "river"},
    "troncon_hydrographique": {"waterway": "stream"},
    "plan_d_eau": {"natural": "water"},
    "detail_hydrographique": {"natural": "spring"},
    # bâti / structures
    "batiment": {"building": "yes"},
    "construction_surfacique": {"building": "wall"},
    "cimetiere": {"landuse": "cemetery"},
    # transport
    "troncon_de_route": {"highway": "unclassified"},
    "itineraire_autre": {"highway": "track"},
    # orographie
    "ligne_orographique": {"natural": "ridge"},
    "detail_orographique": {"natural": "rock"},
    # végétation / milieu
    "foret_publique": {"landuse": "forest"},
    "parc_ou_reserve": {"leisure": "nature_reserve"},
    # cadastre / administration
    "commune": {"boundary": "administrative", "admin_level": "8"},
    "parcelle": {"barrier": "fence"},
    # lieux-dits
    "lieu_dit_non_habite": {"place": "locality"},
    # RPG
    "parcelles_graphiques": {"landuse": "farmland"},
}


def _tags_pour_layer(layer_short: str) -> dict:
    """Retourne les tags OSM à appliquer pour un nom court de couche IGN."""
    for cle, tags in _IGN_LAYER_TAGS.items():
        if cle in layer_short:
            return tags
    return {"note": layer_short}


# Style des overlays raster transparents : couleur RGBA, largeur, remplissage.
_OVERLAY_STYLE = {
    "highway": ((232, 80, 20, 255), 1.4, False),
    "waterway": ((30, 110, 220, 255), 1.4, False),
    "railway": ((70, 70, 70, 255), 1.2, False),
    "building": ((150, 100, 70, 255), 1.0, True),
    "natural": ((30, 140, 200, 255), 1.2, False),
    "landuse": ((70, 150, 70, 255), 1.0, False),
    "leisure": ((70, 150, 90, 255), 1.0, False),
    "boundary": ((160, 70, 160, 255), 0.9, False),
    "barrier": ((150, 120, 40, 255), 0.8, False),
    "place": ((90, 90, 90, 255), 1.2, False),
}
_OVERLAY_DEFAUT = ((120, 120, 120, 255), 1.0, False)

# Seuil d'avertissement du coût d'un overlay transparent.
_OVERLAY_TILE_WARN = 200_000


def _overlay_style_key(props, layer_hint=""):
    """Détermine la clé de style d'une feature GeoJSON OSM ou IGN."""
    cle = props.get("_cle")
    if cle:
        return cle
    src = str(props.get("source", "")) or layer_hint
    for nom_couche, tags in _IGN_LAYER_TAGS.items():
        if nom_couche in src:
            return next(iter(tags))
    for nom_style in _OVERLAY_STYLE:
        if nom_style in props:
            return nom_style
    return None


def _overlay_sequences(geom):
    """Décompose une géométrie GeoJSON en lignes et polygones groupés.

    Chaque polygone conserve son anneau extérieur et ses trous. Les points sont
    ignorés, car ils n'ont pas de trait pertinent à l'échelle d'un overlay.
    """
    geom_type = geom.get("type", "")
    coordinates = geom.get("coordinates", [])
    lignes, polygones = [], []
    if geom_type == "LineString":
        lignes.append(coordinates)
    elif geom_type == "MultiLineString":
        lignes.extend(coordinates)
    elif geom_type == "Polygon":
        if coordinates:
            polygones.append(list(coordinates))
    elif geom_type == "MultiPolygon":
        for poly in coordinates:
            if poly:
                polygones.append(list(poly))
    elif geom_type == "GeometryCollection":
        for sub in geom.get("geometries", []):
            sub_lignes, sub_polygones = _overlay_sequences(sub)
            lignes.extend(sub_lignes)
            polygones.extend(sub_polygones)
    return lignes, polygones


def _seg_inter_box(ax, ay, bx, by, x0, y0, x1, y1):
    """Indique par Liang-Barsky si un segment coupe une boîte axis-aligned."""
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return x0 <= ax <= x1 and y0 <= ay <= y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0:
            if q < 0:
                return False
        else:
            ratio = q / p
            if p < 0:
                if ratio > t1:
                    return False
                if ratio > t0:
                    t0 = ratio
            else:
                if ratio < t0:
                    return False
                if ratio < t1:
                    t1 = ratio
    return True


def _clip_polygone_rect(ring, x0, y0, x1, y1):
    """Clippe un anneau fermé contre un rectangle par Sutherland-Hodgman."""
    points = ring[:-1] if len(ring) >= 2 and ring[0] == ring[-1] else list(ring)
    if len(points) < 3:
        return []

    def _clip_bord(poly, dedans, intersection):
        sortie = []
        for index in range(len(poly)):
            courant, precedent = poly[index], poly[index - 1]
            courant_dedans = dedans(courant)
            precedent_dedans = dedans(precedent)
            if courant_dedans:
                if not precedent_dedans:
                    sortie.append(intersection(precedent, courant))
                sortie.append(courant)
            elif precedent_dedans:
                sortie.append(intersection(precedent, courant))
        return sortie

    def _interpoler(a, b, ratio):
        return (
            a[0] + (b[0] - a[0]) * ratio,
            a[1] + (b[1] - a[1]) * ratio,
        )

    poly = _clip_bord(
        points,
        lambda point: point[0] >= x0,
        lambda a, b: _interpoler(a, b, (x0 - a[0]) / (b[0] - a[0])),
    )
    if poly:
        poly = _clip_bord(
            poly,
            lambda point: point[0] <= x1,
            lambda a, b: _interpoler(a, b, (x1 - a[0]) / (b[0] - a[0])),
        )
    if poly:
        poly = _clip_bord(
            poly,
            lambda point: point[1] >= y0,
            lambda a, b: _interpoler(a, b, (y0 - a[1]) / (b[1] - a[1])),
        )
    if poly:
        poly = _clip_bord(
            poly,
            lambda point: point[1] <= y1,
            lambda a, b: _interpoler(a, b, (y1 - a[1]) / (b[1] - a[1])),
        )
    if len(poly) < 3:
        return []
    poly.append(poly[0])
    return poly


def _douglas_peucker(coords, epsilon):
    """Simplifie des coordonnées en conservant toujours leurs extrémités."""
    if len(coords) <= 2:
        return coords

    def _distance_perpendiculaire(point, debut, fin):
        x0, y0 = point[0], point[1]
        x1, y1 = debut[0], debut[1]
        x2, y2 = fin[0], fin[1]
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x0 - x1, y0 - y1)
        ratio = ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)
        ratio = max(0.0, min(1.0, ratio))
        return math.hypot(x0 - (x1 + ratio * dx), y0 - (y1 + ratio * dy))

    def _simplifier(points):
        if len(points) <= 2:
            return points
        distance_max, index_max = 0.0, 0
        for index in range(1, len(points) - 1):
            distance = _distance_perpendiculaire(
                points[index], points[0], points[-1]
            )
            if distance > distance_max:
                distance_max, index_max = distance, index
        if distance_max > epsilon:
            gauche = _simplifier(points[:index_max + 1])
            droite = _simplifier(points[index_max:])
            return gauche[:-1] + droite
        return [points[0], points[-1]]

    return _simplifier(list(coords))


# Tolérance historique de simplification IGN -> OSM XML (~15 m).
_IGN_SIMPLIFY_EPSILON = 0.00015


def _epsilon_depuis_surface_km2(surface_km2: float) -> float:
    """Calcule l'epsilon Douglas-Peucker selon la surface de la zone."""
    metres_par_degre = 111_000.0
    if surface_km2 < 200:
        metres = 3.0
    elif surface_km2 < 1_000:
        metres = 8.0
    elif surface_km2 < 15_000:
        metres = 15.0
    elif surface_km2 < 100_000:
        metres = 25.0
    else:
        metres = 40.0
    return metres / metres_par_degre
