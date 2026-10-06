"""Primitives SQLite propres à lidar2map : nettoyage d'un staging, validation
d'une base avant publication, promotion d'un groupe de fichiers.

L'écriture atomique, la lecture JSON tolérante et le verrou entre processus
(remplacer, lire_json, verrou_inter_processus, chemin_part, ecrire_json) sont
dans nico579_commons.atomique, les mêmes pour les quatre applications.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from nico579_commons import atomique

SQLITE_SUFFIXES = atomique.SUFFIXES_ANNEXES


def nettoyer_sqlite_part(path):
    """Supprime un staging SQLite et ses sidecars, sans toucher au final."""
    path = Path(path)
    for suffixe in SQLITE_SUFFIXES:
        try:
            Path(str(path) + suffixe).unlink(missing_ok=True)
        except OSError:
            pass


def valider_sqlite_part(path, tables_attendues):
    """Valide une base staging fermée avant sa publication finale."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size <= 0:
        raise OSError(f"staging SQLite absent ou vide : {path}")
    for suffixe in SQLITE_SUFFIXES[1:]:
        if Path(str(path) + suffixe).exists():
            raise OSError(
                f"sidecar SQLite encore présent avant publication : "
                f"{path.name}{suffixe}"
            )
    connexion = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        curseur = connexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
        )
        try:
            presentes = {ligne[0] for ligne in curseur}
        finally:
            curseur.close()
        manquantes = set(tables_attendues) - presentes
        if manquantes:
            raise OSError(
                "table(s) SQLite manquante(s) : " + ", ".join(sorted(manquantes))
            )
        for table, attendu in tables_attendues.items():
            curseur = connexion.execute(f'SELECT COUNT(*) FROM "{table}"')
            try:
                obtenu = curseur.fetchone()[0]
            finally:
                curseur.close()
            if attendu is not None and obtenu != attendu:
                raise OSError(
                    f"SQLite {table}: {obtenu} ligne(s), {attendu} attendue(s)"
                )
    finally:
        connexion.close()


def publier_groupe_atomique(paires, creer_sauvegarde=atomique.chemin_part):
    """Promeut plusieurs stagings ou restaure l'ensemble des anciens finals.

    ``paires`` contient des couples ``(staging, final)``. Les anciens finals
    sont d'abord déplacés vers des sauvegardes voisines uniques ; ils ne sont
    supprimés qu'une fois toutes les promotions réussies.
    """
    paires = [(Path(stage), Path(final)) for stage, final in paires]
    sauvegardes = []
    publies = []
    try:
        for _stage, final in paires:
            if final.exists():
                sauvegarde = Path(creer_sauvegarde(final))
                final.replace(sauvegarde)
                sauvegardes.append((sauvegarde, final))
        for stage, final in paires:
            stage.replace(final)
            publies.append(final)
    except BaseException:
        for final in reversed(publies):
            final.unlink(missing_ok=True)
        for sauvegarde, final in reversed(sauvegardes):
            if sauvegarde.exists():
                sauvegarde.replace(final)
        raise
    finally:
        for sauvegarde, _final in sauvegardes:
            sauvegarde.unlink(missing_ok=True)
