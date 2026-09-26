#!/usr/bin/env python3
"""Smoke test de l'exécutable livré (D1, docs/preconisations_evolution.md).

Toutes les suites de tests tournent en mode source : les bugs propres au mode
figé (menu « Redémarrer », démarrage automatique de la 1.50.0) leur
échappaient. Ce script lance le binaire tel qu'il sera publié, hors réseau :

  1. démarrage du programme (serveur web) : /api/init répond
     "app": "lidar2map" et /api/help rend l'aide ; sous Linux, un faux
     systemctl vérifie que les programmes du système reçoivent le
     LD_LIBRARY_PATH d'origine (issue #23 de blink2video) ;
  2. ménage de ce qu'un lanceur <= 1.54 laissait : son dossier d'extraction
     et le lidar2map_bundle.zip voisin du programme, posés avant le
     démarrage, ont disparu (_bootstrap_runtime.nettoyer_ancienne_extraction) ;
  3. fusion de deux MBTiles avec --merge : sqlite, Pillow et composition
     alpha dans le binaire ;
  4. chaîne Java embarquée : le JRE, osmosis et le greffon mapwriter,
     trouvés là où lidar2map les cherche (_osm_runtime.py), écrivent un .map
     à partir d'un fichier OSM minuscule. Le programme figé tient le greffon
     pour acquis : seul ce test prouve qu'il est bien embarqué. Sous macOS,
     PyInstaller répartit aussi le .app entre Contents/Frameworks et
     Contents/Resources, et la chaîne doit y survivre ;
  5. arrêt de l'arbre de processus, puis contrôle qu'aucune donnée
     utilisateur n'a été écrite à côté du binaire : elles vont dans le
     dossier de données (LIDAR2MAP_HOME ici, voir _dossiers.py).

Appelé par release.yml après « Package » sur chaque runner, et utilisable
en local :

    python tests/exe_smoke.py dist/lidar2map-windows-x86_64.zip

Stdlib uniquement : le Python du runner n'a pas les dépendances de l'app.
Le dossier personnel est remplacé par un dossier temporaire (HOME,
USERPROFILE, LOCALAPPDATA, APPDATA) : un lancement local ne touche ni
l'installation ni les préférences réelles, et le ménage de l'étape 2 ne
vise que ce dossier temporaire. Sous macOS, lancer le binaire depuis un
shell ne passe pas par Gatekeeper : ce test ne prouve rien sur la
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

# Premier lancement d'un programme tout juste décompressé : l'antivirus
# (Windows) ou l'évaluation du .app (macOS) examinent ses fichiers, lents sur
# les runners macOS Intel.
DELAI_DEMARRAGE_S = 300
DELAI_FUSION_S = 300
DELAI_JAVA_S = 300

# Doivent aller dans le dossier de données (LIDAR2MAP_HOME ici), jamais à
# côté du binaire, qui peut être installé en lecture seule (Program Files),
# ni dans un .app, dont la signature ne couvre que son contenu d'origine.
DONNEES_UTILISATEUR = ("historique.json", "preferences.json", "Projets",
                       "logs", "cache", "production")

# Valeur donnée au programme (Linux) : les programmes du système doivent la
# recevoir telle quelle, sans les bibliothèques du binaire devant (étape 1b).
LD_LIBRARY_PATH_TEMOIN = "/opt/lidar2map-exe-smoke"

# Étape 4 : deux nœuds et une rue dans l'emprise donnée à mapfile-writer.
OSM_MINUSCULE = """<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6" generator="lidar2map exe_smoke">
  <bounds minlat="43.29" minlon="5.99" maxlat="43.31" maxlon="6.01"/>
  <node id="1" version="1" changeset="1" timestamp="2026-01-01T00:00:00Z" lat="43.295" lon="5.995"/>
  <node id="2" version="1" changeset="1" timestamp="2026-01-01T00:00:00Z" lat="43.305" lon="6.005"/>
  <way id="10" version="1" changeset="1" timestamp="2026-01-01T00:00:00Z">
    <nd ref="1"/>
    <nd ref="2"/>
    <tag k="highway" v="residential"/>
  </way>
</osm>
"""
EMPRISE_MAP = "43.29,5.99,43.31,6.01"       # minLat,minLon,maxLat,maxLon
# En-tête de tout fichier .map (format binaire de mapsforge).
MAGIE_MAP = b"mapsforge binary OSM"


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


def trouver_programme(dest: Path) -> tuple[Path, Path, Path]:
    """(programme, dossier de travail, ressources embarquées). Le dossier de
    travail est celui que calcule _runtime_paths.dossier_programme ; les
    ressources, sys._MEIPASS du programme : _internal/ à côté de lui, ou
    Contents/Frameworks dans un .app."""
    app = dest / "LIDAR2MAP.app"
    if app.is_dir():
        programme = app / "Contents" / "MacOS" / "lidar2map"
        ressources = app / "Contents" / "Frameworks"
        travail = dest                       # dossier qui contient le .app
    else:
        programme = next((candidat for motif in ("*/lidar2map.exe", "*/lidar2map")
                          for candidat in sorted(dest.glob(motif))
                          if candidat.is_file()), None)
        if programme is None:
            raise Echec(f"aucun programme lidar2map dans {dest}")
        ressources = programme.parent / "_internal"
        travail = programme.parent
    if not programme.is_file():
        raise Echec(f"programme introuvable : {programme}")
    if not ressources.is_dir():
        # Archive d'un lanceur <= 1.54 : un binaire et un bundle zippé.
        raise Echec(f"ressources embarquées introuvables : {ressources}")
    return programme, travail, ressources


def dossier_extraction(home: Path) -> Path:
    """Dossier où le lanceur d'une version <= 1.54 extrayait le programme
    (_bootstrap_runtime.chemins_desinstallation)."""
    if sys.platform == "win32":
        return home / "AppData" / "Local" / "lidar2map"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "lidar2map"
    return home / ".local" / "share" / "lidar2map"


def poser_restes_du_lanceur(home: Path, programme: Path) -> list[Path]:
    """Ce qu'un lanceur <= 1.54 laissait derrière lui, recréé avant le
    démarrage : son extraction, marquée .bundle_sha, et son bundle resté à
    côté du programme quand l'archive est décompressée par-dessus."""
    extraction = dossier_extraction(home)
    (extraction / "_internal").mkdir(parents=True)
    (extraction / ".bundle_sha").write_text("0" * 64 + "\n0\n", encoding="utf-8")
    restes = [extraction]
    # Sous macOS, le bundle vivait dans le .app, remplacé d'un bloc ; écrire
    # dans le nouveau casserait d'ailleurs sa signature.
    if programme.parent.name != "MacOS":
        bundle = programme.parent / "lidar2map_bundle.zip"
        bundle.write_bytes(b"PK\x05\x06" + bytes(18))     # zip vide
        restes.append(bundle)
    return restes


def environnement(racine: Path) -> tuple[dict, Path]:
    home = racine / "home"
    for sous_dossier in ("AppData/Local", "AppData/Roaming"):
        (home / sous_dossier).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(HOME=str(home), USERPROFILE=str(home),
               LOCALAPPDATA=str(home / "AppData" / "Local"),
               APPDATA=str(home / "AppData" / "Roaming"),
               # État et sorties (voir _dossiers.py). Indispensable même avec
               # les variables ci-dessus : sous Windows, platformdirs
               # interroge le shell, qui ignore LOCALAPPDATA et USERPROFILE.
               LIDAR2MAP_HOME=str(racine / "donnees"))
    for variable in ("LIDAR2MAP_WORK_DIR", "LIDAR2MAP_LANCEUR"):
        env.pop(variable, None)
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
    """Le programme lance ses traitements dans des processus enfants, et
    osmosis passe par un script qui lance java : tuer tout l'arbre, pas le
    parent seul."""
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


def attendre_fin(processus: subprocess.Popen, delai_s: float, quoi: str) -> int:
    try:
        return processus.wait(timeout=delai_s)
    except subprocess.TimeoutExpired:
        tuer_arbre(processus)
        raise Echec(f"{quoi} toujours en cours après {delai_s:.0f} s") from None


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


# ── Chaîne Java ────────────────────────────────────────────────────────────

def trouver_outil(racine: Path, nom: str) -> Path | None:
    """Même recherche que _osm_runtime : premier fichier de ce nom rangé
    dans un dossier bin/, sous la racine donnée."""
    for candidat in sorted(racine.rglob(nom)):
        if candidat.is_file() and "bin" in candidat.relative_to(racine).parts:
            return candidat
    return None


def chaine_java(ressources: Path, racine: Path) -> None:
    java = trouver_outil(ressources / "jre", "java.exe" if os.name == "nt" else "java")
    if java is None:
        raise Echec(f"aucun JRE embarqué sous {ressources / 'jre'}")
    version = subprocess.run([str(java), "-version"], capture_output=True,
                             text=True, errors="replace", timeout=DELAI_JAVA_S)
    if version.returncode != 0:
        raise Echec(f"java -version : code {version.returncode}\n"
                    f"{(version.stdout + version.stderr)[-2000:]}")
    premiere = (version.stderr or version.stdout or "?").splitlines()[0]
    print(f"   JRE : {premiere}", flush=True)

    osmosis = trouver_outil(ressources / "osmosis",
                            "osmosis.bat" if os.name == "nt" else "osmosis")
    if osmosis is None:
        raise Echec(f"osmosis absent sous {ressources / 'osmosis'}")
    tagmapping = ressources / "tagmapping-min.xml"
    if not tagmapping.is_file():
        raise Echec(f"tagmapping-min.xml absent de {ressources}")
    source, carte = racine / "minuscule.osm", racine / "minuscule.map"
    source.write_text(OSM_MINUSCULE, encoding="utf-8")
    # Comme _osm_map_pipeline et _osm_runtime.java_opts_extra : JAVA_HOME
    # désigne le JRE embarqué, et user.home les ressources du programme. Sans
    # ce second réglage, osmosis chargerait aussi le greffon d'un
    # ~/.openstreetmap/osmosis/plugins (runner de build, poste qui a fait
    # tourner les sources) et s'arrêterait sur « Task type "mapfile-writer"
    # already exists ». Java lit user.home dans le système, pas dans HOME ni
    # USERPROFILE : l'environnement isolé des autres étapes n'y suffit pas.
    maison = str(ressources).replace("\\", "/")
    env = dict(os.environ, JAVA_HOME=str(java.parent.parent),
               JAVA_OPTS=f'-Xmx1g "-Duser.home={maison}"')
    processus = lancer([str(osmosis), "--read-xml", f"file={source}",
                        "--mapfile-writer", f"file={carte}", f"bbox={EMPRISE_MAP}",
                        "type=ram", f"tag-conf-file={tagmapping}"],
                       env, racine, racine / "4_osmosis.log")
    code = attendre_fin(processus, DELAI_JAVA_S, "osmosis")
    if code != 0 or not carte.is_file():
        raise Echec(f"osmosis : code {code}, carte présente : {carte.is_file()}"
                    " (greffon mapwriter absent du classpath ?)")
    with open(carte, "rb") as fichier:
        entete = fichier.read(len(MAGIE_MAP))
    if entete != MAGIE_MAP:
        raise Echec(f"{carte.name} n'est pas une carte mapsforge : {entete!r}")
    print(f"   OK : {carte.name} écrite ({carte.stat().st_size} octets)", flush=True)


# ── Étapes ─────────────────────────────────────────────────────────────────

def etape(titre: str) -> None:
    print(f"\n== {titre}", flush=True)


def smoke(archive: Path, racine: Path) -> None:
    dest = racine / "archive"
    etape(f"extraction de {archive.name}")
    extraire(archive, dest)
    programme, travail, ressources = trouver_programme(dest)
    env, home = environnement(racine)
    restes = poser_restes_du_lanceur(home, programme)
    print(f"   programme : {programme}\n   travail   : {travail}", flush=True)
    options_gui = ["--serve-gui", "--no-browser", "--no-tray"]
    processus = None
    try:
        etape("1. démarrage du programme (serveur web)")
        port = port_libre()
        processus = lancer([str(programme), *options_gui, "--port", str(port)],
                           env, travail, racine / "1_demarrage.log")
        attendre_serveur(port, processus, DELAI_DEMARRAGE_S)
        aide = lire_json(f"http://127.0.0.1:{port}/api/help", 30)
        if not (isinstance(aide, str) and "lidar2map" in aide):
            raise Echec(f"/api/help inattendu : {str(aide)[:120]!r}")
        print(f"   OK : /api/init et /api/help sur le port {port}", flush=True)

        if sys.platform.startswith("linux"):
            etape("1b. programmes du système : LD_LIBRARY_PATH d'origine")
            # Désactiver le démarrage automatique lance systemctl --user (le
            # faux, ici) depuis le programme, dont le bootloader PyInstaller
            # a préfixé la variable de ses bibliothèques.
            poster_json(f"http://127.0.0.1:{port}/api/set-autostart", {"actif": False})
            sonde = racine / "systemctl.txt"
            recu = (sonde.read_text(encoding="utf-8").splitlines()
                    if sonde.is_file() else [])
            attendu = f"{LD_LIBRARY_PATH_TEMOIN}|{LD_LIBRARY_PATH_TEMOIN}"
            # Le second champ (LD_LIBRARY_PATH_ORIG, posé par le bootloader)
            # prouve que la variable avait bien été préfixée, et que le
            # programme a rendu la valeur d'origine.
            if not recu or any(ligne != attendu for ligne in recu):
                raise Echec(f"systemctl a reçu {recu}, attendu {attendu!r}"
                            " (LD_LIBRARY_PATH|LD_LIBRARY_PATH_ORIG)")
            print(f"   OK : systemctl lancé {len(recu)} fois avec la valeur d'origine",
                  flush=True)

        etape("2. ménage de ce que laissait un lanceur <= 1.54")
        encore = [str(chemin) for chemin in restes if chemin.exists()]
        if encore:
            raise Echec(f"restes du lanceur toujours présents : {', '.join(encore)}")
        print(f"   OK : {len(restes)} reste(s) retiré(s) au démarrage", flush=True)
    finally:
        if processus is not None:
            tuer_arbre(processus)

    etape("3. fusion de deux MBTiles (sqlite, Pillow, composition alpha)")
    opaque_a, opaque_b = png_uni((200, 30, 30, 255)), png_uni((30, 30, 200, 255))
    translucide = png_uni((30, 200, 30, 128))
    source_a, source_b = racine / "a.mbtiles", racine / "b.mbtiles"
    ecrire_mbtiles(source_a, {(0, 0): opaque_a, (1, 0): opaque_a})
    ecrire_mbtiles(source_b, {(1, 0): translucide, (2, 0): opaque_b})
    sortie = racine / "fusion.mbtiles"
    fusion = lancer([str(programme), "--merge", "--source", str(source_a), str(source_b),
                     "--output-file", str(sortie)], env, travail, racine / "3_fusion.log")
    code = attendre_fin(fusion, DELAI_FUSION_S, "--merge")
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

    etape("4. chaîne Java embarquée (JRE, osmosis, greffon mapwriter)")
    chaine_java(ressources, racine)

    etape("5. données utilisateur dans le dossier de données, pas à côté du binaire")
    for dossier in {travail, programme.parent}:
        intrus = [nom for nom in DONNEES_UTILISATEUR if (dossier / nom).exists()]
        if intrus:
            raise Echec(f"données utilisateur dans {dossier} : {', '.join(intrus)}")
    donnees = Path(env["LIDAR2MAP_HOME"])
    if not (donnees / "logs").is_dir():
        raise Echec(f"aucun dossier logs/ dans {donnees} : LIDAR2MAP_HOME ignoré ?")
    print(f"   OK : rien à côté du binaire, journaux dans {donnees}/logs", flush=True)


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
