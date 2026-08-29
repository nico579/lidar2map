"""Passage monolithique du workflow raster WMTS/XYZ.

Le parser, la préparation, la résolution couche/zone et le dispatch du
découpage a priori restent dans :func:`lidar2map.main_wmts`. Les coutures
applicatives sont injectées tardivement par sa façade historique.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class DependancesRunWmts:
    """Dépendances du passage WMTS sans découpage a priori."""

    dossier_travail: Path
    dossier_cache: Path
    garde_disque: Callable[..., Any]
    calculer_grille_xyz: Callable[..., Any]
    compter_tuiles_xyz: Callable[..., int]
    estimer_taille: Callable[..., Any]
    jpeg_quality_sortie: Callable[..., Any]
    nom_mbtiles_wmts: Callable[..., str]
    mbtiles_a_regenerer: Callable[..., bool]
    generer_mbtiles_wmts: Callable[..., Any]
    convertir_formats: Callable[..., Any]
    planche_depuis_dossier: Callable[..., Any]
    maintenant: Callable[[], float]
    formater_duree: Callable[[Any], str]
    historique_depuis_argv: Callable[..., Any]
    imprimer: Callable[..., Any]


def executer_run_wmts_monolithique(
    args,
    t_debut,
    *,
    layer,
    style,
    img_fmt,
    apikey_requis,
    fmt_ext,
    bbox_wgs84,
    nom_zone,
    dependances,
):
    """Génère et convertit le MBTiles d'une zone WMTS non découpée."""

    d = dependances
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84

    d.garde_disque(
        Path(args.dossier).resolve() if args.dossier else d.dossier_travail,
        getattr(args, "min_free_gb", 0.0) or 0.0,
        "single-pass",
        0,
        1,
    )

    zoom_min = args.zoom_min
    zoom_max = args.zoom_max
    tuiles = d.calculer_grille_xyz(
        lat_min,
        lon_min,
        lat_max,
        lon_max,
        zoom_min,
        zoom_max,
    )
    total = d.compter_tuiles_xyz(
        lat_min,
        lon_min,
        lat_max,
        lon_max,
        zoom_min,
        zoom_max,
    )
    taille_est = d.estimer_taille(total, fmt_ext)

    source = layer[4:] if layer.startswith("XYZ:") else layer
    label = "Raster map" if layer.startswith("XYZ:") else "IGN map"
    d.imprimer("=" * 55)
    d.imprimer(f"  {label} - {args.couche} ({source})")
    d.imprimer("=" * 55)
    d.imprimer(f"  Zone    : {nom_zone}")
    d.imprimer(
        f"  BBox    : {lon_min:.4f},{lat_min:.4f} → "
        f"{lon_max:.4f},{lat_max:.4f}"
    )
    d.imprimer(f"  Zooms   : {zoom_min}–{zoom_max}")
    d.imprimer(f"  Tiles: {total:,}  (~{taille_est} MB estimated)")
    d.imprimer(f"  Workers : {args.workers}")

    dossier = (
        Path(args.dossier).resolve()
        if args.dossier
        else d.dossier_travail / "Projets" / nom_zone / "raster"
    )
    dossier.mkdir(parents=True, exist_ok=True)

    dossier_cache = d.dossier_cache / "ign_raster"
    dossier_cache.mkdir(parents=True, exist_ok=True)
    d.imprimer(f"  Tiles cache: {dossier_cache}")

    jpeg_quality = d.jpeg_quality_sortie(
        img_fmt,
        args.formats_image,
        args.qualite_image,
    )
    nom_fichier = d.nom_mbtiles_wmts(
        nom_zone,
        args.couche,
        zoom_min,
        zoom_max,
        jpeg_quality,
    )
    chemin_mbtiles = dossier / f"{nom_fichier}.mbtiles"

    mbtiles_requis = d.mbtiles_a_regenerer(
        chemin_mbtiles,
        args.tuiles_ecraser,
    )
    if not mbtiles_requis and chemin_mbtiles.exists():
        d.imprimer(
            f"  Existing MBTiles: {chemin_mbtiles.name}, "
            "direct split/conversion"
        )

    if mbtiles_requis:
        d.generer_mbtiles_wmts(
            chemin=chemin_mbtiles,
            tuiles_iter=tuiles,
            total=total,
            nom_zone=nom_zone,
            fmt_ext=fmt_ext,
            zoom_min=zoom_min,
            zoom_max=zoom_max,
            layer=layer,
            style=style,
            img_fmt=img_fmt,
            apikey=args.apikey,
            apikey_requis=apikey_requis,
            workers=args.workers,
            bbox_wgs84=bbox_wgs84,
            jpeg_quality=jpeg_quality,
            dossier_cache=dossier_cache,
            ecraser_tuiles=args.tuiles_ecraser,
            ecraser_dalles=args.telechargement_ecraser,
        )

    livrables_raster_ok = False
    if chemin_mbtiles.exists():
        livrables_raster_ok = bool(
            d.convertir_formats(
                chemin_mbtiles,
                args,
                mbtiles_neuf=mbtiles_requis,
            )
        )
    else:
        d.imprimer(
            f"  ERROR: expected MBTiles not produced: {chemin_mbtiles.name}"
        )

    d.planche_depuis_dossier(
        dossier,
        args,
        nom_zone,
        zone_bbox_wgs84=bbox_wgs84,
    )
    elapsed = int(d.maintenant() - t_debut)
    d.imprimer(f"\n  Done in {d.formater_duree(elapsed)}")
    d.imprimer(f"  Done! Folder: {dossier}")
    d.historique_depuis_argv(
        elapsed,
        str(dossier),
        statut=("ok" if livrables_raster_ok else "ko"),
    )
    if not livrables_raster_ok:
        raise RuntimeError(
            "raster generation/conversion incomplete - partial outputs kept; "
            "rerun to retry failed deliverables"
        )
