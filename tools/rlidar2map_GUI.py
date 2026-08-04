#!/usr/bin/env python3
"""Déploie rlidar2map_GUI_vm.sh par SSH depuis Windows, Linux ou macOS."""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# Unifie l'encodage du processus superviseur, du processus journalisé et des
# sorties SSH Ubuntu. Sans cela, la console Windows CP-1252 peut échouer sur un
# caractère UTF-8 reçu dans le flux combiné.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


REMOTE_SCRIPT_NAME = "rlidar2map_GUI_vm.sh"
ICON_FILE_NAME = "lidar2map_icon.png"
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]*$")
LOG_CHILD_ENV = "RLIDAR2MAP_GUI_LOGGED_CHILD"
LOG_FILE_NAME = "rlidar2map_GUI.log"


def bundled_resource(name: str) -> Path:
    """Retourne une ressource voisine, y compris dans un onefile PyInstaller.

    En mode source (non frozen), le script vit dans tools/ mais certaines
    ressources (l'icône commune) sont à la racine du projet, un niveau
    au-dessus : repli sur ce parent si le fichier n'est pas à côté du
    script. Sans ce repli, --remote-gui échouait en mode source avec
    « Icône introuvable » (bug vécu 2026-08-04) : le fichier n'a jamais été
    copié dans tools/, il n'existe qu'à la racine du dépôt et dans le
    bundle frozen, où le .spec le place explicitement à côté de l'exe."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / name
    here = Path(__file__).resolve().parent
    candidate = here / name
    if candidate.exists():
        return candidate
    return here.parent / name


def normalized_lf_copy(source: Path, destination: Path) -> None:
    """Copie un script texte en imposant les fins de ligne Unix LF."""
    content = source.read_text(encoding="utf-8")
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    with destination.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def log_path() -> Path:
    """Retourne le journal voisin de l'exécutable, avec un repli inscriptible."""
    executable = (
        Path(sys.executable).resolve()
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve()
    )
    candidates = (
        executable.with_name(LOG_FILE_NAME),
        Path.cwd() / LOG_FILE_NAME,
        Path(tempfile.gettempdir()) / LOG_FILE_NAME,
    )
    for candidate in candidates:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            with candidate.open("a", encoding="utf-8"):
                pass
            return candidate
        except OSError:
            continue
    raise SystemExit("Impossible de créer le fichier journal rlidar2map_GUI.log.")


def run_with_log(argv=None, *, relaunch=None) -> int:
    """Relance le programme en capturant aussi les sorties de ssh/scp.

    `relaunch` est la commande de base à réexécuter (sans les arguments) ;
    par défaut, le programme se relance lui-même (usage standalone). Délégué
    par lidar2map (--remote-gui), `relaunch` pointe vers lidar2map lui-même
    pour que le processus journalisé retombe dans le même dispatch."""
    argv = list(sys.argv[1:] if argv is None else argv)
    journal = log_path()
    if relaunch is not None:
        command = list(relaunch)
    else:
        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command.append(str(Path(__file__).resolve()))
    command.extend(argv)

    environment = os.environ.copy()
    environment[LOG_CHILD_ENV] = "1"
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUNBUFFERED"] = "1"

    print(f"Journal : {journal}")
    with journal.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(
            "\n{line}\nDémarrage : {started}\nCommande : {command}\n{line}\n".format(
                line="=" * 72,
                started=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                command=subprocess.list2cmdline(command),
            )
        )
        stream.flush()
        process = subprocess.Popen(
            command,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=environment,
        )
        assert process.stdout is not None
        while True:
            chunk = process.stdout.read(1)
            if not chunk:
                break
            print(chunk, end="", flush=True)
            stream.write(chunk)
            stream.flush()
        return_code = process.wait()
        stream.write(f"\nCode de sortie : {return_code}\n")

    print(f"\nJournal enregistré dans : {journal}")
    if return_code and os.name == "nt":
        try:
            input("Échec de l'installation. Appuie sur Entrée pour fermer...")
        except EOFError:
            pass
    return return_code


def require_command(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise SystemExit(
            f"Commande '{name}' introuvable. Installe le client OpenSSH."
        )
    return executable


def ask_ip(value: str | None) -> str:
    value = value or input("Adresse IP de la VM : ").strip()
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise SystemExit(f"Adresse IP invalide : {value}") from exc


def ask_username(value: str | None) -> str:
    value = value or "userlidar"
    if not USERNAME_RE.fullmatch(value):
        raise SystemExit(f"Nom de compte Linux invalide : {value}")
    return value


def ask_ssh_user(value: str | None) -> str:
    value = value or "root"
    if not USERNAME_RE.fullmatch(value):
        raise SystemExit(f"Nom de compte SSH invalide : {value}")
    return value


def ssh_host(ip: str) -> str:
    """Ajoute les crochets requis par scp pour une adresse IPv6."""
    return f"[{ip}]" if ipaddress.ip_address(ip).version == 6 else ip


def remove_old_host_key(ssh_keygen: str, ip: str) -> None:
    print(f"\nRenouvellement de l'empreinte SSH pour {ip}...")
    # -R sait aussi retrouver les entrées hachées de known_hosts.
    subprocess.run(
        [ssh_keygen, "-R", ip], check=False,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [ssh_keygen, "-R", f"[{ip}]:22"], check=False,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print("La nouvelle empreinte sera acceptée automatiquement.")


def deploy(
    ip: str,
    ssh_user: str,
    gui_user: str,
    identity_file: str | None,
    upgrade_system: bool,
) -> None:
    ssh = require_command("ssh")
    scp = require_command("scp")
    ssh_keygen = require_command("ssh-keygen")

    local_script = bundled_resource("rlidar2map_GUI_vm.sh")
    local_icon = bundled_resource(ICON_FILE_NAME)
    if not local_script.is_file():
        raise SystemExit(f"Script Linux introuvable : {local_script}")
    if not local_icon.is_file():
        raise SystemExit(f"Icône lidar2map introuvable : {local_icon}")

    identity_args: list[str] = []
    if identity_file:
        key_path = Path(identity_file).expanduser().resolve()
        if not key_path.is_file():
            raise SystemExit(f"Clé SSH introuvable : {key_path}")
        identity_args = ["-i", str(key_path)]

    host_key_args = ["-o", "StrictHostKeyChecking=accept-new"]

    remove_old_host_key(ssh_keygen, ip)
    scp_destination = f"{ssh_user}@{ssh_host(ip)}"
    ssh_destination = f"{ssh_user}@{ip}"

    print(f"\nCopie du script et de l'icône vers {ssh_destination}...")
    with tempfile.TemporaryDirectory(prefix="rlidar2map-GUI-") as temp_dir:
        normalized_script = Path(temp_dir) / REMOTE_SCRIPT_NAME
        normalized_lf_copy(local_script, normalized_script)
        subprocess.run(
            [
                scp,
                *host_key_args,
                *identity_args,
                str(normalized_script),
                str(local_icon),
                f"{scp_destination}:.",
            ],
            check=True,
        )

    print(f"\nInstallation de XFCE et xrdp sur {ip}...")
    upgrade_value = "yes" if upgrade_system else "no"
    root_command = (
        f"SET_RDP_PASSWORD=default UPGRADE_SYSTEM={upgrade_value} "
        f"USERNAME='{gui_user}' "
        f"LIDAR2MAP_ICON_SOURCE=\"$HOME/{ICON_FILE_NAME}\" "
        f"bash \"$HOME/{REMOTE_SCRIPT_NAME}\""
    )

    remote_command = (
        root_command if ssh_user == "root" else f"sudo -n env {root_command}"
    )

    subprocess.run(
        [ssh, *host_key_args, *identity_args, ssh_destination, remote_command],
        check=True,
    )


def launch_rdp(ip: str, gui_user: str) -> None:
    address = f"{ssh_host(ip)}:3389"
    print(f"\nOuverture du client RDP vers {address} (utilisateur {gui_user})...")

    if sys.platform == "win32":
        client = require_command("mstsc.exe")
        cmdkey = require_command("cmdkey.exe")
        rdp_file = Path(tempfile.gettempdir()) / f"lidar2map-{ip}.rdp"
        rdp_file.write_text(
            "\r\n".join(
                (
                    f"full address:s:{address}",
                    f"username:s:{gui_user}",
                    "prompt for credentials:i:0",
                    "authentication level:i:2",
                    "",
                )
            ),
            encoding="utf-16",
        )
        subprocess.run(
            [
                cmdkey,
                f"/generic:TERMSRV/{ip}",
                f"/user:{gui_user}",
                "/pass:userlidar",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.Popen(
            [client, str(rdp_file)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    if sys.platform.startswith("linux"):
        for command in ("xfreerdp3", "xfreerdp"):
            client = shutil.which(command)
            if client:
                subprocess.Popen(
                    [
                        client,
                        f"/v:{address}",
                        f"/u:{gui_user}",
                        "/p:userlidar",
                        "/cert:ignore",
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
        remmina = shutil.which("remmina")
        if remmina:
            subprocess.Popen(
                [remmina, "-c", f"rdp://{gui_user}@{address}"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        print("Aucun client RDP trouvé. Installe FreeRDP ou Remmina.")
        return

    if sys.platform == "darwin":
        rdp_file = Path(tempfile.gettempdir()) / f"lidar2map-{ip}.rdp"
        rdp_file.write_text(
            "\r\n".join(
                (
                    f"full address:s:{address}",
                    f"username:s:{gui_user}",
                    "prompt for credentials:i:1",
                    "",
                )
            ),
            encoding="utf-16",
        )
        result = subprocess.run(["open", str(rdp_file)], check=False)
        if result.returncode:
            print(f"Ouvre Windows App manuellement et utilise {address}.")
        return

    print(f"Système non reconnu : ouvre un client RDP vers {address}.")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prépare une VM Ubuntu 24.04/26.04 avec XFCE et xrdp."
    )
    parser.add_argument("--ip", help="adresse IP de la VM")
    parser.add_argument(
        "--ssh-user",
        help="compte administrateur SSH (défaut : root)",
    )
    parser.add_argument("--user", help="compte Linux RDP (défaut : userlidar)")
    parser.add_argument("--identity", help="chemin de la clé SSH privée")
    parser.add_argument(
        "--upgrade-system",
        action="store_true",
        help="mettre à niveau tous les paquets Ubuntu avant l'installation",
    )
    parser.add_argument(
        "--no-rdp",
        action="store_true",
        help="ne pas ouvrir le client RDP après l'installation",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    ip = ask_ip(args.ip)
    ssh_user = ask_ssh_user(args.ssh_user)
    gui_user = ask_username(args.user)
    identity_file = args.identity

    print(
        f"\nCompte Linux/RDP initial : {gui_user}/userlidar\n"
        "Tu pourras changer ce mot de passe après l'installation avec :\n"
        f"  ssh -t {gui_user}@{ip} passwd\n"
    )

    try:
        deploy(
            ip,
            ssh_user,
            gui_user,
            identity_file,
            args.upgrade_system,
        )
    except subprocess.CalledProcessError as exc:
        print(f"\nÉchec de la commande externe (code {exc.returncode}).", file=sys.stderr)
        return exc.returncode or 1
    print(
        "\nVM prête.\n"
        f"Compte RDP par défaut : {gui_user}/userlidar\n"
        "Pour changer le mot de passe :\n"
        f"  ssh -t {gui_user}@{ip} passwd"
    )
    if not args.no_rdp:
        launch_rdp(ip, gui_user)
    return 0


def cli_main(argv=None, *, relaunch=None) -> int:
    """Point d'entrée unifié, appelé en standalone ou délégué par lidar2map
    (--remote-gui) : capture les sorties dans rlidar2map_GUI.log via un
    relaunch, sauf si on est déjà le processus enfant journalisé."""
    if os.environ.get(LOG_CHILD_ENV) == "1":
        return main(argv)
    return run_with_log(argv, relaunch=relaunch)


if __name__ == "__main__":
    raise SystemExit(cli_main())
