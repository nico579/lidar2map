"""Sélection bulk/WFS et acquisition des couches du mode vecteur."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependancesAcquisitionVecteur:
    telecharger_bulk: object
    telecharger_wfs: object
    executor_factory: object


def _couches_absentes(couches, sorties, nom_zone):
    noms = {Path(sortie).name for sortie in sorties}
    absentes = []
    for typename, description in couches:
        couche = typename.split(":")[-1].lower()
        gzip = f"{nom_zone}_ign_{couche}.geojson.gz"
        brut = f"{nom_zone}_ign_{couche}.geojson"
        if gzip not in noms and brut not in noms:
            absentes.append((typename, description))
    return absentes


def acquerir_couches_vecteur(
    couches_resolues,
    bbox_wgs84,
    nom_zone,
    dossier,
    *,
    num_dep=None,
    ecraser=False,
    formats=None,
    workers=1,
    dependances,
):
    """Acquiert les couches par bulk puis WFS, sans doubler les tentatives."""
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84

    def telecharger_une(couche):
        typename, description = couche
        print(f"\n  [{description}]")
        return dependances.telecharger_wfs(
            typename,
            lon_min,
            lat_min,
            lon_max,
            lat_max,
            nom_zone,
            dossier,
            ecraser_telechargement=ecraser,
            formats=formats,
        )

    if num_dep:
        sorties_bulk = dependances.telecharger_bulk(
            num_dep=num_dep,
            couches_resolues=couches_resolues,
            nom_zone=nom_zone,
            dossier_sortie=dossier,
            bbox_l93=None,
            ecraser=ecraser,
            formats=formats,
        )
        if sorties_bulk is not None:
            sorties = list(sorties_bulk)
            absentes = _couches_absentes(couches_resolues, sorties, nom_zone)
            if absentes:
                print(
                    f"  Bulk covered {len(sorties)}/{len(couches_resolues)} "
                    f"layers; retrying {len(absentes)} via WFS pagination..."
                )
                for couche in absentes:
                    resultat = telecharger_une(couche)
                    if resultat:
                        sorties.append(resultat)
            return sorties
        print("  Falling back to WFS pagination...")

    sorties = []
    if workers > 1 and len(couches_resolues) > 1:
        maximum = min(workers, len(couches_resolues))
        with dependances.executor_factory(max_workers=maximum) as executor:
            for resultat in executor.map(telecharger_une, couches_resolues):
                if resultat:
                    sorties.append(resultat)
    else:
        for couche in couches_resolues:
            resultat = telecharger_une(couche)
            if resultat:
                sorties.append(resultat)
    return sorties
