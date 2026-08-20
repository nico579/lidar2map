"""Primitives pures de résolution des zones terrain.

Ce module ne connaît ni le provider actif ni le réseau. Les conversions
approchées sont conservées uniquement comme repli France (Lambert 93).
"""

import math
import re
import unicodedata


def normaliser_nom(texte):
    """Transforme un libellé de zone en nom de dossier stable."""
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    texte = re.sub(r"[^a-zA-Z0-9_-]", "_", texte.lower())
    return re.sub(r"_+", "_", texte).strip("_")


def nom_zone_gps_auto(lat, lon):
    return normaliser_nom(f"gps_{lat:.5f}_{lon:.5f}")


def nom_zone_bbox_auto(lon_min, lat_min, lon_max, lat_max):
    return normaliser_nom(
        f"bbox_{lon_min:.5f}_{lat_min:.5f}_{lon_max:.5f}_{lat_max:.5f}"
    )


def zone_cli_presente(args):
    return any(getattr(args, nom, None) for nom in (
        "zone_ville", "zone_gps", "zone_bbox", "zone_departement", "zone_region",
    ))


def regions_disponibles(geofabrik):
    """Retourne les slugs Geofabrik uniques dans un ordre stable."""
    return sorted(set(geofabrik.values()))


def departements_de_region(geofabrik, slug):
    """Retourne les codes INSEE associés à un slug Geofabrik."""
    return sorted(code for code, region in geofabrik.items() if region == slug)


def parser_departements(valeur):
    """Parse une liste de codes INSEE et de plages numériques inclusives."""
    codes = []
    for token in valeur.upper().split(","):
        token = token.strip()
        if not token:
            continue
        plage = re.fullmatch(r"([0-9]+)-([0-9]+)", token)
        if plage:
            debut, fin = int(plage.group(1)), int(plage.group(2))
            for numero in range(debut, fin + 1):
                codes.append(str(numero).zfill(2) if numero < 10 else str(numero))
        elif token.isdigit():
            codes.append(token.zfill(2) if len(token) == 1 else token)
        else:
            codes.append(token)
    return codes


def wgs84_to_lamb93_approx(lon, lat):
    e, n, F = 0.0818191908426, 0.7256077650, 11754255.426
    rho0, lam0 = 6055612.050, math.radians(3.0)
    phi, lam = math.radians(lat), math.radians(lon)
    e_sin = e * math.sin(phi)
    t = math.tan(math.pi / 4 - phi / 2) / ((1 - e_sin) / (1 + e_sin)) ** (e / 2)
    rho = F * t**n
    theta = n * (lam - lam0)
    return 700000 + rho * math.sin(theta), 6600000 + rho0 - rho * math.cos(theta)


def lamb93_to_wgs84_approx(x, y):
    n, F = 0.7256077650, 11754255.426
    rho0, e, lam0 = 6055612.050, 0.0818191908426, math.radians(3.0)
    dx, dy = x - 700000.0, rho0 - (y - 6600000.0)
    rho, theta = math.hypot(dx, dy), math.atan2(dx, dy)
    lam, t = theta / n + lam0, (rho / F) ** (1.0 / n)
    phi = math.pi / 2 - 2 * math.atan(t)
    for _ in range(5):
        e_sin = e * math.sin(phi)
        phi = math.pi / 2 - 2 * math.atan(t * ((1 - e_sin) / (1 + e_sin)) ** (e / 2))
    return math.degrees(lam), math.degrees(phi)


def bbox_enveloppe_transform(transform_fn, x1, y1, x2, y2, densify=21):
    n = max(1, int(densify))
    xs, ys = [], []
    for i in range(n + 1):
        t = i / n
        xt, yt = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        for px, py in ((xt, y1), (xt, y2), (x1, yt), (x2, yt)):
            qx, qy = transform_fn(px, py)
            xs.append(qx)
            ys.append(qy)
    return min(xs), min(ys), max(xs), max(ys)


def exiger_pyproj_hors_france(crs_natif, cible):
    """Refuse le repli Lambert 93 lorsqu'un autre CRS provider est actif."""
    crs = crs_natif or "EPSG:2154"
    if crs != "EPSG:2154":
        raise RuntimeError(
            f"pyproj required to reproject {cible} {crs}; the pure-Python "
            "fallback only covers France (EPSG:2154)."
        )


def wgs84_vers_natif(lon, lat, *, crs_natif, get_transformer):
    try:
        return get_transformer("EPSG:4326", crs_natif).transform(lon, lat)
    except ImportError:
        exiger_pyproj_hors_france(crs_natif, "to")
        return wgs84_to_lamb93_approx(lon, lat)


def natif_vers_wgs84(x, y, *, crs_natif, get_transformer):
    try:
        return get_transformer(crs_natif, "EPSG:4326").transform(x, y)
    except ImportError:
        exiger_pyproj_hors_france(crs_natif, "from")
        return lamb93_to_wgs84_approx(x, y)
