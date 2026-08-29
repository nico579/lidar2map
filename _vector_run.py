"""Orchestration du workflow vectoriel WFS après préparation de la CLI.

Le démarrage crash-safe de l'historique reste dans :func:`lidar2map.main_wfs`.
Toutes les coutures applicatives de ce module sont injectées par la façade du
script principal afin de préserver les monkeypatchs historiques.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class DependancesRunWfs:
    """Dépendances tardives nécessaires à l'exécution d'un run WFS."""

    couches_wfs: Mapping[str, Any]
    dossier_travail: Path
    resoudre_zone_wgs84: Callable[[Any], Any]
    acquerir_couches_vecteur: Callable[..., Any]
    produire_sorties_vecteur: Callable[..., Any]
    planche_depuis_dossier: Callable[..., Any]
    maintenant: Callable[[], float]
    formater_duree: Callable[[int], str]
    historique_depuis_argv: Callable[..., Any]
    imprimer: Callable[..., Any]


def executer_run_wfs(args, formats_geojson, t_debut, *, dependances):
    """Exécute le workflow WFS déjà validé et finalise son historique."""

    d = dependances

    couches_resolues = []
    for couche in args.couche:
        if couche in d.couches_wfs:
            definition = d.couches_wfs[couche]
            couches_resolues.append((definition[0], definition[1]))
        else:
            couches_resolues.append((couche, couche))

    lon_min, lat_min, lon_max, lat_max, nom_zone = d.resoudre_zone_wgs84(args)
    bbox_wgs84 = (lon_min, lat_min, lon_max, lat_max)

    dossier = (
        Path(args.dossier).resolve()
        if args.dossier
        else d.dossier_travail / "Projets" / nom_zone / "ign_vecteur"
    )
    dossier.mkdir(parents=True, exist_ok=True)

    d.imprimer("=" * 56)
    d.imprimer("  Vecteur IGN WFS → GeoJSON")
    d.imprimer("=" * 56)
    d.imprimer(f"  Zone     : {nom_zone}")
    d.imprimer(
        f"  BBox     : {lon_min:.4f},{lat_min:.4f} → "
        f"{lon_max:.4f},{lat_max:.4f}"
    )
    d.imprimer(f"  Layer(s): {', '.join(c[1] for c in couches_resolues)}")
    d.imprimer(f"  Output   : {dossier}")

    sorties = d.acquerir_couches_vecteur(
        couches_resolues,
        bbox_wgs84,
        nom_zone,
        dossier,
        num_dep=getattr(args, "zone_departement", None),
        ecraser=args.telechargement_ecraser,
        formats=formats_geojson,
        workers=args.workers,
    )

    resultat_vecteur = d.produire_sorties_vecteur(
        sorties,
        dossier,
        nom_zone,
        bbox_wgs84,
        formats=getattr(args, "formats_fichier", ["gz"]),
        ecraser=args.tuiles_ecraser,
        simplification=getattr(args, "simplification_vecteur", None),
        zoom_min=getattr(args, "zoom_min", 8),
        zoom_max=getattr(args, "zoom_max", 18),
    )
    livrables_ok = resultat_vecteur.complet

    d.planche_depuis_dossier(
        dossier,
        args,
        nom_zone,
        zone_bbox_wgs84=bbox_wgs84,
    )
    elapsed = int(d.maintenant() - t_debut)
    d.imprimer(
        f"\n  Done in {d.formater_duree(elapsed)}: "
        f"{len(sorties)}/{len(couches_resolues)} layers"
    )
    d.imprimer(f"  Done! Folder: {dossier}")
    for sortie in sorties:
        d.imprimer(f"  → {sortie}")

    wfs_partiel = len(sorties) < len(couches_resolues)
    traitement_ko = wfs_partiel or not livrables_ok
    d.historique_depuis_argv(
        elapsed,
        str(dossier),
        statut=("ko" if traitement_ko else "ok"),
    )
    if wfs_partiel:
        raise RuntimeError(
            f"{len(couches_resolues) - len(sorties)} WFS "
            "layer(s) failed - rerun to retry them"
        )
    if not livrables_ok:
        raise RuntimeError("Requested vector deliverable generation failed")
