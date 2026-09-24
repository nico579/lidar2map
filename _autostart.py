"""Active/desactive le lancement automatique de lidar2map (mode serveur web,
--serve-gui) au demarrage de la session, selon l'OS courant. Meme mecanisme
que watch2notif/autostart_manager.py (le seul jumeau de ce pattern dans les
projets de Nico) : un lancement sans argument sert deja le GUI par defaut,
donc rien de plus a passer que --no-browser (le navigateur ne doit pas
s'ouvrir tout seul a l'ouverture de session, seulement le serveur)."""
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
    tray/l'acces distant restent la, ouvrir la page reste un choix)."""
    if frozen():
        suffix = ".exe" if platform.system() == "Windows" else ""
        binary = Path(sys.executable).parent / f"lidar2map{suffix}"
        return [str(binary), "--serve-gui", "--no-browser"]
    if platform.system() == "Windows":
        return [str(Path(sys.executable).with_name("pythonw.exe")),
                str(PROJECT_DIR / "lidar2map.py"), "--serve-gui", "--no-browser"]
    return [sys.executable, str(PROJECT_DIR / "lidar2map.py"),
            "--serve-gui", "--no-browser"]


def _lidar2map_environment() -> dict:
    """Variables a transmettre au lancement automatique.

    Fige, sys.executable est l'exe INTERNE extrait par le launcher (dossier
    d'application), lance par lui avec LIDAR2MAP_WORK_DIR = dossier de l'exe
    visible par l'utilisateur. Relance tel quel a l'ouverture de session sans
    cette variable, il prenait son propre dossier d'extraction comme dossier
    de travail : Projets/, cache/, historique et preferences separes de ceux
    de l'utilisateur, et effaces par le launcher (rmtree du dossier
    d'application) a la mise a jour suivante."""
    if not frozen():
        return {}
    dossier_travail = os.environ.get("LIDAR2MAP_WORK_DIR", "").strip()
    return {"LIDAR2MAP_WORK_DIR": dossier_travail} if dossier_travail else {}


def _systemd_quote(valeur: str) -> str:
    """Argument ExecStart=/Environment= entre guillemets (espaces dans un
    chemin) ; % est un specificateur systemd, a doubler."""
    echappe = valeur.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return f'"{echappe}"'


def _xml_escape(valeur: str) -> str:
    return (valeur.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _windows_startup_file() -> Path:
    appdata = os.environ["APPDATA"]
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "lidar2map.vbs"


def _linux_service_file() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / LINUX_SERVICE_NAME


def _mac_plist_file() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{MAC_LABEL}.plist"


def is_enabled() -> bool:
    system = platform.system()
    if system == "Windows":
        return _windows_startup_file().exists()
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


def _enable_windows() -> None:
    quoted = " ".join(f'""{part}""' for part in _lidar2map_command())
    # Environment("PROCESS") : herite par le process que lance shell.Run.
    env_lignes = "".join(
        f'shell.Environment("PROCESS")("{nom}") = "{valeur.replace(chr(34), chr(34) * 2)}"\n'
        for nom, valeur in _lidar2map_environment().items()
    )
    vbs_content = (
        'Set shell = CreateObject("WScript.Shell")\n'
        f'shell.CurrentDirectory = "{PROJECT_DIR}"\n'
        + env_lignes +
        f'shell.Run "{quoted}", 0, False\n'
    )
    fichier = _windows_startup_file()
    # mkdir : le dossier Démarrage existe toujours sur une vraie installation
    # Windows, donc ce cas ne se manifeste jamais en usage réel - mais un
    # test avec un dossier isolé (jamais le vrai %APPDATA%) le révèle
    # immédiatement (trouvé en écrivant test_autostart.py, absent du
    # autostart_manager.py de watch2notif dont ce fichier s'inspire).
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(vbs_content, encoding="utf-8")


def _disable_windows() -> None:
    path = _windows_startup_file()
    if path.exists():
        path.unlink()


def _enable_linux() -> None:
    service_content = (
        "[Unit]\n"
        "Description=lidar2map (GUI web local, --serve-gui)\n"
        "After=graphical-session.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={PROJECT_DIR}\n"
        + "".join(f"Environment={_systemd_quote(f'{nom}={valeur}')}\n"
                  for nom, valeur in _lidar2map_environment().items())
        + f"ExecStart={' '.join(_systemd_quote(p) for p in _lidar2map_command())}\n"
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
    environnement = _lidar2map_environment()
    env_plist = ""
    if environnement:
        env_plist = (
            "    <key>EnvironmentVariables</key>\n    <dict>\n"
            + "".join(f"        <key>{_xml_escape(nom)}</key>\n"
                      f"        <string>{_xml_escape(valeur)}</string>\n"
                      for nom, valeur in environnement.items())
            + "    </dict>\n"
        )
    plist_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n<dict>\n'
        f"    <key>Label</key>\n    <string>{MAC_LABEL}</string>\n"
        "    <key>ProgramArguments</key>\n    <array>\n"
        + "".join(f"        <string>{_xml_escape(part)}</string>\n"
                  for part in _lidar2map_command())
        + "    </array>\n"
        + env_plist +
        f"    <key>WorkingDirectory</key>\n    <string>{_xml_escape(str(PROJECT_DIR))}</string>\n"
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
