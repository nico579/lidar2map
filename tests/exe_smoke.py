#!/usr/bin/env python3
"""Smoke test de l'exécutable livré (D1, docs/preconisations_evolution.md).

Toutes les suites de tests tournent en mode source : les bugs propres au mode
figé (menu « Redémarrer », démarrage automatique de la 1.50.0) leur
échappaient. Ce script lance le binaire tel qu'il sera publié, hors réseau :

  1. démarrage par le lanceur (extraction du bundle, puis serveur web) :
     /api/init répond "app": "lidar2map" et /api/help rend l'aide ; sous
     Linux, un faux systemctl vérifie que les programmes du système reçoivent
     le LD_LIBRARY_PATH d'origine (issue #23 de blink2video) ;
  2. relance de l'exe interne extrait avec la sentinelle, comme le fait
     « Redémarrer » (_commande_relance dans lidar2map.py). C'est la commande
     qui est vérifiée, pas le menu lui-même : pas d'icône de notification
     sur un runner ;
  3. fusion de deux MBTiles avec --merge : sqlite, Pillow et composition
     alpha dans le binaire ;
  4. arrêt de l'arbre de processus, puis contrôle qu'aucune donnée
     utilisateur n'a été écrite dans le dossier d'extraction : elles vont à
     côté du binaire (LIDAR2MAP_WORK_DIR).

Appelé par release.yml après « Package » sur chaque runner, et utilisable
en local :

    python tests/exe_smoke.py dist/lidar2map-windows-x86_64.zip

Stdlib uniquement : le Python du runner n'a pas les dépendances de l'app.
Le dossier personnel est remplacé par un dossier temporaire (HOME,
USERPROFILE, LOCALAPPDATA, APPDATA) : un lancement local ne touche ni
l'extraction ni les préférences réelles. Sous macOS, lancer le binaire
depuis un shell ne passe pas par Gatekeeper : ce test ne prouve rien sur la
quarantaine.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import sqlite3
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
import zlib
from pathlib import Path

# Premier lancement : le lanceur extrait d'abord le bundle (~650 Mio sous
# Windows, 1 Gio sous Linux), lent sur les runners macOS Intel.
DELAI_PREMIER_DEMARRAGE_S = 300
DELAI_DEMARRAGE_S = 120
DELAI_FUSION_S = 300

# Doivent aller dans le dossier de travail (à côté du binaire), jamais dans
# le dossier d'extraction, remplacé à chaque mise à jour.
DONNEES_UTILISATEUR = ("historique.json", "preferences.json", "Projets",
                       "logs", "cache", "production")

# Valeur donnée au lanceur (Linux) : les programmes du système doivent la
# recevoir telle quelle, sans les bibliothèques du binaire devant (étape 1b).
LD_LIBRARY_PATH_TEMOIN = "/opt/lidar2map-exe-smoke"


class Echec(Exception):
    """Contrôle en échec : message affiché, code de sortie 1."""


# ── Archive et chemins ─────────────────────────────────────────────────────

def extraire(archive: Path, dest: Path) -> None:
    if archive.name.endswith(".tar.gz"):
        with tarfile.open(archive) as tar:
            tar.extractall(dest, filter="data")
    elif sys.platform == "darwin":
        # ditto conserve permissions, liens symboliques et attributs du .app,
        # que zipfile perdrait (bit exécutable compris).
        subprocess.run(["ditto", "-x", "-k", str(archive), str(dest)], check=True)
    else:
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)


def trouver_lanceur(dest: Path) -> tuple[Path, Path]:
    """(lanceur, dossier de travail), comme les calcule le bloc lanceur."""
    app = dest / "LIDAR2MAP.app" / "Contents" / "MacOS" / "lidar2map"
    if app.is_file():
        return app, dest                      # dossier qui contient le .app
    for motif in ("*/lidar2map.exe", "*/lidar2map"):
        for candidat in sorted(dest.glob(motif)):
            if candidat.is_file():
                return candidat, candidat.parent
    raise Echec(f"aucun lanceur lidar2map dans {dest}")


def dossier_extraction(home: Path) -> Path:
    """Dossier où le lanceur extrait le bundle (bloc lanceur de lidar2map.py)."""
    if sys.platform == "win32":
        return home / "AppData" / "Local" / "lidar2map"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "lidar2map"
    return home / ".local" / "share" / "lidar2map"


def exe_interne(dossier: Path) -> Path:
    exe = dossier / ("lidar2map.exe" if sys.platform == "win32" else "lidar2map")
    if exe.is_dir() and (exe / exe.name).is_file():   # même règle que _resolve_exe
        return exe / exe.name
    return exe


def environnement(racine: Path) -> tuple[dict, Path]:
    home = racine / "home"
    for sous_dossier in ("AppData/Local", "AppData/Roaming"):
        (home / sous_dossier).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(HOME=str(home), USERPROFILE=str(home),
               LOCALAPPDATA=str(home / "AppData" / "Local"),
               APPDATA=str(home / "AppData" / "Roaming"))
    env.pop("LIDAR2MAP_WORK_DIR", None)
    if sys.platform.startswith("linux"):
        # Faux systemctl en tête du PATH (étape 1b) : note le LD_LIBRARY_PATH
        # que reçoivent les programmes du système lancés par lidar2map.
        faux = racine / "bin"
        faux.mkdir(exist_ok=True)
        systemctl = faux / "systemctl"
        systemctl.write_text(
            "#!/bin/sh\n"
            'printf "%s|%s\\n" "${LD_LIBRARY_PATH-<absent>}" '
            '"${LD_LIBRARY_PATH_ORIG-<absent>}" >> "$LIDAR2MAP_SONDE"\n',
            encoding="utf-8")
        systemctl.chmod(0o755)
        env.update(PATH=f"{faux}{os.pathsep}{env.get('PATH', '')}",
                   LD_LIBRARY_PATH=LD_LIBRARY_PATH_TEMOIN,
                   LIDAR2MAP_SONDE=str(racine / "systemctl.txt"))
        env.pop("LD_LIBRARY_PATH_ORIG", None)
    return env, home


# ── Processus ──────────────────────────────────────────────────────────────

def port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def lancer(commande: list[str], env: dict, cwd: Path, journal: Path) -> subprocess.Popen:
    options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == "nt" else {"start_new_session": True})
    with open(journal, "wb") as sortie:
        # stdin fermé : une question interactive ne doit jamais bloquer.
        return subprocess.Popen(commande, env=env, cwd=cwd,
                                stdin=subprocess.DEVNULL, stdout=sortie,
                                stderr=subprocess.STDOUT, **options)


def tuer_arbre(processus: subprocess.Popen) -> None:
    """Le lanceur attend l'exe interne : tuer tout l'arbre, pas le parent seul."""
    if processus.poll() is None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(processus.pid)],
                           capture_output=True, check=False)
        else:
            try:
                os.killpg(processus.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        processus.wait(timeout=30)
    except subprocess.TimeoutExpired:
        pass


def lire_json(url: str, delai_s: float = 10):
    with urllib.request.urlopen(url, timeout=delai_s) as reponse:
        return json.loads(reponse.read())


def poster_json(url: str, donnees: dict, delai_s: float = 30):
    requete = urllib.request.Request(
        url, data=json.dumps(donnees).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=delai_s) as reponse:
        return json.loads(reponse.read())


def attendre_serveur(port: int, processus: subprocess.Popen, delai_s: float) -> None:
    fin = time.monotonic() + delai_s
    derniere = None
    while time.monotonic() < fin:
        if processus.poll() is not None:
            raise Echec(f"arrêté (code {processus.returncode}) avant de répondre"
                        f" sur le port {port}")
        try:
            if lire_json(f"http://127.0.0.1:{port}/api/init", 5).get("app") == "lidar2map":
                return
            derniere = "réponse sans \"app\": \"lidar2map\""
        except (OSError, ValueError) as exc:
            derniere = exc
        time.sleep(2)
    raise Echec(f"/api/init muet après {delai_s:.0f} s sur le port {port} ({derniere})")


# ── Fixtures MBTiles (PNG écrits à la main : pas de Pillow ici) ────────────

def png_uni(rgba: tuple[int, int, int, int], taille: int = 256) -> bytes:
    def bloc(nature: bytes, donnees: bytes) -> bytes:
        return (struct.pack(">I", len(donnees)) + nature + donnees
                + struct.pack(">I", zlib.crc32(nature + donnees) & 0xFFFFFFFF))
    brut = (b"\x00" + bytes(rgba) * taille) * taille   # filtre 0 par ligne
    return (b"\x89PNG\r\n\x1a\n"
            + bloc(b"IHDR", struct.pack(">IIBBBBB", taille, taille, 8, 6, 0, 0, 0))
            + bloc(b"IDAT", zlib.compress(brut))
            + bloc(b"IEND", b""))


def ecrire_mbtiles(chemin: Path, tuiles: dict) -> None:
    con = sqlite3.connect(chemin)
    con.executescript(
        "CREATE TABLE metadata (name TEXT, value TEXT);"
        "CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER,"
        " tile_row INTEGER, tile_data BLOB);"
        "CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);")
    con.executemany("INSERT INTO metadata VALUES (?, ?)", [
        ("name", chemin.stem), ("format", "png"), ("minzoom", "10"),
        ("maxzoom", "10"), ("bounds", "5.0,43.0,6.0,44.0")])
    con.executemany("INSERT INTO tiles VALUES (10, ?, ?, ?)",
                    [(x, y, donnees) for (x, y), donnees in tuiles.items()])
    con.commit()
    con.close()


def lire_tuiles(chemin: Path) -> dict:
    con = sqlite3.connect(chemin)
    try:
        return {(x, y): bytes(d) for x, y, d in con.execute(
            "SELECT tile_column, tile_row, tile_data FROM tiles WHERE zoom_level = 10")}
    finally:
        con.close()


# ── Étapes ─────────────────────────────────────────────────────────────────

def etape(titre: str) -> None:
    print(f"\n== {titre}", flush=True)


def smoke(archive: Path, racine: Path) -> None:
    dest = racine / "archive"
    etape(f"extraction de {archive.name}")
    extraire(archive, dest)
    lanceur, travail = trouver_lanceur(dest)
    env, home = environnement(racine)
    print(f"   lanceur : {lanceur}\n   travail : {travail}", flush=True)
    options_gui = ["--serve-gui", "--no-browser", "--no-tray"]
    processus = []
    try:
        etape("1. démarrage par le lanceur (extraction du bundle au premier lancement)")
        port = port_libre()
        processus.append(lancer([str(lanceur), *options_gui, "--port", str(port)],
                                env, travail, racine / "1_lanceur.log"))
        attendre_serveur(port, processus[-1], DELAI_PREMIER_DEMARRAGE_S)
        aide = lire_json(f"http://127.0.0.1:{port}/api/help", 30)
        if not (isinstance(aide, str) and "lidar2map" in aide):
            raise Echec(f"/api/help inattendu : {str(aide)[:120]!r}")
        print(f"   OK : /api/init et /api/help sur le port {port}", flush=True)

        if sys.platform.startswith("linux"):
            etape("1b. programmes du système : LD_LIBRARY_PATH d'origine")
            # Désactiver le démarrage automatique lance systemctl --user (le
            # faux, ici) depuis l'exe interne, lui-même lancé par le lanceur :
            # deux binaires PyInstaller, qui préfixent chacun la variable.
            poster_json(f"http://127.0.0.1:{port}/api/set-autostart", {"actif": False})
            sonde = racine / "systemctl.txt"
            recu = (sonde.read_text(encoding="utf-8").splitlines()
                    if sonde.is_file() else [])
            attendu = f"{LD_LIBRARY_PATH_TEMOIN}|{LD_LIBRARY_PATH_TEMOIN}"
            # Le second champ (LD_LIBRARY_PATH_ORIG, posé par le lanceur de
            # l'exe interne) prouve que la variable avait bien été préfixée,
            # et que le lanceur lui avait transmis la valeur d'origine.
            if not recu or any(ligne != attendu for ligne in recu):
                raise Echec(f"systemctl a reçu {recu}, attendu {attendu!r}"
                            " (LD_LIBRARY_PATH|LD_LIBRARY_PATH_ORIG)")
            print(f"   OK : systemctl lancé {len(recu)} fois avec la valeur d'origine",
                  flush=True)

        etape("2. relance de l'exe interne avec la sentinelle (« Redémarrer »)")
        interne = exe_interne(dossier_extraction(home))
        if not interne.is_file():
            raise Echec(f"exe interne introuvable après extraction : {interne}")
        # Même commande que _commande_relance(), même environnement hérité
        # que celui que le lanceur a donné à l'exe interne.
        env_relance = dict(env, LIDAR2MAP_WORK_DIR=str(travail))
        port2 = port_libre()
        processus.append(lancer(
            [str(interne), "--__lidar2map_inner__", *options_gui, "--port", str(port2)],
            env_relance, travail, racine / "2_relance.log"))
        attendre_serveur(port2, processus[-1], DELAI_DEMARRAGE_S)
        print(f"   OK : exe interne relancé sur le port {port2}", flush=True)
    finally:
        for p in processus:
            tuer_arbre(p)

    etape("3. fusion de deux MBTiles (sqlite, Pillow, composition alpha)")
    opaque_a, opaque_b = png_uni((200, 30, 30, 255)), png_uni((30, 30, 200, 255))
    translucide = png_uni((30, 200, 30, 128))
    source_a, source_b = racine / "a.mbtiles", racine / "b.mbtiles"
    ecrire_mbtiles(source_a, {(0, 0): opaque_a, (1, 0): opaque_a})
    ecrire_mbtiles(source_b, {(1, 0): translucide, (2, 0): opaque_b})
    sortie = racine / "fusion.mbtiles"
    fusion = lancer([str(lanceur), "--merge", "--source", str(source_a), str(source_b),
                     "--output-file", str(sortie)], env, travail, racine / "3_fusion.log")
    try:
        code = fusion.wait(timeout=DELAI_FUSION_S)
    except subprocess.TimeoutExpired:
        tuer_arbre(fusion)
        raise Echec(f"--merge toujours en cours après {DELAI_FUSION_S} s") from None
    if code != 0 or not sortie.is_file():
        raise Echec(f"--merge : code {code}, sortie présente : {sortie.is_file()}")
    tuiles = lire_tuiles(sortie)
    if sorted(tuiles) != [(0, 0), (1, 0), (2, 0)]:
        raise Echec(f"tuiles fusionnées inattendues : {sorted(tuiles)}")
    # La tuile commune translucide doit être COMPOSÉE sur l'opaque : sans
    # Pillow dans le binaire, composer_tuiles() garderait la dernière telle
    # quelle, en silence.
    if tuiles[(1, 0)] in (translucide, opaque_a):
        raise Echec("tuile commune non composée : Pillow absent du binaire ?")
    print("   OK : 3 tuiles, tuile commune composée", flush=True)

    etape("4. données utilisateur à côté du binaire, pas dans l'extraction")
    extraction = dossier_extraction(home)
    intrus = [nom for nom in DONNEES_UTILISATEUR if (extraction / nom).exists()]
    if intrus:
        raise Echec(f"données utilisateur dans le dossier d'extraction {extraction} :"
                    f" {', '.join(intrus)}")
    if not (travail / "logs").is_dir():
        raise Echec(f"aucun dossier logs/ dans {travail} : LIDAR2MAP_WORK_DIR ignoré ?")
    print(f"   OK : rien dans {extraction.name}/, journaux dans {travail}/logs",
          flush=True)


def afficher_journaux(racine: Path) -> None:
    for journal in sorted(racine.glob("*.log")):
        lignes = journal.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"\n--- {journal.name} ({len(lignes)} lignes, 60 dernières) ---")
        print("\n".join(lignes[-60:]))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("archive", type=Path,
                        help="archive publiée (.zip, ou .tar.gz sous Linux)")
    parser.add_argument("--garder", action="store_true",
                        help="conserver le dossier temporaire (diagnostic)")
    args = parser.parse_args(argv)
    if not args.archive.is_file():
        print(f"archive introuvable : {args.archive}", file=sys.stderr)
        return 2
    racine = Path(tempfile.mkdtemp(prefix="lidar2map_exe_smoke_"))
    debut = time.monotonic()
    try:
        smoke(args.archive.resolve(), racine)
    except Echec as exc:
        print(f"\nÉCHEC : {exc}", flush=True)
        afficher_journaux(racine)
        return 1
    finally:
        if args.garder:
            print(f"\nDossier conservé : {racine}")
        else:
            shutil.rmtree(racine, ignore_errors=True)
    print(f"\nSmoke test du binaire : OK en {time.monotonic() - debut:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
