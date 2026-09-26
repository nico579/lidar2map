"""Active/desactive le lancement automatique de lidar2map (mode serveur web,
--serve-gui) au demarrage de la session, selon l'OS courant. Meme mecanisme
que blink2video et watch2notif : raccourci .lnk dans le dossier Demarrage
sous Windows, service systemd utilisateur sous Linux, agent launchd sous
macOS. Un lancement sans argument sert deja le GUI par defaut, donc rien de
plus a passer que --no-browser (le navigateur ne doit pas s'ouvrir tout seul
a l'ouverture de session, seulement le serveur)."""
import os
import platform
import subprocess
import sys
from pathlib import Path


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


def _systemd_quote(valeur: str) -> str:
    """Argument ExecStart= entre guillemets (espaces dans un chemin) ; % est
    un specificateur systemd, a doubler."""
    echappe = valeur.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return f'"{echappe}"'


def _xml_escape(valeur: str) -> str:
    return (valeur.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _windows_startup_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _windows_startup_file() -> Path:
    return _windows_startup_dir() / "lidar2map.lnk"


def _windows_legacy_file() -> Path:
    """Script .vbs des versions <= 1.53, remplace par le raccourci."""
    return _windows_startup_dir() / "lidar2map.vbs"


def _linux_service_file() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / LINUX_SERVICE_NAME


def _mac_plist_file() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{MAC_LABEL}.plist"


def is_enabled() -> bool:
    system = platform.system()
    if system == "Windows":
        return _windows_startup_file().exists() or _windows_legacy_file().exists()
    if system == "Linux":
        return _linux_service_file().exists()
    if system == "Darwin":
        return _mac_plist_file().exists()
    return False


def enable() -> None:
    system = platform.system()
    if system == "Windows":
        _enable_windows()
    elif system == "Linux":
        _enable_linux()
    elif system == "Darwin":
        _enable_mac()
    else:
        raise RuntimeError(f"OS non supporte pour l'autostart: {system}")


def disable() -> None:
    system = platform.system()
    if system == "Windows":
        _disable_windows()
    elif system == "Linux":
        _disable_linux()
    elif system == "Darwin":
        _disable_mac()
    else:
        raise RuntimeError(f"OS non supporte pour l'autostart: {system}")


def migrer_ancien_demarrage() -> bool:
    """Remplace le .vbs d'une version <= 1.53 par le raccourci, sans toucher
    au choix de l'utilisateur : rien si le demarrage automatique n'etait pas
    actif. Vrai si un remplacement a eu lieu.

    Executable seulement, contrairement a watch2notif : plusieurs instances
    de lidar2map peuvent tourner a la fois, et un lancement depuis les
    sources a cote d'une installation (le cas du developpeur) repointerait
    sinon le demarrage automatique de l'installation vers python."""
    if (not frozen() or platform.system() != "Windows"
            or not _windows_legacy_file().exists()):
        return False
    _enable_windows()
    return True


def _chaine_ps(valeur: str) -> str:
    """Chaine litterale PowerShell : seule l'apostrophe se double."""
    return "'" + valeur.replace("'", "''") + "'"


def _enable_windows() -> None:
    """Raccourci .lnk dans le dossier Demarrage, cree par l'interface COM de
    l'explorateur via PowerShell, present sur tout Windows.

    lidar2map.exe est un programme console, mais construit avec
    hide_console="hide-early" : il cache sa fenetre des son demarrage, et
    WindowStyle 7 la fait naitre reduite, donc sans eclair a l'ecran.

    Remplace le script .vbs des versions <= 1.53 : VBScript est en cours de
    retrait de Windows, et wscript lisait ce script, ecrit en UTF-8 sans BOM,
    dans la page de code ANSI (un chemin accentue ne menait nulle part)."""
    commande = _lidar2map_command()
    cible = _windows_startup_file()
    # mkdir : le dossier Démarrage existe toujours sur une vraie installation
    # Windows, mais pas le dossier isolé d'un test (jamais le vrai %APPDATA%).
    cible.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut({cible});"
        "$s.TargetPath = {executable}; $s.Arguments = {arguments};"
        "$s.WorkingDirectory = {dossier}; $s.WindowStyle = 7;"
        "$s.Description = 'lidar2map'; $s.Save()"
    ).format(
        cible=_chaine_ps(str(cible)),
        executable=_chaine_ps(commande[0]),
        arguments=_chaine_ps(subprocess.list2cmdline(commande[1:])),
        dossier=_chaine_ps(str(_dossier_lancement())),
    )
    resultat = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        text=True, errors="replace", check=False,
        # CREATE_NO_WINDOW seul : avec DETACHED_PROCESS, il serait ignore.
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if resultat.returncode != 0 or not cible.exists():
        raise RuntimeError("raccourci de demarrage non cree : "
                           + ((resultat.stderr or "").strip() or str(cible)))
    # Deux entrees lanceraient deux fois lidar2map a l'ouverture de session.
    _windows_legacy_file().unlink(missing_ok=True)


def _disable_windows() -> None:
    # Le .vbs d'une version <= 1.53 aussi : sinon il relancerait lidar2map.
    for path in (_windows_startup_file(), _windows_legacy_file()):
        path.unlink(missing_ok=True)


def _enable_linux() -> None:
    service_content = (
        "[Unit]\n"
        "Description=lidar2map (GUI web local, --serve-gui)\n"
        "After=graphical-session.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={_dossier_lancement()}\n"
        f"ExecStart={' '.join(_systemd_quote(p) for p in _lidar2map_command())}\n"
        "Restart=on-failure\n"
        "RestartSec=10\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )
    service_file = _linux_service_file()
    service_file.parent.mkdir(parents=True, exist_ok=True)
    service_file.write_text(service_content, encoding="utf-8")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", LINUX_SERVICE_NAME], check=True)


def _disable_linux() -> None:
    subprocess.run(["systemctl", "--user", "disable", "--now", LINUX_SERVICE_NAME], check=False)
    path = _linux_service_file()
    if path.exists():
        path.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)


def _enable_mac() -> None:
    plist_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n<dict>\n'
        f"    <key>Label</key>\n    <string>{MAC_LABEL}</string>\n"
        "    <key>ProgramArguments</key>\n    <array>\n"
        + "".join(f"        <string>{_xml_escape(part)}</string>\n"
                  for part in _lidar2map_command())
        + "    </array>\n"
        f"    <key>WorkingDirectory</key>\n    <string>{_xml_escape(str(_dossier_lancement()))}</string>\n"
        "    <key>RunAtLoad</key>\n    <true/>\n"
        # Relancer uniquement apres un crash, pas apres un Stop volontaire
        # depuis le tray : meme raison que watch2notif (KeepAlive=true serait
        # combattu par launchd, qui relancerait l'ancienne instance juste
        # apres le Stop).
        "    <key>KeepAlive</key>\n"
        "    <dict>\n"
        "        <key>SuccessfulExit</key>\n"
        "        <false/>\n"
        "    </dict>\n"
        "</dict>\n</plist>\n"
    )
    plist_file = _mac_plist_file()
    plist_file.parent.mkdir(parents=True, exist_ok=True)
    plist_file.write_text(plist_content, encoding="utf-8")
    subprocess.run(["launchctl", "load", str(plist_file)], check=True)


def _disable_mac() -> None:
    plist_file = _mac_plist_file()
    if plist_file.exists():
        subprocess.run(["launchctl", "unload", str(plist_file)], check=False)
        plist_file.unlink()
