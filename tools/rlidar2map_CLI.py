#!/usr/bin/env python3
"""
rlidar2map_CLI.py — Lancement et supervision d'un calcul lidar2map sur une VM
=========================================================================

Contrôleur local sans dépendance Python externe. Il lance lidar2map dans une
session tmux détachée, surveille son état persistant et recopie les résultats
vers le PC au fur et à mesure.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PRINCIPE ET REPRISE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  La VM conserve l'état du run sous ~/.lidar2map-runs/<session>. Le nom de
  session (lidar par défaut) est donc l'identifiant d'un lancement ; plusieurs
  calculs peuvent être suivis avec plusieurs noms.

  Ctrl-C arrête uniquement le contrôleur local, jamais le tmux ni lidar2map.
  Relancer la même commande avec la même VM et --session reprend la surveillance
  et la synchronisation sans démarrer un second calcul. Une session terminée
  n'est pas relancée implicitement : utiliser --resume, --restart, ou un
  nouveau nom.

  --resume relance les MÊMES arguments lidar2map dans la session terminée SANS
  toucher à ses résultats : les dalles déjà téléchargées restent en cache
  (seules celles manquantes ou en erreur sont retéléchargées), utile après un
  échec réseau ponctuel (cf. invariant "jamais de trou de couverture"). Ne
  s'applique qu'à une session terminée (échec ou succès), jamais active.
  --restart, lui, ARCHIVE l'état existant (résultats compris) puis redémarre
  tout depuis zéro : à réserver à un vrai changement de paramètres.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LANCEMENT ET SYNCHRONISATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  --source       Lance depuis le checkout source (défaut).
  --bundle       Lance le bundle lidar2map configuré.
  --detach       Lance ou retrouve le run puis rend la main immédiatement.
  --once         Effectue un seul contrôle et une seule synchronisation.

  rsync est utilisé lorsqu'il est disponible (--sync-method auto ou rsync).
  Sinon, le fallback SSH transfère les fichiers réguliers publiés sous le
  dossier results isolé du run. Les fichiers/répertoires *.part et les
  fichiers auxiliaires SQLite sont ignorés ; pendant un run actif, l'inventaire
  doit être identique deux fois avant transfert. Chaque fichier est vérifié par
  SHA-256 et publié atomiquement en local. Le journal est copié une seule fois
  lorsque le run est terminal. Les méthodes ssh et scp utilisent ce flux.

  Le contrôleur ne déduit pas le résultat en analysant le texte du journal :
  l'état, le code de sortie et les horodatages publiés par le wrapper tmux font
  foi. Une fin normale, un plantage ou une disparition de tmux sont signalés.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PARAMÈTRES DU CONTRÔLEUR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Les exemples ci-dessous utilisent la VM Ubuntu 192.0.2.10 et ce calcul de
  référence : MNT LiDAR de Garéoult sur 5 km, LRM sigma 3, sortie MBTiles.

  python tools/rlidar2map_CLI.py --source --session doc-gareoult-lrm3 \
      root@192.0.2.10 -- --ignlidar --zone-ville gareoult \
      --zone-width 5 --zone-nom doc_gareoult_lrm3 --telechargement \
      --ombrages lrm --shading lrm:sigma=3 --formats-fichier mbtiles

  VM                         [OBLIGATOIRE, sans défaut]
                             Cible SSH : user@hote, adresse IP ou
                             alias déclaré dans ~/.ssh/config.
                             Ex. : root@192.0.2.10 dans la commande ci-dessus.

  --source                   [OPTIONNEL, mode par défaut]
                             Utilise le checkout source.
                             Ex. : la commande de référence utilise --source.

  --bundle                   [OPTIONNEL, défaut : désactivé]
                             Télécharge et utilise le bundle Linux publié.
                             Ex. : même calcul avec le bundle :
                             python tools/rlidar2map_CLI.py --bundle -s doc-bundle \
                                 root@192.0.2.10 -- --ignlidar \
                                 --zone-ville gareoult --zone-width 5 \
                                 --zone-nom doc_bundle --telechargement \
                                 --ombrages lrm --shading lrm:sigma=3 \
                                 --formats-fichier mbtiles

  --session NOM, -s NOM      [OPTIONNEL, défaut : lidar]
                             Nom tmux et identifiant persistant du run.
                             Ex. : reprendre le calcul de référence :
                             python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 root@192.0.2.10

  --local-dir DOSSIER        [OPTIONNEL]
                             Racine de destination locale. Défaut calculé :
                             ./vm-results/<hôte>/<session>/<run-id>/.
                             Ex. : reprendre la copie sous D:/lidar/vm-results :
                             python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 --local-dir D:/lidar/vm-results root@192.0.2.10

  --interval SECONDES        [OPTIONNEL, défaut : 30]
                             Délai en secondes entre contrôles/synchronisations.
                             Ex. : contrôler toutes les 10 secondes :
                             python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 --interval 10 root@192.0.2.10

  --sync-method MÉTHODE      [OPTIONNEL, défaut : auto]
                             Valeurs : auto, rsync, ssh ou scp ; auto préfère rsync.
                             Ex. : forcer le flux SSH incrémental :
                             python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 --sync-method ssh root@192.0.2.10

  --identity FICHIER         [OPTIONNEL, défaut : aucune option -i]
                             Clé privée utilisée par SSH. Sans cette option,
                             SSH utilise son agent et sa configuration normale.
                             Prérequis : ce fichier de clé doit exister.
                             Ex. : python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 --identity C:/Users/Nico/.ssh/id_ed25519 \
                                 root@192.0.2.10

  --ssh-timeout SECONDES     [OPTIONNEL, défaut : 10]
                             Délai maximal d'une commande SSH, en secondes.
                             Ex. : tolérer 20 secondes par commande :
                             python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 --ssh-timeout 20 root@192.0.2.10

  --ssh-option KEY=VALUE     [OPTIONNEL, défaut : aucune]
                             Option OpenSSH supplémentaire, répétable.
                             Ex. : maintenir la connexion active :
                             python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 --ssh-option ServerAliveInterval=15 \
                                 --ssh-option ServerAliveCountMax=4 \
                                 root@192.0.2.10

  --reset-host-key           [OPTIONNEL, défaut : désactivé]
                             Supprime explicitement l'ancienne clé de cette
                             cible dans known_hosts avant la connexion. Utile
                             quand la VM change tout en gardant son IP.
                             Ex. : reprendre après réinstallation de la VM :
                             python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 --reset-host-key root@192.0.2.10

  --max-ssh-errors N         [OPTIONNEL, défaut : 3]
                             Nombre d'échecs SSH consécutifs tolérés avant
                             l'abandon de la surveillance.
                             Ex. : tolérer huit erreurs consécutives :
                             python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 --max-ssh-errors 8 root@192.0.2.10

  --no-bell                  [OPTIONNEL, défaut : bip activé]
                             Désactive le bip terminal de fin ou de plantage.
                             Ex. : python tools/rlidar2map_CLI.py -s doc-gareoult-lrm3 \
                                 --no-bell root@192.0.2.10

  --restart                  [OPTIONNEL, défaut : désactivé]
                             Archive un run terminé puis relance la session.
                             Prérequis : doc-gareoult-lrm3 doit être terminé.
                             Ex. : relancer le même calcul :
                             python tools/rlidar2map_CLI.py --restart \
                                 -s doc-gareoult-lrm3 root@192.0.2.10 -- \
                                 --ignlidar --zone-ville gareoult --zone-width 5 \
                                 --zone-nom doc_gareoult_lrm3 --telechargement \
                                 --ombrages lrm --shading lrm:sigma=3 \
                                 --formats-fichier mbtiles

  --resume                   [OPTIONNEL, défaut : désactivé]
                             Relance la session terminée SANS archiver ses
                             résultats : les dalles déjà en cache sont gardées,
                             seules celles manquantes ou en erreur sont
                             retéléchargées. Prérequis : doc-gareoult-lrm3 doit
                             être terminé (échec ou succès), jamais actif.
                             Ex. : reprendre après une erreur réseau ponctuelle,
                             mêmes arguments que le lancement d'origine :
                             python tools/rlidar2map_CLI.py --resume \
                                 -s doc-gareoult-lrm3 root@192.0.2.10 -- \
                                 --ignlidar --zone-ville gareoult --zone-width 5 \
                                 --zone-nom doc_gareoult_lrm3 --telechargement \
                                 --ombrages lrm --shading lrm:sigma=3 \
                                 --formats-fichier mbtiles

  --purge-remote             [OPTIONNEL, défaut : désactivé]
                             Synchronise puis purge les données du run terminé.
                             Prérequis : doc-gareoult-lrm3 doit être terminé.
                             Ex. : python tools/rlidar2map_CLI.py --purge-remote \
                                 -s doc-gareoult-lrm3 root@192.0.2.10

  --detach                   [OPTIONNEL, défaut : surveillance continue]
                             Lance/retrouve le run sans surveillance continue.
                             Ex. : lancer un calcul LAZ puis rendre la main :
                             python tools/rlidar2map_CLI.py --detach -s doc-gareoult-laz \
                                 root@192.0.2.10 -- --laz --ignlidar \
                                 --zone-ville gareoult --zone-width 5 \
                                 --zone-nom doc_gareoult_laz --telechargement \
                                 --ombrages lrm --shading lrm:sigma=3 \
                                 --formats-fichier mbtiles

  --once                     [OPTIONNEL, défaut : surveillance continue]
                             Effectue un seul contrôle et une synchronisation.
                             Prérequis : doc-gareoult-laz a été lancé ci-dessus.
                             Ex. : python tools/rlidar2map_CLI.py --once \
                                 -s doc-gareoult-laz root@192.0.2.10

  -h, --help                 [OPTIONNEL, défaut : désactivé]
                             Affiche l'aide complète puis quitte.
                             Ex. : python tools/rlidar2map_CLI.py --help

  --                         [CONDITIONNEL, recommandé au lancement]
                             Sépare les options du contrôleur des arguments
                             transmis tels quels à lidar2map. Ces arguments
                             sont obligatoires pour créer un run absent ou avec
                             --restart/--resume, et doivent être omis pour une
                             reprise de surveillance ou --purge-remote.
                             Ex. : la commande de référence sépare
                             root@192.0.2.10 de --ignlidar avec « -- ».

  Contraintes : --source et --bundle sont mutuellement exclusifs ; --restart,
  --resume et --purge-remote aussi (un seul des trois à la fois). --detach et
  --once ne peuvent pas être combinés, et aucun des deux n'est accepté avec
  --purge-remote.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PURGE ET ARCHIVAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  --purge-remote est réservé à un run terminé : il fait une dernière copie,
  puis supprime uniquement l'état, le journal et les résultats de ce run sur la
  VM. Les dossiers partagés cache/, production/, le dépôt, le venv et le
  runtime ne sont jamais supprimés. --restart archive l'état terminé avant de
  lancer un nouveau run sous le même nom de session ; --resume relance dans le
  MÊME run sans rien archiver (dalles déjà en cache conservées).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EXEMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # MNT LiDAR de Garéoult sur 5 km, LRM sigma 3, MBTiles
  python tools/rlidar2map_CLI.py --session gareoult-lrm3 \
      root@192.0.2.10 -- --ignlidar --zone-ville gareoult \
      --zone-width 5 --zone-nom gareoult_lrm3 --telechargement \
      --ombrages lrm --shading lrm:sigma=3 --formats-fichier mbtiles

  # Calcul LAZ indépendant, avec un nom de session explicite
  python tools/rlidar2map_CLI.py --session gareoult-laz \
      root@192.0.2.10 -- --laz --ignlidar \
      --zone-ville gareoult --zone-width 5 --telechargement \
      --ombrages lrm --shading lrm:sigma=3 --formats-fichier mbtiles

  # Reconnexion après fermeture du contrôleur local
  python tools/rlidar2map_CLI.py --session gareoult-laz root@192.0.2.10

  # Lancement sans attendre, puis contrôle ponctuel
  python tools/rlidar2map_CLI.py --detach --session gareoult-detache \
      root@192.0.2.10 -- --ignlidar --zone-ville gareoult \
      --zone-width 5 --zone-nom gareoult_detache --telechargement \
      --ombrages lrm --shading lrm:sigma=3 --formats-fichier mbtiles
  python tools/rlidar2map_CLI.py --once --session gareoult-detache \
      root@192.0.2.10

  # Après la fin : dernière synchronisation puis purge distante du run
  python tools/rlidar2map_CLI.py --session gareoult-detache --purge-remote \
      root@192.0.2.10

  # Aide complète des options
  python tools/rlidar2map_CLI.py --help

Les arguments destinés à lidar2map doivent être placés séparément après « -- ».
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, List, Optional, Sequence, Tuple


DEFAULT_SESSION = "lidar"
DEFAULT_INTERVAL = 30.0
SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
TERMINAL_STATES = frozenset(("succeeded", "failed"))
# --sync-only : extensions rapatriées par catégorie. "ombrages" = TIF
# intermédiaires (produits par lidar2map, jamais le livrable final) ;
# "carte" = les formats de sortie tuilés (--file-formats). "tout" (défaut)
# ne filtre rien, cf. _sync_only_excludes.
SYNC_ONLY_EXTENSIONS = {
    "ombrages": (".tif",),
    "carte": (".mbtiles", ".rmap", ".sqlitedb"),
}
# Jamais utiles en local, quel que soit --sync-only : intermédiaires purs
# (VRT de fusion voisins pour le tuilage, cf. _traiter_bbox_lidar_tuilage).
# Exclus inconditionnellement, pas seulement selon la catégorie demandée.
ALWAYS_EXCLUDED_EXTENSIONS = (".vrt",)
ACTIVE_STATES = frozenset(("provisioning", "starting", "running"))
# Cadence de rafraîchissement du tail de log PENDANT un sync en fond (cf.
# _sync_once_with_live_log_tail) : plus court que --interval, juste pour que
# l'affichage continue de bouger sur un gros transfert, pas pour re-sonder
# l'état du run (ça reste au rythme normal, après le sync).
_LOG_TAIL_POLL_INTERVAL_S = 3.0
PURGE_PENDING_MARKER = ".rlidar2map-purge-pending.json"
PURGED_MARKER = ".rlidar2map-purged.json"
PURGE_SUPERSEDED_MARKER = ".rlidar2map-purge-superseded.json"
SCP_INDEX_NAME = ".rlidar2map-ssh-index.json"
FILE_STREAM_MAGIC = b"L2M-FILE-STREAM-1\n"


REMOTE_QUERY_SCRIPT = r"""#!/usr/bin/env bash
set -u
umask 077

SESSION="${1:-}"
if [[ ! "$SESSION" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]]; then
  echo "invalid session" >&2
  exit 64
fi

BASE="$HOME/.lidar2map-runs"
RUN_DIR="$BASE/$SESSION"
SESSION_LOCK_FILE="$BASE/.session-${SESSION}.flock"

refresh_tmux() {
  TMUX_ALIVE=0
  if command -v tmux >/dev/null 2>&1 &&
     tmux has-session -t "=$SESSION" 2>/dev/null; then
    TMUX_ALIVE=1
  fi
}

refresh_tmux

if [ ! -d "$RUN_DIR" ]; then
  printf 'protocol=1\nexists=0\ntmux=%s\n' "$TMUX_ALIVE"
  exit 0
fi

read_value() {
  local path="$1"
  local value=""
  if [ -r "$path" ]; then
    IFS= read -r value < "$path" || true
  fi
  printf '%s' "$value"
}

write_value() {
  local path="$1"
  local value="$2"
  local tmp="${path}.tmp.$$"
  printf '%s\n' "$value" > "$tmp"
  mv -f -- "$tmp" "$path"
}

QUERY_LOCK_HELD=0

release_query_lock() {
  if [ "$QUERY_LOCK_HELD" -eq 1 ]; then
    flock -u 9 2>/dev/null || true
    exec 9>&-
    QUERY_LOCK_HELD=0
  fi
}

claim_query_lock() {
  if ! command -v flock >/dev/null 2>&1; then
    echo "flock (util-linux) is required to reconcile remote run state." >&2
    return 2
  fi
  if ! exec 9>"$SESSION_LOCK_FILE"; then
    return 2
  fi
  if flock -n 9; then
    QUERY_LOCK_HELD=1
    return 0
  fi
  exec 9>&-
  return 1
}

refresh_bootstrap() {
  BOOTSTRAP_ALIVE=0
  bootstrap_pid="$(read_value "$RUN_DIR/bootstrap_pid")"
  if [[ "$bootstrap_pid" =~ ^[0-9]+$ ]] &&
     kill -0 "$bootstrap_pid" 2>/dev/null; then
    BOOTSTRAP_ALIVE=1
  fi
}

STATUS="$(read_value "$RUN_DIR/status")"
refresh_bootstrap

if { [ "$STATUS" = "provisioning" ] ||
     [ "$STATUS" = "starting" ] ||
     [ "$STATUS" = "running" ]; } &&
   [ "$TMUX_ALIVE" -eq 0 ]; then
  # Never derive a crash from the snapshot above while a launcher may be
  # publishing or handing the run to tmux.  The launcher owns this same lock
  # until tmux exists and the complete initial state has been published.
  if claim_query_lock; then
    STATUS="$(read_value "$RUN_DIR/status")"
    refresh_tmux
    refresh_bootstrap
    if { [ "$STATUS" = "provisioning" ] ||
         [ "$STATUS" = "starting" ] ||
         [ "$STATUS" = "running" ]; } &&
       [ "$TMUX_ALIVE" -eq 0 ]; then
      if [ "$STATUS" = "provisioning" ]; then
        write_value "$RUN_DIR/exit_code" "125"
        write_value "$RUN_DIR/reason" "remote provisioning process disappeared before tmux startup"
      else
        write_value "$RUN_DIR/exit_code" "255"
        write_value "$RUN_DIR/reason" "tmux session disappeared before the process recorded its exit"
      fi
      write_value "$RUN_DIR/finished_at" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      write_value "$RUN_DIR/status" "failed"
      STATUS="failed"
    fi
    release_query_lock
  else
    query_lock_rc=$?
    if [ "$query_lock_rc" -eq 2 ]; then
      exit 69
    fi
    # A concurrent launcher owns the lock.  Refresh only for display and let
    # a later query decide once the atomic handoff is complete.
    STATUS="$(read_value "$RUN_DIR/status")"
    refresh_tmux
    refresh_bootstrap
  fi
fi

RSYNC_AVAILABLE=0
command -v rsync >/dev/null 2>&1 && RSYNC_AVAILABLE=1

printf 'protocol=1\n'
printf 'exists=1\n'
printf 'session=%s\n' "$SESSION"
printf 'run_id=%s\n' "$(read_value "$RUN_DIR/run_id")"
printf 'status=%s\n' "$STATUS"
printf 'tmux=%s\n' "$TMUX_ALIVE"
printf 'bootstrap=%s\n' "$BOOTSTRAP_ALIVE"
printf 'mode=%s\n' "$(read_value "$RUN_DIR/mode")"
printf 'exit_code=%s\n' "$(read_value "$RUN_DIR/exit_code")"
printf 'reason=%s\n' "$(read_value "$RUN_DIR/reason")"
printf 'created_at=%s\n' "$(read_value "$RUN_DIR/created_at")"
printf 'started_at=%s\n' "$(read_value "$RUN_DIR/started_at")"
printf 'finished_at=%s\n' "$(read_value "$RUN_DIR/finished_at")"
printf 'run_dir=%s\n' "$RUN_DIR"
printf 'results_dir=%s\n' "$RUN_DIR/results"
printf 'log_path=%s\n' "$RUN_DIR/run.log"
printf 'rsync=%s\n' "$RSYNC_AVAILABLE"
"""


REMOTE_LAUNCH_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail
umask 077

MODE="${1:-}"
SESSION="${2:-}"
NEED_RSYNC="${3:-0}"
RESTART="${4:-0}"
RESUME="${5:-0}"
shift 5
LIDAR_ARGS=("$@")

if [ "$MODE" != "source" ] && [ "$MODE" != "bundle" ]; then
  echo "Invalid mode: $MODE" >&2
  exit 64
fi
if [[ ! "$SESSION" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]]; then
  echo "Invalid tmux session: $SESSION" >&2
  exit 64
fi
if [ "${#LIDAR_ARGS[@]}" -eq 0 ]; then
  echo "No lidar2map arguments were provided." >&2
  exit 64
fi
for arg in "${LIDAR_ARGS[@]}"; do
  case "$arg" in
    --output-dir|--output-dir=*|--dossier|--dossier=*)
      echo "rlidar2map_CLI reserves --output-dir/--dossier for synchronized results." >&2
      exit 64
      ;;
  esac
done

BASE="$HOME/.lidar2map-runs"
RUN_DIR="$BASE/$SESSION"
ARCHIVE_DIR="$BASE/archive"
LOCK_FILE="$BASE/.provision.flock"
SESSION_LOCK_FILE="$BASE/.session-${SESSION}.flock"
mkdir -p -- "$BASE"
if ! command -v flock >/dev/null 2>&1; then
  echo "flock (from util-linux) is required on the VM." >&2
  exit 69
fi

SESSION_LOCK_HELD=0
INIT_DIR=""

write_value() {
  local path="$1"
  local value="$2"
  local tmp="${path}.tmp.$$"
  printf '%s\n' "$value" > "$tmp"
  mv -f -- "$tmp" "$path"
}

release_session_lock() {
  if [ "$SESSION_LOCK_HELD" -eq 1 ]; then
    flock -u 9 2>/dev/null || true
    exec 9>&-
    SESSION_LOCK_HELD=0
  fi
}

acquire_session_lock() {
  exec 9>"$SESSION_LOCK_FILE"
  if ! flock -n 9; then
    echo "Waiting for another launcher of session '$SESSION'..."
    if ! flock -w 600 9; then
      echo "Timed out waiting for session lock '$SESSION'." >&2
      exec 9>&-
      return 1
    fi
  fi
  SESSION_LOCK_HELD=1
}

cleanup_initial_state() {
  if [ -n "$INIT_DIR" ]; then
    case "$INIT_DIR" in
      "$BASE"/.init-"$SESSION"-*)
        rm -rf -- "$INIT_DIR" 2>/dev/null || true
        ;;
    esac
  fi
}

on_early_exit() {
  local rc=$?
  trap - EXIT HUP INT TERM
  cleanup_initial_state
  release_session_lock
  exit "$rc"
}

trap on_early_exit EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
acquire_session_lock

TMUX_ALIVE=0
if command -v tmux >/dev/null 2>&1 && tmux has-session -t "=$SESSION" 2>/dev/null; then
  TMUX_ALIVE=1
fi
if [ "$TMUX_ALIVE" -eq 1 ]; then
  if [ -d "$RUN_DIR" ] && [ "$RESTART" != "1" ] && [ "$RESUME" != "1" ]; then
    echo "Managed run '$SESSION' was started concurrently; attaching to it."
    exit 0
  fi
  echo "An unmanaged or active tmux session named '$SESSION' already exists." >&2
  exit 3
fi

if [ -d "$RUN_DIR" ]; then
  if [ "$RESTART" = "1" ]; then
    mkdir -p -- "$ARCHIVE_DIR"
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    archive_target="$ARCHIVE_DIR/${SESSION}-${stamp}"
    suffix=0
    while [ -e "$archive_target" ]; do
      suffix=$((suffix + 1))
      archive_target="$ARCHIVE_DIR/${SESSION}-${stamp}-${suffix}"
    done
    mv -- "$RUN_DIR" "$archive_target"
    echo "Archived previous run in $archive_target"
  elif [ "$RESUME" = "1" ]; then
    # Reprise en place : contrairement à --restart, RUN_DIR (donc
    # results/, avec les dalles déjà téléchargées) n'est PAS déplacé.
    # Seule la comptabilité du run est réinitialisée ; le bootstrap
    # neuf ci-dessous est sauté (cf. `if [ ! -d "$RUN_DIR" ]`) puisque
    # RUN_DIR existe encore. lidar2map.py retélécharge alors uniquement
    # les dalles manquantes/en erreur (cache par dalle + manifeste).
    echo "Resuming '$SESSION' in place (cached tiles kept)."
    mkdir -p -- "$RUN_DIR/results"
    rm -f -- "$RUN_DIR/exit_code" "$RUN_DIR/app_exit_code" \
            "$RUN_DIR/tee_exit_code" "$RUN_DIR/finished_at"
    : > "$RUN_DIR/reason"
    # run_id INCHANGÉ (contrairement à --restart) : c'est toujours logiquement
    # le même run qui continue, pas un nouveau. Ça évite qu'un client local
    # (--remote-cli) resynchronise les dalles déjà en cache dans un DEUXIÈME
    # dossier local (vu que local_run_dir() dérive le chemin du run_id), et ça
    # reste cohérent avec la détection de changement de run côté sync/purge
    # (expected_run_id, cf. REMOTE_FILE_SYNC_HELPER) : rien n'a changé d'identité.
    RUN_ID="$(cat -- "$RUN_DIR/run_id")"
    write_value "$RUN_DIR/bootstrap_pid" "$$"
    write_value "$RUN_DIR/status" "provisioning"
  else
    echo "Run '$SESSION' already has persistent state; it will not be relaunched."
    exit 0
  fi
fi

if [ ! -d "$RUN_DIR" ]; then
  RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  INIT_DIR="$BASE/.init-${SESSION}-${RUN_ID}"
  mkdir -- "$INIT_DIR"
  mkdir -- "$INIT_DIR/results"
  write_value "$INIT_DIR/run_id" "$RUN_ID"
  write_value "$INIT_DIR/mode" "$MODE"
  write_value "$INIT_DIR/created_at" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  write_value "$INIT_DIR/bootstrap_pid" "$$"
  : > "$INIT_DIR/reason"
  write_value "$INIT_DIR/status" "provisioning"
  mv -- "$INIT_DIR" "$RUN_DIR"
  INIT_DIR=""
fi

LOCK_HELD=0
HANDOFF=0

release_lock() {
  if [ "$LOCK_HELD" -eq 1 ]; then
    flock -u 8 2>/dev/null || true
    exec 8>&-
    LOCK_HELD=0
  fi
}

on_bootstrap_exit() {
  local rc=$?
  trap - EXIT HUP INT TERM
  release_lock
  release_session_lock
  if [ "$HANDOFF" -eq 0 ]; then
    [ "$rc" -eq 0 ] && rc=125
    rm -f -- "$RUN_DIR/bootstrap_pid" 2>/dev/null || true
    write_value "$RUN_DIR/exit_code" "$rc"
    write_value "$RUN_DIR/reason" "remote provisioning or tmux startup failed (exit $rc)"
    write_value "$RUN_DIR/finished_at" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    write_value "$RUN_DIR/status" "failed"
  fi
  exit "$rc"
}
trap on_bootstrap_exit EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

acquire_lock() {
  exec 8>"$LOCK_FILE"
  if ! flock -n 8; then
    echo "Waiting for another VM provisioning step..."
    if ! flock -w 600 8; then
      echo "Timed out waiting for the provisioning lock." >&2
      exec 8>&-
      return 1
    fi
  fi
  LOCK_HELD=1
}

acquire_lock

SUDO=()
if [ "$(id -u)" -ne 0 ]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required to install missing VM packages." >&2
    exit 1
  fi
  SUDO=(sudo)
fi

packages=(tmux)
need_packages=0
command -v tmux >/dev/null 2>&1 || need_packages=1
if [ "$MODE" = "bundle" ]; then
  packages+=(curl)
  command -v curl >/dev/null 2>&1 || need_packages=1
else
  packages+=(git python3 python3-venv)
  command -v git >/dev/null 2>&1 || need_packages=1
  command -v python3 >/dev/null 2>&1 || need_packages=1
  if command -v python3 >/dev/null 2>&1 &&
     ! python3 -c "import ensurepip" >/dev/null 2>&1; then
    need_packages=1
  fi
fi
if [ "$NEED_RSYNC" = "1" ]; then
  packages+=(rsync)
  command -v rsync >/dev/null 2>&1 || need_packages=1
fi

if [ "$need_packages" -eq 1 ]; then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "Missing dependencies and apt-get is unavailable on this VM." >&2
    exit 1
  fi
  echo "Installing VM prerequisites: ${packages[*]}"
  "${SUDO[@]}" apt-get update -qq
  "${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive \
    apt-get install -y -qq "${packages[@]}"
fi

ensure_swap() {
  # Cloud Ubuntu images ship with 0 swap. Large shading chunks (SVF,
  # openness) can exceed RAM and trigger the OOM killer instead of just
  # slowing down. Size a dedicated swapfile to match RAM as a safety net.
  local ram_kb swap_kb target_mb swapfile avail_kb need_kb existing_kb
  ram_kb=$(awk '/^MemTotal:/{print $2}' /proc/meminfo)
  swap_kb=$(awk '/^SwapTotal:/{print $2}' /proc/meminfo)
  if [ "$swap_kb" -ge "$ram_kb" ]; then
    return
  fi
  swapfile="/swapfile_lidar2map"
  target_mb=$(( (ram_kb + 1023) / 1024 ))
  existing_kb=0
  [ -f "$swapfile" ] && existing_kb=$(du -k "$swapfile" 2>/dev/null | cut -f1)
  need_kb=$(( target_mb * 1024 - existing_kb ))
  avail_kb=$(df --output=avail -k / | tail -n1)
  if [ "$avail_kb" -lt $(( need_kb + 2097152 )) ]; then
    echo "Not enough free disk to size swap to ${target_mb}M, skipping." >&2
    return
  fi
  echo "Sizing swap to ${target_mb}M (was $((swap_kb / 1024))M) to avoid OOM kills on large shading chunks..."
  if [ -f "$swapfile" ] && swapon --show=NAME --noheadings 2>/dev/null | grep -qx "$swapfile"; then
    "${SUDO[@]}" swapoff "$swapfile"
  fi
  "${SUDO[@]}" fallocate -l "${target_mb}M" "$swapfile" 2>/dev/null ||
    "${SUDO[@]}" dd if=/dev/zero of="$swapfile" bs=1M count="$target_mb" status=none
  "${SUDO[@]}" chmod 600 "$swapfile"
  "${SUDO[@]}" mkswap "$swapfile" >/dev/null
  "${SUDO[@]}" swapon "$swapfile"
  grep -q "^$swapfile " /etc/fstab 2>/dev/null ||
    echo "$swapfile none swap sw 0 0" | "${SUDO[@]}" tee -a /etc/fstab >/dev/null
  echo "Swap ready: ${target_mb}M active at $swapfile"
}
ensure_swap

RESULTS="$RUN_DIR/results"
COMMAND=()
if [ "$MODE" = "bundle" ]; then
  URL="https://github.com/nico579/lidar2map/releases/latest/download/lidar2map-linux-x86_64.tar.gz"
  BIN="$HOME/lidar2map-linux-x86_64/lidar2map"
  if [ ! -x "$BIN" ]; then
    echo "Downloading the lidar2map bundle (~380 MB)..."
    archive="$RUN_DIR/lidar2map-bundle.tgz"
    curl -fsSL -o "$archive" "$URL"
    tar xzf "$archive" -C "$HOME"
    rm -f -- "$archive"
    chmod +x "$BIN"
  fi
  "$BIN" --version
  COMMAND=("$BIN")
else
  REPO="https://github.com/nico579/lidar2map.git"
  DIR="$HOME/lidar2map"
  if [ ! -d "$DIR/.git" ]; then
    echo "Cloning lidar2map..."
    git clone "$REPO" "$DIR"
  else
    active_source=0
    for status_path in "$BASE"/*/status; do
      [ -e "$status_path" ] || continue
      other_dir="${status_path%/status}"
      [ "$other_dir" = "$RUN_DIR" ] && continue
      other_mode=""
      other_status=""
      IFS= read -r other_mode < "$other_dir/mode" 2>/dev/null || true
      IFS= read -r other_status < "$status_path" 2>/dev/null || true
      other_session="${other_dir##*/}"
      if [ "$other_mode" = "source" ] &&
         { [ "$other_status" = "starting" ] || [ "$other_status" = "running" ]; } &&
         tmux has-session -t "=$other_session" 2>/dev/null; then
        active_source=1
        break
      fi
    done
    if [ "$active_source" -eq 1 ]; then
      echo "A source run is active; keeping its checked-out revision."
    else
      echo "Updating the shared lidar2map source checkout..."
      git -C "$DIR" pull --ff-only
    fi
  fi

  venv="$HOME/.lidar2map/venv"
  if [ -d "$venv" ] &&
     ! "$venv/bin/python3" -m pip --version >/dev/null 2>&1; then
    echo "Removing an incomplete lidar2map virtual environment..."
    rm -rf -- "$venv"
  fi
  echo "Bootstrapping lidar2map dependencies when needed..."
  (cd "$DIR" && python3 lidar2map.py --version)
  COMMAND=(python3 "$DIR/lidar2map.py")
fi

COMMAND+=("${LIDAR_ARGS[@]}" --output-dir "$RESULTS")
RUNNER="$RUN_DIR/runner.sh"
{
  printf '%s\n' '#!/usr/bin/env bash'
  printf '%s\n' 'set -uo pipefail'
  declare -p COMMAND
  cat <<'RUNNER_BODY'
RUN_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
STATUS="$RUN_DIR/status"
LOG="$RUN_DIR/run.log"
APP_RC=""
TEE_RC=""

write_value() {
  local path="$1"
  local value="$2"
  local tmp="${path}.tmp.$$"
  printf '%s\n' "$value" > "$tmp"
  mv -f -- "$tmp" "$path"
}

finish_run() {
  local rc=$?
  trap - EXIT HUP INT TERM
  write_value "$RUN_DIR/finished_at" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [ -n "$APP_RC" ] && [ -n "$TEE_RC" ]; then
    write_value "$RUN_DIR/app_exit_code" "$APP_RC"
    write_value "$RUN_DIR/tee_exit_code" "$TEE_RC"
  fi
  if [ -n "$APP_RC" ] && [ "$APP_RC" -ne 0 ]; then
    write_value "$RUN_DIR/exit_code" "$APP_RC"
    write_value "$RUN_DIR/reason" "lidar2map exited with code $APP_RC"
    write_value "$STATUS" "failed"
  elif [ -n "$TEE_RC" ] && [ "$TEE_RC" -ne 0 ]; then
    write_value "$RUN_DIR/exit_code" "74"
    write_value "$RUN_DIR/reason" "lidar2map succeeded but writing run.log failed (tee exit $TEE_RC)"
    write_value "$STATUS" "failed"
  elif [ "$rc" -eq 0 ]; then
    write_value "$RUN_DIR/exit_code" "0"
    : > "$RUN_DIR/reason"
    write_value "$STATUS" "succeeded"
  else
    write_value "$RUN_DIR/exit_code" "$rc"
    write_value "$RUN_DIR/reason" "lidar2map exited with code $rc"
    write_value "$STATUS" "failed"
  fi
  exit "$rc"
}

trap finish_run EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

write_value "$RUN_DIR/started_at" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
write_value "$STATUS" "running"
set +e
"${COMMAND[@]}" 2>&1 | tee -a -- "$LOG"
pipeline_status=("${PIPESTATUS[@]}")
APP_RC="${pipeline_status[0]}"
TEE_RC="${pipeline_status[1]:-1}"
if [ "$APP_RC" -ne 0 ]; then
  exit "$APP_RC"
fi
if [ "$TEE_RC" -ne 0 ]; then
  exit 74
fi
exit 0
RUNNER_BODY
} > "$RUNNER"
chmod 700 "$RUNNER"

write_value "$RUN_DIR/status" "starting"
printf -v runner_command 'exec bash %q' "$RUNNER"
if ! tmux new-session -d -s "$SESSION" -c "$HOME" "$runner_command" \
     8>&- 9>&-; then
  echo "Unable to create tmux session '$SESSION'." >&2
  exit 1
fi

HANDOFF=1
rm -f -- "$RUN_DIR/bootstrap_pid"
release_lock
release_session_lock
trap - EXIT HUP INT TERM
echo "Started run '$SESSION' (id $RUN_ID) in tmux."
echo "Remote results: $RESULTS"
"""


REMOTE_PURGE_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail
umask 077

SESSION="${1:-}"
EXPECTED_RUN_ID="${2:-}"
if [[ ! "$SESSION" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]]; then
  echo "Invalid session." >&2
  exit 64
fi
if [[ ! "$EXPECTED_RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$ ]]; then
  echo "Invalid run id." >&2
  exit 64
fi

BASE="$HOME/.lidar2map-runs"
RUN_DIR="$BASE/$SESSION"
LOCK_FILE="$BASE/.session-${SESSION}.flock"
RECEIPT_DIR="$BASE/.purged"
RECEIPT="$RECEIPT_DIR/${SESSION}-${EXPECTED_RUN_ID}"
PURGING_DIR="$BASE/.purging-${SESSION}-${EXPECTED_RUN_ID}"
mkdir -p -- "$BASE"

if ! command -v flock >/dev/null 2>&1; then
  echo "flock (from util-linux) is required on the VM." >&2
  exit 69
fi

read_value() {
  local path="$1"
  local value=""
  if [ -r "$path" ]; then
    IFS= read -r value < "$path" || true
  fi
  printf '%s' "$value"
}

write_value() {
  local path="$1"
  local value="$2"
  local tmp="${path}.tmp.$$"
  printf '%s\n' "$value" > "$tmp"
  mv -f -- "$tmp" "$path"
}

emit_result() {
  local already="$1"
  printf 'protocol=1\n'
  printf 'purged=1\n'
  printf 'already_purged=%s\n' "$already"
  printf 'session=%s\n' "$SESSION"
  printf 'run_id=%s\n' "$EXPECTED_RUN_ID"
}

exec 9>>"$LOCK_FILE"
if ! flock -w 60 9; then
  echo "Session state is busy; purge refused." >&2
  exit 75
fi

if [ -L "$RECEIPT_DIR" ]; then
  echo "Unsafe purge receipt directory." >&2
  exit 65
fi
mkdir -p -- "$RECEIPT_DIR"
receipt_state="$(read_value "$RECEIPT")"
if [ "$receipt_state" = "purged" ]; then
  emit_result 1
  exit 0
fi

if command -v tmux >/dev/null 2>&1 &&
   tmux has-session -t "=$SESSION" 2>/dev/null; then
  echo "The tmux session is still active; purge refused." >&2
  exit 76
fi

already=0
if [ -e "$PURGING_DIR" ] || [ -L "$PURGING_DIR" ]; then
  already=1
  if [ -L "$PURGING_DIR" ] || [ ! -d "$PURGING_DIR" ]; then
    echo "Unsafe staged purge directory." >&2
    exit 65
  fi
  if [ "$(read_value "$PURGING_DIR/run_id")" != "$EXPECTED_RUN_ID" ] &&
     [ "$receipt_state" != "purging" ]; then
    echo "Staged purge run id mismatch." >&2
    exit 77
  fi
elif [ -e "$RUN_DIR" ] || [ -L "$RUN_DIR" ]; then
  if [ -L "$RUN_DIR" ] || [ ! -d "$RUN_DIR" ]; then
    echo "Unsafe remote run directory." >&2
    exit 65
  fi
  actual_run_id="$(read_value "$RUN_DIR/run_id")"
  status="$(read_value "$RUN_DIR/status")"
  if [ "$actual_run_id" != "$EXPECTED_RUN_ID" ]; then
    echo "Remote run id changed; purge refused." >&2
    exit 78
  fi
  if [ "$status" != "succeeded" ] && [ "$status" != "failed" ]; then
    echo "Remote run is not terminal; purge refused." >&2
    exit 76
  fi
  mv -- "$RUN_DIR" "$PURGING_DIR"
  write_value "$RECEIPT" "purging"
elif [ "$receipt_state" = "purging" ]; then
  # The previous request removed the staged tree but lost its SSH response
  # before publishing the final receipt.
  write_value "$RECEIPT" "purged"
  emit_result 1
  exit 0
else
  echo "Remote run does not exist and no purge receipt matches it." >&2
  exit 66
fi

if ! rm -rf --one-file-system -- "$PURGING_DIR"; then
  echo "Unable to remove the staged remote run." >&2
  exit 74
fi
if [ -e "$PURGING_DIR" ] || [ -L "$PURGING_DIR" ]; then
  echo "Unable to remove the staged remote run." >&2
  exit 74
fi
write_value "$RECEIPT" "purged"
emit_result "$already"
"""


REMOTE_FILE_SYNC_HELPER = r"""
import base64
import fcntl
import hashlib
import json
import os
import re
import stat
import struct
import sys
import time

MAGIC = b"L2M-FILE-STREAM-1\n"
SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")

action, session, expected_run_id = sys.argv[1:4]
if (
    action not in ("inventory", "copy")
    or not SESSION_RE.fullmatch(session)
    or not RUN_ID_RE.fullmatch(expected_run_id)
):
    raise SystemExit(64)

base = os.path.join(os.path.expanduser("~"), ".lidar2map-runs")
run_dir = os.path.join(base, session)
results_dir = os.path.join(run_dir, "results")
lock_path = os.path.join(base, ".session-{}.flock".format(session))
lock_stream = open(lock_path, "a+b")
fcntl.flock(lock_stream.fileno(), fcntl.LOCK_SH)

def read_value(path):
    with open(path, "r", encoding="utf-8") as stream:
        return stream.readline().rstrip("\r\n")

if (
    not os.path.isdir(run_dir)
    or read_value(os.path.join(run_dir, "run_id")) != expected_run_id
    or not os.path.isdir(results_dir)
):
    raise SystemExit(77)

def fingerprint(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]

def ignored_name(name):
    return name.endswith(
        (".part", ".part-wal", ".part-shm", ".part-journal")
    )

def inventory():
    files = []
    for directory, directory_names, file_names in os.walk(
        results_dir, followlinks=False
    ):
        directory_names[:] = [
            name
            for name in directory_names
            if not ignored_name(name)
            and not os.path.islink(os.path.join(directory, name))
        ]
        for name in file_names:
            if ignored_name(name):
                continue
            full_path = os.path.join(directory, name)
            try:
                info = os.lstat(full_path)
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode):
                continue
            relative = os.path.relpath(full_path, results_dir)
            raw_relative = os.fsencode(relative).replace(os.sep.encode(), b"/")
            files.append(
                {
                    "path": base64.b64encode(raw_relative).decode("ascii"),
                    "fingerprint": fingerprint(info),
                }
            )
    files.sort(key=lambda item: item["path"])
    payload = {
        "protocol": 1,
        "run_id": expected_run_id,
        "now_ns": time.time_ns(),
        "files": files,
    }
    sys.stdout.buffer.write(
        json.dumps(payload, separators=(",", ":")).encode("ascii")
    )

def decode_relative(encoded):
    raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    components = raw.split(b"/")
    if (
        not raw
        or raw.startswith(b"/")
        or b"\0" in raw
        or any(component in (b"", b".", b"..") for component in components)
    ):
        raise ValueError("unsafe relative path")
    return raw

def write_frame(payload):
    encoded = json.dumps(payload, separators=(",", ":")).encode("ascii")
    sys.stdout.buffer.write(struct.pack(">Q", len(encoded)))
    sys.stdout.buffer.write(encoded)

def copy_files():
    request_raw = sys.stdin.buffer.read(16 * 1024 * 1024 + 1)
    if len(request_raw) > 16 * 1024 * 1024:
        raise ValueError("copy request too large")
    request = json.loads(request_raw.decode("ascii"))
    requested = request.get("files")
    if request.get("protocol") != 1 or not isinstance(requested, list):
        raise ValueError("invalid copy request")
    sys.stdout.buffer.write(MAGIC)
    unstable = False
    for item in requested:
        encoded_path = item["path"]
        expected = item["fingerprint"]
        if (
            not isinstance(encoded_path, str)
            or not isinstance(expected, list)
            or len(expected) != 4
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in expected
            )
        ):
            raise ValueError("invalid requested file")
        relative = decode_relative(encoded_path)
        full_path = os.path.join(
            os.fsencode(results_dir), *relative.split(b"/")
        )
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(full_path, flags)
        except FileNotFoundError:
            # Le pipeline distant peut purger un intermediaire (VRT voisin,
            # etc.) pendant que ce sync tourne : pas fatal, ce fichier sera
            # simplement absent du prochain inventaire. Ne pas planter tout
            # le lot pour un seul fichier disparu entre l'inventaire et la
            # copie. Distinct de `unstable` (contenu modifie PENDANT la
            # lecture) : ici rien n'a ete lu, code de sortie normal (0).
            write_frame({"type": "missing", "path": encoded_path})
            continue
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or fingerprint(before) != expected
            ):
                raise RuntimeError("remote file changed before copy")
            write_frame(
                {
                    "type": "file",
                    "path": encoded_path,
                    "size": before.st_size,
                }
            )
            digest = hashlib.sha256()
            remaining = before.st_size
            while remaining:
                block = os.read(descriptor, min(1024 * 1024, remaining))
                if not block:
                    raise RuntimeError("remote file shortened during copy")
                sys.stdout.buffer.write(block)
                digest.update(block)
                remaining -= len(block)
            after = os.fstat(descriptor)
            stable = fingerprint(after) == expected
            unstable = unstable or not stable
            write_frame(
                {
                    "type": "trailer",
                    "path": encoded_path,
                    "stable": stable,
                    "sha256": digest.hexdigest(),
                }
            )
        finally:
            os.close(descriptor)
    write_frame({"type": "end", "count": len(requested)})
    sys.stdout.buffer.flush()
    if unstable:
        raise SystemExit(74)

if action == "inventory":
    inventory()
else:
    copy_files()
"""


class RunOnVmError(RuntimeError):
    """User-facing controller error."""


class SshError(RunOnVmError):
    def __init__(self, message: str, returncode: int = 255):
        super().__init__(message)
        self.returncode = returncode


class PurgeTargetChangedError(RunOnVmError):
    """The copied run is no longer the current remote run."""


@dataclass
class RuntimeDeps:
    """Replaceable process/runtime dependencies for deterministic tests."""

    ssh_prefix: Tuple[str, ...] = ("ssh",)
    scp_prefix: Tuple[str, ...] = ("scp",)
    rsync_prefix: Tuple[str, ...] = ("rsync",)
    sleep: Callable[[float], None] = time.sleep
    which: Callable[[str], Optional[str]] = shutil.which


@dataclass
class Options:
    vm: str
    lidar_args: List[str]
    mode: str
    session: str
    local_dir: Optional[Path]
    interval: float
    sync_method: str
    sync_only: str
    ssh_timeout: int
    ssh_options: List[str]
    identity: Optional[Path]
    reset_host_key: bool
    restart: bool
    resume: bool
    purge_remote: bool
    detach: bool
    once: bool
    max_ssh_errors: int
    no_bell: bool


@dataclass
class RemoteState:
    exists: bool
    tmux: bool = False
    session: str = ""
    run_id: str = ""
    status: str = "absent"
    mode: str = ""
    exit_code: Optional[int] = None
    reason: str = ""
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    run_dir: str = ""
    results_dir: str = ""
    log_path: str = ""
    rsync: bool = False

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_STATES


def _parser() -> argparse.ArgumentParser:
    if os.environ.get("LIDAR2MAP_REMOTE_MODE") == "1":
        # Délégué par lidar2map --remote-cli : refléter l'invocation réelle
        # plutôt que le nom du script interne.
        program_name = example_command = "lidar2map --remote-cli"
    else:
        frozen = getattr(sys, "frozen", False)
        program_name = "rlidar2map_CLI" if frozen else "rlidar2map_CLI.py"
        example_command = "rlidar2map_CLI" if frozen else "python tools/rlidar2map_CLI.py"
    parser = argparse.ArgumentParser(
        prog=program_name,
        add_help=False,
        description=(
            "Lance lidar2map dans tmux, surveille son état et synchronise "
            "progressivement ses résultats."
        ),
        epilog=(
            "Exemples:\n"
            f"  {example_command} --session gareoult-lrm3 root@192.0.2.10 -- "
            "--ignlidar --zone-ville gareoult --zone-width 5 --zone-nom gareoult_lrm3 "
            "--telechargement --ombrages lrm --shading lrm:sigma=3 "
            "--formats-fichier mbtiles\n"
            f"  {example_command} --session gareoult-laz root@192.0.2.10 -- --laz "
            "--ignlidar --zone-ville gareoult --zone-width 5 --telechargement "
            "--ombrages lrm --shading lrm:sigma=3 --formats-fichier mbtiles\n"
            f"  {example_command} --session gareoult-laz root@192.0.2.10\n"
            f"  {example_command} --session gareoult-laz --purge-remote "
            "root@192.0.2.10\n\n"
            "Après Ctrl-C, relancer la même session reprend la surveillance et la copie. "
            "Les arguments lidar2map doivent être placés après '--'. "
            "Chaque argument lidar2map est transmis sans réinterprétation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-h", "--help", action="help",
        help="optionnel ; affiche cette aide complète puis quitte",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--source", dest="mode", action="store_const", const="source",
        help="optionnel ; utilise le checkout source (mode par défaut)",
    )
    mode.add_argument(
        "--bundle", dest="mode", action="store_const", const="bundle",
        help="optionnel ; utilise le bundle Linux publié (désactivé par défaut)",
    )
    parser.set_defaults(mode="source")
    parser.add_argument(
        "-s", "--session", default=DEFAULT_SESSION,
        help="optionnel ; nom tmux et identifiant du run (défaut : lidar)",
    )
    parser.add_argument(
        "--local-dir", type=Path,
        help=(
            "optionnel ; racine locale (défaut : "
            "./vm-results/<hôte>/<session>/<run-id>)"
        ),
    )
    parser.add_argument(
        "--interval", type=float, default=DEFAULT_INTERVAL,
        help="optionnel ; secondes entre contrôles/synchronisations (défaut : 30)",
    )
    parser.add_argument(
        "--sync-method",
        choices=("auto", "rsync", "ssh", "scp"),
        default="auto",
        help=(
            "optionnel, défaut auto ; transport (auto préfère rsync ; ssh et "
            "scp utilisent le flux SSH incrémental)"
        ),
    )
    parser.add_argument(
        "--sync-only",
        choices=("ombrages", "carte", "tout"),
        default="tout",
        help=(
            "optionnel, défaut tout ; quels résultats rapatrier localement : "
            "ombrages (.tif intermédiaires), carte (.mbtiles/.rmap/.sqlitedb) "
            "ou tout"
        ),
    )
    parser.add_argument(
        "--ssh-timeout", type=int, default=10, metavar="SECONDES",
        help="optionnel ; délai maximal d'une commande SSH (défaut : 10)",
    )
    parser.add_argument(
        "--ssh-option", action="append", default=[], metavar="KEY=VALUE",
        help="optionnel, aucune par défaut ; option OpenSSH répétable",
    )
    parser.add_argument(
        "--identity", type=Path, metavar="FICHIER",
        help="optionnel, aucune par défaut ; clé privée SSH (-i)",
    )
    parser.add_argument(
        "--reset-host-key", action="store_true",
        help="optionnel, désactivé par défaut ; retire l'ancienne clé known_hosts",
    )
    lifecycle = parser.add_mutually_exclusive_group()
    lifecycle.add_argument(
        "--restart", action="store_true",
        help="optionnel, désactivé par défaut ; archive puis redémarre un run terminé",
    )
    lifecycle.add_argument(
        "--resume", action="store_true",
        help=(
            "optionnel, désactivé par défaut ; relance un run terminé dans la "
            "même session SANS archiver ses résultats (dalles déjà en cache "
            "conservées, seules celles manquantes/en erreur sont retéléchargées)"
        ),
    )
    lifecycle.add_argument(
        "--purge-remote", action="store_true",
        help=(
            "optionnel, désactivé par défaut ; pour un run terminé, synchronise "
            "puis supprime son état, son log et ses résultats distants"
        ),
    )
    parser.add_argument(
        "--detach", action="store_true",
        help="optionnel, désactivé par défaut ; quitte sans surveillance continue",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="optionnel, désactivé par défaut ; un contrôle et une synchronisation",
    )
    parser.add_argument(
        "--max-ssh-errors", type=int, default=3,
        help="optionnel ; échecs SSH consécutifs tolérés (défaut : 3)",
    )
    parser.add_argument(
        "--no-bell", action="store_true",
        help="optionnel, désactivé par défaut ; coupe le bip final",
    )
    parser.add_argument(
        "vm", metavar="VM",
        help="obligatoire ; cible SSH, par exemple root@host ou alias SSH",
    )
    parser.add_argument(
        "lidar_args", nargs=argparse.REMAINDER, metavar="ARGUMENT_LIDAR2MAP",
        help=(
            "conditionnels : obligatoires pour lancer/redémarrer, absents pour "
            "reprendre ; à placer après --"
        ),
    )
    return parser


def parse_options(argv: Optional[Sequence[str]] = None) -> Options:
    parser = _parser()
    ns = parser.parse_args(argv)
    if not SESSION_RE.fullmatch(ns.session):
        parser.error(
            "--session doit respecter [A-Za-z0-9][A-Za-z0-9_.-]{0,63}"
        )
    if ns.interval <= 0:
        parser.error("--interval doit être strictement positif")
    if ns.ssh_timeout <= 0:
        parser.error("--ssh-timeout doit être strictement positif")
    if ns.max_ssh_errors <= 0:
        parser.error("--max-ssh-errors doit être strictement positif")
    if ns.detach and ns.once:
        parser.error("--detach et --once sont mutuellement exclusifs")
    if ns.purge_remote and (ns.detach or ns.once):
        parser.error("--purge-remote est incompatible avec --detach/--once")
    if (
        ns.vm.startswith("-")
        or any(ord(ch) < 32 for ch in ns.vm)
        or any(ch.isspace() for ch in ns.vm)
    ):
        parser.error("cible SSH invalide")
    for ssh_option in ns.ssh_option:
        if not ssh_option or any(ord(ch) < 32 for ch in ssh_option):
            parser.error("--ssh-option invalide")

    lidar_args = list(ns.lidar_args)
    if lidar_args and lidar_args[0] == "--":
        lidar_args.pop(0)
    if "--purge-remote" in lidar_args:
        parser.error("--purge-remote doit être placé avant la cible VM")
    if ns.purge_remote and lidar_args:
        parser.error("--purge-remote n'accepte aucun argument lidar2map")
    for arg in lidar_args:
        if (
            arg in ("--output-dir", "--dossier")
            or arg.startswith("--output-dir=")
            or arg.startswith("--dossier=")
        ):
            parser.error(
                "--output-dir/--dossier est géré par rlidar2map_CLI pour garantir "
                "la synchronisation"
            )

    return Options(
        vm=ns.vm,
        lidar_args=lidar_args,
        mode=ns.mode,
        session=ns.session,
        local_dir=ns.local_dir,
        interval=ns.interval,
        sync_method=ns.sync_method,
        sync_only=ns.sync_only,
        ssh_timeout=ns.ssh_timeout,
        ssh_options=list(ns.ssh_option),
        identity=ns.identity,
        reset_host_key=ns.reset_host_key,
        restart=ns.restart,
        resume=ns.resume,
        purge_remote=ns.purge_remote,
        detach=ns.detach,
        once=ns.once,
        max_ssh_errors=ns.max_ssh_errors,
        no_bell=ns.no_bell,
    )


def parse_state(output: str, expected_session: str) -> RemoteState:
    values: Dict[str, str] = {}
    for raw_line in output.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key] = value
    if values.get("protocol") != "1":
        raise RunOnVmError("réponse distante invalide (protocole absent)")
    exists = values.get("exists") == "1"
    state = RemoteState(exists=exists, tmux=values.get("tmux") == "1")
    if not exists:
        return state

    state.session = values.get("session", "")
    state.run_id = values.get("run_id", "")
    state.status = values.get("status", "unknown")
    state.mode = values.get("mode", "")
    state.reason = values.get("reason", "")
    state.created_at = values.get("created_at", "")
    state.started_at = values.get("started_at", "")
    state.finished_at = values.get("finished_at", "")
    state.run_dir = values.get("run_dir", "")
    state.results_dir = values.get("results_dir", "")
    state.log_path = values.get("log_path", "")
    state.rsync = values.get("rsync") == "1"
    raw_exit = values.get("exit_code", "")
    if raw_exit:
        try:
            state.exit_code = int(raw_exit)
        except ValueError as exc:
            raise RunOnVmError("code de sortie distant invalide") from exc

    if state.session != expected_session:
        raise RunOnVmError("la réponse distante ne correspond pas à la session")
    if not RUN_ID_RE.fullmatch(state.run_id):
        raise RunOnVmError("identifiant de run distant invalide")
    if state.status not in ACTIVE_STATES | TERMINAL_STATES:
        raise RunOnVmError("état distant inconnu : {}".format(state.status))
    if state.mode not in ("source", "bundle"):
        raise RunOnVmError("mode distant invalide")
    run_suffix = "/.lidar2map-runs/{}".format(expected_session)
    normalized_run = state.run_dir.replace("\\", "/").rstrip("/")
    normalized_results = state.results_dir.replace("\\", "/")
    normalized_log = state.log_path.replace("\\", "/")
    if not normalized_run.endswith(run_suffix):
        raise RunOnVmError("chemin de run distant inattendu")
    if normalized_results != normalized_run + "/results":
        raise RunOnVmError("chemin de résultats distant inattendu")
    if normalized_log != normalized_run + "/run.log":
        raise RunOnVmError("chemin de log distant invalide")
    return state


def parse_purge_response(
    output: str, expected_session: str, expected_run_id: str
) -> bool:
    values: Dict[str, str] = {}
    for raw_line in output.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key] = value
    if values.get("protocol") != "1" or values.get("purged") != "1":
        raise RunOnVmError("réponse de purge distante invalide")
    if values.get("session") != expected_session:
        raise RunOnVmError("la purge distante ne correspond pas à la session")
    if values.get("run_id") != expected_run_id:
        raise RunOnVmError("la purge distante ne correspond pas au run")
    already = values.get("already_purged")
    if already not in ("0", "1"):
        raise RunOnVmError("indicateur de purge distante invalide")
    return already == "1"


def _safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return cleaned or "vm"


_HOST_KEY_CHANGED_MARKERS = (
    b"Host key verification failed",
    b"REMOTE HOST IDENTIFICATION HAS CHANGED",
)


def _is_host_key_changed(stderr_bytes: Optional[bytes]) -> bool:
    """True si un stderr SSH signale une clé hote qui a CHANGE (pas juste
    une machine jamais vue : StrictHostKeyChecking=accept-new, deja pose
    dans _connection_options, accepte deja celle-la sans broncher). Le cas
    courant avec une VM ephemere (Hetzner...) reconstruite/reinstallee
    depuis la derniere connexion, pas une anomalie."""
    data = stderr_bytes or b""
    return any(marker in data for marker in _HOST_KEY_CHANGED_MARKERS)


class VmController:
    def __init__(self, options: Options, deps: Optional[RuntimeDeps] = None):
        self.options = options
        self.deps = deps or RuntimeDeps()
        self._warned_scp = False
        # Octets déjà affichés du journal distant, par run_id : permet un tail
        # incrémental (cf. print_remote_log_tail) sans retélécharger le fichier
        # en entier à chaque cycle de surveillance.
        self._log_offsets: Dict[str, int] = {}
        # État \r/\n reporté d'un sondage au suivant (buf, cr_buf), même
        # machine à états que _TeeLogger côté lidar2map.py : un run.log
        # distant contient les répétitions \r des barres de progression, et
        # un sondage peut couper une répétition en plein milieu.
        self._log_tail_buf: Dict[str, Tuple[str, str]] = {}

    def _connection_options(self) -> List[str]:
        result = [
            "-o", "ConnectTimeout={}".format(self.options.ssh_timeout),
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-o", "StrictHostKeyChecking=accept-new",
        ]
        if self.options.identity is not None:
            result.extend(("-i", str(self.options.identity)))
        for option in self.options.ssh_options:
            result.extend(("-o", option))
        return result

    def _ssh_command(self, remote_args: Sequence[str]) -> List[str]:
        remote_command = shlex.join(["bash", "-s", "--"] + list(remote_args))
        return (
            list(self.deps.ssh_prefix)
            + self._connection_options()
            + [self.options.vm, remote_command]
        )

    def _direct_ssh_command(
        self, remote_command: Sequence[str]
    ) -> List[str]:
        return (
            list(self.deps.ssh_prefix)
            + self._connection_options()
            + [self.options.vm, shlex.join(list(remote_command))]
        )

    def print_remote_log_tail(self, state: "RemoteState") -> None:
        """Affiche les nouvelles lignes du journal distant depuis le dernier
        sondage (tail incrémental sur `state.log_path`, pas de
        retéléchargement complet à chaque cycle : cf. le choix inverse dans
        _sync_log, qui ne copie le fichier qu'une fois le run terminal).
        Best-effort : une erreur SSH ici ne fait pas échouer le cycle de
        surveillance, elle est juste ignorée (le prochain cycle réessaiera).

        L'offset est repris depuis rlidar2map.json (log_tail_offset) au
        premier appel pour une clé donnée : sans ça, chaque reconnexion
        (nouveau process --remote-cli = self._log_offsets vide en mémoire)
        retéléchargeait et réimprimait tout le run.log distant depuis le
        début, provoquant un burst de plusieurs milliers de lignes [VM] qui
        figeait le panneau de log du GUI (bug vécu 2026-08-05).

        run.log est la capture terminal BRUTE (tmux/tee), pas le log interne
        horodaté de lidar2map.py (publié atomiquement seulement à la fin du
        run, donc pas encore lisible en cours de route) : elle contient les
        répétitions \r des barres de progression. Un splitlines() naïf les
        aurait fanées en autant de lignes [VM] distinctes (splitlines coupe
        aussi sur \r) → même barre de progression réimprimée des dizaines de
        fois dans le GUI. Même machine à états \r/\n que _TeeLogger côté
        lidar2map.py (ne garde que l'état final d'une répétition \r), état
        reporté d'un sondage au suivant dans _log_tail_buf (une répétition
        peut être coupée en plein milieu par la frontière entre deux tail)."""
        if not state.log_path:
            return
        key = state.run_id or self.options.session
        if key not in self._log_offsets:
            self._log_offsets[key] = self._load_persisted_log_offset(state)
        offset = self._log_offsets.get(key, 0)
        remote_command = ["tail", "-c", "+{}".format(offset + 1), state.log_path]
        try:
            completed = subprocess.run(
                self._direct_ssh_command(remote_command),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=self.options.ssh_timeout,
            )
        except Exception:
            return
        data = completed.stdout or b""
        if not data:
            return
        self._log_offsets[key] = offset + len(data)
        text = data.decode("utf-8", errors="replace")
        buf, cr_buf = self._log_tail_buf.get(key, ("", ""))
        lines = []
        pos = 0
        n = len(text)
        while pos < n:
            i_r = text.find("\r", pos)
            i_n = text.find("\n", pos)
            if i_r == -1 and i_n == -1:
                buf += text[pos:]
                break
            if i_n == -1 or (i_r != -1 and i_r < i_n):
                cr_buf = buf + text[pos:i_r]
                buf = ""
                pos = i_r + 1
            else:
                line = (buf + text[pos:i_n]) or cr_buf
                if line.strip():
                    lines.append(line)
                buf = ""
                cr_buf = ""
                pos = i_n + 1
        self._log_tail_buf[key] = (buf, cr_buf)
        for line in lines:
            print("  [VM] " + line, flush=True)

    def _load_persisted_log_offset(self, state: "RemoteState") -> int:
        """Relit log_tail_offset dans le rlidar2map.json local (écrit par
        _write_manifest à chaque cycle) pour reprendre le tail où le
        process --remote-cli précédent s'est arrêté, plutôt que de repartir
        de 0 à chaque reconnexion. Absent/illisible -> 0, comportement
        d'avant ce fix, jamais pire."""
        try:
            path = self.local_run_dir(state) / "rlidar2map.json"
            if not path.exists():
                return 0
            payload = self._read_json_object(path)
        except Exception:
            return 0
        raw = payload.get("log_tail_offset")
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            return raw
        return 0

    def reset_host_key(self) -> None:
        host = self.options.vm.rsplit("@", 1)[-1]
        completed = subprocess.run(["ssh-keygen", "-R", host], check=False)
        if completed.returncode not in (0, 1):
            raise RunOnVmError("impossible de supprimer l'ancienne clé SSH")

    def _auto_reset_host_key(self) -> None:
        """Appelé UNIQUEMENT après un échec SSH confirmé (_is_host_key_changed)
        avant de retenter une fois : annonce toujours l'action (rien de
        silencieux), même si elle est automatique."""
        host = self.options.vm.rsplit("@", 1)[-1]
        print(f"  SSH: host key for {host} has changed (VM rebuilt/reinstalled?) "
              f"- clearing the stale known_hosts entry and retrying once...",
              flush=True)
        self.reset_host_key()

    def query_state(self) -> RemoteState:
        completed = subprocess.run(
            self._ssh_command([self.options.session]),
            input=REMOTE_QUERY_SCRIPT.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0 and _is_host_key_changed(completed.stderr):
            self._auto_reset_host_key()
            completed = subprocess.run(
                self._ssh_command([self.options.session]),
                input=REMOTE_QUERY_SCRIPT.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace").strip()
            raise SshError(
                stderr or "connexion SSH impossible",
                returncode=completed.returncode,
            )
        output = completed.stdout.decode("utf-8", errors="replace")
        return parse_state(output, self.options.session)

    def local_rsync_available(self) -> bool:
        executable = self.deps.rsync_prefix[0]
        return self.deps.which(executable) is not None

    def launch(self) -> None:
        need_rsync = (
            self.options.sync_method == "rsync"
            or (
                self.options.sync_method == "auto"
                and self.local_rsync_available()
            )
        )
        remote_args = [
            self.options.mode,
            self.options.session,
            "1" if need_rsync else "0",
            "1" if self.options.restart else "0",
            "1" if self.options.resume else "0",
        ] + self.options.lidar_args
        completed = subprocess.run(
            self._ssh_command(remote_args),
            input=REMOTE_LAUNCH_SCRIPT.encode("utf-8"),
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0 and _is_host_key_changed(completed.stderr):
            self._auto_reset_host_key()
            completed = subprocess.run(
                self._ssh_command(remote_args),
                input=REMOTE_LAUNCH_SCRIPT.encode("utf-8"),
                stderr=subprocess.PIPE,
                check=False,
            )
        if completed.returncode != 0:
            sys.stderr.buffer.write(completed.stderr or b"")
            raise RunOnVmError(
                "le lancement distant a échoué (code {})".format(
                    completed.returncode
                )
            )

    def purge_remote(self, state: RemoteState) -> bool:
        if not state.terminal or state.tmux:
            raise RunOnVmError(
                "la purge exige un run terminal sans session tmux active"
            )
        last_error = ""
        for attempt in range(2):
            completed = subprocess.run(
                self._ssh_command(
                    [self.options.session, state.run_id]
                ),
                input=REMOTE_PURGE_SCRIPT.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if completed.returncode == 0:
                output = completed.stdout.decode("utf-8", errors="replace")
                return parse_purge_response(
                    output,
                    self.options.session,
                    state.run_id,
                )
            last_error = completed.stderr.decode(
                "utf-8", errors="replace"
            ).strip()
            if completed.returncode in (66, 78):
                raise PurgeTargetChangedError(
                    last_error
                    or "le run copié n'est plus le run distant courant"
                )
            if completed.returncode == 255 and attempt == 0:
                print(
                    "==> Réponse de purge SSH perdue ; nouvelle vérification "
                    "idempotente.",
                    file=sys.stderr,
                    flush=True,
                )
                continue
            break
        raise RunOnVmError(
            "purge distante refusée ou incomplète : {}".format(
                last_error or "échec SSH"
            )
        )

    def _base_local_dir(self) -> Path:
        if self.options.local_dir is not None:
            return self.options.local_dir.expanduser().resolve()
        target = self.options.vm.rsplit("@", 1)[-1]
        return (
            Path.cwd()
            / "vm-results"
            / _safe_component(target)
            / self.options.session
        ).resolve()

    def local_run_dir(self, state: RemoteState) -> Path:
        if not state.run_id:
            raise RunOnVmError("le run distant n'a pas d'identifiant")
        return self._base_local_dir() / state.run_id

    @contextmanager
    def _local_sync_lock(self, local_dir: Path):
        local_dir.mkdir(parents=True, exist_ok=True)
        lock_path = local_dir / ".rlidar2map-sync.lock"
        if lock_path.is_symlink():
            raise RunOnVmError("verrou local de synchronisation non sûr")
        stream = lock_path.open("a+b")
        locked = False
        try:
            if os.name == "nt":
                import msvcrt

                stream.seek(0, os.SEEK_END)
                if stream.tell() == 0:
                    stream.write(b"\0")
                    stream.flush()
                deadline = time.monotonic() + 600.0
                while True:
                    try:
                        stream.seek(0)
                        msvcrt.locking(
                            stream.fileno(), msvcrt.LK_NBLCK, 1
                        )
                        locked = True
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise RunOnVmError(
                                "une autre synchronisation locale est "
                                "bloquée depuis plus de 10 minutes"
                            )
                        time.sleep(0.2)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                locked = True
            yield
        finally:
            if locked:
                if os.name == "nt":
                    import msvcrt

                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            stream.close()

    @staticmethod
    def _atomic_write_json(path: Path, payload: Dict[str, object]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=path.name + ".tmp-",
            dir=str(path.parent),
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(
                    payload,
                    stream,
                    ensure_ascii=False,
                    indent=2,
                )
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(str(tmp_path), str(path))
        finally:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
        return path

    @staticmethod
    def _purge_marker_paths(local_dir: Path) -> Dict[str, Path]:
        return {
            "pending": local_dir / PURGE_PENDING_MARKER,
            "purged": local_dir / PURGED_MARKER,
            "superseded": local_dir / PURGE_SUPERSEDED_MARKER,
        }

    @staticmethod
    def _read_json_object(path: Path) -> Dict[str, object]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RunOnVmError(
                "fichier d'état local invalide : {}".format(path)
            ) from exc
        if not isinstance(payload, dict):
            raise RunOnVmError(
                "fichier d'état local invalide : {}".format(path)
            )
        return payload

    def _decode_purge_record(
        self,
        path: Path,
        expected_outcome: str,
    ) -> Tuple[RemoteState, str, Dict[str, object]]:
        if path.is_symlink() or not path.is_file():
            raise RunOnVmError(
                "marqueur local de purge non sûr : {}".format(path)
            )
        payload = self._read_json_object(path)
        run_id = payload.get("run_id")
        status = payload.get("status")
        mode = payload.get("mode")
        method = payload.get("sync_method")
        if (
            payload.get("protocol") != 1
            or payload.get("vm") != self.options.vm
            or payload.get("session") != self.options.session
            or payload.get("outcome") != expected_outcome
            or payload.get("sync_pending") is not False
            or not isinstance(run_id, str)
            or not RUN_ID_RE.fullmatch(run_id)
            or path.parent.name != run_id
            or status not in TERMINAL_STATES
            or mode not in ("source", "bundle")
            or method not in ("rsync", "ssh", "scp")
        ):
            raise RunOnVmError(
                "marqueur local de purge invalide : {}".format(path)
            )
        raw_exit = payload.get("exit_code")
        if raw_exit is not None and (
            isinstance(raw_exit, bool) or not isinstance(raw_exit, int)
        ):
            raise RunOnVmError(
                "code de sortie invalide dans le marqueur de purge"
            )
        run_dir = str(payload.get("remote_run_dir") or "")
        state = RemoteState(
            exists=True,
            tmux=False,
            session=self.options.session,
            run_id=run_id,
            status=str(status),
            mode=str(mode),
            exit_code=raw_exit,
            reason=str(payload.get("reason") or ""),
            created_at=str(payload.get("created_at") or ""),
            started_at=str(payload.get("started_at") or ""),
            finished_at=str(payload.get("finished_at") or ""),
            run_dir=run_dir,
            results_dir=str(payload.get("remote_results_dir") or ""),
            log_path=str(
                payload.get("remote_log_path")
                or (run_dir.rstrip("/") + "/run.log")
            ),
        )
        return state, str(method), payload

    def _purge_marker_snapshot(
        self, local_dir: Path
    ) -> Dict[
        str,
        Tuple[RemoteState, str, Dict[str, object]],
    ]:
        records = {}
        for outcome, path in self._purge_marker_paths(local_dir).items():
            if path.exists() or path.is_symlink():
                records[outcome] = self._decode_purge_record(
                    path, outcome
                )
        return records

    def _purge_record(
        self,
        state: RemoteState,
        sync_method: str,
        outcome: str,
        *,
        superseded_reason: str = "",
    ) -> Dict[str, object]:
        return {
            "protocol": 1,
            "outcome": outcome,
            "vm": self.options.vm,
            "session": self.options.session,
            "run_id": state.run_id,
            "mode": state.mode,
            "status": state.status,
            "exit_code": state.exit_code,
            "reason": state.reason,
            "created_at": state.created_at,
            "started_at": state.started_at,
            "finished_at": state.finished_at,
            "remote_run_dir": state.run_dir,
            "remote_results_dir": state.results_dir,
            "remote_log_path": state.log_path,
            "sync_method": sync_method,
            "sync_pending": False,
            "superseded_reason": superseded_reason,
            "recorded_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            ),
        }

    def _write_manifest(
        self,
        state: RemoteState,
        sync_method: str,
        sync_pending: bool,
    ) -> Path:
        local_dir = self.local_run_dir(state)
        local_dir.mkdir(parents=True, exist_ok=True)
        path = local_dir / "rlidar2map.json"
        for _attempt in range(4):
            records = self._purge_marker_snapshot(local_dir)
            effective_state = state
            effective_method = sync_method
            effective_sync_pending = sync_pending
            record: Dict[str, object] = {}
            for outcome in ("purged", "superseded", "pending"):
                if outcome in records:
                    effective_state, effective_method, record = records[
                        outcome
                    ]
                    effective_sync_pending = False
                    break
            remote_purged = "purged" in records
            remote_superseded = (
                not remote_purged and "superseded" in records
            )
            remote_pending = (
                not remote_purged
                and not remote_superseded
                and "pending" in records
            )
            manifest: Dict[str, object] = {
                "protocol": 1,
                "vm": self.options.vm,
                "session": self.options.session,
                "run_id": effective_state.run_id,
                "mode": effective_state.mode,
                "status": effective_state.status,
                "exit_code": effective_state.exit_code,
                "reason": effective_state.reason,
                "created_at": effective_state.created_at,
                "started_at": effective_state.started_at,
                "finished_at": effective_state.finished_at,
                "remote_run_dir": effective_state.run_dir,
                "remote_results_dir": effective_state.results_dir,
                "remote_log_path": effective_state.log_path,
                # Reprise du tail [VM] entre deux process --remote-cli (cf.
                # print_remote_log_tail / _load_persisted_log_offset) : sans
                # ce champ, une reconnexion repart de l'octet 0 du run.log
                # distant et fige le panneau de log du GUI (bug 2026-08-05).
                "log_tail_offset": self._log_offsets.get(
                    effective_state.run_id or self.options.session, 0),
                "sync_method": effective_method,
                "sync_pending": effective_sync_pending,
                "remote_purged": remote_purged,
                "remote_purge_pending": remote_pending,
                "remote_purge_superseded": remote_superseded,
                "remote_purged_at": (
                    str(record.get("recorded_at") or "")
                    if remote_purged
                    else ""
                ),
                "remote_purge_superseded_at": (
                    str(record.get("recorded_at") or "")
                    if remote_superseded
                    else ""
                ),
                "remote_purge_superseded_reason": (
                    str(record.get("superseded_reason") or "")
                    if remote_superseded
                    else ""
                ),
                "updated_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                ),
            }
            self._atomic_write_json(path, manifest)
            if self._purge_marker_snapshot(local_dir) == records:
                return path
        return path

    def mark_remote_purged(
        self, state: RemoteState, sync_method: str
    ) -> Path:
        local_dir = self.local_run_dir(state)
        marker = self._purge_marker_paths(local_dir)["purged"]
        self._atomic_write_json(
            marker,
            self._purge_record(state, sync_method, "purged"),
        )
        return self._write_manifest(
            state,
            sync_method,
            sync_pending=False,
        )

    def mark_remote_purge_pending(
        self, state: RemoteState, sync_method: str
    ) -> Path:
        local_dir = self.local_run_dir(state)
        marker = self._purge_marker_paths(local_dir)["pending"]
        self._atomic_write_json(
            marker,
            self._purge_record(state, sync_method, "pending"),
        )
        return self._write_manifest(
            state,
            sync_method,
            sync_pending=False,
        )

    def mark_remote_purge_superseded(
        self,
        state: RemoteState,
        sync_method: str,
        reason: str,
    ) -> Path:
        local_dir = self.local_run_dir(state)
        marker = self._purge_marker_paths(local_dir)["superseded"]
        self._atomic_write_json(
            marker,
            self._purge_record(
                state,
                sync_method,
                "superseded",
                superseded_reason=reason,
            ),
        )
        return self._write_manifest(
            state,
            sync_method,
            sync_pending=False,
        )

    def load_remote_purge_pending(
        self,
    ) -> Optional[Tuple[RemoteState, str]]:
        base = self._base_local_dir()
        if not base.is_dir():
            return None
        candidates: List[Tuple[RemoteState, str]] = []
        for pending_path in base.glob("*/{}".format(PURGE_PENDING_MARKER)):
            local_dir = pending_path.parent
            paths = self._purge_marker_paths(local_dir)
            if (
                paths["purged"].exists()
                or paths["purged"].is_symlink()
                or paths["superseded"].exists()
                or paths["superseded"].is_symlink()
            ):
                continue
            pending_state, method, _payload = self._decode_purge_record(
                pending_path, "pending"
            )
            candidates.append((pending_state, method))
        if len(candidates) > 1:
            raise RunOnVmError(
                "plusieurs purges locales sont en attente pour cette session"
            )
        return candidates[0] if candidates else None

    def load_remote_purged(
        self,
    ) -> Optional[Tuple[RemoteState, str]]:
        base = self._base_local_dir()
        if not base.is_dir():
            return None
        candidates = []
        for marker in base.glob("*/{}".format(PURGED_MARKER)):
            purged_state, method, payload = self._decode_purge_record(
                marker, "purged"
            )
            candidates.append(
                (
                    str(payload.get("recorded_at") or ""),
                    purged_state,
                    method,
                )
            )
        if not candidates:
            return None
        _recorded_at, state, method = max(
            candidates, key=lambda item: item[0]
        )
        return state, method

    def _sync_method(self, state: RemoteState) -> str:
        local_rsync = self.local_rsync_available()
        if self.options.sync_method == "rsync":
            if not local_rsync:
                raise RunOnVmError("rsync demandé mais introuvable en local")
            if not state.rsync:
                raise RunOnVmError("rsync demandé mais introuvable sur la VM")
            return "rsync"
        if self.options.sync_method in ("ssh", "scp"):
            return "ssh"
        if local_rsync and state.rsync:
            return "rsync"
        if not self._warned_scp:
            print(
                "==> rsync indisponible : repli sur le transfert SSH "
                "incrémental (fichiers stables uniquement).",
                file=sys.stderr,
                flush=True,
            )
            self._warned_scp = True
        return "ssh"

    def _rsync_ssh_shell(self) -> str:
        return shlex.join(
            list(self.deps.ssh_prefix) + self._connection_options()
        )

    def _sync_only_excludes(self) -> Tuple[str, ...]:
        """Extensions à exclure du rapatriement : ALWAYS_EXCLUDED_EXTENSIONS
        (intermédiaires jamais utiles, quel que soit --sync-only) + les
        catégories non demandées par --sync-only (cf. SYNC_ONLY_EXTENSIONS).
        "tout" (défaut) -> seul le premier groupe s'applique."""
        excluded: List[str] = list(ALWAYS_EXCLUDED_EXTENSIONS)
        wanted = self.options.sync_only
        if wanted != "tout":
            for categorie, extensions in SYNC_ONLY_EXTENSIONS.items():
                if categorie != wanted:
                    excluded.extend(extensions)
        return tuple(excluded)

    def _sync_results_rsync(
        self, state: RemoteState, local_results: Path
    ) -> bool:
        remote = "{}:{}/".format(self.options.vm, state.results_dir)
        command = list(self.deps.rsync_prefix) + [
            "-a",
            "--partial-dir=.rlidar2map-rsync-partial",
            "--protect-args",
            "--itemize-changes",
            "--exclude=*.part",
            "--exclude=*.part-wal",
            "--exclude=*.part-shm",
            "--exclude=*.part-journal",
        ] + [
            "--exclude=*{}".format(ext) for ext in self._sync_only_excludes()
        ] + [
            "-e",
            self._rsync_ssh_shell(),
            remote,
            "./",
        ]
        completed = subprocess.run(
            command,
            cwd=str(local_results),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        if stdout:
            print(stdout)
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace").strip()
            print(
                "==> Synchronisation rsync incomplète : {}".format(
                    stderr or "code {}".format(completed.returncode)
                ),
                file=sys.stderr,
                flush=True,
            )
            return False
        return True

    def _sync_results_scp(
        self, state: RemoteState, local_results: Path
    ) -> bool:
        local_run_dir = local_results.parent
        try:
            inventory = self._remote_results_inventory(state)
            excludes = self._sync_only_excludes()
            if excludes:
                inventory = {
                    relative: entry
                    for relative, entry in inventory.items()
                    if not relative.endswith(excludes)
                }
            observed, copied = self._load_scp_index(
                state, local_run_dir
            )
        except RunOnVmError as exc:
            print(
                "==> Inventaire SSH des résultats impossible : {}".format(
                    exc
                ),
                file=sys.stderr,
                flush=True,
            )
            return False

        selected = []
        for relative, (encoded, remote_fingerprint) in inventory.items():
            copied_record = copied.get(relative)
            destination = self._safe_local_result_path(
                local_results, relative, create_parents=False
            )
            locally_complete = (
                copied_record is not None
                and copied_record.get("fingerprint")
                == list(remote_fingerprint)
                and destination.is_file()
                and not destination.is_symlink()
                and destination.stat().st_size == remote_fingerprint[2]
            )
            if locally_complete and state.terminal:
                expected_hash = copied_record.get("sha256")
                locally_complete = (
                    isinstance(expected_hash, str)
                    and len(expected_hash) == 64
                    and self._sha256_path(destination) == expected_hash
                )
            if locally_complete:
                continue
            if state.terminal or observed.get(relative) == remote_fingerprint:
                selected.append((relative, encoded, remote_fingerprint))

        current_observed = {
            relative: fingerprint
            for relative, (_encoded, fingerprint) in inventory.items()
        }
        if not selected:
            self._write_scp_index(
                state, local_run_dir, current_observed, copied
            )
            return True

        transfer_size = sum(item[2][2] for item in selected)
        _marge = 100 * 1024 * 1024   # garde-fou : un peu de marge, pas juste l'exact
        try:
            _libre = shutil.disk_usage(local_run_dir).free
        except OSError:
            _libre = None
        if _libre is not None and _libre < transfer_size + _marge:
            print(
                "==> Espace disque local insuffisant pour la copie SSH : "
                "{:.1f} Mio requis, {:.1f} Mio libres. Copie annulée, "
                "réessai au prochain cycle de synchronisation.".format(
                    transfer_size / (1024 * 1024), _libre / (1024 * 1024)
                ),
                file=sys.stderr,
                flush=True,
            )
            return False
        print(
            "==> Copie SSH de {} fichier(s) nouveau(x)/modifié(s), "
            "{:.1f} Mio.".format(
                len(selected), transfer_size / (1024 * 1024)
            ),
            flush=True,
        )
        transferred = self._copy_remote_result_files(
            state,
            local_results,
            selected,
        )
        if transferred is None:
            self._write_scp_index(
                state, local_run_dir, current_observed, copied
            )
            return False
        for relative, _encoded, remote_fingerprint in selected:
            if relative not in transferred:
                continue   # purgé côté distant entre inventaire et copie
            copied[relative] = {
                "fingerprint": list(remote_fingerprint),
                "sha256": transferred[relative],
            }
        self._write_scp_index(
            state, local_run_dir, current_observed, copied
        )
        return True

    @staticmethod
    def _parse_fingerprint(value: object) -> Tuple[int, int, int, int]:
        if (
            not isinstance(value, list)
            or len(value) != 4
            or any(
                isinstance(item, bool) or not isinstance(item, int)
                for item in value
            )
            or value[2] < 0
        ):
            raise RunOnVmError("empreinte de fichier distante invalide")
        return value[0], value[1], value[2], value[3]

    @staticmethod
    def _decode_result_path(encoded: object) -> str:
        if not isinstance(encoded, str):
            raise RunOnVmError("chemin de résultat distant invalide")
        try:
            raw = base64.b64decode(encoded.encode("ascii"), validate=True)
            relative = raw.decode("utf-8")
        except (UnicodeError, ValueError) as exc:
            raise RunOnVmError(
                "nom de résultat distant non portable"
            ) from exc
        pure = PurePosixPath(relative)
        if (
            not relative
            or "\\" in relative
            or pure.is_absolute()
            or any(part in ("", ".", "..") for part in pure.parts)
        ):
            raise RunOnVmError("chemin de résultat distant non sûr")
        invalid_windows = set('<>:"\\|?*')
        reserved_windows = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *{"COM{}".format(index) for index in range(1, 10)},
            *{"LPT{}".format(index) for index in range(1, 10)},
        }
        for part in pure.parts:
            stem = part.split(".", 1)[0].upper()
            if (
                part.endswith((" ", "."))
                or stem in reserved_windows
                or any(
                    ord(character) < 32
                    or character in invalid_windows
                    for character in part
                )
            ):
                raise RunOnVmError(
                    "nom de résultat incompatible avec Windows : {}".format(
                        relative
                    )
                )
        return pure.as_posix()

    def _remote_results_inventory(
        self, state: RemoteState
    ) -> Dict[str, Tuple[str, Tuple[int, int, int, int]]]:
        command = self._direct_ssh_command(
            (
                "python3",
                "-c",
                REMOTE_FILE_SYNC_HELPER,
                "inventory",
                self.options.session,
                state.run_id,
            )
        )
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.decode(
                "utf-8", errors="replace"
            ).strip()
            raise RunOnVmError(
                stderr
                or "inventaire distant en échec (code {})".format(
                    completed.returncode
                )
            )
        try:
            payload = json.loads(completed.stdout.decode("ascii"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise RunOnVmError(
                "réponse d'inventaire distante invalide"
            ) from exc
        files = payload.get("files") if isinstance(payload, dict) else None
        if (
            not isinstance(payload, dict)
            or payload.get("protocol") != 1
            or payload.get("run_id") != state.run_id
            or not isinstance(files, list)
        ):
            raise RunOnVmError("protocole d'inventaire distant invalide")
        inventory = {}
        casefolded = {}
        for item in files:
            if not isinstance(item, dict):
                raise RunOnVmError("entrée d'inventaire distante invalide")
            encoded = item.get("path")
            relative = self._decode_result_path(encoded)
            fingerprint = self._parse_fingerprint(
                item.get("fingerprint")
            )
            folded = relative.casefold()
            if relative in inventory or (
                folded in casefolded
                and casefolded[folded] != relative
            ):
                raise RunOnVmError(
                    "collision de noms de résultats : {}".format(relative)
                )
            casefolded[folded] = relative
            inventory[relative] = (str(encoded), fingerprint)
        return inventory

    def _load_scp_index(
        self,
        state: RemoteState,
        local_run_dir: Path,
    ) -> Tuple[
        Dict[str, Tuple[int, int, int, int]],
        Dict[str, Dict[str, object]],
    ]:
        path = local_run_dir / SCP_INDEX_NAME
        if not path.exists():
            return {}, {}
        if path.is_symlink() or not path.is_file():
            raise RunOnVmError("index de synchronisation local non sûr")
        payload = self._read_json_object(path)
        if (
            payload.get("protocol") != 1
            or payload.get("vm") != self.options.vm
            or payload.get("session") != self.options.session
            or payload.get("run_id") != state.run_id
            or not isinstance(payload.get("observed"), dict)
            or not isinstance(payload.get("copied"), dict)
        ):
            raise RunOnVmError("index de synchronisation local invalide")
        observed = {}
        for relative, value in payload["observed"].items():
            if (
                not isinstance(relative, str)
                or self._decode_result_path(
                    base64.b64encode(
                        relative.encode("utf-8")
                    ).decode("ascii")
                )
                != relative
            ):
                raise RunOnVmError(
                    "chemin invalide dans l'index de synchronisation"
                )
            observed[relative] = self._parse_fingerprint(value)
        copied = {}
        for relative, record in payload["copied"].items():
            if (
                not isinstance(relative, str)
                or not isinstance(record, dict)
            ):
                raise RunOnVmError(
                    "copie invalide dans l'index de synchronisation"
                )
            fingerprint = self._parse_fingerprint(
                record.get("fingerprint")
            )
            digest = record.get("sha256")
            if (
                not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
            ):
                raise RunOnVmError(
                    "hash invalide dans l'index de synchronisation"
                )
            copied[relative] = {
                "fingerprint": list(fingerprint),
                "sha256": digest,
            }
        return observed, copied

    def _write_scp_index(
        self,
        state: RemoteState,
        local_run_dir: Path,
        observed: Dict[str, Tuple[int, int, int, int]],
        copied: Dict[str, Dict[str, object]],
    ) -> Path:
        return self._atomic_write_json(
            local_run_dir / SCP_INDEX_NAME,
            {
                "protocol": 1,
                "vm": self.options.vm,
                "session": self.options.session,
                "run_id": state.run_id,
                "observed": {
                    relative: list(fingerprint)
                    for relative, fingerprint in observed.items()
                },
                "copied": copied,
                "updated_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                ),
            },
        )

    @staticmethod
    def _sha256_path(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _read_exact(stream, size: int) -> bytes:
        chunks = []
        remaining = size
        while remaining:
            chunk = stream.read(remaining)
            if not chunk:
                raise RunOnVmError("flux de copie SSH tronqué")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    @classmethod
    def _read_stream_frame(cls, stream) -> Dict[str, object]:
        raw_length = cls._read_exact(stream, 8)
        length = struct.unpack(">Q", raw_length)[0]
        if length > 1024 * 1024:
            raise RunOnVmError("trame de copie SSH trop grande")
        try:
            payload = json.loads(
                cls._read_exact(stream, length).decode("ascii")
            )
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise RunOnVmError("trame de copie SSH invalide") from exc
        if not isinstance(payload, dict):
            raise RunOnVmError("trame de copie SSH invalide")
        return payload

    @staticmethod
    def _safe_local_result_path(
        root: Path,
        relative: str,
        *,
        create_parents: bool,
    ) -> Path:
        parts = PurePosixPath(relative).parts
        current = root
        for part in parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise RunOnVmError(
                    "un parent local de résultat est un lien symbolique"
                )
            if create_parents:
                current.mkdir(exist_ok=True)
        destination = current / parts[-1]
        if destination.is_symlink():
            raise RunOnVmError(
                "la destination locale est un lien symbolique"
            )
        return destination

    def _copy_remote_result_files(
        self,
        state: RemoteState,
        local_results: Path,
        selected: Sequence[
            Tuple[str, str, Tuple[int, int, int, int]]
        ],
    ) -> Optional[Dict[str, str]]:
        request = {
            "protocol": 1,
            "files": [
                {
                    "path": encoded,
                    "fingerprint": list(fingerprint),
                }
                for _relative, encoded, fingerprint in selected
            ],
        }
        command = self._direct_ssh_command(
            (
                "python3",
                "-c",
                REMOTE_FILE_SYNC_HELPER,
                "copy",
                self.options.session,
                state.run_id,
            )
        )
        local_run_dir = local_results.parent
        stage = Path(
            tempfile.mkdtemp(
                prefix=".rlidar2map-sync-",
                dir=str(local_run_dir),
            )
        )
        process = None
        transferred: Dict[str, str] = {}
        with tempfile.TemporaryFile() as stderr_stream:
            try:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=stderr_stream,
                )
                assert process.stdin is not None
                assert process.stdout is not None
                process.stdin.write(
                    json.dumps(
                        request, separators=(",", ":")
                    ).encode("ascii")
                )
                process.stdin.close()
                if self._read_exact(
                    process.stdout, len(FILE_STREAM_MAGIC)
                ) != FILE_STREAM_MAGIC:
                    raise RunOnVmError(
                        "signature du flux de copie SSH invalide"
                    )
                staged_paths = {}
                for relative, encoded, fingerprint in selected:
                    header = self._read_stream_frame(process.stdout)
                    if (
                        header.get("type") == "missing"
                        and header.get("path") == encoded
                    ):
                        # Purgé côté distant entre l'inventaire et cette
                        # copie (intermédiaire nettoyé par le pipeline en
                        # cours) : pas fatal, ce fichier n'est simplement
                        # pas transféré cette fois (cf. copy_files côté
                        # remote_file_sync_helper).
                        continue
                    if (
                        header.get("type") != "file"
                        or header.get("path") != encoded
                        or header.get("size") != fingerprint[2]
                    ):
                        raise RunOnVmError(
                            "fichier inattendu dans le flux de copie SSH"
                        )
                    staged = self._safe_local_result_path(
                        stage, relative, create_parents=True
                    )
                    part = staged.with_name(staged.name + ".part")
                    digest = hashlib.sha256()
                    remaining = fingerprint[2]
                    with part.open("wb") as output:
                        while remaining:
                            block = process.stdout.read(
                                min(1024 * 1024, remaining)
                            )
                            if not block:
                                raise RunOnVmError(
                                    "contenu de fichier SSH tronqué"
                                )
                            output.write(block)
                            digest.update(block)
                            remaining -= len(block)
                        output.flush()
                        os.fsync(output.fileno())
                    trailer = self._read_stream_frame(process.stdout)
                    local_hash = digest.hexdigest()
                    if (
                        trailer.get("type") != "trailer"
                        or trailer.get("path") != encoded
                        or trailer.get("stable") is not True
                        or trailer.get("sha256") != local_hash
                    ):
                        raise RunOnVmError(
                            "le fichier distant a changé pendant sa copie"
                        )
                    os.replace(str(part), str(staged))
                    staged_paths[relative] = staged
                    transferred[relative] = local_hash
                end = self._read_stream_frame(process.stdout)
                if (
                    end.get("type") != "end"
                    or end.get("count") != len(selected)
                ):
                    raise RunOnVmError(
                        "fin du flux de copie SSH invalide"
                    )
                return_code = process.wait()
                if return_code != 0:
                    raise RunOnVmError(
                        "helper distant en échec (code {})".format(
                            return_code
                        )
                    )
                for relative, _encoded, _fingerprint in selected:
                    if relative not in staged_paths:
                        continue   # "missing" côté distant : rien à promouvoir
                    destination = self._safe_local_result_path(
                        local_results,
                        relative,
                        create_parents=True,
                    )
                    os.replace(
                        str(staged_paths[relative]), str(destination)
                    )
                return transferred
            except (OSError, RunOnVmError, BrokenPipeError) as exc:
                if process is not None and process.poll() is None:
                    process.kill()
                if process is not None:
                    process.wait()
                stderr_stream.seek(0)
                stderr = stderr_stream.read().decode(
                    "utf-8", errors="replace"
                ).strip()
                print(
                    "==> Synchronisation SSH incrémentale incomplète : "
                    "{}".format(stderr or exc),
                    file=sys.stderr,
                    flush=True,
                )
                return None
            finally:
                if process is not None and process.stdout is not None:
                    process.stdout.close()
                shutil.rmtree(stage, ignore_errors=True)

    def _sync_log(self, state: RemoteState, local_dir: Path) -> bool:
        # Le journal n'est pas un livrable et n'est jamais parsé. Le recopier
        # intégralement à chaque poll avec scp gaspillerait la bande passante ;
        # tmux fournit la vue live, et la copie locale est publiée atomiquement
        # une seule fois quand le processus est terminal.
        if not state.terminal:
            return True
        tmp_name = "run.log.tmp"
        remote = "{}:{}".format(self.options.vm, state.log_path)
        command = (
            list(self.deps.scp_prefix)
            + self._connection_options()
            + ["-q", remote, tmp_name]
        )
        completed = subprocess.run(
            command,
            cwd=str(local_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        tmp_path = local_dir / tmp_name
        if completed.returncode == 0 and tmp_path.exists():
            os.replace(str(tmp_path), str(local_dir / "run.log"))
            return True
        if tmp_path.exists():
            tmp_path.unlink()
        # The runner may not have created its log yet. This is not a final
        # synchronization error while the process is still starting/running.
        if not state.terminal:
            return True
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        print(
            "==> Copie du log final impossible : {}".format(
                stderr or "code {}".format(completed.returncode)
            ),
            file=sys.stderr,
            flush=True,
        )
        return False

    def sync_once(self, state: RemoteState) -> Tuple[bool, str, Path]:
        method = self._sync_method(state)
        local_dir = self.local_run_dir(state)
        with self._local_sync_lock(local_dir):
            local_results = local_dir / "results"
            local_results.mkdir(parents=True, exist_ok=True)
            print(
                "==> Synchronisation {} vers {}".format(
                    method, local_results
                ),
                flush=True,
            )
            if method == "rsync":
                results_ok = self._sync_results_rsync(
                    state, local_results
                )
            else:
                results_ok = self._sync_results_scp(
                    state, local_results
                )
            log_ok = self._sync_log(state, local_dir)
            ok = results_ok and log_ok
            self._write_manifest(state, method, sync_pending=not ok)
            return ok, method, local_dir

    def reconnect_command(self) -> str:
        parts = [sys.executable]
        if os.environ.get("LIDAR2MAP_REMOTE_MODE") == "1":
            # Délégué par lidar2map --remote-cli : la commande de reprise doit
            # repasser par lidar2map, pas par ce script interne.
            if not getattr(sys, "frozen", False):
                parts.append(str(Path(__file__).resolve().parent.parent / "lidar2map.py"))
            parts.append("--remote-cli")
        elif not getattr(sys, "frozen", False):
            parts.append(str(Path(__file__).resolve()))
        parts.extend([
            "--session",
            self.options.session,
            "--local-dir",
            str(self._base_local_dir()),
            "--interval",
            str(self.options.interval),
            "--sync-method",
            self.options.sync_method,
            "--ssh-timeout",
            str(self.options.ssh_timeout),
            "--max-ssh-errors",
            str(self.options.max_ssh_errors),
        ])
        if self.options.identity is not None:
            parts.extend(
                (
                    "--identity",
                    str(self.options.identity.expanduser().resolve()),
                )
            )
        for option in self.options.ssh_options:
            parts.append("--ssh-option={}".format(option))
        if self.options.purge_remote:
            parts.append("--purge-remote")
        if self.options.no_bell:
            parts.append("--no-bell")
        parts.append(self.options.vm)
        if os.name == "nt":
            return subprocess.list2cmdline(parts)
        return shlex.join(parts)

    def print_remote_hints(self, state: RemoteState) -> None:
        print(
            "  tmux : ssh {} -t {}".format(
                self.options.vm,
                shlex.quote("tmux attach -t {}".format(self.options.session)),
            )
        )
        print("  reprise : {}".format(self.reconnect_command()))
        if state.run_id:
            print("  local : {}".format(self.local_run_dir(state)))

    def notify(self, title: str, message: str) -> None:
        if not self.options.no_bell:
            print("\a", end="", flush=True)
        border = "=" * 72
        print("\n{}\n{}\n{}\n{}".format(border, title, message, border), flush=True)


def _display_state(state: RemoteState) -> None:
    detail = "status={}".format(state.status)
    if state.exit_code is not None:
        detail += ", exit={}".format(state.exit_code)
    if state.reason:
        detail += ", {}".format(state.reason)
    print("==> État distant : {}".format(detail), flush=True)


def _terminal_return_code(state: RemoteState, sync_ok: bool) -> int:
    if state.status == "succeeded":
        return 0 if sync_ok else 4
    if state.exit_code is not None and 1 <= state.exit_code <= 125:
        return state.exit_code
    return 1


def _sync_once_with_live_log_tail(
    controller: "VmController", state: "RemoteState"
) -> Tuple[bool, str, Path]:
    """sync_once en tâche de fond, tail du log distant rafraîchi PENDANT le
    transfert (rsync/scp peut prendre plusieurs minutes sur un gros lot) au
    lieu de figer l'affichage jusqu'à sa fin (observé : le panneau semblait
    mort pendant une grosse copie, alors que le calcul distant continuait
    normalement). Un seul sync à la fois, comme avant : cette fonction ne
    rend la main qu'une fois CE sync terminé, mêmes garanties d'ordre pour
    l'appelant (même résultat, juste sans le blocage silencieux)."""
    box: Dict[str, object] = {}

    def _run():
        try:
            box["result"] = controller.sync_once(state)
        except BaseException as exc:   # relayé au thread principal ci-dessous
            box["error"] = exc

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    # join(timeout) rend la main DÈS que le thread finit, sans attendre le
    # timeout complet : un sync rapide (cas normal, et tous les tests avec
    # subprocess simulés) ne déclenche jamais le corps de la boucle -
    # comportement identique à un appel synchrone. Seul un sync qui dépasse
    # vraiment _LOG_TAIL_POLL_INTERVAL_S déclenche un rafraîchissement.
    thread.join(_LOG_TAIL_POLL_INTERVAL_S)
    while thread.is_alive():
        controller.print_remote_log_tail(state)
        thread.join(_LOG_TAIL_POLL_INTERVAL_S)
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box["result"]  # type: ignore[return-value]


def run_controller(options: Options, deps: Optional[RuntimeDeps] = None) -> int:
    controller = VmController(options, deps)
    if options.reset_host_key:
        controller.reset_host_key()

    state = controller.query_state()
    pending: Optional[Tuple[RemoteState, str]] = None
    if (
        options.purge_remote
        or options.restart
        or options.resume
        or (not state.exists and bool(options.lidar_args))
    ):
        pending = controller.load_remote_purge_pending()
    if pending is not None and not options.purge_remote:
        pending_state, _pending_method = pending
        raise RunOnVmError(
            "la purge du run {} est encore en attente ; reprenez d'abord "
            "`--session {} --purge-remote {}` avant de relancer cette "
            "session".format(
                pending_state.run_id,
                options.session,
                options.vm,
            )
        )

    if options.purge_remote:
        if pending is not None:
            pending_state, pending_method = pending
            if not state.exists or state.run_id != pending_state.run_id:
                try:
                    already_purged = controller.purge_remote(pending_state)
                except PurgeTargetChangedError as exc:
                    controller.mark_remote_purge_superseded(
                        pending_state,
                        pending_method,
                        str(exc),
                    )
                    controller.notify(
                        "ANCIENNE PURGE CLASSÉE",
                        "Le run {} n'est plus le run distant courant ; "
                        "aucun autre run ni aucune archive n'a été supprimé."
                        .format(pending_state.run_id),
                    )
                    if state.exists:
                        raise RunOnVmError(
                            "un autre run est maintenant courant ; relancez "
                            "la commande de purge pour le traiter"
                        )
                    return 0
                controller.mark_remote_purged(
                    pending_state, pending_method
                )
                local_dir = controller.local_run_dir(pending_state)
                controller.notify(
                    "PURGE DISTANTE REPRISE",
                    "Le reçu distant du run {} a été vérifié ; les données "
                    "distantes sont {}. La copie locale reste dans {}.".format(
                        pending_state.run_id,
                        (
                            "déjà supprimées"
                            if already_purged
                            else "maintenant supprimées"
                        ),
                        local_dir,
                    ),
                )
                print("  local : {}".format(local_dir))
                return 0
        if not state.exists:
            completed = controller.load_remote_purged()
            if completed is not None:
                completed_state, _completed_method = completed
                local_dir = controller.local_run_dir(completed_state)
                controller.notify(
                    "DONNÉES DISTANTES DÉJÀ SUPPRIMÉES",
                    "Le marqueur local confirme la purge du run {} ; "
                    "la copie locale reste dans {}.".format(
                        completed_state.run_id, local_dir
                    ),
                )
                print("  local : {}".format(local_dir))
                return 0
            raise RunOnVmError(
                "aucun run distant courant pour '{}'".format(options.session)
            )
        if not state.terminal or state.tmux:
            raise RunOnVmError(
                "la purge est refusée tant que le run ou sa session tmux "
                "est actif"
            )
        _display_state(state)
        sync_ok, method, local_dir = controller.sync_once(state)
        if not sync_ok:
            controller.notify(
                "PURGE DISTANTE ANNULÉE",
                "La dernière synchronisation locale est incomplète ; "
                "aucune donnée distante n'a été supprimée.",
            )
            controller.print_remote_hints(state)
            return 4
        controller.mark_remote_purge_pending(state, method)
        try:
            already_purged = controller.purge_remote(state)
        except PurgeTargetChangedError as exc:
            controller.mark_remote_purge_superseded(
                state,
                method,
                str(exc),
            )
            raise RunOnVmError(
                "le run distant a changé entre la copie et la purge ; "
                "aucun nouveau run n'a été supprimé, relancez la commande"
            ) from exc
        controller.mark_remote_purged(state, method)
        original_result = "status={}".format(state.status)
        if state.exit_code is not None:
            original_result += ", exit={}".format(state.exit_code)
        controller.notify(
            "DONNÉES DISTANTES SUPPRIMÉES",
            "La copie locale est complète dans {}. Le run distant {} "
            "a été {}.".format(
                local_dir,
                original_result,
                "déjà purgé" if already_purged else "purgé",
            ),
        )
        print("  local : {}".format(local_dir))
        return 0

    if state.exists:
        if options.restart:
            if not options.lidar_args:
                raise RunOnVmError("--restart exige les arguments lidar2map")
            if state.status in ACTIVE_STATES and state.tmux:
                raise RunOnVmError(
                    "la session est encore active ; utilisez un autre nom ou attendez sa fin"
                )
            print("==> Archivage puis redémarrage de '{}'.".format(options.session))
            controller.launch()
            state = controller.query_state()
        elif options.resume:
            if not options.lidar_args:
                raise RunOnVmError("--resume exige les arguments lidar2map")
            if state.status in ACTIVE_STATES and state.tmux:
                raise RunOnVmError(
                    "la session est encore active ; utilisez --restart, un "
                    "autre nom, ou attendez sa fin"
                )
            print(
                "==> Reprise de '{}' en place (dalles déjà en cache "
                "conservées).".format(options.session)
            )
            controller.launch()
            state = controller.query_state()
        else:
            if options.lidar_args:
                print(
                    "==> La session '{}' existe déjà : aucun second lancement, "
                    "reprise de la surveillance.".format(options.session),
                    flush=True,
                )
    else:
        if state.tmux:
            raise RunOnVmError(
                "une session tmux non gérée porte déjà le nom '{}'".format(
                    options.session
                )
            )
        if not options.lidar_args:
            raise RunOnVmError(
                "aucun état distant pour '{}' et aucun argument de lancement".format(
                    options.session
                )
            )
        print(
            "==> Lancement {} sur {} dans tmux '{}'.".format(
                options.mode, options.vm, options.session
            ),
            flush=True,
        )
        controller.launch()
        state = controller.query_state()

    last_status: Optional[str] = None
    consecutive_ssh_errors = 0
    while True:
        if state.status != last_status:
            _display_state(state)
            last_status = state.status

        controller.print_remote_log_tail(state)
        sync_ok, _method, local_dir = _sync_once_with_live_log_tail(
            controller, state
        )
        if state.terminal:
            if state.status == "succeeded" and sync_ok:
                controller.notify(
                    "RUN TERMINÉ",
                    "lidar2map s'est terminé correctement ; résultats synchronisés dans {}".format(
                        local_dir
                    ),
                )
            elif state.status == "succeeded":
                controller.notify(
                    "RUN TERMINÉ, SYNCHRONISATION INCOMPLÈTE",
                    "Le calcul a réussi mais certains résultats restent à recopier. "
                    "Relancez la commande de reprise.",
                )
            else:
                controller.notify(
                    "RUN EN ÉCHEC",
                    "{} (code {}). Le résultat partiel et le log ont été synchronisés dans {}.".format(
                        state.reason or "arrêt inattendu",
                        state.exit_code if state.exit_code is not None else "?",
                        local_dir,
                    ),
                )
            controller.print_remote_hints(state)
            return _terminal_return_code(state, sync_ok)

        if options.detach or options.once:
            print("==> Le run continue sur la VM.")
            controller.print_remote_hints(state)
            return 0 if sync_ok else 4

        try:
            controller.deps.sleep(options.interval)
            state = controller.query_state()
            consecutive_ssh_errors = 0
        except SshError as exc:
            consecutive_ssh_errors += 1
            print(
                "==> SSH indisponible ({}/{}): {}".format(
                    consecutive_ssh_errors, options.max_ssh_errors, exc
                ),
                file=sys.stderr,
                flush=True,
            )
            if consecutive_ssh_errors >= options.max_ssh_errors:
                controller.notify(
                    "SURVEILLANCE INTERROMPUE",
                    "La VM est injoignable ; l'état du processus distant est inconnu. "
                    "Relancez la commande de reprise.",
                )
                controller.print_remote_hints(state)
                return 3


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    deps: Optional[RuntimeDeps] = None,
) -> int:
    options: Optional[Options] = None
    try:
        options = parse_options(argv)
        return run_controller(options, deps)
    except KeyboardInterrupt:
        print(
            "\n==> Surveillance locale interrompue. Le processus tmux distant "
            "n'a pas été arrêté.",
            file=sys.stderr,
        )
        if options is not None:
            print(
                "==> Reprise : {}".format(
                    VmController(options, deps).reconnect_command()
                ),
                file=sys.stderr,
            )
        return 130
    except SshError as exc:
        print("ERREUR SSH: {}".format(exc), file=sys.stderr)
        return 3
    except RunOnVmError as exc:
        print("ERREUR: {}".format(exc), file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(
            "ERREUR: commande locale introuvable : {}".format(exc.filename or exc),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
