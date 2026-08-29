"""Acquisition monolithique des dalles terrain avant production raster.

La découverte, la validation du cache, le téléchargement et la sélection des
dalles d'ombrage forment une transaction cohérente. Les dépendances du
monolithe sont injectées par une façade tardive afin de conserver les coutures
historiques et de rendre les sorties anticipées explicitement testables.
"""

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Callable, List, Optional, Tuple


@dataclass(frozen=True)
class DependancesAcquisitionTerrain:
    """Coutures nécessaires à l'acquisition d'une zone terrain."""

    provider: Any
    dossier_cache: Path
    get_transformer: Callable[..., Any]
    bbox_enveloppe_transform: Callable[..., Any]
    rglob_tif_robuste: Callable[[Path], List[Path]]
    seuil_dalle_valide: int
    telecharger_dalles_zone: Callable[..., Any]
    dalles_zone_hdr_ok: Callable[..., bool]
    ecrire_dalles_zone: Callable[..., Any]
    historique_depuis_argv: Callable[..., Any]
    maintenant: Callable[[], float]
    imprimer: Callable[..., Any] = print
    quitter: Callable[[int], Any] = sys.exit


@dataclass(frozen=True)
class ResultatAcquisitionTerrain:
    """État transmis à la production terrain après l'acquisition."""

    bbox_wgs: Optional[Tuple[float, float, float, float]]
    dalles_ombrages: List[Path]
    termine_sans_couverture: bool = False


def acquerir_dalles_terrain(
    args,
    bbox,
    nom_zone,
    dossier_dalles,
    dossier_ville,
    osm_seul,
    t_debut,
    *,
    dependances,
):
    """Découvre, acquiert et filtre les dalles utiles au passage monolithique."""
    d = dependances

    # OSM-seul ne doit jamais interroger le provider : certaines découvertes
    # TMS parcourent des milliers de tuiles d'index sur une grande région.
    if osm_seul:
        bbox_wgs = None
        dalles_dict = {}
        noms_attendus = set()
    else:
        transformeur = d.get_transformer(
            d.provider.CRS_NATIF,
            "EPSG:4326",
        )
        lon1, lat1, lon2, lat2 = d.bbox_enveloppe_transform(
            transformeur.transform,
            bbox[0],
            bbox[1],
            bbox[2],
            bbox[3],
        )
        bbox_wgs = (lon1 - 0.05, lat1 - 0.05, lon2 + 0.05, lat2 + 0.05)
        cache_discover = (
            d.dossier_cache / f"discover_{d.provider.CODE}.json"
        )

        # None signifie que le service de découverte est indisponible ; un
        # dictionnaire vide signifie au contraire une absence de couverture
        # légitime. Cette distinction détermine le statut final du run.
        try:
            decouverte = d.provider.discover_dalles(
                bbox_wgs,
                bbox,
                cache_discover,
            )
            if decouverte is None:
                d.imprimer(
                    "  ⚠ Tile discovery unavailable (network/endpoint),"
                    " zone skipped, retry.",
                    flush=True,
                )
        except Exception as exc:
            d.imprimer(
                f"  ⚠ Tile discovery failed ({type(exc).__name__}: {exc}),"
                " zone skipped, retry.",
                flush=True,
            )
            decouverte = None

        dalles_dict = decouverte or {}
        noms_attendus = set(dalles_dict.keys())

        if args.telechargement and not dalles_dict and not args.source:
            duree = max(0, int(d.maintenant() - t_debut))
            if decouverte is None:
                d.historique_depuis_argv(
                    duree,
                    str(dossier_ville),
                    statut="ko",
                )
                d.quitter(1)
            d.imprimer(
                "  No LiDAR tile for this zone (out of coverage), "
                "nothing to download."
            )
            d.imprimer(f"  Done! Folder: {dossier_ville}")
            d.historique_depuis_argv(
                duree,
                str(dossier_ville),
                statut="ok",
            )
            return ResultatAcquisitionTerrain(
                bbox_wgs=bbox_wgs,
                dalles_ombrages=[],
                termine_sans_couverture=True,
            )

    sauter_telechargement = False
    if osm_seul:
        sauter_telechargement = True
    if not args.telechargement and not args.ombrages:
        sauter_telechargement = True

    if not sauter_telechargement and not args.telechargement:
        source_ext = Path(args.source).suffix.lower() if args.source else ""
        if source_ext in (".tif", ".tiff", ".mbtiles"):
            sauter_telechargement = True
        else:
            dalles_existantes = (
                d.rglob_tif_robuste(dossier_dalles)
                if dossier_dalles.exists()
                else []
            )
            if not dalles_existantes:
                d.imprimer(
                    "\n  WARNING: downloads are disabled and no cached tile "
                    "was found."
                )
                d.imprimer(f"  Tiles folder : {dossier_dalles}")
                d.imprimer(
                    "  Remove --no-download (normal --lidar default), or add "
                    "--download to a maintenance command."
                )
                d.quitter(1)

            if noms_attendus:
                dalles_zone_cache = [
                    dalle
                    for dalle in dalles_existantes
                    if dalle.name in noms_attendus
                    and dalle.stat().st_size > d.seuil_dalle_valide
                ]
                if not dalles_zone_cache:
                    d.imprimer(
                        f"\n  WARNING: {len(dalles_existantes)} tile(s) in cache,"
                    )
                    d.imprimer(
                        "              but NONE covers the requested zone."
                    )
                    d.imprimer(f"  Global cache: {dossier_dalles}")
                    libelle_zone = args.zone_ville or nom_zone
                    d.imprimer(
                        f"  Requested zone: {len(noms_attendus)} tile(s) around "
                        f"{libelle_zone}"
                    )
                    d.imprimer(
                        "  Remove --no-download (normal --lidar default), or "
                        "add --download to a maintenance command."
                    )
                    d.quitter(1)
                d.imprimer(
                    "\n  Download skipped "
                    f"({len(dalles_zone_cache)}/{len(noms_attendus)} zone "
                    "tile(s) found in cache)"
                )
            else:
                d.imprimer(
                    f"\n  Download skipped ({len(dalles_existantes)} tile(s) "
                    "in cache)"
                )
            sauter_telechargement = True

    if not sauter_telechargement:
        d.telecharger_dalles_zone(
            dalles_dict,
            bbox,
            dossier_dalles,
            dossier_ville,
            args,
        )

    # La liste persistée borne strictement l'assemblage à la zone courante : le
    # cache disque peut contenir plusieurs départements et plusieurs providers.
    if dossier_dalles.exists() and not osm_seul:
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        noms_zone = set()
        if dalles_zone_txt.exists():
            lignes = dalles_zone_txt.read_text(encoding="utf-8").splitlines()
            bbox_courante = (
                f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},"
                f"{bbox[2]:.0f},{bbox[3]:.0f}"
            )
            bbox_fichier = lignes[0].strip() if lignes else ""
            if not d.dalles_zone_hdr_ok(lignes, bbox):
                d.imprimer(
                    "  Zone/provider changed - rebuilding "
                    f"{dalles_zone_txt.name} from cache..."
                )
                d.imprimer(f"    Ancienne bbox : {bbox_fichier}")
                d.imprimer(f"    Nouvelle bbox : {bbox_courante}")
                toutes_dalles_dispo = d.rglob_tif_robuste(dossier_dalles)
                noms_zone = {
                    dalle.name
                    for dalle in toutes_dalles_dispo
                    if dalle.name in noms_attendus
                    and dalle.stat().st_size > d.seuil_dalle_valide
                }
                if noms_zone:
                    d.ecrire_dalles_zone(dalles_zone_txt, bbox, noms_zone)
                    d.imprimer(
                        f"  {dalles_zone_txt.name} rebuilt: {len(noms_zone)} "
                        "tile(s) in cache"
                    )
                else:
                    d.imprimer(
                        "  No tile in cache for this zone - enable downloads"
                    )
                    noms_zone = set()
            else:
                noms_zone = {
                    nom.strip()
                    for nom in lignes[1:]
                    if nom.strip() and not nom.startswith("#")
                }
                d.imprimer(
                    f"  Zone tiles list: {dalles_zone_txt.name} "
                    f"({len(noms_zone)} tiles)"
                )
        elif not args.telechargement and noms_attendus:
            if args.osm and not args.ombrages and not args.mbtiles:
                pass
            else:
                d.imprimer(
                    f"  Rebuilding {dalles_zone_txt.name} from disk cache..."
                )
                toutes_dalles_dispo = d.rglob_tif_robuste(dossier_dalles)
                noms_zone = {
                    dalle.name
                    for dalle in toutes_dalles_dispo
                    if dalle.name in noms_attendus
                    and dalle.stat().st_size > d.seuil_dalle_valide
                }
                if noms_zone:
                    d.ecrire_dalles_zone(dalles_zone_txt, bbox, noms_zone)
                    d.imprimer(
                        "  dalles_zone.txt rebuilt: "
                        f"{len(noms_zone)} tile(s) found on disk"
                    )
                else:
                    d.imprimer(
                        f"  ERROR: no tile of the zone found in {dossier_dalles}"
                    )
                    d.imprimer(
                        "  Relaunch without --no-download, or pass --download "
                        "explicitly."
                    )
                    d.quitter(1)
        else:
            if args.osm and not args.ombrages and not args.mbtiles:
                pass
            else:
                d.imprimer(
                    f"\n  ERROR: {dalles_zone_txt.name} not found in "
                    f"{dossier_ville}/"
                )
                d.imprimer(
                    "  This file is created automatically during download."
                )
                d.imprimer(
                    "  Relaunch without --no-download, or pass --download "
                    "explicitly."
                )
                d.imprimer(
                    "  (Tiles already present on disk will be skipped, "
                    "~a few seconds)"
                )
                d.quitter(1)

        toutes_dalles = sorted(d.rglob_tif_robuste(dossier_dalles))
        dalles_zone = [
            dalle for dalle in toutes_dalles if dalle.name in noms_zone
        ]
        dalles_ombrages = [
            dalle
            for dalle in dalles_zone
            if dalle.stat().st_size > d.seuil_dalle_valide
        ]
        nb_hors_zone = len(toutes_dalles) - len(dalles_zone)
        nb_invalides = len(dalles_zone) - len(dalles_ombrages)
        if nb_hors_zone:
            d.imprimer(
                f"  {nb_hors_zone} out-of-zone tile(s) skipped "
                "(other departments)"
            )
        if nb_invalides:
            d.imprimer(
                f"  {nb_invalides} invalid tile(s) skipped "
                "(< 2 MB - sea or out of coverage)"
            )
        d.imprimer(
            f"  {len(dalles_ombrages)} tile(s) kept for shadings"
        )
    else:
        dalles_ombrages = []

    return ResultatAcquisitionTerrain(
        bbox_wgs=bbox_wgs,
        dalles_ombrages=dalles_ombrages,
    )
