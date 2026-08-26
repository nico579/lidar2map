"""Construction et défauts de la ligne de commande du workflow terrain.

Ce module ne lit aucun état global de :mod:`lidar2map`. Les validateurs,
constantes d'affichage et le contrat de zone partagé sont fournis par la façade
historique afin de préserver les coutures de test et la configuration active.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class DependancesParserLidar:
    """Coutures nécessaires à la construction du parser LiDAR/OSM."""

    argparse: Any
    ajouter_args_zone: Callable[..., Any]
    arg_float_non_negatif: Callable[[str], float]
    arg_int_positif: Callable[[str], int]
    arg_float_positif: Callable[[str], float]
    shading_types_ordre: Sequence[str]
    version: str
    version_date: str
    nb_workers: int
    elevation_soleil: int
    svf_gamma: float


def appliquer_defauts_cli_lidar(args):
    """Applique le contrat par défaut d'un run LiDAR en ligne de commande.

    Un traitement normal télécharge les données manquantes, calcule LRM et
    produit MBTiles. Une commande de maintenance seule ou une conversion de
    source ne télécharge pas les données implicitement. Les choix explicites
    priment (la découverte d'index du provider peut toujours vérifier la zone).
    """
    maintenance_demandee = any((
        args.dalles_purger_invalides,
        args.dalles_purger_hors_zone,
        args.ombrages_compresser,
    ))
    produit_explicitement_demande = bool(
        args.ombrages is not None
        or args.shading_specs
        or args.shading_preset
        or args.formats_fichier
    )
    maintenance_seule = (
        maintenance_demandee and not produit_explicitement_demande
    )

    if args.telechargement_forcer or args.telechargement_ecraser:
        args.telechargement = True
    elif args.telechargement is None:
        args.telechargement = bool(
            args.ignlidar and not args.source and not maintenance_seule
        )

    if (args.ignlidar and not args.source and not maintenance_seule
            and args.ombrages is None and not args.shading_specs
            and not args.shading_preset):
        args.ombrages = ["lrm"]

    source_tif = bool(
        args.source and Path(args.source).suffix.lower() in (".tif", ".tiff")
    )
    ombrage_productif = bool(
        args.ombrages
        and not any(v in args.ombrages for v in ("aucun", "none"))
    )
    if (args.ignlidar and not args.formats_fichier
            and (ombrage_productif or args.shading_specs
                 or args.shading_preset or source_tif)):
        args.formats_fichier = ["mbtiles"]
    return args


def construire_parser_lidar(*, dependances: DependancesParserLidar):
    """Construit le parser argparse du workflow LiDAR/OSM."""
    d = dependances
    argparse = d.argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lidar2map.py
  python lidar2map.py --lidar --provider fr-ign --zone-city gareoult --zone-width 5
  python lidar2map.py --lidar --provider fr-ign --zone-department 83 --shadings multi --file-formats mbtiles
  python lidar2map.py --osm --zone-city gareoult
        """
    )
    parser.add_argument(
        "--version", action="version",
        version=f"lidar2map {d.version} ({d.version_date}), multi-provider",
    )
    parser.add_argument(
        "--lidar", "--ignlidar", action="store_true", dest="ignlidar",
        help="LiDAR terrain-processing workflow",
    )

    grp_priori = parser.add_argument_group(
        "A priori splitting — --lidar only",
        "Sequential chunk processing with automatic resume (manifeste.json).\n"
        "The same parameters also control the splitting of output files.",
    )
    grp_priori.add_argument(
        "--split-cols", "--cols-decoupe", type=int, default=0, metavar="N",
        dest="cols_decoupe", help="Number of grid columns (East-West).",
    )
    grp_priori.add_argument(
        "--split-rows", "--rows-decoupe", type=int, default=0, metavar="N",
        dest="rows_decoupe", help="Number of grid rows (North-South).",
    )
    grp_priori.add_argument(
        "--split-width", "--split-largeur", type=d.arg_float_non_negatif,
        default=0.0, metavar="KM", dest="split_width",
        help="Alternative: split into ~KM km squares (KM = the side).",
    )
    grp_priori.add_argument(
        "--block", "--bloc", default="", metavar="i/M", dest="block",
        help="Process only block i of M: M-way geographic split of the "
             "zone, this run does block i only. For sharding one area "
             "across several machines (same command each, only i changes). "
             "Composes with --split-width (internal chunking of the block).",
    )
    grp_priori.add_argument(
        "--cleanup", "--nettoyage", action="store_true", dest="nettoyage",
        help="Delete intermediate tiles + TIFs after each chunk. "
             "Essential for large areas (a whole department).",
    )
    grp_priori.add_argument(
        "--cleanup-keep-tiles", action="store_true",
        dest="nettoyage_garder_dalles",
        help="With --cleanup: keep the downloaded tiles in the shared "
             "cache, delete the other intermediates. Use when a later "
             "run reprocesses the same area (the GUI queue sets it "
             "automatically) to avoid re-downloading them.",
    )
    grp_priori.add_argument(
        "--min-free-gb", "--min-disque-go", type=d.arg_float_non_negatif,
        default=0.0, metavar="GB", dest="min_free_gb",
        help="Stop cleanly before a chunk if free disk space drops below GB "
             "(0 = disabled). Set it ABOVE one chunk's peak footprint "
             "(intermediates + tile pyramid). Exits with code 3 so a shell "
             "loop can tell a resumable disk-stop from a real error.",
    )

    d.ajouter_args_zone(
        parser,
        width_default=None,
        bbox_metavar="W,S,E,N",
        bbox_help="WGS84 bbox in degrees: lon_min,lat_min,lon_max,lat_max, "
                  "e.g. 5.9,43.1,6.6,43.8",
        avec_help_full=True,
    )

    parser.add_argument(
        "--output-dir", "--dossier", metavar="PATH", default=None,
        dest="dossier",
        help="Root output folder (default: <script>/ign_lidar/). "
             "Can be an external drive.",
    )
    parser.add_argument(
        "--tiles-dir", "--dossier-dalles", metavar="PATH", default=None,
        dest="dossier_dalles",
        help="IGN tiles cache folder (default: <output-dir>/dalles/). "
             "Useful to separate cache and outputs on different drives.",
    )

    parser.add_argument(
        "--provider", default=None, metavar="CODE",
        help="LiDAR provider code (required with --lidar). See the "
             "GUI selector or docs/providers.md for the current list.",
    )
    parser.add_argument(
        "--api-key", "--apikey", default="", metavar="KEY", dest="apikey",
        help="Provider API key when required. For us-3dep: "
             "https://portal.opentopography.org/myopentopo. "
             "For IGN scan*: cartes.gouv.fr pro account (see --raster). "
             "Can also be set via env IGN_APIKEY or "
             "OPENTOPOGRAPHY_API_KEY depending on the provider.",
    )
    parser.add_argument(
        "--workers", type=d.arg_int_positif, default=d.nb_workers, metavar="N",
        help=f"Parallel connections (default: {d.nb_workers})",
    )
    parser.add_argument(
        "--laz-parallel", type=d.arg_int_positif, default=1, metavar="N",
        dest="laz_parallel",
        help="LAZ (mode LAZ / --laz) : nb de conversions CSF/DFM "
             "SIMULTANÉES (défaut 1). Chaque conversion pique ~3 Go "
             "de RAM, donc N>1 exige la RAM (N x 3 Go) ET des cœurs "
             "(OMP est réparti à cœurs/N par conversion). Pour une "
             "VM multi-cœurs ; laisser 1 sur une machine 8 Go.",
    )
    parser.add_argument(
        "--download-compress", "--telechargement-compresser",
        action=argparse.BooleanOptionalAction, default=True,
        dest="telechargement_compresser",
        help="Compress cached tiles (DEFLATE, ~halves the cache: "
             "a whole department drops from ~90 GB to ~40 GB). "
             "Enabled by default; --no-download-compress keeps "
             "raw downloads (slightly faster CPU-wise).",
    )
    parser.add_argument(
        "--download-force", "--telechargement-forcer", action="store_true",
        dest="telechargement_forcer",
        help="Re-download tiles already present",
    )
    parser.add_argument(
        "--index-map", action=argparse.BooleanOptionalAction, default=True,
        dest="index_map",
        help="Generate <zone>_planche.png next to the deliverables: "
             "an index sheet (extent + department outline + numbered "
             "chunk cells for splits). Enabled by default; "
             "--no-index-map disables it. Standalone on an existing "
             "project folder: --index-sheet DIR (alias --planche).",
    )

    parser.add_argument(
        "--shadings", "--ombrages", metavar="TYPE", nargs="+",
        dest="ombrages",
        choices=list(d.shading_types_ordre) + ["all", "none", "tous", "aucun"],
        help=(
            "Shadings to generate (default for --lidar: lrm). "
            "Values: " + " ".join(d.shading_types_ordre) + " all none "
            "(French aliases: tous aucun). "
            "Names: lrm = Local Relief Model (implemented as SLRM, Simple LRM); "
            "vat = Visualization for Archaeological Topography (VAT-style variant); "
            "e4mstp = Multiscale Topographic Position, enhanced version 4 "
            "(lidar2map variant); svf = Sky-View Factor; "
            "rrim = Red Relief Image Map. "
            "opos/oneg = positive/negative openness (Yokoyama 2002; "
            "radius and gamma use the SVF defaults). "
            "See also --shading-preset. "
            "SVF is tuned via --svf-conv / --svf-dist / --svf-gamma / --svf-sweep. "
            "svf/lrm/rrim/vat: computed with numpy/scipy/numba (auto-installed). "
            "Ex: --shadings multi slope svf rrim"
        ),
    )
    parser.add_argument(
        "--shading", metavar="TYPE[:k=v,...]", action="append",
        dest="shading_specs", default=None,
        help=(
            "Parameterized shading instance, repeatable. "
            "Each occurrence requests one output with its own parameters. "
            "Filename suffixes are canonicalized; if two specifications "
            "resolve to the same filename, the first output is kept. "
            "--shading svf:dist=20,gamma=2 --shading svf:dist=100 "
            "--shading oneg:dist=20,gamma=1.5 --shading 315:elevation=20 "
            "--shading lrm:sigma=10. "
            "Params: 315/045/135/225/multi=elevation ; "
            "svf=conv,dist,gamma,sweep ; "
            "opos/oneg=dist,gamma,sweep ; "
            "vat/e4mstp=dist,gamma ; lrm/rrim=sigma(m) ; "
            "slope=none. Unset params inherit --svf-* / "
            "--shading-elevation, except e4mstp gamma, which "
            "defaults to 0.8. "
            "Combines with --shadings (a type listed in --shading "
            "is not re-generated at default params)."
        ),
    )
    parser.add_argument(
        "--shading-preset",
        choices=["auto", "micro", "standard", "landscape"],
        default=None, dest="shading_preset",
        help="Resolution-tuned shading stack (opt-in, params in "
             "metres): adds svf + opos + lrm sized for the DEM "
             "resolution, plus multi + slope. 'auto' picks micro "
             "(<=0.75 m), standard (>0.75 and <=2.5 m), or landscape "
             "(>2.5 m) from the active provider. Off by default; when "
             "set it takes precedence over --shadings default params.",
    )
    parser.add_argument(
        "--svf-conv", choices=["flux", "rvt"], default="flux",
        dest="svf_conv",
        help="SVF convention: flux = cos²γ (compressed near 1, "
             "contrast to the eye); rvt = 1−sin γ (Kokalj/Hesse, "
             "archaeology standard/openness). Default: flux.",
    )
    parser.add_argument(
        "--svf-dist", type=d.arg_float_positif, default=20.0, metavar="M",
        dest="svf_dist",
        help="Horizon-search radius in metres for SVF, openness, "
             "and their composites (GUI range 10–200). Default: "
             "20 (micro-relief). 100 = enclosures/roads.",
    )
    parser.add_argument(
        "--shading-elevation", "--ombrages-elevation", type=int,
        default=None, metavar="DEG", dest="ombrages_elevation",
        help=f"Sun angle of directional hillshades in degrees "
             f"(default: {d.elevation_soleil}°, archaeology optimal). "
             f"General use: 45°. Archaeology: 20-30°.",
    )
    parser.add_argument(
        "--svf-gamma", type=d.arg_float_positif, default=None, metavar="G",
        dest="svf_gamma",
        help=f"Gamma after percentile stretch for SVF, openness, "
             f"and VAT (default: {d.svf_gamma}). <1 lightens, "
             f"1 = linear, >1 darkens; negative openness uses "
             f"mirror gamma. e4mstp has its own final gamma "
             f"(default 0.8).",
    )

    parser.add_argument(
        "--download", "--telechargement",
        action=argparse.BooleanOptionalAction, default=None,
        dest="telechargement",
        help="Download missing provider tiles (default for a normal "
             "--lidar run). --no-download enforces cache-only processing. "
             "Valid cached tiles are never re-downloaded unless "
             "--download-force/--download-overwrite is set.",
    )
    parser.add_argument(
        "--tiles-purge-invalid", "--dalles-purger-invalides",
        action="store_true", dest="dalles_purger_invalides",
        help="Delete cache tiles < 2 MB (sea tiles, partial errors). "
             "Omit --download to purge without re-downloading.",
    )
    parser.add_argument(
        "--tiles-purge-out-of-zone", "--dalles-purger-hors-zone",
        action="store_true", dest="dalles_purger_hors_zone",
        help="Delete from cache the tiles outside the current zone "
             "(bbox/department). Useful to free space taken by tiles of other "
             "departments. Requires --zone-department, --zone-bbox, "
             "--zone-city or --zone-gps.",
    )
    parser.add_argument(
        "--shadings-compress", "--ombrages-compresser",
        action="store_true", dest="ombrages_compresser",
        help="Compress existing raw shadings (DEFLATE)",
    )
    parser.add_argument(
        "--download-overwrite", "--telechargement-ecraser",
        action="store_true", dest="telechargement_ecraser",
        help="Overwrite & re-download cached tiles, incl. LAZ point clouds "
             "(same as --download-force)",
    )
    parser.add_argument(
        "--shadings-overwrite", "--ombrages-ecraser",
        action="store_true", dest="ombrages_ecraser",
        help="Overwrite existing shadings",
    )
    parser.add_argument(
        "--svf-sweep", action=argparse.BooleanOptionalAction,
        default=True, dest="sweep_horizon",
        help="SVF sweep-horizon kernel with running max on a deque "
             "(upper convex hull). O(W·H·N) complexity instead of "
             "O(W·H·N·max_r). Speedup ~×5-15 for SVF20m, ~×30-50 "
             "for SVF100m, several hundred for large radii. "
             "Slight NN aliasing at low gradients, imperceptible "
             "for structures > 1-2 px. Default: enabled "
             "(--no-svf-sweep to disable).",
    )
    parser.add_argument(
        "--tiles-overwrite", "--tuiles-ecraser", action="store_true",
        dest="tuiles_ecraser", help="Overwrite existing tiles/MBTiles/.map",
    )
    parser.add_argument(
        "--file-formats", "--formats-fichier", nargs="+",
        dest="formats_fichier",
        choices=[
            "mbtiles", "rmap", "sqlitedb", "map", "gz", "geojson",
            "transparent-raster",
        ],
        default=[], metavar="FMT",
        help="Output file formats (multi-value; default for --lidar: mbtiles): "
             "mbtiles rmap sqlitedb (raster) ; map geojson gz (vector) ; "
             "transparent-raster (transparent PNG tiles rasterizing OSM/IGN "
             "vector -> .sqlitedb overlay for OsmAnd over the LiDAR).",
    )
    parser.add_argument(
        "--source", metavar="PATH", default=None,
        help="Existing source file. MBTiles conversion needs no zone; "
             "TIF and PBF processing still require a geographic area. "
             ".tif/.tiff: existing shading → MBTiles/RMAP "
             "            (CRS auto-detected: 3857=direct tiling, other=warp). "
             ".mbtiles  : conversion → RMAP (requires rmap format). "
             ".pbf      : OSM data → map (requires --osm). "
             "Ex: --source var_83_hillshade_multi.tif --zone-bbox ... "
             "--file-formats mbtiles rmap "
             "Ex: --source provence-alpes-cote-d-azur-latest.osm.pbf --osm",
    )
    parser.add_argument(
        "--zoom-min", type=int, default=13, metavar="N",
        help="Minimum MBTiles zoom (default: 13)",
    )
    parser.add_argument(
        "--zoom-max", type=int, default=18, metavar="N",
        help="Maximum MBTiles zoom (default: 18)",
    )
    parser.add_argument(
        "--image-quality", "--qualite-image", type=int, default=85,
        metavar="Q", dest="qualite_image",
        help="JPEG quality of tile images (default: 85). "
             "75 = -35%% size, almost invisible. 60 = -55%%, slight blur.",
    )
    parser.add_argument(
        "--image-format", "--formats-image", choices=["auto", "jpeg", "png"],
        default="auto", metavar="FMT", dest="formats_image",
        help="Format of tile images: auto, jpeg or png (default: auto).",
    )
    parser.add_argument(
        "--osm", action="store_true",
        help="Generate a vector OSM overlay MBTiles "
             "(paths, place names, hydrography, historical sites). "
             "The Geofabrik PBF is downloaded automatically if absent.",
    )
    parser.add_argument(
        "--layer", "--couche", metavar="TAGS", nargs="+", default=None,
        dest="couche",
        help="For --osm: OSM tags to include. "
             "Ex: --layer highway=* waterway=* natural=water",
    )
    return parser
