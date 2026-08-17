"""Helpers purs de journalisation partagés par lidar2map."""

from __future__ import annotations

import re
from pathlib import Path


SECRET_FLAGS = ("--api-key", "--apikey")


def rediger_secrets(texte: str) -> str:
    """Masque les valeurs des options secrètes dans une commande."""
    if not texte:
        return texte
    resultat = texte
    for flag in SECRET_FLAGS:
        motif = re.escape(flag)
        resultat = re.sub(rf"({motif}=)\S+", r"\1***", resultat)
        resultat = re.sub(rf"({motif}\s+)\S+", r"\1***", resultat)
    return resultat


def formater_duree(secondes) -> str:
    """Formate des secondes sous la forme ``Xs``, ``XmYYs`` ou ``XhYYmZZs``."""
    secondes = int(secondes)
    if secondes < 60:
        return f"{secondes}s"
    minutes, secondes = divmod(secondes, 60)
    if minutes < 60:
        return f"{minutes}m{secondes:02d}s"
    heures, minutes = divmod(minutes, 60)
    return f"{heures}h{minutes:02d}m{secondes:02d}s"


def formater_requete(url_ou_commande, label="") -> str:
    """Retourne la ligne de log d'une requête HTTP ou d'une commande."""
    if isinstance(url_ou_commande, list):
        executable = Path(url_ou_commande[0]).name if url_ou_commande else ""
        arguments = " ".join(
            str(argument)
            for argument in url_ou_commande[1:]
            if not str(argument).startswith("--config")
        )
        return f"  $ {executable} {arguments}"
    prefixe = f"{label} " if label else ""
    return f"  → {prefixe}{url_ou_commande}"
