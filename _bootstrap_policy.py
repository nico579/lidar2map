"""Politiques pures du bootstrap precoce de lidar2map.

Ce module ne realise aucun import applicatif, acces reseau ou mutation du
processus. Il peut donc etre charge avant l'installation des dependances.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


_MODES_BOOTSTRAP = ("auto", "pip", "none")


@dataclass(frozen=True)
class ResolutionModeBootstrap:
    """Résultat pur de l'analyse des options précoces de bootstrap."""

    mode: str
    argv: tuple[str, ...]
    aide: bool = False


def resoudre_mode_bootstrap(
    argv: Sequence[str],
    environnement: Mapping[str, str],
) -> ResolutionModeBootstrap:
    """Résout le mode et retourne une copie nettoyée de ``argv``.

    La fonction ne modifie ni la séquence ni l'environnement reçus. L'aide a
    priorité sur les erreurs afin de conserver le comportement historique de
    ``--help-bootstrap``. Une valeur CLI invalide est en revanche rejetée : le
    résultat reste ainsi atomique et une option suivante ne peut plus être
    avalée comme valeur de ``--bootstrap``.
    """
    args = list(argv)
    mode = "auto"

    if "--help-bootstrap" in args:
        return ResolutionModeBootstrap(mode, tuple(args), aide=True)

    env_mode = environnement.get("LIDAR2MAP_BOOTSTRAP", "").lower().strip()
    if env_mode in _MODES_BOOTSTRAP:
        mode = env_mode

    indices_a_retirer = []
    for index, argument in enumerate(args):
        valeur = None
        if argument.startswith("--bootstrap="):
            valeur = argument.split("=", 1)[1].lower().strip()
            indices_a_retirer.append(index)
        elif argument == "--bootstrap":
            if index + 1 >= len(args) or args[index + 1].startswith("-"):
                raise ValueError(
                    "--bootstrap requiert une valeur parmi auto, pip et none"
                )
            valeur = args[index + 1].lower().strip()
            indices_a_retirer.extend((index, index + 1))
        if valeur is not None:
            if valeur not in _MODES_BOOTSTRAP:
                raise ValueError(
                    f"valeur invalide pour --bootstrap : {valeur!r} "
                    "(attendu : auto, pip ou none)"
                )
            mode = valeur

    # Les alias gardent leur priorité historique fixe, indépendamment de leur
    # position dans argv. En particulier --no-venv gagne sur les deux autres.
    if "--no-bootstrap" in args:
        mode = "none"
    if "--venv" in args:
        mode = "auto"
    if "--no-venv" in args:
        mode = "pip"

    for index in sorted(set(indices_a_retirer), reverse=True):
        del args[index]
    for flag in ("--no-bootstrap", "--venv", "--no-venv", "--help-bootstrap"):
        while flag in args:
            args.remove(flag)

    return ResolutionModeBootstrap(mode, tuple(args))


def dependances_gui_plateforme(systeme: str) -> tuple[list[str], list[str]]:
    """Retourne ``(critiques, optionnelles)`` pour le systeme indique.

    pywebview a besoin d'un backend graphique adapte a la plateforme :

    - Windows utilise Qt pour eviter les regressions du bridge
      pythonnet/WebView2 ;
    - macOS installe Cocoa/WebKit et Qt afin de couvrir aussi les machines
      sans affichage local ;
    - Linux et les plateformes inconnues utilisent Qt, seul backend disponible
      de facon fiable par pip.

    Les deux listes distinguent les dependances critiques des optionnelles.
    La politique actuelle rend tous les backends retenus critiques et ne
    retourne donc aucune dependance optionnelle.

    De nouvelles listes sont creees a chaque appel pour que l'appelant puisse
    les completer sans modifier une politique globale partagee.
    """
    if systeme == "Darwin":
        return (
            [
                "pyobjc-framework-WebKit",
                "pyobjc-framework-Cocoa",
                "PyQt6",
                "PyQt6-WebEngine",
                "qtpy",
            ],
            [],
        )
    return (["PyQt6", "PyQt6-WebEngine", "qtpy"], [])
