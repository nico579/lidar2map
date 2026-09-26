"""Calcul pur des chemins d'exécution et des indicateurs de plateforme."""

from __future__ import annotations

from pathlib import Path


def dossier_programme(*, frozen, environnement, executable, script_path):
    """Dossier du programme une fois figé (celui qui contient le .app sous
    macOS), celui des sources sinon. Jusqu'à la 1.53, lidar2map y rangeait
    tout, état et sorties (voir _dossiers.py). Jusqu'à la 1.54, le lanceur le
    transmettait par LIDAR2MAP_WORK_DIR ; depuis la 1.55, le programme est
    livré tel quel et le trouve lui-même. ``environnement`` reste accepté
    pour les appelants, mais ne sert plus."""
    if frozen:
        chemin = Path(executable).resolve()
        dossier = chemin.parent
        if (dossier.name == "MacOS" and dossier.parent.name == "Contents"
                and dossier.parent.parent.suffix == ".app"):
            return dossier.parent.parent.parent
        return dossier
    return Path(script_path).resolve().parent


def calculer_chemins(*, frozen, environnement, executable, script_path,
                     meipass=None, home, dossier_travail=None):
    """Retourne travail, bundle, outils lidar2map, cache et production.

    ``dossier_travail`` est la racine des sorties ; à défaut, celle d'avant
    la 1.54, le dossier du programme."""
    executable_dir = Path(executable).resolve().parent
    if frozen:
        bundle_dir = Path(meipass or executable_dir)
    else:
        bundle_dir = Path(script_path).resolve().parent
    if dossier_travail is None:
        dossier_travail = dossier_programme(
            frozen=frozen, environnement=environnement,
            executable=executable, script_path=script_path)
    dossier_travail = Path(dossier_travail)

    lidar2map_home = Path(home) / ".lidar2map"
    return (
        dossier_travail,
        bundle_dir,
        lidar2map_home,
        dossier_travail / "cache",
        dossier_travail / "production",
    )


def indicateurs_plateforme(systeme):
    """Retourne les indicateurs Windows, Linux et macOS pour *systeme*."""
    return systeme == "Windows", systeme == "Linux", systeme == "Darwin"
