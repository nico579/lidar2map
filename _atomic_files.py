"""Primitives de staging atomique et de validation SQLite."""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

# Sous Windows, remplacer ou lire un fichier qu'un autre fil ou processus tient
# ouvert échoue en PermissionError le temps de cet accès : quelques nouvelles
# tentatives rapprochées l'absorbent (pip fait de même autour d'os.replace).
_TENTATIVES_REFUS = 10
_PAUSE_REFUS_S = 0.05


def lire_json(path, defaut):
    """Contenu JSON de ``path``, ou ``defaut`` s'il est absent ou corrompu.

    Un fichier PRÉSENT mais illisible (refus Windows qui persiste, erreur
    disque) lève l'OSError au lieu de rendre ``defaut`` : un appelant qui
    réécrit ensuite (lecture-modification-écriture) effacerait sinon tout le
    contenu sur un simple refus d'accès passager."""
    path = Path(path)
    for tentative in range(_TENTATIVES_REFUS):
        try:
            # utf-8-sig : accepte aussi le BOM qu'ajoutent le Bloc-notes
            # (Windows 10 avant 1903) et Out-File -Encoding utf8 (PowerShell
            # 5.1). En utf-8, json.loads le rejetait, le fichier passait pour
            # corrompu et la réécriture suivante n'en gardait qu'une clé.
            texte = path.read_text(encoding="utf-8-sig")
            break
        except FileNotFoundError:
            return defaut
        except PermissionError:
            if tentative == _TENTATIVES_REFUS - 1:
                raise
            time.sleep(_PAUSE_REFUS_S)
    try:
        return json.loads(texte)
    except ValueError:
        return defaut   # contenu corrompu : repartir de zéro, comme avant


def remplacer(source, cible):
    """``os.replace`` qui retente un refus Windows passager (lecteur en cours)."""
    for tentative in range(_TENTATIVES_REFUS):
        try:
            os.replace(source, cible)
            return
        except PermissionError:
            if tentative == _TENTATIVES_REFUS - 1:
                raise
            time.sleep(_PAUSE_REFUS_S)


if os.name == "nt":
    import msvcrt

    def _verrouiller(fd):
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

    def _deverrouiller(fd):
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _verrouiller(fd):
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _deverrouiller(fd):
        fcntl.flock(fd, fcntl.LOCK_UN)


@contextlib.contextmanager
def verrou_inter_processus(path, delai_s=30.0):
    """Verrou exclusif sur ``path`` (fichier ``.lock`` voisin), entre fils ET
    entre processus : msvcrt.locking sous Windows, fcntl.flock ailleurs (le
    mécanisme du paquet filelock, sans dépendance). Chaque prise ouvre son
    propre descripteur, donc deux fils d'un même processus s'excluent aussi.
    L'OS relâche le verrou à la mort du processus : jamais d'orphelin à
    nettoyer, contrairement à un fichier créé en O_EXCL. TimeoutError au-delà
    de ``delai_s``."""
    verrou = Path(str(path) + ".lock")
    verrou.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(verrou, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fin = time.monotonic() + delai_s
        while True:
            try:
                _verrouiller(fd)
                break
            except OSError:
                if time.monotonic() >= fin:
                    raise TimeoutError(f"verrou occupé : {verrou}") from None
                time.sleep(_PAUSE_REFUS_S)
        try:
            yield
        finally:
            _deverrouiller(fd)
    finally:
        os.close(fd)


SQLITE_SUFFIXES = ("", "-wal", "-shm", "-journal")


def chemin_part(path):
    """Retourne un chemin staging unique et nettoie uniquement ses sidecars."""
    path = Path(path)
    token = uuid.uuid4().hex[:12]
    part = path.parent / f"{path.name}.{os.getpid()}.{token}.part"
    for suffixe in SQLITE_SUFFIXES:
        Path(str(part) + suffixe).unlink(missing_ok=True)
    return part


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


def publier_groupe_atomique(paires, creer_sauvegarde=chemin_part):
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
