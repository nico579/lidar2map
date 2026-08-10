"""Runner classique des traitements découpés.

Le runner orchestre des callbacks LiDAR ou WMTS sans importer le monolithe.
Ses dépendances d'intégration sont fournies à chaque appel par la façade
``lidar2map``, ce qui évite les imports circulaires et conserve les coutures de
test historiques.
"""

from __future__ import annotations

import gc
import time
from dataclasses import dataclass
from typing import Callable

from _split_planning import _cle_chunk, _identite_chunk


@dataclass(frozen=True)
class _DependancesRunnerClassique:
    """Coutures entre l'orchestrateur générique et l'application."""

    fabrique_manifeste: Callable
    signature_config: Callable
    morceau_termine_reutilisable: Callable
    garde_disque: Callable
    definir_chunk_log: Callable
    normaliser_resultat_chunk: Callable
    chunk_livrable_complet: Callable
    dossier_dalles_actif: Callable
    supprimer_fichiers: Callable
    formater_duree: Callable
    zone_hors_couverture: type
    planche_depuis_dossier: Callable


def _run_split_priori(
    args,
    sous_zones,
    mode_desc,
    nom_zone,
    racine_pr,
    overwrite_actif,
    entete_chunk,
    traiter_chunk,
    t_debut,
    vide_sans_couverture_ok=True,
    *,
    dependances,
):
    """Exécute séquentiellement les chunks avec reprise transactionnelle.

    ``entete_chunk`` formate la bbox propre au pipeline. ``traiter_chunk``
    produit un résultat normalisable et, si possible, les chemins canoniques
    des cartes attendues. Toute exception autre qu'une absence explicite de
    couverture remonte immédiatement afin que le prochain run reprenne le
    morceau non terminé.
    """
    # Un batch multi-département peut rappeler le runner dans le même process.
    # Son en-tête global ne doit pas hériter du chunk qui vient d'échouer.
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
    nb_done = sum(
        1
        for zone in sous_zones
        if manifeste.deja_traite(_cle_chunk(zone[0], zone[1]))
    )
    print(f"\n  ══ A-priori splitting: {mode_desc} ══")
    print(f"  Manifeste : {manifeste.path}")
    if nb_done:
        print(f"  Resume: {nb_done}/{n_total} chunks already done")

    nb_ok = 0
    nb_incomplet = 0
    for index_zone, sous_zone in enumerate(sous_zones):
        # Les datasets GDAL/rasterio peuvent participer à des cycles. Une
        # collecte en frontière de chunk évite leur accumulation sur un run
        # départemental long.
        gc.collect()
        index_ligne, index_colonne = sous_zone[0], sous_zone[1]
        coords = tuple(sous_zone[2:])
        cle, nom_chunk = _identite_chunk(
            nom_zone,
            index_ligne,
            index_colonne,
        )
        # Poser le contexte avant tout message du chunk (reprise, garde disque
        # et en-tête compris), sinon le fichier log les attribue au précédent.
        dependances.definir_chunk_log(cle)

        if (
            not overwrite_actif
            and dependances.morceau_termine_reutilisable(
                manifeste,
                cle,
                racine_pr / nom_chunk,
                args,
            )
        ):
            print(f"  [{cle}] {nom_chunk}: already done")
            nb_ok += 1
            continue

        dependances.garde_disque(
            racine_pr,
            getattr(args, "min_free_gb", 0.0) or 0.0,
            cle,
            nb_ok,
            n_total,
        )

        print(
            f"\n  ── Chunk {cle}  "
            f"({index_zone + 1}/{n_total})  {nom_chunk} ──"
        )
        print(f"     {entete_chunk(coords)}")
        manifeste.debut_morceau(cle, nom_chunk)
        debut_chunk = time.time()
        try:
            resultat = traiter_chunk(
                coords,
                nom_chunk,
                cle,
                manifeste,
            )
            traitement_ok, mbtiles_attendus = (
                dependances.normaliser_resultat_chunk(resultat)
            )
            dossier_chunk = racine_pr / nom_chunk
            complet = (
                traitement_ok is not False
                and dependances.chunk_livrable_complet(
                    dossier_chunk,
                    args,
                    mbtiles_attendus,
                )
            )
            echec_explicite = traitement_ok is False
            avait_couverture = any(
                str(path).lower().endswith(".tif")
                for path in manifeste.fichiers_morceau(cle)
            )
            if not complet and (
                echec_explicite
                or avait_couverture
                or not vide_sans_couverture_ok
            ):
                raison = (
                    "coverage present but no valid deliverable"
                    if avait_couverture
                    else "processing returned no valid deliverable"
                )
                print(
                    f"  [{cle}] ⚠ INCOMPLETE ({raison})"
                    " - NOT marked done, rerun to complete "
                    "(intermediates kept)"
                )
                nb_incomplet += 1
                continue

            if getattr(args, "nettoyage", False) and complet:
                if getattr(args, "nettoyage_garder_dalles", False):
                    fichiers_gardes = [
                        dependances.dossier_dalles_actif(args)
                    ]
                    cache_nuages = getattr(args, "_cloud_cache_dir", None)
                    if cache_nuages is not None:
                        fichiers_gardes.append(cache_nuages)
                else:
                    fichiers_gardes = None
                dependances.supprimer_fichiers(
                    manifeste.fichiers_morceau(cle),
                    fichiers_gardes,
                )

            manifeste.fin_morceau(
                cle,
                int(time.time() - debut_chunk),
                mbtiles_attendus if complet else (),
            )
            duree = int(time.time() - debut_chunk)
            print(
                f"  [{cle}] ✓ Done in "
                f"{dependances.formater_duree(duree)}"
            )
            nombre_termine, eta = manifeste.eta_global(n_total)
            if eta:
                print(
                    f"  [{cle}] {nombre_termine}/{n_total} done, "
                    f"ETA ~{dependances.formater_duree(eta)} "
                    "remaining (coarse)"
                )
            nb_ok += 1
        except dependances.zone_hors_couverture:
            manifeste.fin_morceau(
                cle,
                int(time.time() - debut_chunk),
                (),
            )
            print(
                f"  [{cle}] ⊘ No coverage "
                "(sea / outside layer) - chunk skipped"
            )
            nb_ok += 1
            continue
        except Exception as erreur:
            print(f"  [{cle}] ✗ ERROR: {erreur} - relaunch to resume")
            raise

    # Le bilan et la planche sont globaux : ne pas les préfixer avec le dernier
    # chunk traité.
    dependances.definir_chunk_log(None)
    duree_totale = int(time.time() - t_debut)
    print(f"\n  ══ A-priori splitting done: {nb_ok}/{n_total} chunks ==")
    if nb_incomplet:
        print(
            f"  ⚠ {nb_incomplet} chunk(s) INCOMPLETE "
            "(not marked done) - rerun to complete them"
        )
    print(f"  Total time: {dependances.formater_duree(duree_totale)}")

    dependances.planche_depuis_dossier(racine_pr, args, nom_zone)
    return nb_incomplet == 0


__all__ = ("_DependancesRunnerClassique", "_run_split_priori")
