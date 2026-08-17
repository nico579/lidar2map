"""Orchestration métier de la commande de fusion GeoJSON."""

from dataclasses import dataclass
import glob
from pathlib import Path


@dataclass(frozen=True)
class DependancesFusionCli:
    fusionner_geojson: object
    epsilon_depuis_surface_km2: object
    epsilon_defaut: float
    generer_map: object
    rasteriser: object


@dataclass(frozen=True)
class ResultatFusionCli:
    sortie: object
    bbox: object
    fichiers_ignores: tuple
    fusion_ok: bool
    map_ok: bool
    raster_ok: bool

    @property
    def complet(self):
        return (
            self.fusion_ok
            and self.map_ok
            and self.raster_ok
            and not self.fichiers_ignores
        )


def resoudre_sources_fusion(patterns):
    """Développe les globs en conservant les chemins sans correspondance."""
    fichiers = []
    for pattern in patterns:
        correspondances = glob.glob(pattern)
        if correspondances:
            fichiers.extend(sorted(correspondances))
        else:
            fichiers.append(pattern)
    return fichiers


def determiner_sortie_fusion(fichiers, sortie=None, dossier=None, no_gz=False):
    """Détermine le chemin explicite ou historique de la fusion."""
    if sortie:
        return Path(sortie)
    dossier_sortie = Path(dossier) if dossier else Path(fichiers[0]).parent
    base = Path(fichiers[0]).stem.split(".")[0]
    extension = ".geojson" if no_gz else ".geojson.gz"
    return dossier_sortie / f"{base}_fusion{extension}"


def executer_fusion_cli(
        fichiers, sortie, *, formats, simplification=None,
        zoom_min=8, zoom_max=18, dependances):
    """Fusionne les sources puis produit tous les livrables demandés."""
    ignores = []
    fusion = dependances.fusionner_geojson(
        fichiers, sortie, fichiers_ignores=ignores,
    )
    fusion_ok = bool(fusion and fusion[0] is not None)
    if not fusion_ok:
        return ResultatFusionCli(
            None, None, tuple(ignores), False, True, True,
        )

    resultat, bbox = fusion
    formats_normalises = {str(fmt).lower() for fmt in formats}
    nom_zone = Path(sortie).stem.split(".")[0]
    map_ok = True
    raster_ok = True

    if "map" in formats_normalises:
        if simplification:
            epsilon = simplification / 111_000.0
            print(
                f"  Vector simplification: epsilon={simplification:.1f} m "
                "(forced)"
            )
        elif bbox:
            surface = (
                (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                * (111_000 ** 2) / 1e6
            )
            epsilon = dependances.epsilon_depuis_surface_km2(surface)
            print(
                f"  Vector simplification: epsilon={epsilon * 111000:.0f} m "
                f"(auto, surface≈{surface:.0f} km²)"
            )
        else:
            epsilon = dependances.epsilon_defaut
        try:
            map_ok = bool(dependances.generer_map(
                resultat,
                Path(sortie).parent,
                nom_zone,
                bbox_wgs84=bbox,
                ecraser=True,
                epsilon=epsilon,
            ))
        except Exception as exc:
            print(f"  ERROR generating .map: {exc}")
            map_ok = False

    if "transparent-raster" in formats_normalises:
        zoom_maximum = int(zoom_max)
        zoom_minimum = min(max(int(zoom_min), 13), zoom_maximum)
        try:
            raster_ok = bool(dependances.rasteriser(
                resultat,
                Path(sortie).parent / f"{nom_zone}_transparent.sqlitedb",
                zoom_minimum,
                zoom_maximum,
                ecraser=True,
                bbox_wgs84=bbox,
            ))
        except Exception as exc:
            print(f"  ERROR generating transparent raster: {exc}")
            raster_ok = False

    return ResultatFusionCli(
        resultat,
        bbox,
        tuple(ignores),
        True,
        map_ok,
        raster_ok,
    )
