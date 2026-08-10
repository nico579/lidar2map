"""Manifeste de reprise et suivi des fichiers des traitements découpés.

Ce module reste privé. ``lidar2map`` réexporte sa façade historique afin que
les appels et les tests existants continuent de fonctionner sans migration.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


def _ecrire_json_atomique(path, data, indent=None):
    """Écrit un petit document JSON sans exposer de fichier tronqué."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / (
        f"{path.name}.{os.getpid()}.{uuid.uuid4().hex[:12]}.part"
    )
    try:
        payload = json.dumps(data, ensure_ascii=False, indent=indent)
        with open(tmp, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            try:
                os.fsync(stream.fileno())
            except (OSError, AttributeError):
                pass
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


class Manifeste:
    """Manifeste JSON local au projet — reprise et nettoyage des morceaux."""

    _warned_save_failed = False

    def __init__(self, path: Path):
        self.path = Path(path)
        self._data = self._charger()
        # Le préchargement glissant écrit depuis un thread de fond pendant que
        # le thread principal calcule l'ombrage du morceau courant.
        self._lock = threading.Lock()

    def _charger(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data.setdefault("morceaux", {})
                    data.setdefault("fichiers", {})
                    return data
                print(
                    f"  ⚠ Manifeste {self.path.name}: unexpected structure "
                    f"(type={type(data).__name__}), resetting"
                )
            except (OSError, json.JSONDecodeError) as exc:
                print(
                    f"  ⚠ Manifeste {self.path.name} unreadable "
                    f"({type(exc).__name__}: {exc}), resetting "
                    "(previous progress lost)"
                )
        return {"morceaux": {}, "fichiers": {}}

    def deja_traite(self, cle: str) -> bool:
        with self._lock:
            return self._data["morceaux"].get(cle, {}).get("termine", False)

    def verifier_signature(self, sig: str) -> bool:
        """Invalide la progression si la configuration du run a changé."""
        with self._lock:
            ancienne = self._data.get("config_sig")
            self._data["config_sig"] = sig
            if ancienne is None or ancienne == sig:
                if ancienne is None:
                    self._sauver()
                return False
            self._data["morceaux"] = {}
            self._data["fichiers"] = {}
            self._sauver()
            return True

    def debut_morceau(self, cle: str, nom: str):
        """Marque le début d'une tentative et retire son ancienne preuve."""
        with self._lock:
            morceau = self._data["morceaux"].setdefault(cle, {})
            morceau.update(
                {
                    "debut": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "nom": nom,
                    "termine": False,
                }
            )
            morceau.pop("mbtiles_attendus", None)
            self._sauver()

    def fin_morceau(self, cle: str, duree_s: int, mbtiles_attendus=None):
        """Publie la fin d'un morceau et, si connue, sa preuve de sortie.

        Une liste non vide contient les chemins canoniques à revalider. Une
        liste vide signifie explicitement « hors couverture ». ``None`` garde
        la compatibilité avec les étapes sans livrable final.
        """
        with self._lock:
            morceau = self._data["morceaux"][cle]
            morceau.update({"termine": True, "duree_s": duree_s})
            if mbtiles_attendus is not None:
                morceau["mbtiles_attendus"] = [
                    str(Path(path).resolve()) for path in mbtiles_attendus
                ]
            self._sauver()

    def mbtiles_attendus_morceau(self, cle: str):
        """Retourne None (legacy), () (hors couverture) ou les sorties."""
        with self._lock:
            morceau = self._data["morceaux"].get(cle, {})
            if "mbtiles_attendus" not in morceau:
                return None
            return tuple(Path(path) for path in morceau["mbtiles_attendus"])

    def invalider_morceau(self, cle: str):
        """Remet un morceau terminé en attente d'un rejeu."""
        with self._lock:
            morceau = self._data["morceaux"].get(cle)
            if morceau is not None and morceau.get("termine"):
                morceau["termine"] = False
                self._sauver()

    def enregistrer_fichier(self, path, cle: str):
        resolved = str(Path(path).resolve())
        with self._lock:
            fichiers = self._data["fichiers"].setdefault(cle, [])
            if resolved not in fichiers:
                fichiers.append(resolved)
            self._sauver()

    def enregistrer_fichiers(self, paths, cle: str):
        """Enregistre plusieurs fichiers avec une seule sauvegarde JSON."""
        with self._lock:
            fichiers = self._data["fichiers"].setdefault(cle, [])
            connus = set(fichiers)
            ajout = False
            for path in paths:
                resolved = str(Path(path).resolve())
                if resolved not in connus:
                    fichiers.append(resolved)
                    connus.add(resolved)
                    ajout = True
            if ajout:
                self._sauver()

    def fichiers_morceau(self, cle: str) -> list:
        with self._lock:
            return list(self._data["fichiers"].get(cle, []))

    def oublier_fichiers_absents(self, cle: str):
        """Retire les chemins disparus avant de rejouer un morceau."""
        with self._lock:
            avant = self._data["fichiers"].get(cle, [])
            apres = [path for path in avant if Path(path).exists()]
            if apres != avant:
                self._data["fichiers"][cle] = apres
                self._sauver()

    def eta_global(self, n_total: int):
        """Retourne ``(nombre terminé, ETA grossière en secondes)``."""
        with self._lock:
            durees = sorted(
                morceau["duree_s"]
                for morceau in self._data["morceaux"].values()
                if morceau.get("termine")
                and isinstance(morceau.get("duree_s"), (int, float))
            )
        if not durees:
            return 0, None
        nombre = len(durees)
        mediane = (
            durees[nombre // 2]
            if nombre % 2
            else (durees[nombre // 2 - 1] + durees[nombre // 2]) / 2
        )
        return nombre, int(mediane * max(0, n_total - nombre))

    def _sauver(self):
        try:
            _ecrire_json_atomique(self.path, self._data, indent=2)
        except Exception as exc:
            # Le manifeste reste best-effort : ne pas interrompre un calcul
            # long, mais avertir une seule fois que la reprise est fragilisée.
            if not Manifeste._warned_save_failed:
                Manifeste._warned_save_failed = True
                print(
                    f"  ⚠ Manifeste {self.path.name} : write failure "
                    f"({type(exc).__name__}: {exc}). "
                    "Resume may be inconsistent."
                )


_manifest_ctx = threading.local()


@contextmanager
def _contexte_manifeste(manifeste, cle: str):
    """Active le suivi pour un morceau et restaure un contexte imbriqué."""
    precedent_manifeste = getattr(_manifest_ctx, "manifeste", None)
    precedente_cle = getattr(_manifest_ctx, "cle", None)
    _manifest_ctx.manifeste = manifeste
    _manifest_ctx.cle = cle
    try:
        yield
    finally:
        _manifest_ctx.manifeste = precedent_manifeste
        _manifest_ctx.cle = precedente_cle


def _creer_fichier(path):
    """Déclare un fichier intermédiaire dans le contexte actif."""
    manifeste = getattr(_manifest_ctx, "manifeste", None)
    if manifeste is None:
        return
    manifeste.enregistrer_fichier(path, getattr(_manifest_ctx, "cle", "global"))


def _creer_fichiers(paths):
    """Déclare plusieurs fichiers intermédiaires en une écriture."""
    manifeste = getattr(_manifest_ctx, "manifeste", None)
    if manifeste is None:
        return
    manifeste.enregistrer_fichiers(paths, getattr(_manifest_ctx, "cle", "global"))


__all__ = (
    "Manifeste",
    "_contexte_manifeste",
    "_creer_fichier",
    "_creer_fichiers",
)
