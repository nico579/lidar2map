"""Orchestration finale d'un PBF OSM déjà acquis."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class DependancesRunOsm:
    """Coutures tardives du passage OSM post-acquisition."""

    dossier_travail: Path
    bbox_enveloppe_transform: Callable[..., Any]
    natif_vers_wgs84: Callable[..., Any]
    produire_sorties_osm: Callable[..., Any]
    imprimer: Callable[..., Any] = print


@dataclass(frozen=True)
class ResultatRunOsm:
    """État OSM utile au postlude commun de ``main()``."""

    bbox_wgs: Any
    dossier: Optional[Path]
    complet: bool


def executer_run_osm(args, bbox_natif, nom_zone, pbf, *, dependances):
    """Produit les livrables depuis un PBF dont l'existence est déjà vérifiée."""

    d = dependances
    region_mode = bool(getattr(args, "zone_region", None))
    if region_mode:
        # Le PBF est déjà découpé à la région : ni Osmosis ni l'export GeoJSON
        # ne doivent appliquer un second clip.
        bbox_wgs = (-180.0, -90.0, 180.0, 90.0)
    else:
        # Les bords sont densifiés par la couture commune afin de conserver une
        # enveloppe juste pour tous les CRS natifs des providers.
        try:
            bbox_wgs = d.bbox_enveloppe_transform(
                d.natif_vers_wgs84,
                bbox_natif[0],
                bbox_natif[1],
                bbox_natif[2],
                bbox_natif[3],
            )
        except (ValueError, TypeError, ImportError, RuntimeError) as exc:
            d.imprimer(
                f"  ERROR bbox WGS84 conversion "
                f"({type(exc).__name__}): {exc}"
            )
            return ResultatRunOsm(None, None, False)

    if not bbox_wgs:
        return ResultatRunOsm(bbox_wgs, None, False)

    dossier = (
        Path(args.dossier).resolve()
        if args.dossier
        else d.dossier_travail / "Projets" / nom_zone / "osm_vecteur"
    )
    dossier.mkdir(parents=True, exist_ok=True)
    resultat = d.produire_sorties_osm(
        bbox_wgs,
        dossier,
        nom_zone,
        pbf,
        formats=args.formats_fichier,
        osm_tags=(
            args.couche
            if getattr(args, "couche", None)
            else getattr(args, "osm_tags", None)
        ),
        ecraser=args.tuiles_ecraser,
        skip_bbox=region_mode,
        zoom_min=getattr(args, "zoom_min", 8),
        zoom_max=getattr(args, "zoom_max", 18),
    )
    return ResultatRunOsm(bbox_wgs, dossier, resultat.complet)
