"""Verrou d'extraction du lanceur (bloc « frozen » de lidar2map.py) face aux
refus passagers de Windows.

Le lanceur ne tourne que dans l'exécutable figé : ses deux fonctions de
verrou sont donc extraites du source par l'AST, puis exécutées pour de vrai.
Un antivirus qui tient encore un fichier tout juste supprimé le laisse « en
attente de suppression » : le recréer est alors refusé (PermissionError), et
non signalé comme existant. Vu sur blink2video, dont le verrou a le même
principe (CI Windows des 25 et 26/09/2026)."""
import ast
import os
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path

os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
# Jamais les vrais dossiers d'état et de sorties de l'utilisateur (voir
# _dossiers.py) : run_tests.py en fournit un, sinon un dossier temporaire.
if not os.environ.get("LIDAR2MAP_HOME"):
    os.environ["LIDAR2MAP_HOME"] = tempfile.mkdtemp(prefix="lidar2map-tests-")

ROOT = Path(__file__).resolve().parent.parent
FONCTIONS = ("_prendre_lock", "_retirer_lock")


def fonctions_du_lanceur(verrou: Path) -> dict:
    """Les fonctions de verrou telles qu'écrites dans le lanceur, liées au
    fichier `verrou` comme l'est _lock dans l'exécutable."""
    source = (ROOT / "lidar2map.py").read_text(encoding="utf-8")
    lignes = source.splitlines(keepends=True)
    espace = {"os": os, "_time": time, "_lock": verrou}
    noeuds = [n for n in ast.walk(ast.parse(source))
              if isinstance(n, ast.FunctionDef) and n.name in FONCTIONS]
    assert sorted(n.name for n in noeuds) == sorted(FONCTIONS), \
        [n.name for n in noeuds]
    for noeud in noeuds:
        code = textwrap.dedent("".join(lignes[noeud.lineno - 1:noeud.end_lineno]))
        exec(compile(code, "lidar2map.py (lanceur)", "exec"), espace)
    return espace


class VerrouDuLanceurTests(unittest.TestCase):
    def setUp(self):
        temporaire = tempfile.TemporaryDirectory(prefix="lidar2map-lanceur-")
        self.addCleanup(temporaire.cleanup)
        self.verrou = Path(temporaire.name) / ".lidar2map_extracting"
        self.lanceur = fonctions_du_lanceur(self.verrou)

    def test_une_seule_instance_prend_le_verrou(self):
        self.assertTrue(self.lanceur["_prendre_lock"]())
        self.assertFalse(self.lanceur["_prendre_lock"]())
        self.lanceur["_retirer_lock"]()
        self.assertFalse(self.verrou.exists())


@unittest.skipUnless(os.name == "nt", "état propre au système de fichiers de Windows")
class VerrouDuLanceurWindowsTests(unittest.TestCase):
    """On reproduit les deux gestes d'un antivirus : garder ouvert, en
    partageant tout, un fichier qu'on supprime (il reste alors en attente de
    suppression), ou le garder ouvert sans partager la suppression (unlink()
    est alors refusé)."""

    GENERIC_READ = 0x80000000
    DELETE = 0x00010000
    PARTAGE_LECTURE_ECRITURE = 0x1 | 0x2
    PARTAGE_TOTAL = 0x1 | 0x2 | 0x4
    OPEN_EXISTING = 3
    FILE_FLAG_DELETE_ON_CLOSE = 0x04000000

    def setUp(self):
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.invalide = wintypes.HANDLE(-1).value
        # Instance propre à ce test : ses argtypes ne touchent pas
        # ctypes.windll.kernel32, partagé avec le reste du processus.
        self.k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k32.CreateFileW.restype = wintypes.HANDLE
        self.k32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self.k32.CloseHandle.argtypes = [wintypes.HANDLE]
        temporaire = tempfile.TemporaryDirectory(prefix="lidar2map-lanceur-")
        self.addCleanup(temporaire.cleanup)
        self.verrou = Path(temporaire.name) / ".lidar2map_extracting"
        self.lanceur = fonctions_du_lanceur(self.verrou)
        self.lecteurs = []
        self.addCleanup(self.liberer)

    def ouvrir(self, acces: int, partage: int, drapeaux: int = 0):
        poignee = self.k32.CreateFileW(str(self.verrou), acces, partage, None,
                                       self.OPEN_EXISTING, drapeaux, None)
        if poignee in (None, self.invalide):
            raise self.ctypes.WinError(self.ctypes.get_last_error())
        return poignee

    def liberer(self):
        """Ferme le lecteur ; sans effet la seconde fois, une poignée fermée
        deux fois pouvant en viser une autre, réattribuée entre-temps."""
        try:
            poignee = self.lecteurs.pop()
        except IndexError:
            return
        self.k32.CloseHandle(poignee)

    def test_verrou_en_attente_de_suppression_reste_pris(self):
        self.verrou.write_bytes(b"")
        self.lecteurs.append(self.ouvrir(self.GENERIC_READ, self.PARTAGE_TOTAL))
        self.k32.CloseHandle(self.ouvrir(self.DELETE, self.PARTAGE_TOTAL,
                                         self.FILE_FLAG_DELETE_ON_CLOSE))
        # L'état est bien reproduit : la création exclusive est refusée.
        with self.assertRaises(PermissionError):
            os.close(os.open(self.verrou, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        self.assertFalse(self.lanceur["_prendre_lock"]())
        self.liberer()
        self.assertTrue(self.lanceur["_prendre_lock"]())

    def test_suppression_refusee_un_instant_aboutit(self):
        self.verrou.write_bytes(b"")
        self.lecteurs.append(self.ouvrir(self.GENERIC_READ,
                                         self.PARTAGE_LECTURE_ECRITURE))
        threading.Timer(0.2, self.liberer).start()
        self.lanceur["_retirer_lock"]()
        self.assertFalse(self.verrou.exists())

    def test_suppression_refusee_durablement_ne_plante_pas(self):
        self.verrou.write_bytes(b"")
        self.lecteurs.append(self.ouvrir(self.GENERIC_READ,
                                         self.PARTAGE_LECTURE_ECRITURE))
        with self.assertRaises(PermissionError):
            self.verrou.unlink()
        self.lanceur["_retirer_lock"]()
        self.assertTrue(self.verrou.exists())


if __name__ == "__main__":
    unittest.main()
