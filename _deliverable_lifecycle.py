"""Politiques de cycle de vie des livrables et intermédiaires.

Ce module ne connaît ni les arguments CLI ni les runners. Les accès au système
de fichiers, à SQLite et à la validation d'un morceau sont injectés afin que
``lidar2map.py`` reste la façade de compatibilité pendant la refonte.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Tuple


@dataclass(frozen=True)
class DependancesNettoyage:
    path_factory: Callable = Path
    ecrire: Callable = print


@dataclass(frozen=True)
class DependancesRepriseMorceau:
    chunk_livrable_complet: Callable
    ecrire: Callable = print


@dataclass(frozen=True)
class DependancesFraicheurMbtiles:
    path_factory: Callable = Path
    sqlite_connect: Callable = sqlite3.connect
    sqlite_errors: Tuple[type, ...] = (
        sqlite3.DatabaseError,
        sqlite3.OperationalError,
    )
    ecrire: Callable = print


def supprimer_fichiers(
    fichiers: list,
    dossiers_garder=None,
    noms_garder=None,
    *,
    dependances: DependancesNettoyage,
):
    """Supprime les intermédiaires d'un morceau en respectant ses caches."""
    path_factory = dependances.path_factory
    ecrire = dependances.ecrire
    suppr = 0
    gardees = 0
    dirs_a_verifier = set()
    noms_a_garder = noms_garder or ()
    if dossiers_garder is None:
        caches = []
    elif isinstance(dossiers_garder, (str, Path)):
        caches = [path_factory(dossiers_garder).resolve()]
    else:
        caches = [
            path_factory(dossier).resolve()
            for dossier in dossiers_garder
            if dossier is not None
        ]
    for chemin in fichiers:
        path = path_factory(chemin)
        if path.name in noms_a_garder:
            gardees += 1
            continue
        if caches:
            epargne = False
            for cache in caches:
                try:
                    path.resolve().relative_to(cache)
                    epargne = True
                    break
                except (ValueError, OSError):
                    continue
            if epargne:
                gardees += 1
                continue
        if path.exists():
            try:
                path.unlink()
                dirs_a_verifier.add(path.parent)
                suppr += 1
            except Exception:
                pass
    for dossier in sorted(
        dirs_a_verifier, key=lambda item: len(item.parts), reverse=True
    ):
        try:
            if dossier.exists() and not any(dossier.iterdir()):
                dossier.rmdir()
        except Exception:
            pass
    if suppr or gardees:
        suffixe = f", {gardees} cached tile(s) kept" if gardees else ""
        ecrire(f"  Cleanup: {suppr} intermediate file(s) removed{suffixe}")


def morceau_termine_reutilisable(
    manifeste,
    cle,
    dossier_chunk,
    args,
    *,
    dependances: DependancesRepriseMorceau,
):
    """Valide la preuve persistée avant de croire ``termine=True``."""
    if not manifeste.deja_traite(cle):
        return False
    attendus = manifeste.mbtiles_attendus_morceau(cle)
    if attendus == ():
        return True
    if (
        attendus is not None
        and dependances.chunk_livrable_complet(dossier_chunk, args, attendus)
    ):
        return True
    raison = (
        "legacy manifest without output proof"
        if attendus is None
        else "expected deliverable missing or invalid"
    )
    dependances.ecrire(f"  [{cle}] {raison} - replaying chunk")
    manifeste.invalider_morceau(cle)
    return False


def mbtiles_a_regenerer(
    mbt_path,
    ecraser,
    source=None,
    *,
    dependances: DependancesFraicheurMbtiles,
):
    """Détermine si un magasin MBTiles doit être produit de nouveau."""
    if not mbt_path.exists() or ecraser:
        return True
    if source is not None:
        try:
            source_path = dependances.path_factory(source)
            if source_path.stat().st_mtime > mbt_path.stat().st_mtime:
                dependances.ecrire(
                    f"  {mbt_path.name} → older than {source_path.name}, "
                    "regenerating",
                    flush=True,
                )
                return True
        except OSError:
            pass
    try:
        connection = dependances.sqlite_connect(
            f"file:{mbt_path}?mode=ro", uri=True
        )
        try:
            tile_count = connection.execute(
                "SELECT COUNT(*) FROM tiles"
            ).fetchone()[0]
        finally:
            connection.close()
    except dependances.sqlite_errors as error:
        dependances.ecrire(
            f"  {mbt_path.name} → SQLite unreadable "
            f"({type(error).__name__}), regenerating",
            flush=True,
        )
        return True
    if tile_count == 0:
        dependances.ecrire(
            f"  {mbt_path.name} → exists but empty (0 tiles), regenerating",
            flush=True,
        )
        return True
    return False
