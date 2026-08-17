"""Sonde et garde-fou d'espace disque, indépendants du pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path


def espace_libre_go(chemin, *, disk_usage=None):
    """Espace libre (Go) sur le volume de ``chemin``.

    La sonde remonte au premier parent existant. Une erreur retourne l'infini :
    ce garde-fou défensif ne doit pas devenir un point de défaillance du run.
    """
    disk_usage = disk_usage or shutil.disk_usage
    path = Path(chemin)
    while not path.exists() and path != path.parent:
        path = path.parent
    try:
        return disk_usage(path).free / (1024 ** 3)
    except OSError:
        return float("inf")


def garder_disque(chemin, seuil_go, cle, nb_ok, n_total, *, sonde,
                  exit_code, ecrire, quitter):
    """Arrête proprement avant un chunk lorsque le seuil n'est plus respecté.

    Le contrôle précède le démarrage du morceau : aucun état de manifeste ni
    fichier n'est engagé et une relance peut reprendre normalement. Un seuil
    inférieur ou égal à zéro désactive entièrement la sonde.
    """
    if seuil_go <= 0:
        return
    libre = sonde(chemin)
    if libre < seuil_go:
        ecrire(
            f"\n  ⚠ Disk space low: {libre:.1f} GB free < "
            f"{seuil_go:.0f} GB threshold."
        )
        ecrire(
            f"  Stopping cleanly before chunk {cle}: {nb_ok}/{n_total} "
            "chunks done. Free space and relaunch to resume."
        )
        quitter(exit_code)
