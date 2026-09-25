"""Dossiers de lidar2map depuis la 1.54.0 : l'état dans le dossier de données
standard de l'OS, les sorties dans un dossier visible.

L'état, ce sont les préférences, l'historique, la clé API (lidar2map.env) et
les journaux : de petits fichiers que l'utilisateur n'a pas à voir. Les
sorties, ce sont Projets, cache et production : des gigaoctets qu'il cherche,
copie et supprime lui-même, d'où Documents/lidar2map par défaut. C'est la
convention de blink2video et de watch2notif. LIDAR2MAP_HOME, s'il est fourni,
regroupe l'un et l'autre, comme le dossier du programme le faisait jusqu'à la
1.53.

Le dossier d'état s'appelle lidar2map-data et non lidar2map : sous ce nom-là,
le dossier standard est déjà celui où le lanceur extrait le programme, et la
documentation invite à le supprimer quand une extraction tourne mal. Les
réglages et l'historique ne doivent pas partir avec lui.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path

import _atomic_files

NOM_ETAT = "lidar2map-data"
NOM_SORTIES = "lidar2map"
PREFERENCES = "preferences.json"
CLE_SORTIES = "dossier_sorties"
# Ce qu'une version <= 1.53 rangeait dans son dossier de travail.
FICHIERS_ETAT = (PREFERENCES, "historique.json", "lidar2map.env")
DOSSIERS_SORTIES = ("Projets", "cache", "production")
MARQUEUR = ".lidar2map_etat_migre.json"


def _force(environnement) -> Path | None:
    valeur = (environnement.get("LIDAR2MAP_HOME") or "").strip()
    return Path(valeur).expanduser().resolve() if valeur else None


def dossier_etat(environnement=None) -> Path:
    """LIDAR2MAP_HOME s'il est fourni, sinon le dossier standard de l'OS.
    Calcul pur : rien n'est créé sur le disque."""
    environnement = os.environ if environnement is None else environnement
    return _force(environnement) or _dossier_etat_standard()


def _dossier_etat_standard() -> Path:
    """Celui que donne platformdirs. Des sources lancées avant que le
    bootstrap l'ait installé appliquent les mêmes règles pour les trois
    systèmes pris en charge (même repli que blink2video)."""
    try:
        from platformdirs import user_data_dir
    except ImportError:
        if os.name == "nt":
            base = (os.environ.get("LOCALAPPDATA")
                    or str(Path.home() / "AppData" / "Local"))
        elif sys.platform == "darwin":
            base = str(Path.home() / "Library" / "Application Support")
        else:
            base = (os.environ.get("XDG_DATA_HOME", "").strip()
                    or str(Path.home() / ".local" / "share"))
        return (Path(base) / NOM_ETAT).resolve()
    return Path(user_data_dir(NOM_ETAT, appauthor=False)).resolve()


def _documents() -> Path:
    """Le dossier Documents, même déplacé (OneDrive, autre disque) quand
    platformdirs est là ; ~/Documents sinon."""
    try:
        from platformdirs import user_documents_dir
    except ImportError:
        return Path.home() / "Documents"
    return Path(user_documents_dir())


def dossier_sorties(etat=None, environnement=None) -> Path:
    """Racine des sorties (Projets, cache, production) : le réglage
    dossier_sorties des préférences, que pose la reprise d'une version
    <= 1.53, sinon LIDAR2MAP_HOME, sinon Documents/lidar2map. Calcul pur,
    comme dossier_etat()."""
    environnement = os.environ if environnement is None else environnement
    etat = dossier_etat(environnement) if etat is None else Path(etat)
    preferences = _atomic_files.lire_json(etat / PREFERENCES, {})
    reglage = preferences.get(CLE_SORTIES) if isinstance(preferences, dict) else None
    if isinstance(reglage, str) and reglage.strip():
        return Path(reglage.strip()).expanduser().resolve()
    return _force(environnement) or (_documents() / NOM_SORTIES).resolve()


def preparer_etat(ancien, *, version="", environnement=None) -> list:
    """Reprend, une fois, l'état qu'une version <= 1.53 rangeait dans son
    dossier de travail `ancien` (celui du lanceur, ou des sources), et rend
    la liste de ce qui a été repris. Sans effet avec LIDAR2MAP_HOME.

    Appelée au démarrage par lidar2map.py, sous __main__ seulement : un
    simple calcul de chemin, dans un test, ne doit jamais copier d'état.

    Les fichiers d'état sont copiés sans rien écraser, jamais déplacés :
    revenir à la 1.53 reste possible. Les sorties ne bougent pas : si
    l'ancien dossier en contient, le réglage dossier_sorties y pointe. Le
    marqueur n'est posé que si quelque chose a été repris ; sans rien à
    reprendre, l'examen recommence au lancement suivant, pour quelques accès
    disque."""
    environnement = os.environ if environnement is None else environnement
    if _force(environnement):
        return []
    etat = _dossier_etat_standard()
    ancien = Path(ancien).resolve()
    if ancien == etat or (etat / MARQUEUR).is_file():
        return []
    # Démarrage automatique et lancement manuel peuvent partir ensemble : un
    # seul processus reprend, l'autre attend son verrou et trouve le marqueur.
    with _atomic_files.verrou_inter_processus(etat / MARQUEUR, delai_s=60):
        if (etat / MARQUEUR).is_file():
            return []
        return _reprendre(ancien, etat, version)


def _reprendre(ancien: Path, etat: Path, version: str) -> list:
    repris = [nom for nom in FICHIERS_ETAT
              if _copier_si_absent(ancien / nom, etat / nom)]

    sorties = ""
    if any((ancien / nom).is_dir() for nom in DOSSIERS_SORTIES):
        chemin = etat / PREFERENCES
        # Même verrou que _ecrire_pref() : une instance déjà passée à la 1.54
        # peut écrire une préférence au même moment.
        with _atomic_files.verrou_inter_processus(chemin):
            preferences = _atomic_files.lire_json(chemin, {})
            if not isinstance(preferences, dict):
                preferences = {}
            if not str(preferences.get(CLE_SORTIES) or "").strip():
                preferences[CLE_SORTIES] = sorties = str(ancien)
                _ecrire_json(chemin, preferences)

    if not (repris or sorties):
        return []
    _ecrire_json(etat / MARQUEUR, {
        "version": version,
        "date": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "depuis": str(ancien),
        "repris": repris,
        CLE_SORTIES: sorties,
    })
    return repris + ([CLE_SORTIES] if sorties else [])


def _copier_si_absent(source: Path, cible: Path) -> bool:
    """Copie atomique d'un fichier, sans jamais écraser la cible."""
    if cible.exists() or not source.is_file():
        return False
    cible.parent.mkdir(parents=True, exist_ok=True)
    temporaire = _atomic_files.chemin_part(cible)
    try:
        shutil.copy2(source, temporaire)
        _atomic_files.remplacer(temporaire, cible)
    finally:
        temporaire.unlink(missing_ok=True)
    return True


def _ecrire_json(chemin: Path, donnees) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = _atomic_files.chemin_part(chemin)
    try:
        temporaire.write_text(json.dumps(donnees, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        _atomic_files.remplacer(temporaire, chemin)
    finally:
        temporaire.unlink(missing_ok=True)
