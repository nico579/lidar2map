"""Calcul pur des chemins d'exécution et des indicateurs de plateforme."""

from __future__ import annotations

from pathlib import Path


def calculer_chemins(*, frozen, environnement, executable, script_path,
                     meipass=None, home):
    """Retourne travail, bundle, home lidar2map, cache et production."""
    executable_dir = Path(executable).resolve().parent
    if frozen:
        dossier_travail = Path(
            environnement.get("LIDAR2MAP_WORK_DIR") or executable_dir
        )
        bundle_dir = Path(meipass or executable_dir)
    else:
        dossier_travail = Path(script_path).resolve().parent
        bundle_dir = dossier_travail

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
