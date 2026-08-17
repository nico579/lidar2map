"""Fusion et livrables dérivés du mode vecteur."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependancesSortiesVecteur:
    fusionner_geojson: object
    epsilon_depuis_surface_km2: object
    generer_map: object
    rasteriser: object


@dataclass(frozen=True)
class ResultatSortiesVecteur:
    source_geojson: object
    complet: bool


def produire_sorties_vecteur(
    sorties,
    dossier,
    nom_zone,
    bbox_wgs84,
    *,
    formats=None,
    ecraser=False,
    simplification=None,
    zoom_min=8,
    zoom_max=18,
    dependances,
):
    """Fusionne les couches et produit les livrables explicitement demandés."""
    formats = formats or ["gz"]
    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    complet = True
    fusion = None
    if len(sorties) > 1:
        fusion = dependances.fusionner_geojson(
            sorties, Path(dossier) / f"{nom_zone}_ign.geojson"
        )
        if fusion is None:
            complet = False

    source = (fusion if len(sorties) > 1 else sorties[0]) if sorties else None

    if "map" in formats and sorties:
        if source is None or not Path(source).exists():
            print("\n  ⚠ Map generation skipped: no feature available.")
            complet = False
        else:
            if simplification:
                epsilon_m = simplification
                print(
                    f"\n  Vector simplification: epsilon={epsilon_m:.1f} m "
                    "(forced)"
                )
            else:
                surface = (
                    (lon_max - lon_min)
                    * (lat_max - lat_min)
                    * (111_000 ** 2)
                    / 1e6
                )
                epsilon_m = (
                    dependances.epsilon_depuis_surface_km2(surface) * 111_000
                )
                print(
                    f"\n  Vector simplification: epsilon={epsilon_m:.0f} m "
                    f"(auto, surface≈{surface:.0f} km²)"
                )
            print("  Generating Mapsforge map (.map) from IGN GeoJSON...")
            resultat = dependances.generer_map(
                geojson_src=source,
                dossier_ville=dossier,
                nom_zone=nom_zone,
                bbox_wgs84=bbox_wgs84,
                ecraser=ecraser,
                epsilon=epsilon_m / 111_000.0,
            )
            if resultat is None:
                complet = False

    if "transparent-raster" in formats:
        if source and Path(source).exists():
            zoom_max = int(zoom_max)
            zoom_min = min(max(int(zoom_min), 13), zoom_max)
            resultat = dependances.rasteriser(
                source,
                Path(dossier) / f"{nom_zone}_ign_transparent.sqlitedb",
                zoom_min,
                zoom_max,
                ecraser=ecraser,
                bbox_wgs84=bbox_wgs84,
            )
            if resultat is None:
                complet = False
        else:
            print("\n  ⚠ transparent-raster skipped: no feature available.")
            complet = False

    return ResultatSortiesVecteur(source, complet)
