"""Validation et préparation d'un run LiDAR avant le pipeline métier.

Ce module ne télécharge rien et ne lance aucun traitement raster. Il normalise
uniquement le contrat CLI, les racines de stockage, les instances d'ombrage,
les options du provider et les indicateurs de formats attendus par la suite du
pipeline. Les accès au monolithe restent injectés tardivement par sa façade.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class DependancesPreparationRunLidar:
    """Coutures nécessaires à la préparation reproductible d'un run."""

    zone_cli_presente: Callable[[Any], bool]
    valider_contrat_cli_lidar: Callable[[Any, Any], Any]
    appliquer_defauts_cli_lidar: Callable[[Any], Any]
    valider_zooms: Callable[[Any, Any], Any]
    appliquer_cache_dir: Callable[[Any], Any]
    appliquer_production_dir: Callable[[Any], Any]
    configurer_cloud_cache: Callable[[Any], Any]
    parser_shading_spec: Callable[[str], Any]
    resoudre_preset_shading: Callable[[str, float], Any]
    resolution_m: float
    provider: Any
    imprimer: Callable[..., Any] = print


def valider_contrat_cli_lidar(args, parser, *, provider_explicit):
    """Valide les paramètres rendant un run LiDAR reproductible."""
    if not getattr(args, "ignlidar", False):
        return None
    if not provider_explicit:
        parser.error(
            "--provider is required with --lidar "
            "(for example: --provider fr-ign)"
        )
    if ((getattr(args, "zone_ville", None)
         or getattr(args, "zone_gps", None))
            and getattr(args, "zone_width", None) is None):
        parser.error(
            "--zone-width is required with --zone-city or --zone-gps"
        )
    return None


def valider_zooms(args, parser):
    """Vérifie l'ordre et les bornes de la plage de zoom demandée."""
    zoom_min = getattr(args, "zoom_min", None)
    zoom_max = getattr(args, "zoom_max", None)
    if zoom_min is None or zoom_max is None:
        return None
    if zoom_min > zoom_max:
        parser.error(
            f"--zoom-min ({zoom_min}) > --zoom-max ({zoom_max}). "
            "Inversez les valeurs ou retirez l'un des deux pour utiliser "
            "le défaut."
        )
    if zoom_min < 0 or zoom_max > 22:
        parser.error(
            f"Zoom hors plage : --zoom-min={zoom_min} --zoom-max={zoom_max} "
            "(valeurs valides : 0 à 22)."
        )
    return None


def preparer_run_lidar(args, parser, *, dependances):
    """Valide et normalise ``args`` sans démarrer le pipeline métier."""
    d = dependances

    # Une conversion --source constitue sa propre intention. --osm partage le
    # parser terrain mais n'impose naturellement pas le workflow LiDAR.
    if not args.ignlidar and not args.osm and not args.source:
        parser.error(
            "choose a workflow: --lidar or --osm "
            "(or pass --source for a conversion)"
        )

    d.valider_contrat_cli_lidar(args, parser)

    source_ext = Path(args.source).suffix.lower() if args.source else ""
    if not d.zone_cli_presente(args) and source_ext not in (".mbtiles",):
        parser.error(
            "one geographic area is required: --zone-city, --zone-gps, "
            "--zone-bbox, --zone-department, or --zone-region"
        )

    d.appliquer_defauts_cli_lidar(args)
    d.valider_zooms(args, parser)
    d.appliquer_cache_dir(args)
    d.appliquer_production_dir(args)
    d.configurer_cloud_cache(args)

    # --shading TYPE:k=v est répétable. Les types explicites alimentent aussi
    # args.ombrages afin que les gates historiques voient le travail demandé.
    args.shading_instances = None
    if getattr(args, "shading_specs", None):
        instances = []
        for spec in args.shading_specs:
            try:
                instances.append(d.parser_shading_spec(spec))
            except ValueError as exc:
                parser.error(f"--shading : {exc}")
        args.shading_instances = instances
        args.ombrages = list(dict.fromkeys(
            (args.ombrages or []) + [type_ for type_, _ in instances]
        ))

    # Le preset suit la résolution du provider actif et complète les instances
    # explicites sans réintroduire leurs paramètres par défaut au dispatch.
    if getattr(args, "shading_preset", None):
        preset, preset_instances, elevation = d.resoudre_preset_shading(
            args.shading_preset, d.resolution_m
        )
        args.shading_instances = (
            (args.shading_instances or []) + preset_instances
        )
        args.ombrages = list(dict.fromkeys(
            (args.ombrages or [])
            + ["multi", "slope"]
            + [type_ for type_, _ in preset_instances]
        ))
        if args.ombrages_elevation is None:
            args.ombrages_elevation = elevation
        distance = preset_instances[0][1]["dist"]
        sigma = preset_instances[2][1]["sigma"]
        d.imprimer(
            f"  Shadings preset '{preset}' (res {d.resolution_m:g} m): "
            f"svf/opos radius {distance:g} m, lrm sigma {sigma:g} m, sun "
            f"{args.ombrages_elevation}°"
        )

    if hasattr(d.provider, "set_apikey"):
        d.provider.set_apikey(args.apikey)

    formats = args.formats_fichier
    args.mbtiles = "mbtiles" in formats
    args.rmap = "rmap" in formats
    args.sqlitedb = "sqlitedb" in formats
    args.transparent_raster = "transparent-raster" in formats
    return args
