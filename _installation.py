"""Installation de lidar2map : la désinstallation et le ménage de ce qu'un
lanceur <= 1.54 laissait sur disque.

Le module ne produit aucun effet lors de son import. Bibliothèque standard
seule : ces fonctions passent avant l'installation de tout paquet.

L'amorçage des dépendances (venv, verrou requirements.txt, modes auto, force,
pip et none) n'est plus ici : c'est _amorcage.py, copie octet pour octet de
nico579_commons.amorcage, commune aux quatre applications.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def chemins_desinstallation(*, systeme, home, localappdata=None):
    """Retourne les cibles de désinstallation sans accéder au disque."""
    home = Path(home)
    lidar2map_home = home / ".lidar2map"
    if systeme == "Windows":
        base = Path(localappdata) if localappdata else home / "AppData" / "Local"
        app_data = base / "lidar2map"
    elif systeme == "Darwin":
        app_data = home / "Library" / "Application Support" / "lidar2map"
    else:
        app_data = home / ".local" / "share" / "lidar2map"
    return (
        (app_data, "ancienne extraction du lanceur (<= 1.54)"),
        (lidar2map_home / "venv", "venv Python"),
        (lidar2map_home / "osmosis", "osmosis"),
        (lidar2map_home / "jre", "JRE Java"),
    )


def _taille_arbre_sans_suivre_liens(chemin):
    """Mesure un arbre sans parcourir les liens vers des données externes."""
    total = 0
    for racine, dossiers, fichiers in os.walk(chemin, followlinks=False):
        racine = Path(racine)
        for nom in dossiers:
            entree = racine / nom
            if not entree.is_symlink():
                continue
            try:
                total += entree.lstat().st_size
            except OSError:
                pass
        for nom in fichiers:
            try:
                total += (racine / nom).lstat().st_size
            except OSError:
                pass
    return total


def desinstaller_lidar2map(
    *,
    systeme,
    home,
    localappdata=None,
    executable=None,
    supprimer_arbre=shutil.rmtree,
    ecrire=print,
):
    """Supprime les seules cibles planifiées et retourne ``True`` si complet.

    ``executable`` est le programme figé en cours. Depuis la 1.55, il peut
    être installé n'importe où, y compris dans le dossier où le lanceur d'une
    version <= 1.54 extrayait le sien : une cible qui le contient est gardée,
    sa suppression détruirait le programme lui-même."""
    cibles = chemins_desinstallation(
        systeme=systeme,
        home=home,
        localappdata=localappdata,
    )
    programme = Path(executable).resolve() if executable else None
    total = 0
    complet = True
    ecrire("")
    ecrire("  ── lidar2map uninstall ──────────────────────────────────")
    ecrire("")
    for chemin, label in cibles:
        if not chemin.exists() and not chemin.is_symlink():
            ecrire(f"  {label} : absent ({chemin})")
            continue
        if programme is not None and chemin.resolve() in programme.parents:
            ecrire(f"  {label} : kept, the running program lives there ({chemin})")
            continue
        taille = (
            chemin.lstat().st_size
            if chemin.is_symlink()
            else _taille_arbre_sans_suivre_liens(chemin)
        )
        total += taille
        ecrire(f"  Removing {label} ({taille / 1e6:.0f} MB)")
        ecrire(f"    {chemin}")
        try:
            if chemin.is_symlink():
                chemin.unlink()
            else:
                supprimer_arbre(chemin)
        except OSError as exc:
            complet = False
            ecrire(f"    ⚠ partial ({exc})")
            continue
        if chemin.exists() or chemin.is_symlink():
            complet = False
            ecrire("    ⚠ partial")
        else:
            ecrire("    ✓ removed")
    ecrire("")
    ecrire(f"  {total / 1e6:.0f} MB freed.")
    ecrire("")
    ecrire("  Note: lidar2map.py and the program folder (.app/.exe) are not removed.")
    ecrire("  Remove them manually if needed.")
    ecrire("")
    return complet


def nettoyer_ancienne_extraction(*, systeme, home, localappdata=None, executable):
    """Retire ce qu'un lanceur d'une version <= 1.54 a laissé, et rend la
    liste de ce qui a été retiré.

    Deux restes : le programme qu'il extrayait dans le dossier de données de
    l'OS (même chemin que chemins_desinstallation), et son bundle zippé resté
    à côté du programme quand la nouvelle archive a été décompressée
    par-dessus l'ancienne. Le dossier n'est retiré que s'il porte la marque
    du lanceur (.bundle_sha) et que le programme ne tourne pas depuis lui. Il
    est d'abord renommé : sous Windows, le renommage échoue tant qu'une
    ancienne instance y tourne encore, et le nettoyage attend alors le
    lancement suivant."""
    retires = []
    programme = Path(executable).resolve()
    zip_voisin = programme.parent / "lidar2map_bundle.zip"
    if zip_voisin.is_file():
        try:
            zip_voisin.unlink()
            retires.append(zip_voisin)
        except OSError:
            pass

    dossier = chemins_desinstallation(
        systeme=systeme, home=home, localappdata=localappdata)[0][0]
    corbeille = dossier.with_name(dossier.name + ".ancienne-extraction")
    if corbeille.exists():   # reste d'un nettoyage interrompu
        shutil.rmtree(corbeille, ignore_errors=True)
    if not (dossier / ".bundle_sha").is_file():
        return retires
    if dossier.resolve() in programme.parents:
        return retires
    try:
        os.rename(dossier, corbeille)
    except OSError:
        return retires
    shutil.rmtree(corbeille, ignore_errors=True)
    retires.append(dossier)
    return retires
