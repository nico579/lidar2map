"""Construction du parser et préparation initiale du workflow raster WMTS.

Ce module reste indépendant de :mod:`lidar2map` : les constantes et les
helpers historiques sont fournis explicitement par les façades du script
principal. Cela conserve les points de patch des tests et des intégrations.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class DependancesParserWmts:
    """Dépendances nécessaires à la construction du parser WMTS."""

    argparse: Any
    ajouter_args_zone: Callable[..., Any]
    arg_float_non_negatif: Callable[[str], float]
    arg_int_positif: Callable[[str], int]
    version: str
    version_date: str
    apikey_defaut: str
    nb_workers: int


@dataclass(frozen=True)
class DependancesPreparationRunWmts:
    """Dépendances de la validation immédiate après ``parse_args``."""

    zone_cli_presente: Callable[[Any], bool]
    valider_zooms: Callable[[Any, Any], Any]
    appliquer_cache_dir: Callable[[Any], Any]


@dataclass(frozen=True)
class DependancesResolutionCoucheWmts:
    """Coutures de résolution d'une couche et de ses zooms réels."""

    couches: Any
    lire_zoom_limites_wmts: Callable[..., Any]
    imprimer: Callable[..., Any] = print


def construire_parser_wmts(*, dependances):
    """Construit le parser argparse du workflow raster WMTS (``--raster``)."""

    d = dependances
    parser = d.argparse.ArgumentParser(
        formatter_class=d.argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lidar2map.py --raster --zone-city gareoult --zoom-min 12 --zoom-max 16 --file-formats mbtiles
  python lidar2map.py --raster --layer ORTHOIMAGERY.ORTHOPHOTOS --zone-department 83 --zoom-min 14 --zoom-max 17 --file-formats mbtiles
  python lidar2map.py --raster --layer GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2 --zone-city gareoult --zoom-min 10 --zoom-max 16 --file-formats mbtiles
  python lidar2map.py --osm --layer "highway=* waterway=* natural=water" --zone-city gareoult
  python lidar2map.py --raster --source gareoult_scan25_z12-16.mbtiles --file-formats rmap
        """,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"lidar2map {d.version} ({d.version_date}), multi-provider",
    )
    parser.add_argument(
        "--raster",
        "--ignraster",
        action="store_true",
        dest="ignraster",
        help=(
            "IGN raster mode via WMTS. "
            "Use --layer for the layer (default: planign). "
            "Ex: --raster --layer GEOGRAPHICALGRIDSYSTEMS.MAPS"
        ),
    )
    # Consommé tôt par _load_provider (scan de sys.argv) ; déclaré ici uniquement
    # pour qu'argparse ne le rejette pas. Le raster US (--layer naip) passe par
    # --provider us-tnm depuis le GUI comme depuis la CLI.
    parser.add_argument(
        "--provider",
        default=None,
        metavar="CODE",
        help=(
            "Provider (default: fr-ign). Détermine les couches "
            "raster disponibles (fr-ign → IGN ; us-tnm → naip)."
        ),
    )

    # ── Découpage a priori (raster uniquement) ────────────────────────────────
    grp_priori = parser.add_argument_group(
        "A priori splitting — --raster only",
        "Sequential chunk processing with automatic resume (manifeste.json).\n"
        "The same parameters also control the splitting of output files.",
    )
    grp_priori.add_argument(
        "--split-cols",
        "--cols-decoupe",
        type=int,
        default=0,
        metavar="N",
        dest="cols_decoupe",
        help="Number of grid columns (East-West).",
    )
    grp_priori.add_argument(
        "--split-rows",
        "--rows-decoupe",
        type=int,
        default=0,
        metavar="N",
        dest="rows_decoupe",
        help="Number of grid rows (North-South).",
    )
    grp_priori.add_argument(
        "--split-width",
        "--split-largeur",
        type=d.arg_float_non_negatif,
        default=0.0,
        metavar="KM",
        dest="split_width",
        help="Alternative: split into ~KM km squares (KM = the side).",
    )
    grp_priori.add_argument(
        "--cleanup",
        "--nettoyage",
        action="store_true",
        dest="nettoyage",
        help=(
            "Delete intermediate tiles + TIFs after each chunk. "
            "Essential for large areas (a whole department)."
        ),
    )
    grp_priori.add_argument(
        "--min-free-gb",
        "--min-disque-go",
        type=d.arg_float_non_negatif,
        default=0.0,
        metavar="GB",
        dest="min_free_gb",
        help=(
            "Stop cleanly before a chunk if free disk space drops below GB "
            "(0 = disabled). Set it ABOVE one chunk's peak footprint "
            "(intermediates + tile pyramid). Exits with code 3 so a shell "
            "loop can tell a resumable disk-stop from a real error."
        ),
    )

    d.ajouter_args_zone(
        parser,
        width_default=20.0,
        bbox_metavar="W,S,E,N",
        bbox_help="WGS84 bbox: lon_min,lat_min,lon_max,lat_max",
    )

    # Pas de choices : le résolveur accepte aussi un identifiant WMTS complet.
    parser.add_argument(
        "--layer",
        "--couche",
        default="planign",
        dest="couche",
        metavar="LAYER",
        help=(
            "WMTS layer alias (planign, ortho, scan25…) or full "
            "id (GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2). Default: "
            "planign (public, no key). Restricted pro layers: "
            "scan25 scan25tour scan100 scanoaci."
        ),
    )
    parser.add_argument(
        "--api-key",
        "--apikey",
        default=d.apikey_defaut,
        metavar="KEY",
        dest="apikey",
        help=(
            "IGN API key for restricted layers (scan25, scan100…). "
            "⚠ Professional access only (cartes.gouv.fr account + SIRET). "
            "Individuals must use the public layers (planign, ortho…). "
            "Can also be set via the IGN_APIKEY env variable."
        ),
    )

    parser.add_argument("--zoom-min", type=int, default=10, metavar="N")
    parser.add_argument("--zoom-max", type=int, default=16, metavar="N")

    # Mode raster uniquement : pas de map/geojson/transparent-raster.
    parser.add_argument(
        "--file-formats",
        "--formats-fichier",
        nargs="+",
        dest="formats_fichier",
        choices=["mbtiles", "rmap", "sqlitedb"],
        default=[],
        metavar="FMT",
        help="Output file formats: mbtiles rmap sqlitedb (multi-value).",
    )
    parser.add_argument(
        "--source",
        metavar="PATH",
        default=None,
        help=(
            "Existing .mbtiles file → RMAP conversion "
            "(standalone mode, no zone required). Requires rmap format. "
            "Ex: --source gareoult_scan25_z12-16.mbtiles --file-formats rmap"
        ),
    )
    parser.add_argument(
        "--output-dir",
        "--dossier",
        metavar="PATH",
        default=None,
        dest="dossier",
        help="Output folder (default: Projets/<name>/raster/)",
    )

    parser.add_argument(
        "--workers",
        type=d.arg_int_positif,
        default=d.nb_workers,
        metavar="N",
    )
    parser.add_argument(
        "--image-format",
        "--formats-image",
        choices=["auto", "jpeg", "png"],
        default="auto",
        metavar="FMT",
        dest="formats_image",
        help="Format of tile images: auto, jpeg or png (default: auto).",
    )
    parser.add_argument(
        "--image-quality",
        "--qualite-image",
        type=int,
        default=85,
        metavar="Q",
        dest="qualite_image",
        help="JPEG quality of tile images (default: 85).",
    )
    parser.add_argument(
        "--download-overwrite",
        "--telechargement-ecraser",
        action="store_true",
        dest="telechargement_ecraser",
        help="Overwrite cached tiles (force re-download)",
    )
    parser.add_argument(
        "--tiles-overwrite",
        "--tuiles-ecraser",
        action="store_true",
        dest="tuiles_ecraser",
        help="Overwrite existing MBTiles",
    )
    return parser


def preparer_run_wmts(args, parser, *, dependances):
    """Valide et normalise les options communes avant le workflow WMTS."""

    d = dependances
    if not args.source and not d.zone_cli_presente(args):
        parser.error(
            "one geographic area is required: --zone-city, --zone-gps, "
            "--zone-bbox, --zone-department, or --zone-region"
        )

    d.valider_zooms(args, parser)
    d.appliquer_cache_dir(args)

    formats = args.formats_fichier
    args.mbtiles = "mbtiles" in formats
    args.rmap = "rmap" in formats
    args.sqlitedb = "sqlitedb" in formats
    args.transparent_raster = "transparent-raster" in formats
    return args


def resoudre_couche_wmts(args, *, dependances):
    """Résout la couche WMTS et borne les zooms aux capacités du service."""

    d = dependances
    # --couche accepte un alias court ou un identifiant complet. Une valeur
    # absente conserve le défaut historique planign.
    if not args.couche:
        args.couche = "planign"
    if args.couche in d.couches:
        layer, style, img_fmt, apikey_requis = d.couches[args.couche]
    else:
        layer = args.couche
        style = "normal"
        img_fmt = (
            "image/jpeg"
            if any(
                token in layer
                for token in ["MAPS", "ORTHOIMAGERY", "ETATMAJOR"]
            )
            else "image/png"
        )
        apikey_requis = any(token in layer for token in ["MAPS", "SCAN"])
        d.imprimer(f"  Layer: {layer} (direct id)")

    # Le format demandé au serveur reste natif. ``formats_image`` ne pilote que
    # le réencodage des tuiles de sortie.
    fmt_ext = "jpg" if "jpeg" in img_fmt else "png"
    if "jpeg" in img_fmt and args.formats_image == "png":
        d.imprimer(
            f"  Note: layer '{args.couche}' is served as JPEG; --image-format "
            "png ignored (PNG would only bloat the file, no quality gain). "
            "Keeping JPEG."
        )

    # Cette mutation précède impérativement le découpage a priori : chaque
    # morceau doit hériter des bornes réellement servies.
    zoom_min = min(args.zoom_min, args.zoom_max)
    zoom_max = max(args.zoom_min, args.zoom_max)
    limites_reelles = d.lire_zoom_limites_wmts(
        layer,
        apikey_requis,
        apikey=getattr(args, "apikey", ""),
    )
    if limites_reelles:
        source_capacites = "service" if layer.startswith("XYZ:") else "IGN"
        zoom_min_reel, zoom_max_reel = limites_reelles
        if zoom_max > zoom_max_reel:
            d.imprimer(
                f"  ⚠ Layer {args.couche}: {source_capacites} max zoom = "
                f"{zoom_max_reel}, zoom_max lowered from {zoom_max} to "
                f"{zoom_max_reel}."
            )
            zoom_max = zoom_max_reel
            zoom_min = min(zoom_min, zoom_max)
        if zoom_min < zoom_min_reel:
            d.imprimer(
                f"  ⚠ Layer {args.couche}: {source_capacites} min zoom = "
                f"{zoom_min_reel}, zoom_min raised from {zoom_min} to "
                f"{zoom_min_reel}."
            )
            zoom_min = zoom_min_reel
            zoom_max = max(zoom_max, zoom_min)
    args.zoom_min, args.zoom_max = zoom_min, zoom_max

    return layer, style, img_fmt, apikey_requis, fmt_ext, zoom_min, zoom_max
