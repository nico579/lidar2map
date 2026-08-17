"""Logger atomique et thread-safe de lidar2map."""

from __future__ import annotations

import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path


class TeeLogger:
    """
    Duplique stdout vers un fichier log avec horodatage.

    Gestion des \r : les barres de progression terminent par \r (pas \n).
    Pour le terminal, \r écrase la ligne courante — comportement normal.
    Pour le log, on ne conserve que le dernier état de chaque ligne \r
    (la valeur finale), en ignorant les mises à jour intermédiaires.

    Pendant un découpage à priori, les lignes de détail du terminal/GUI sont
    aussi préfixées par le chunk et la phase. Les en-têtes et bilans qui portent
    déjà ``[LLLxCCC]`` ne sont pas doublés.
    """
    def __init__(self, log_path):
        self._terminal = sys.stdout
        self._log_path = Path(log_path)
        self._part_path = self._log_path.with_name(
            f"{self._log_path.name}.{os.getpid()}.{uuid.uuid4().hex[:12]}.part"
        )
        self._log = open(self._part_path, "w", encoding="utf-8", buffering=1)
        self._closed = False
        self._published = False
        self._buf = ""          # buffer jusqu'au prochain \n
        self._cr_buf = ""       # dernier contenu de ligne \r (écrase les précédents)
        # Verrou : write() est appelé par PLUSIEURS threads (pools d'encodage
        # de tuiles, workers). Sans lui, la machine à états _buf/_cr_buf
        # s'entrelace entre threads → lignes de log corrompues.
        self._lock = threading.Lock()
        self._chunk_actuel = None   # cf. definir_chunk
        self._terminal_debut_ligne = True

    def definir_chunk(self, cle):
        """Marque le chunk en cours (découpage à priori) : préfixe chaque
        ligne de log qui suit, pour qu'un extrait du log soit auto-suffisant
        sans avoir à remonter chercher le dernier « ── Ombrage XXX ── »."""
        with self._lock:
            self._chunk_actuel = cle

    def _log_line(self, line):
        """Écrit une ligne dans le fichier log avec horodatage."""
        # Nettoyer les séquences \r résiduelles dans la ligne
        if "\r" in line:
            line = line.split("\r")[-1]
        line = line.strip()
        if line:
            ts = time.strftime("%H:%M:%S")
            _cle = f"[{self._chunk_actuel}] " if self._chunk_actuel else ""
            self._log.write(f"[{ts}] {_cle}{line}\n")

    def _terminal_avec_chunk(self, msg):
        """Préfixe chaque ligne logique sans casser les progressions ``\r``.

        ``print`` peut appeler ``write`` une fois pour le texte puis une seconde
        fois pour le saut de ligne. L'état ``_terminal_debut_ligne`` évite donc
        d'insérer un préfixe au milieu d'un message fragmenté. Chaque retour
        chariot redémarre en revanche une ligne de progression complète.
        """
        if not msg:
            return msg

        contexte = self._chunk_actuel
        debut_ligne = self._terminal_debut_ligne
        resultat = msg
        if contexte:
            contexte = str(contexte)
            bloc = contexte.split(":", 1)[0]
            marqueur_bloc = f"[{bloc}]"
            marqueur_contexte = f"[{contexte}]"

            def _prefixer(match):
                separateur, contenu = match.groups()
                # Le premier fragment peut continuer un write précédent ; les
                # fragments suivant \r/\n commencent toujours une nouvelle ligne.
                if not separateur and not debut_ligne:
                    return contenu
                # En-têtes et messages de bilan ont déjà leur bloc visible.
                if (marqueur_bloc in contenu
                        or marqueur_contexte in contenu):
                    return separateur + contenu
                indentation = contenu[:len(contenu) - len(contenu.lstrip())]
                texte = contenu[len(indentation):]
                return (
                    f"{separateur}{indentation}"
                    f"{marqueur_contexte} {texte}"
                )

            resultat = re.sub(
                r"(^|[\r\n])([^\r\n]+)",
                _prefixer,
                msg,
            )

        self._terminal_debut_ligne = msg.endswith(("\r", "\n"))
        return resultat

    def write(self, msg):
        # ── Terminal ─────────────────────────────────────────────────────────
        # Toutes les opérations sont défensives parce que cette méthode est
        # appelée par Python lui-même au shutdown. Si un de ses appels lève
        # une exception, Windows retourne le code 120 (ERROR_CALL_NOT_IMPLEMENTED)
        # à la place du code passé à sys.exit().
        try:
            # Même verrou que le fichier : un worker ne doit pas couper une
            # ligne entre son préfixe et son contenu pendant un changement de
            # contexte effectué par le thread principal.
            with self._lock:
                msg_terminal = self._terminal_avec_chunk(msg)
        except Exception:
            msg_terminal = msg
        try:
            self._terminal.write(msg_terminal)
        except UnicodeEncodeError:
            try:
                self._terminal.write(
                    msg_terminal.encode(
                        self._terminal.encoding or "cp1252",
                        errors="replace",
                    ).decode(self._terminal.encoding or "cp1252")
                )
            except Exception:
                pass
        except Exception:
            pass
        try:
            # Flush sur \r ET \n. Sans flush sur \n, les lignes restent
            # bufferisées dans le pipe quand stdout est redirigé (cas de la
            # GUI qui lance le script comme subprocess). Conséquence : les
            # messages n'arrivent au parent qu'au moment du wait() final,
            # ce qui rend le panneau de log inutile en temps réel.
            if "\r" in msg or "\n" in msg:
                self._terminal.flush()
        except Exception:
            pass

        # ── Log ──────────────────────────────────────────────────────────────
        # Même machine à états \r/\n qu'avant, mais opérée par RUNS (find +
        # slice, vitesse C) au lieu de caractère par caractère : write() est
        # traversé par TOUTE la sortie, y compris les dizaines de milliers de
        # repaints des barres de progression.
        try:
            with self._lock:
                pos = 0
                n = len(msg)
                while pos < n:
                    i_r = msg.find("\r", pos)
                    i_n = msg.find("\n", pos)
                    if i_r == -1 and i_n == -1:
                        self._buf += msg[pos:]
                        break
                    if i_n == -1 or (i_r != -1 and i_r < i_n):
                        # \r : écrase le contenu de la ligne courante (barre de
                        # progression) — dernier état gardé dans _cr_buf
                        self._cr_buf = self._buf + msg[pos:i_r]
                        self._buf = ""
                        pos = i_r + 1
                    else:
                        # \n : fin de ligne — logguer le contenu final (si la ligne
                        # était précédée de \r, prendre le dernier segment \r)
                        line = (self._buf + msg[pos:i_n]) or self._cr_buf
                        self._log_line(line)
                        self._buf = ""
                        self._cr_buf = ""
                        pos = i_n + 1
        except Exception:
            pass

    def flush(self):
        # Défensif : flush() est appelé par Python au shutdown, après que
        # close() a peut-être déjà fermé self._log. Sans try/except, l'erreur
        # "I/O operation on closed file" remonte → code retour Windows = 120.
        try:
            self._terminal.flush()
        except Exception:
            pass
        try:
            self._log.flush()
        except Exception:
            pass

    def close(self):
        if self._closed:
            return
        self._closed = True
        # Flush des buffers résiduels — défensif : pendant le shutdown
        # Python, sys.stdout/sys.stderr peuvent être dans un état partiel,
        # et toute exception ici peut polluer le code retour du process
        # (Windows retourne 120 si l'atexit handler échoue).
        try:
            remaining = self._buf or self._cr_buf
            if remaining:
                self._log_line(remaining)
        except Exception:
            pass
        try:
            self._log.close()
        except Exception:
            pass
        # Le log suit le même contrat que les livrables : tant qu'il est
        # ouvert il porte le suffixe .part. Après fermeture du handle, sa
        # publication est un rename atomique. Un kill brutal laisse donc un
        # .part identifiable au lieu d'un faux log final.
        try:
            os.replace(self._part_path, self._log_path)
            self._published = True
        except FileNotFoundError:
            # close() peut être rappelé par atexit après le finally principal.
            self._published = self._log_path.exists()
        except Exception as exc:
            try:
                self._terminal.write(
                    f"\n  WARNING: log publication failed "
                    f"({type(exc).__name__}: {exc}); partial log: "
                    f"{self._part_path}\n"
                )
                self._terminal.flush()
            except Exception:
                pass


