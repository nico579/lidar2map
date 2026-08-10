"""Runner LiDAR glissant des traitements découpés.

Ce module porte l'ordonnancement ombrage/tuilage par rangée et le voisinage
3×3. Les producteurs raster et les services applicatifs restent fournis par
la façade ``lidar2map`` afin d'éviter tout import circulaire et de préserver
les coutures de test historiques.
"""

from __future__ import annotations

import gc
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from _split_planning import _cle_chunk, _identite_chunk


def _voisins_dossiers(
    racine,
    nom_zone_base,
    i_lat,
    i_lon,
    n_lat,
    n_lon,
):
    """Retourne les dossiers des huit voisins valides d'un chunk."""
    voisins = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            vi, vj = i_lat + di, i_lon + dj
            if 0 <= vi < n_lat and 0 <= vj < n_lon:
                voisins.append(
                    racine / _identite_chunk(nom_zone_base, vi, vj)[1]
                )
    return voisins


@dataclass(frozen=True)
class _DependancesRunnerGlissant:
    """Coutures entre l'orchestrateur glissant et l'application."""

    fabrique_manifeste: Callable
    signature_config: Callable
    morceau_termine_reutilisable: Callable
    fabrique_prefetch: Callable
    dalles_zone_lookahead: Callable
    garde_disque: Callable
    definir_chunk_log: Callable
    traiter_ombrage: Callable
    traiter_tuilage: Callable
    normaliser_resultat_chunk: Callable
    chunk_livrable_complet: Callable
    supprimer_fichiers: Callable
    formater_duree: Callable
    planche_depuis_dossier: Callable
    dossier_travail: Path
    lidar_subdir: str


def _run_split_priori_lidar_glissant(
    args,
    sous_zones,
    nom_zone,
    racine_pr,
    overwrite_actif,
    entete_chunk,
    t_debut,
    *,
    dependances,
):
    """Exécute le pipeline glissant ombrage/tuilage par rangée.

    Une rangée d'ombrages est calculée avant de tuiler la précédente : les
    voisins 3×3 sont ainsi disponibles sans conserver tout le département.
    La reprise prévalide les livrables finaux avant l'ombrage afin de recréer
    également les voisins qui auraient déjà été purgés.
    """
    # Un même processus peut enchaîner plusieurs départements ou plusieurs
    # appels de test : ne jamais hériter du dernier chunk du run précédent.
    dependances.definir_chunk_log(None)
    manifeste = dependances.fabrique_manifeste(
        racine_pr / nom_zone / "manifeste.json"
    )
    if manifeste.verifier_signature(
        dependances.signature_config(args, sous_zones)
    ):
        print(
            "  ⚠ Output config changed since last run "
            "(bbox/split/zoom/format/shading): reprocessing all chunks."
        )
        if hasattr(args, "tuiles_ecraser"):
            args.tuiles_ecraser = True
        if hasattr(args, "ombrages_ecraser"):
            args.ombrages_ecraser = True
        overwrite_actif = True

    n_total = len(sous_zones)
    n_lat = max(zone[0] for zone in sous_zones) + 1
    n_lon = max(zone[1] for zone in sous_zones) + 1
    rangees = [[] for _ in range(n_lat)]
    for sous_zone in sous_zones:
        rangees[sous_zone[0]].append(sous_zone)
    for rangee in rangees:
        rangee.sort(key=lambda zone: zone[1])

    print(
        "\n  ══ A-priori splitting (VRT voisins glissant): "
        f"{n_lat} rangée(s), {n_total} chunk(s) ══"
    )
    print(f"  Manifeste : {manifeste.path}")

    racine = (
        Path(args.dossier).resolve()
        if args.dossier
        else dependances.dossier_travail
        / "Projets"
        / nom_zone
        / dependances.lidar_subdir
    )

    def _cle(sous_zone):
        return _cle_chunk(sous_zone[0], sous_zone[1])

    # Si un livrable final a disparu, son tuilage et toute sa fermeture de
    # voisins 3×3 doivent être reconstruits. Le détecter pendant le tuilage
    # serait trop tard : les rangées d'ombrage auraient déjà été sautées.
    zones_par_index = {
        (sous_zone[0], sous_zone[1]): sous_zone
        for sous_zone in sous_zones
    }
    tuilages_a_rejouer = set()
    for sous_zone in sous_zones:
        cle_zone = _cle(sous_zone)
        cle_tuilage = cle_zone + "_t"
        nom_chunk = f"{nom_zone}_{cle_zone}"
        if overwrite_actif or not dependances.morceau_termine_reutilisable(
            manifeste,
            cle_tuilage,
            racine / nom_chunk,
            args,
        ):
            tuilages_a_rejouer.add(cle_zone)

    ombrages_requis = set()
    for sous_zone in sous_zones:
        if _cle(sous_zone) not in tuilages_a_rejouer:
            continue
        for delta_ligne in (-1, 0, 1):
            for delta_colonne in (-1, 0, 1):
                voisin = zones_par_index.get(
                    (
                        sous_zone[0] + delta_ligne,
                        sous_zone[1] + delta_colonne,
                    )
                )
                if voisin is not None:
                    ombrages_requis.add(_cle(voisin))

    def _ombrage_termine_reutilisable(cle):
        """Valide la preuve TIF seulement si un tuilage en dépend encore."""
        if not manifeste.deja_traite(cle) or overwrite_actif:
            return False
        if cle not in ombrages_requis:
            return True
        dossier_chunk = (racine / f"{nom_zone}_{cle}").resolve()
        tifs_suivis = []
        for fichier in manifeste.fichiers_morceau(cle):
            path = Path(fichier)
            if (
                path.suffix.lower() == ".tif"
                and path.parent.resolve() == dossier_chunk
                and not path.name.startswith("_")
                and not re.search(r"_tuilage_z\d+\.tif$", path.name)
            ):
                tifs_suivis.append(path)
        if tifs_suivis and all(path.is_file() for path in tifs_suivis):
            return True
        if tifs_suivis:
            print(
                f"  [{cle}] tracked shading missing "
                "- recomputing before resume"
            )
        else:
            print(
                f"  [{cle}] shading proof missing "
                "- recomputing before resume"
            )
        manifeste.oublier_fichiers_absents(cle)
        manifeste.invalider_morceau(cle)
        return False

    # Ordre exact de l'ombrage : le téléchargement du morceau suivant peut
    # recouvrir le calcul courant sans changer l'ordre ni le résultat.
    flat_ombrage = [sous_zone for rangee in rangees for sous_zone in rangee]
    index_ombrage = {
        _cle(sous_zone): index
        for index, sous_zone in enumerate(flat_ombrage)
    }
    prefetch = dependances.fabrique_prefetch()

    def _lancer_prefetch_suivant(cle_courant):
        index = index_ombrage[cle_courant] + 1
        if index >= len(flat_ombrage):
            return
        sous_zone_suivante = flat_ombrage[index]
        cle_suivante = _cle(sous_zone_suivante)
        if _ombrage_termine_reutilisable(cle_suivante):
            return
        prefetch.lancer(
            args,
            manifeste,
            racine_pr,
            nom_zone,
            sous_zone_suivante,
            cle_suivante,
        )

    def _noms_dalles_morceau_suivant(cle_courant):
        """Protège du nettoyage les dalles réclamées par le chunk suivant."""
        index = index_ombrage[cle_courant] + 1
        if index >= len(flat_ombrage):
            return None
        sous_zone_suivante = flat_ombrage[index]
        if _ombrage_termine_reutilisable(_cle(sous_zone_suivante)):
            return None
        return dependances.dalles_zone_lookahead(
            tuple(sous_zone_suivante[2:])
        )

    def _etape_ombrage(sous_zone):
        gc.collect()
        cle = _cle(sous_zone)
        if _ombrage_termine_reutilisable(cle):
            return
        nom_chunk = f"{nom_zone}_{cle}"
        dependances.definir_chunk_log(f"{cle}:ombrage")
        print(
            f"\n  ── Ombrage [{cle}]  "
            f"({index_ombrage[cle] + 1}/{n_total})  {nom_chunk} ──"
        )
        print(f"     {entete_chunk(tuple(sous_zone[2:]))}")
        dependances.garde_disque(
            racine_pr,
            getattr(args, "min_free_gb", 0.0) or 0.0,
            cle,
            0,
            n_total,
        )
        manifeste.debut_morceau(cle, nom_chunk)
        debut_ombrage = time.time()
        dalles_precharge = prefetch.recuperer(cle)
        dependances.traiter_ombrage(
            args,
            tuple(sous_zone[2:]),
            nom_chunk,
            nom_zone,
            manifeste,
            cle,
            dalles_precharge=dalles_precharge,
            on_download_done=lambda: _lancer_prefetch_suivant(cle),
            noms_dalles_a_garder=_noms_dalles_morceau_suivant(cle),
        )
        manifeste.fin_morceau(cle, int(time.time() - debut_ombrage))
        print(
            f"  [{cle}] ombrage done in "
            f"{dependances.formater_duree(int(time.time() - debut_ombrage))}"
        )

    nb_incomplet = 0

    def _etape_tuilage(sous_zone):
        nonlocal nb_incomplet
        cle = _cle(sous_zone)
        cle_tuilage = cle + "_t"
        nom_chunk = f"{nom_zone}_{cle}"
        if (
            not overwrite_actif
            and dependances.morceau_termine_reutilisable(
                manifeste,
                cle_tuilage,
                racine / nom_chunk,
                args,
            )
        ):
            return
        dependances.definir_chunk_log(f"{cle}:tuilage")
        print(
            f"\n  ── Tuilage [{cle}]  "
            f"({index_ombrage[cle] + 1}/{n_total})  {nom_chunk} ──"
        )
        print(f"     {entete_chunk(tuple(sous_zone[2:]))}")
        dependances.garde_disque(
            racine_pr,
            getattr(args, "min_free_gb", 0.0) or 0.0,
            cle_tuilage,
            0,
            n_total,
        )
        manifeste.debut_morceau(cle_tuilage, nom_chunk)
        debut_tuilage = time.time()
        resultat_chunk = dependances.traiter_tuilage(
            args,
            tuple(sous_zone[2:]),
            nom_chunk,
            nom_zone,
            manifeste,
            cle,
            sous_zone[0],
            sous_zone[1],
            n_lat,
            n_lon,
        )
        traitement_ok, mbtiles_attendus = (
            dependances.normaliser_resultat_chunk(resultat_chunk)
        )
        complet = (
            traitement_ok is not False
            and dependances.chunk_livrable_complet(
                racine / nom_chunk,
                args,
                mbtiles_attendus,
            )
        )
        avait_couverture = any(
            str(fichier).lower().endswith(".tif")
            for fichier in manifeste.fichiers_morceau(cle)
        )
        if complet or (not avait_couverture and traitement_ok is not False):
            if getattr(args, "nettoyage", False):
                dependances.supprimer_fichiers(
                    manifeste.fichiers_morceau(cle_tuilage),
                    None,
                )
            manifeste.fin_morceau(
                cle_tuilage,
                int(time.time() - debut_tuilage),
                mbtiles_attendus if complet else (),
            )
            if complet:
                print(
                    f"  [{cle}] tuilage done in "
                    f"{dependances.formater_duree(int(time.time() - debut_tuilage))}"
                )
            else:
                print(f"  [{cle}] ⊘ No LiDAR coverage - tuilage skipped")
        else:
            nb_incomplet += 1
            print(
                f"  [{cle}] ⚠ tuilage INCOMPLETE - not marked done, "
                "rerun to complete"
            )

    def _purger_rangee(index_rangee):
        if not getattr(args, "nettoyage", False):
            return
        consommateurs = range(
            max(0, index_rangee - 1),
            min(n_lat, index_rangee + 2),
        )
        if any(
            not manifeste.deja_traite(_cle(sous_zone) + "_t")
            for index_consommateur in consommateurs
            for sous_zone in rangees[index_consommateur]
        ):
            print(
                f"  Row {index_rangee + 1}: cleanup deferred, "
                "needed by unfinished tuiling"
            )
            return
        for sous_zone in rangees[index_rangee]:
            dependances.definir_chunk_log(
                f"{_cle(sous_zone)}:nettoyage"
            )
            dependances.supprimer_fichiers(
                manifeste.fichiers_morceau(_cle(sous_zone)),
                None,
            )

    try:
        for index_rangee in range(n_lat):
            for sous_zone in rangees[index_rangee]:
                _etape_ombrage(sous_zone)
            if index_rangee >= 1:
                for sous_zone in rangees[index_rangee - 1]:
                    _etape_tuilage(sous_zone)
                if index_rangee >= 2:
                    _purger_rangee(index_rangee - 2)
        for sous_zone in rangees[n_lat - 1]:
            _etape_tuilage(sous_zone)
        if n_lat >= 2:
            _purger_rangee(n_lat - 2)
        _purger_rangee(n_lat - 1)
    finally:
        prefetch.purger()

    # Le résumé et la planche concernent le run entier, pas le dernier chunk.
    dependances.definir_chunk_log(None)
    duree_totale = int(time.time() - t_debut)
    print(f"\n  ══ A-priori splitting done: {n_total} chunks ══")
    if nb_incomplet:
        print(
            f"  ⚠ {nb_incomplet} chunk(s) INCOMPLETE "
            "(not marked done) - rerun to complete them"
        )
    print(
        f"  Total time: {dependances.formater_duree(duree_totale)}"
    )
    dependances.planche_depuis_dossier(racine_pr, args, nom_zone)
    return nb_incomplet == 0


__all__ = (
    "_DependancesRunnerGlissant",
    "_run_split_priori_lidar_glissant",
    "_voisins_dossiers",
)
