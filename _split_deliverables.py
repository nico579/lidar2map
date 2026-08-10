"""Résultats de chunks et validation des livrables des traitements découpés.

Le module ne connaît ni le manifeste ni les runners. Il transforme leur
résultat et vérifie les fichiers publiés, ce qui maintient la décision de
reprise indépendante de l'orchestration.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _mbtiles_est_complete(mbtiles_path):
    """Retourne True pour un MBTiles SQLite lisible contenant des tuiles."""
    mbtiles_path = Path(mbtiles_path)
    if not mbtiles_path.exists():
        return False
    try:
        connection = sqlite3.connect(
            f"file:{mbtiles_path}?mode=ro",
            uri=True,
        )
        try:
            return connection.execute(
                "SELECT COUNT(*) FROM tiles"
            ).fetchone()[0] > 0
        finally:
            # Le context manager sqlite3 ne ferme pas la connexion. Sous
            # Windows, le handle empêcherait le rejeu de remplacer le fichier.
            connection.close()
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return False


class _ResultatChunk:
    """Résultat interne d'un chunk et chemins canoniques de ses cartes."""

    __slots__ = ("ok", "mbtiles_attendus")

    def __init__(self, ok, mbtiles_attendus=()):
        self.ok = ok
        self.mbtiles_attendus = tuple(Path(path) for path in mbtiles_attendus)


def _normaliser_resultat_chunk(resultat):
    """Normalise un résultat structuré ou un ancien callback booléen."""
    if isinstance(resultat, _ResultatChunk):
        return resultat.ok, resultat.mbtiles_attendus
    return resultat, None


def _chunk_livrable_complet(
    dossier_chunk,
    args,
    mbtiles_attendus=None,
    *,
    verifier_mbtiles=None,
):
    """Vérifie que tous les formats demandés appartiennent au même produit.

    Lorsque les chemins canoniques du run sont connus, seuls ces produits sont
    contrôlés et les anciens fichiers du dossier sont ignorés. Le repli par
    scan du dossier reste réservé aux anciens appels sans preuve persistée.

    ``verifier_mbtiles`` est injectable afin que la façade historique de
    ``lidar2map`` conserve sa couture de test et de diagnostic.
    """
    dossier_chunk = Path(dossier_chunk)
    if verifier_mbtiles is None:
        verifier_mbtiles = _mbtiles_est_complete

    veut_mbtiles = getattr(args, "mbtiles", False)
    veut_rmap = getattr(args, "rmap", False)
    veut_sqlitedb = getattr(args, "sqlitedb", False)
    format_explicite = veut_mbtiles or veut_rmap or veut_sqlitedb

    if mbtiles_attendus is not None:
        attendus = tuple(
            dict.fromkeys(Path(path) for path in mbtiles_attendus)
        )
        if not attendus:
            return False
        for mbtiles_path in attendus:
            if (
                (veut_mbtiles or not format_explicite)
                and not verifier_mbtiles(mbtiles_path)
            ):
                return False
            if veut_rmap and not mbtiles_path.with_suffix(".rmap").is_file():
                return False
            if (
                veut_sqlitedb
                and not mbtiles_path.with_suffix(".sqlitedb").is_file()
            ):
                return False
        return True

    candidats = None
    if veut_mbtiles or not format_explicite:
        candidats = {
            path.stem
            for path in dossier_chunk.glob("*.mbtiles")
            if verifier_mbtiles(path)
        }
    if veut_rmap:
        stems_rmap = {path.stem for path in dossier_chunk.glob("*.rmap")}
        candidats = (
            stems_rmap if candidats is None else candidats & stems_rmap
        )
    if veut_sqlitedb:
        stems_sqlitedb = {
            path.stem for path in dossier_chunk.glob("*.sqlitedb")
        }
        candidats = (
            stems_sqlitedb
            if candidats is None
            else candidats & stems_sqlitedb
        )
    return bool(candidats)


__all__ = (
    "_ResultatChunk",
    "_chunk_livrable_complet",
    "_mbtiles_est_complete",
    "_normaliser_resultat_chunk",
)
