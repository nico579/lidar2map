"""Utilitaires partagés entre providers.

Point de mutualisation (cf. audit providers 2026-07). Pour l'instant :
extraction ZIP sûre (anti zip-slip #10). Vocation à accueillir aussi le HTTP /
pagination / retry / conversion PDAL communs (architecture cible).
"""
from pathlib import Path


def _membre_sous(nom, cible_resolue):
    """True si le membre d'archive `nom` reste sous `cible_resolue` (déjà
    resolue). Refuse les chemins absolus (/ \\ ou lettre de lecteur) et les
    traversées `..` qui sortiraient du dossier cible."""
    if nom.startswith(("/", "\\")) or (len(nom) > 1 and nom[1] == ":"):
        return False
    dest = (cible_resolue / nom).resolve()
    return dest == cible_resolue or cible_resolue in dest.parents


def extraire_membre(zf, member, dest_dir):
    """Extrait le membre `member` d'un ZipFile OUVERT `zf` sous `dest_dir`, en
    refusant les chemins absolus et les traversées `..` (zip-slip).

    Le cœur valide déjà ses extractions (`_safe_zip_extractall`) ; les
    providers doivent passer par ici plutôt qu'un `zf.extract()` nu, où le nom
    de membre venu d'une archive distante pourrait s'échapper du cache.
    Retourne le Path du fichier extrait. Lève ValueError sur membre suspect."""
    dest_dir = Path(dest_dir).resolve()
    if not _membre_sous(member, dest_dir):
        raise ValueError(f"Chemin de membre ZIP suspect (zip-slip) : {member!r}")
    zf.extract(member, dest_dir)
    return dest_dir / member
