#!/usr/bin/env python3
"""Déploie rlidar2map_GUI_vm.sh par SSH depuis Windows, Linux ou macOS."""

from __future__ import annotations

import argparse
import ipaddress
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REMOTE_SCRIPT_NAME = "rlidar2map_GUI_vm.sh"
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]*$")


def bundled_resource(name: str) -> Path:
    """Retourne une ressource voisine, y compris dans un onefile PyInstaller."""
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_root / name


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
    if not local_script.is_file():
        raise SystemExit(f"Script Linux introuvable : {local_script}")

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

    print(f"\nCopie du script vers {ssh_destination}...")
    subprocess.run(
        [
            scp,
            *host_key_args,
            *identity_args,
            str(local_script),
            f"{scp_destination}:{REMOTE_SCRIPT_NAME}",
        ],
        check=True,
    )

    print(f"\nInstallation de XFCE et xrdp sur {ip}...")
    upgrade_value = "yes" if upgrade_system else "no"
    root_command = (
        f"SET_RDP_PASSWORD=default UPGRADE_SYSTEM={upgrade_value} "
        f"USERNAME='{gui_user}' bash \"$HOME/{REMOTE_SCRIPT_NAME}\""
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
        subprocess.Popen([client, str(rdp_file)])
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
                    ]
                )
                return
        remmina = shutil.which("remmina")
        if remmina:
            subprocess.Popen([remmina, "-c", f"rdp://{gui_user}@{address}"])
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


def parse_args() -> argparse.Namespace:
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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


if __name__ == "__main__":
    raise SystemExit(main())
