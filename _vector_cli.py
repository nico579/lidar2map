"""Construction du parser et préparation initiale du workflow vectoriel WFS.

Le module ne lit aucun global de :mod:`lidar2map`. Les constantes et helpers
historiques sont injectés par les façades du script principal afin de conserver
les coutures de test et d'intégration existantes.
"""

from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class DependancesParserWfs:
    """Dépendances nécessaires à la construction du parser WFS."""

    argparse: Any
    ajouter_args_zone: Callable[..., Any]
    arg_int_positif: Callable[[str], int]
    arg_float_non_negatif: Callable[[str], float]
    couches_wfs: Mapping[str, Any]
    version: str
    version_date: str


@dataclass(frozen=True)
class DependancesPreparationRunWfs:
    """Dépendances de la validation immédiate après ``parse_args``."""

    zone_cli_presente: Callable[[Any], bool]
    appliquer_cache_dir: Callable[[Any], Any]


def construire_parser_wfs(*, dependances):
    """Construit le parser argparse du workflow vectoriel WFS."""

    d = dependances
    parser = d.argparse.ArgumentParser(
        prog="lidar2map.py --vector",
        formatter_class=d.argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            ["Available layers:"]
            + [f"  {key:<16} {value[2]}"
               for key, value in d.couches_wfs.items()]
            + [
                "",
                "Examples:",
                "  python lidar2map.py --vector --zone-city gareoult --zone-width 10",
                "  python lidar2map.py --vector --layer batiments routes --zone-city gareoult",
                "  python lidar2map.py --vector --layer cadastre --zone-department 83",
            ]
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"lidar2map {d.version} ({d.version_date}), multi-provider",
    )
    parser.add_argument(
        "--vector",
        "--ignvecteur",
        action="store_true",
        dest="ignvecteur",
    )
    parser.add_argument(
        "--layer",
        "--couche",
        metavar="NAME",
        nargs="+",
        default=["cadastre"],
        dest="couche",
        help=(
            "WFS layer(s) to download (default: cadastre). "
            "Short alias or full typename. "
            "Multiple layers separated by spaces."
        ),
    )

    d.ajouter_args_zone(
        parser,
        width_default=20.0,
        bbox_metavar="W,S,E,N",
    )
    parser.add_argument(
        "--output-dir",
        "--dossier",
        metavar="PATH",
        default=None,
        dest="dossier",
        help="Output folder (default: ./ign_vecteur/)",
    )
    parser.add_argument(
        "--workers",
        type=d.arg_int_positif,
        default=4,
        metavar="N",
        help="Parallel WFS connections (default: 4)",
    )
    parser.add_argument(
        "--download-overwrite",
        "--telechargement-ecraser",
        action="store_true",
        dest="telechargement_ecraser",
        help="Overwrite existing GeoJSON (force re-download)",
    )
    parser.add_argument(
        "--file-formats",
        "--formats-fichier",
        nargs="+",
        dest="formats_fichier",
        choices=["geojson", "gz", "map", "transparent-raster"],
        default=["gz"],
        metavar="FMT",
        help=(
            "Output formats: geojson gz map transparent-raster (default: gz). "
            "map generates a Mapsforge map via osmosis ; transparent-raster "
            "rasterizes the vector into transparent PNG tiles (.sqlitedb) "
            "for OsmAnd overlay over the LiDAR."
        ),
    )
    parser.add_argument(
        "--tiles-overwrite",
        "--tuiles-ecraser",
        action="store_true",
        dest="tuiles_ecraser",
        help="Overwrite existing .map",
    )
    parser.add_argument(
        "--vector-simplify",
        "--simplification-vecteur",
        type=d.arg_float_non_negatif,
        default=None,
        metavar="M",
        dest="simplification_vecteur",
        help=(
            "Douglas-Peucker simplification epsilon in metres. "
            "Without it, computed automatically from the area "
            "(<200 km²→3 m, <1000→8 m, <15000→15 m, <100000→25 m, "
            "else→40 m)."
        ),
    )
    return parser


def preparer_run_wfs(args, parser, *, dependances):
    """Valide le run WFS, applique le cache et retourne ses formats GeoJSON."""

    d = dependances
    if not d.zone_cli_presente(args):
        parser.error(
            "one geographic area is required: --zone-city, --zone-gps, "
            "--zone-bbox, --zone-department, or --zone-region"
        )

    d.appliquer_cache_dir(args)
    formats = getattr(args, "formats_fichier", ["gz"])
    return [value for value in formats if value in ("gz", "geojson")] or ["gz"]
