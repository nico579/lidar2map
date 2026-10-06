"""Active/desactive le lancement automatique de lidar2map (mode serveur web,
--serve-gui) au demarrage de la session, selon l'OS courant. Meme mecanisme
que blink2video et watch2notif, et le meme code : nico579_commons.demarrage
(raccourci .lnk dans le dossier Demarrage sous Windows, service systemd
utilisateur sous Linux, agent launchd sous macOS). Ne reste ici que ce qui est
propre a lidar2map : la commande a lancer et son dossier.

Un lancement sans argument sert deja le GUI par defaut, donc rien de plus a
passer que --no-browser (le navigateur ne doit pas s'ouvrir tout seul a
l'ouverture de session, seulement le serveur)."""
import platform
import sys
from pathlib import Path

from nico579_commons import demarrage


def frozen() -> bool:
    """Vrai lorsque le programme tourne depuis un bundle PyInstaller."""
    return bool(getattr(sys, "frozen", False))


# __file__ pointe vers le dossier d'extraction temporaire de PyInstaller
# une fois fige, pas vers le dossier de l'executable.
PROJECT_DIR = Path(sys.executable if frozen() else __file__).resolve().parent

LINUX_SERVICE_NAME = "lidar2map.service"
MAC_LABEL = "com.nico.lidar2map"


def _lidar2map_command() -> list:
    """Commande a lancer au demarrage de session : le serveur web, sans
    ouverture automatique du navigateur (--no-browser - un navigateur qui
    s'ouvre tout seul a l'ouverture de session serait surprenant ; le
    tray/l'acces distant restent la, ouvrir la page reste un choix).

    Aucune variable d'environnement a transmettre : l'etat vit dans le
    dossier standard de l'OS (voir _dossiers.py). Fige, le programme en cours
    est celui a relancer : depuis la 1.55, l'archive le livre tel quel, sans
    lanceur qui l'extrairait ailleurs (sous Windows, c'est le meme chemin
    que celui du lanceur d'avant, l'entree de demarrage reste valable)."""
    if frozen():
        return [str(Path(sys.executable)), "--serve-gui", "--no-browser"]
    if platform.system() == "Windows":
        return [str(Path(sys.executable).with_name("pythonw.exe")),
                str(PROJECT_DIR / "lidar2map.py"), "--serve-gui", "--no-browser"]
    return [sys.executable, str(PROJECT_DIR / "lidar2map.py"),
            "--serve-gui", "--no-browser"]


def _dossier_lancement() -> Path:
    """Dossier courant du lancement automatique : celui du programme lance
    une fois fige, celui des sources sinon (pythonw.exe vit ailleurs)."""
    return Path(_lidar2map_command()[0]).parent if frozen() else PROJECT_DIR


def raccourci_bureau() -> tuple:
    """(commande, dossier) du raccourci sur le Bureau que cree le menu de
    l'icone : ceux du demarrage automatique, sans --no-browser cette fois,
    puisque c'est pour ouvrir lidar2map qu'on clique dessus."""
    commande = [a for a in _lidar2map_command() if a != "--no-browser"]
    return commande, _dossier_lancement()


def _entree() -> demarrage.Entree:
    """L'entree de demarrage de lidar2map. Le .vbs des versions <= 1.53 est
    retire avec elle (VBScript quitte Windows)."""
    return demarrage.Entree(
        "lidar2map", tuple(_lidar2map_command()), _dossier_lancement(),
        "lidar2map (GUI web local, --serve-gui)", label_macos=MAC_LABEL,
        apres_session_graphique=True, attente_relance_s=10, retire_vbs=True)


def is_enabled() -> bool:
    return demarrage.est_actif(_entree())


def enable() -> None:
    demarrage.activer(_entree())


def disable() -> None:
    demarrage.desactiver(_entree())


def migrer_ancien_demarrage() -> bool:
    """Remplace le .vbs d'une version <= 1.53 par le raccourci, sans toucher
    au choix de l'utilisateur : rien si le demarrage automatique n'etait pas
    actif. Vrai si un remplacement a eu lieu.

    Executable seulement, contrairement a watch2notif : plusieurs instances
    de lidar2map peuvent tourner a la fois, et un lancement depuis les
    sources a cote d'une installation (le cas du developpeur) repointerait
    sinon le demarrage automatique de l'installation vers python."""
    if not frozen():
        return False
    return demarrage.migrer_vbs(_entree())
