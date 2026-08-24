"""Contrat CLI partagé pour déclarer et résoudre une zone WGS84.

Le module ne connaît ni provider ni état global de :mod:`lidar2map`. Les
géocodeurs, conversions et conventions de nommage sont fournis explicitement
par les façades historiques du script principal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class DependancesArgumentsZone:
    """Validation numérique nécessaire à la construction du parseur."""

    arg_float_positif: Callable[[str], float]


@dataclass(frozen=True)
class DependancesResolutionZone:
    """Coutures nécessaires à la résolution d'une zone WGS84."""

    normaliser_nom: Callable[[str], str]
    geocoder_region: Callable[[str], Any]
    geocoder_departement: Callable[[str], Any]
    bbox_enveloppe_transform: Callable[..., Any]
    natif_vers_wgs84: Callable[[float, float], Any]
    bbox_valide_wgs84: Callable[..., Any]
    nom_zone_bbox_auto: Callable[..., str]
    nom_zone_gps_auto: Callable[[float, float], str]
    geocoder_ville_wgs84: Callable[[str], Any]
    ecrire: Callable[..., None]
    quitter: Callable[[int], Any]


def ajouter_args_zone(
    parser,
    *,
    width_default,
    bbox_metavar,
    bbox_help=None,
    avec_dossier=False,
    avec_help_full=False,
    dependances: DependancesArgumentsZone,
):
    """Ajoute au ``parser`` les arguments de zone communs aux trois CLI."""

    loc = parser.add_mutually_exclusive_group()
    if avec_help_full:
        loc.add_argument(
            "--zone-city", "--zone-ville", metavar="NAME", dest="zone_ville",
            help="City name (Nominatim geocoding)",
        )
        loc.add_argument(
            "--zone-gps", metavar="LAT,LON",
            help="GPS coordinates, e.g. 43.3156,6.0423",
        )
        loc.add_argument(
            "--zone-bbox", metavar=bbox_metavar, help=bbox_help or "",
        )
        loc.add_argument(
            "--zone-department", "--zone-departement", metavar="NUM",
            dest="zone_departement",
            help="Department number, e.g. 83, 2A, 971. "
                 "Automatically fetches the bbox from geo.api.gouv.fr. "
                 "The folder name is set automatically (e.g. var_83).",
        )
        loc.add_argument(
            "--zone-region", metavar="SLUG",
            help="Geofabrik region, e.g. provence-alpes-cote-d-azur. "
                 "Processes the whole region = bounding box of its departments. "
                 "With --osm: single regional map (full PBF, no re-clip).",
        )
    else:
        loc.add_argument(
            "--zone-city", "--zone-ville", metavar="NAME", dest="zone_ville",
        )
        loc.add_argument("--zone-gps", metavar="LAT,LON")
        if bbox_help:
            loc.add_argument(
                "--zone-bbox", metavar=bbox_metavar, help=bbox_help,
            )
        else:
            loc.add_argument("--zone-bbox", metavar=bbox_metavar)
        loc.add_argument(
            "--zone-department", "--zone-departement", metavar="NUM",
            dest="zone_departement",
        )
        loc.add_argument("--zone-region", metavar="SLUG")

    width_contract = (
        f"default: {width_default}"
        if width_default is not None
        else "required with --zone-city/--zone-gps"
    )
    parser.add_argument(
        "--zone-width", "--zone-largeur",
        type=dependances.arg_float_positif,
        default=width_default,
        metavar="KM",
        dest="zone_width",
        help="Width in km of the square around the point "
             f"(the side, not a radius; {width_contract})",
    )
    parser.add_argument(
        "--zone-name", "--zone-nom", metavar="NAME", default=None,
        dest="zone_nom",
        help="Output folder name for the processed zone. "
             "Automatically derived from the city, GPS coordinates, "
             "bbox, department, or region when omitted.",
    )
    if avec_dossier:
        parser.add_argument(
            "--output-dir", "--dossier", metavar="PATH", default=None,
            dest="dossier", help="Root output folder.",
        )
    parser.add_argument(
        "--cache-dir", "--dossier-cache", metavar="PATH", default=None,
        dest="cache_dir",
        help="Root folder for ALL persistent caches (tiles, WMTS, "
             "OSM PBF, discovery index). Default: <work-dir>/cache. "
             "Handy to put a large cache on another drive.",
    )
    parser.add_argument(
        "--production-dir", "--dossier-production", metavar="PATH",
        default=None, dest="production_dir",
        help="Root folder for COMPUTED-but-shared artifacts "
             "(LAZ .tif). Default: <work-dir>/production. The "
             "downloaded point cloud (.laz) stays in the cache.",
    )
    return loc


def resoudre_zone_wgs84(args, *, dependances: DependancesResolutionZone):
    """Résout les arguments de zone en ``(W, S, E, N, nom_zone)``."""

    deps = dependances
    lat_min = lon_min = lat_max = lon_max = None
    zone_nom_raw = getattr(args, "zone_nom", None)
    nom_zone = deps.normaliser_nom(zone_nom_raw) if zone_nom_raw else None

    if getattr(args, "zone_region", None):
        slug = args.zone_region.strip().lower()
        nom_reg, bx1, by1, bx2, by2 = deps.geocoder_region(slug)
        if nom_reg is None:
            deps.quitter(1)
        if not nom_zone:
            nom_zone = deps.normaliser_nom(slug)
        lon_min, lat_min, lon_max, lat_max = deps.bbox_enveloppe_transform(
            deps.natif_vers_wgs84, bx1, by1, bx2, by2,
        )

    elif args.zone_departement:
        num_dep = args.zone_departement.strip().upper()
        nom_dep, bx1, by1, bx2, by2 = deps.geocoder_departement(num_dep)
        if nom_dep is None:
            deps.quitter(1)
        if not nom_zone:
            nom_zone = deps.normaliser_nom(nom_dep) + "_" + num_dep.lower()
        lon_min, lat_min, lon_max, lat_max = deps.bbox_enveloppe_transform(
            deps.natif_vers_wgs84, bx1, by1, bx2, by2,
        )

    elif args.zone_bbox:
        try:
            parts = [float(value.strip()) for value in args.zone_bbox.split(",")]
            lon_min, lat_min, lon_max, lat_max = parts
        except (ValueError, IndexError):
            deps.ecrire(
                "  Invalid bbox format. Example: "
                "--zone-bbox 5.9,43.1,6.6,43.8"
            )
            deps.quitter(1)
        lon_min, lat_min, lon_max, lat_max = deps.bbox_valide_wgs84(
            lon_min, lat_min, lon_max, lat_max,
        )
        if not nom_zone:
            nom_zone = deps.nom_zone_bbox_auto(
                lon_min, lat_min, lon_max, lat_max,
            )

    elif args.zone_gps:
        try:
            parts = [
                part.strip()
                for part in args.zone_gps.replace(";", ",").split(",")
            ]
            lat_c, lon_c = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            deps.ecrire(
                "  Invalid GPS format. Example: --zone-gps 43.3156,6.0423"
            )
            deps.quitter(1)
        if not (
            math.isfinite(lat_c)
            and math.isfinite(lon_c)
            and -90 <= lat_c <= 90
            and -180 <= lon_c <= 180
        ):
            deps.ecrire(
                "  ERROR: GPS out of range (lat [-90,90], lon [-180,180])."
            )
            deps.quitter(1)
        if not nom_zone:
            nom_zone = deps.nom_zone_gps_auto(lat_c, lon_c)
        half_width = (args.zone_width or 20.0) / 2.0
        radius = half_width / 111.0
        radius_lon = half_width / (
            111.0 * max(0.01, math.cos(math.radians(lat_c)))
        )
        lat_min, lat_max = lat_c - radius, lat_c + radius
        lon_min, lon_max = lon_c - radius_lon, lon_c + radius_lon

    elif args.zone_ville:
        nom_zone = nom_zone or deps.normaliser_nom(args.zone_ville)
        deps.ecrire(f"  Geocoding '{args.zone_ville}'...")
        lat_c, lon_c = deps.geocoder_ville_wgs84(args.zone_ville)
        if lat_c is None:
            deps.quitter(1)
        half_width = (args.zone_width or 20.0) / 2.0
        radius = half_width / 111.0
        radius_lon = half_width / (
            111.0 * max(0.01, math.cos(math.radians(lat_c)))
        )
        lat_min, lat_max = lat_c - radius, lat_c + radius
        lon_min, lon_max = lon_c - radius_lon, lon_c + radius_lon

    else:
        deps.ecrire(
            "  ERROR: a zone option is required "
            "(--zone-city / --zone-gps / --zone-bbox / --zone-department)"
        )
        deps.quitter(1)

    if not nom_zone:
        deps.quitter(1)

    return lon_min, lat_min, lon_max, lat_max, nom_zone
