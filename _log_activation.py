"""Activation explicite du logger fichier de lidar2map."""

from __future__ import annotations

import os
import time
import traceback
import uuid
from pathlib import Path


def _verifier_dossier(log_dir):
    log_dir.mkdir(parents=True, exist_ok=True)
    probe = log_dir / f".write_test.{os.getpid()}.{uuid.uuid4().hex[:12]}.part"
    probe.touch()
    probe.unlink()


def activer_log(
    *,
    sys_module,
    environnement,
    script_path,
    classe_logger,
    rediger_secrets,
    enregistrer_atexit,
    verifier_dossier=_verifier_dossier,
    ecrire=None,
):
    """Installe le logger et retourne son instance, ou ``None`` si inaccessible."""
    if ecrire is None:
        ecrire = print
    if getattr(sys_module, "frozen", False):
        base = Path(
            environnement.get("LIDAR2MAP_WORK_DIR")
            or Path(sys_module.executable).resolve().parent
        )
    else:
        base = Path(script_path).resolve().parent
    log_dir = base / "logs"
    try:
        verifier_dossier(log_dir)
    except OSError:
        ecrire("  WARNING: logs/ folder inaccessible, console log only.")
        return None

    nom = "lidar_" + time.strftime("%Y%m%d_%H%M%S") + f"_{os.getpid()}.log"
    log_path = log_dir / nom
    tee = classe_logger(log_path)
    sys_module.stdout = tee
    sys_module.stderr = tee

    def fermer_sans_erreur():
        try:
            if isinstance(sys_module.stdout, classe_logger):
                sys_module.stdout.close()
        except Exception:
            pass

    enregistrer_atexit(fermer_sans_erreur)

    def excepthook(exc_type, exc_value, exc_tb):
        ecrire("\nUNHANDLED EXCEPTION:")
        ecrire("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))

    sys_module.excepthook = excepthook
    horodatage = time.strftime("%Y-%m-%d %H:%M:%S")
    commande = rediger_secrets(" ".join(sys_module.argv))
    tee._log.write("=" * 60 + "\n")
    tee._log.write(f"  lidar2map.py — démarrage {horodatage}\n")
    tee._log.write(f"  Commande : {commande}\n")
    tee._log.write("=" * 60 + "\n")
    ecrire(f"  Log : {log_path} (publication atomique à la fin)")
    return tee
