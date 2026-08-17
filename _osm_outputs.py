"""Orchestration des livrables du mode OSM vectoriel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependancesSortiesOsm:
    generer_carte: object
    rasteriser: object


@dataclass(frozen=True)
class ResultatSortiesOsm:
    carte_ou_geojson_ok: bool
    overlay_ok: bool

    @property
    def complet(self):
        return self.carte_ou_geojson_ok and self.overlay_ok


def produire_sorties_osm(
    bbox_wgs84,
    dossier,
    nom_zone,
    osm_pbf,
    *,
    formats,
    osm_tags=None,
    ecraser=False,
    skip_bbox=False,
    zoom_min=8,
    zoom_max=18,
    dependances,
):
    """Produit tous les livrables OSM demandés et agrège leur statut réel."""
    dossier = Path(dossier)
    formats = tuple(formats or ())
    geojson_formats = [f for f in ("gz", "geojson") if f in formats]
    veut_overlay = "transparent-raster" in formats
    if veut_overlay and not geojson_formats:
        geojson_formats = ["gz"]

    vectoriel_explicite = any(
        f in formats for f in ("map", "gz", "geojson", "transparent-raster")
    )
    veut_map = "map" in formats or not vectoriel_explicite
    resultat_generation = dependances.generer_carte(
        bbox_wgs84,
        dossier,
        nom_zone,
        osm_pbf,
        osm_tags=osm_tags,
        export_geojson=bool(geojson_formats),
        ecraser_tuiles=ecraser,
        skip_bbox=skip_bbox,
        geojson_formats=geojson_formats or ["gz"],
        want_map=veut_map,
    )
    carte_ok = bool(resultat_generation)
    if veut_map:
        carte_ok = carte_ok and (dossier / f"{nom_zone}.map").is_file()
    if "gz" in geojson_formats:
        carte_ok = carte_ok and (
            dossier / f"{nom_zone}_osm.geojson.gz"
        ).is_file()
    if "geojson" in geojson_formats:
        carte_ok = carte_ok and (
            dossier / f"{nom_zone}_osm.geojson"
        ).is_file()

    overlay_ok = True
    if veut_overlay:
        source = dossier / f"{nom_zone}_osm.geojson.gz"
        if not source.exists():
            source = dossier / f"{nom_zone}_osm.geojson"
        if not source.exists():
            overlay_ok = False
        else:
            zmax = int(zoom_max)
            zmin = min(max(int(zoom_min), 13), zmax)
            overlay_ok = bool(dependances.rasteriser(
                source,
                dossier / f"{nom_zone}_osm_transparent.sqlitedb",
                zmin,
                zmax,
                ecraser=ecraser,
                bbox_wgs84=bbox_wgs84,
            ))

    return ResultatSortiesOsm(carte_ok, overlay_ok)
