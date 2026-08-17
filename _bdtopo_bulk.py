"""Découverte, téléchargement et extraction du GPKG BD TOPO départemental."""

from __future__ import annotations

import datetime
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependancesBdtopo:
    api_url: str
    download_base: str
    http_ua: str
    cache_root: object
    log_req: object
    chemin_part: object
    ouvrir_url: object
    stop_event: object
    formater_duree: object


@dataclass(frozen=True)
class DependancesOrchestrationBdtopo:
    """Coutures de l'orchestrateur bulk, injectées par la façade."""

    decouvrir_ressource: object
    telecharger_gpkg: object
    extraire_couche: object
    correspondance_couches: object


def telecharger_bdtopo_bulk(
    num_dep,
    couches_resolues,
    nom_zone,
    dossier_sortie,
    bbox_l93=None,
    ecraser=False,
    formats=None,
    *,
    dependances,
):
    """Orchestre l'acquisition GPKG puis l'extraction des couches demandées."""
    print(
        f"  Bulk BD TOPO GPKG department {num_dep} "
        "(WFS would be too slow at this scale)",
        flush=True,
    )
    url, nom = dependances.decouvrir_ressource(num_dep)
    if not url:
        return None
    gpkg_path = dependances.telecharger_gpkg(
        num_dep, url, nom, ecraser=ecraser
    )
    if not gpkg_path:
        return None

    sorties = []
    for typename, description in couches_resolues:
        layer_name = typename.split(":")[-1].lower()
        gpkg_layer = dependances.correspondance_couches.get(
            layer_name, layer_name
        )
        sortie_gz = (
            Path(dossier_sortie)
            / f"{nom_zone}_ign_{layer_name}.geojson.gz"
        )
        print(f"\n  [{description}]")
        resultat = dependances.extraire_couche(
            gpkg_path,
            gpkg_layer,
            sortie_gz,
            bbox_l93=bbox_l93,
            ecraser=ecraser,
            formats=formats,
        )
        if resultat:
            sorties.append(resultat)
    return sorties


def _cle_ressource(nom):
    match = re.search(r"BDTOPO_(\d+)-(\d+)_.*_(\d{4}-\d{2}-\d{2})$", nom)
    if not match:
        return "", (0, 0)
    majeur, mineur, date = match.groups()
    return date, (int(majeur), int(mineur))


def decouvrir_url_bdtopo_gpkg(num_dep, *, dependances):
    """Retourne l'URL et le nom du GPKG BD TOPO départemental le plus récent."""
    dep_padded = str(num_dep).zfill(3)
    zone = f"D{dep_padded}"
    try:
        api_url = (
            f"{dependances.api_url}?zone={zone}&format=GPKG"
            "&crs=LAMB93&page=1&limit=5"
        )
        requete = urllib.request.Request(
            api_url, headers={"User-Agent": dependances.http_ua}
        )
        with urllib.request.urlopen(requete, timeout=15) as response:
            racine = ET.fromstring(response.read())
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        noms = []
        for entree in racine.findall(".//atom:entry", namespace):
            titre = entree.findtext("atom:title", namespaces=namespace) or ""
            identifiant = entree.findtext("atom:id", namespaces=namespace) or ""
            for candidat in (titre, identifiant):
                if f"GPKG_LAMB93_{zone}" not in candidat:
                    continue
                for partie in candidat.strip("/").split("/"):
                    if f"GPKG_LAMB93_{zone}" in partie:
                        noms.append(
                            partie.replace(".7z", "").replace(".gpkg", "")
                        )
                        break
        if noms:
            noms.sort(key=_cle_ressource, reverse=True)
            nom = noms[0]
            url = f"{dependances.download_base}/{nom}/{nom}.7z"
            print(f"  BD TOPO {zone} GPKG : {nom}", flush=True)
            return url, nom
    except Exception as error:
        print(
            f"  ⚠ API IGN ({type(error).__name__}: {error}) "
            "— essai dates connues"
        )

    aujourd_hui = datetime.date.today()
    dates = []
    for delta in range(8):
        annee = aujourd_hui.year
        trimestre = ((aujourd_hui.month - 1) // 3) - delta
        while trimestre < 0:
            trimestre += 4
            annee -= 1
        mois = [3, 6, 9, 12][trimestre % 4]
        dates.append(f"{annee}-{mois:02d}-15")

    for majeur, mineur in sorted([(3, 5), (3, 4), (3, 3)], reverse=True):
        for date in dates:
            nom = (
                f"BDTOPO_{majeur}-{mineur}_TOUSTHEMES_GPKG_LAMB93_"
                f"{zone}_{date}"
            )
            url = f"{dependances.download_base}/{nom}/{nom}.7z"
            try:
                requete = urllib.request.Request(
                    url,
                    method="HEAD",
                    headers={"User-Agent": dependances.http_ua},
                )
                with urllib.request.urlopen(requete, timeout=10):
                    print(f"  BD TOPO {zone} : {nom}", flush=True)
                    return url, nom
            except Exception:
                continue
    print(f"  ERROR: BD TOPO GPKG archive not found for {num_dep}")
    return None, None


def _charger_py7zr():
    try:
        import py7zr
        return py7zr
    except ImportError:
        print("  Installing py7zr for .7z extraction...", flush=True)
        try:
            resultat = subprocess.run(
                [sys.executable, "-m", "pip", "install", "py7zr", "-q"],
                capture_output=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            print(
                "  ERROR: py7zr install timeout (>600s) - "
                "cannot extract the IGN .7z"
            )
            return None
        if resultat.returncode != 0:
            print("  ERROR: py7zr not installable - cannot extract the IGN .7z")
            return None
        import py7zr
        return py7zr


def telecharger_bdtopo_gpkg(num_dep, url, nom_ressource, ecraser=False, *,
                            dependances):
    """Télécharge et extrait atomiquement le GPKG BD TOPO dans le cache."""
    dep_padded = str(num_dep).zfill(3)
    cache_dir = Path(dependances.cache_root) / "bdtopo"
    cache_dir.mkdir(parents=True, exist_ok=True)
    gpkg_path = cache_dir / f"{nom_ressource}.gpkg"
    if ecraser and gpkg_path.exists():
        print(
            f"  GPKG cache: {gpkg_path.name} -> overwrite (re-download)",
            flush=True,
        )
    if (
        not ecraser
        and gpkg_path.exists()
        and gpkg_path.stat().st_size > 10_000_000
    ):
        print(
            f"  GPKG cache: {gpkg_path.name} "
            f"({gpkg_path.stat().st_size / 1e6:.0f} MB) reused",
            flush=True,
        )
        return gpkg_path

    py7zr = _charger_py7zr()
    if py7zr is None:
        return None
    archive_name = f"{nom_ressource}.7z"
    print(f"  Downloading BD TOPO D{dep_padded} (~200-800 MB)...", flush=True)
    dependances.log_req(url, "IGN bulk GPKG")
    archive_part = dependances.chemin_part(cache_dir / archive_name)
    debut = time.time()
    try:
        try:
            response = dependances.ouvrir_url(url, timeout=120)
        except urllib.error.HTTPError as error:
            print(f"  HTTP ERROR {error.code}: {url}")
            return None
        with response:
            total = int(response.headers.get("content-length") or 0)
            recus = 0
            dernier_affichage = 0.0
            with open(archive_part, "wb") as fichier:
                while True:
                    if dependances.stop_event.is_set():
                        archive_part.unlink(missing_ok=True)
                        return None
                    bloc = response.read(1 << 20)
                    if not bloc:
                        break
                    fichier.write(bloc)
                    recus += len(bloc)
                    maintenant = time.time()
                    if maintenant - dernier_affichage < 0.5:
                        continue
                    dernier_affichage = maintenant
                    ecoule = int(maintenant - debut)
                    if total:
                        pct = min(recus * 100 // total, 99)
                        barre = ("█" * (pct // 5)).ljust(20)
                        sys.stdout.write(
                            f"\r  [{barre}] {pct:3d}%  "
                            f"{recus / 1e6:.0f}/{total / 1e6:.0f} MB  "
                            f"{dependances.formater_duree(ecoule)}   "
                        )
                    else:
                        sys.stdout.write(
                            f"\r  {recus / 1e6:.0f} MB  "
                            f"{dependances.formater_duree(ecoule)}   "
                        )
                    sys.stdout.flush()
        sys.stdout.write("\r" + " " * 70 + "\r")
        sys.stdout.flush()
        if total and recus != total:
            raise OSError(f"archive incomplete: {recus}/{total} bytes")
        if not archive_part.exists() or archive_part.stat().st_size == 0:
            raise OSError("empty archive")
        print(
            f"  ✓ {archive_name}  ({archive_part.stat().st_size / 1e6:.0f} MB)  "
            f"{dependances.formater_duree(int(time.time() - debut))}",
            flush=True,
        )
    except BaseException as error:
        archive_part.unlink(missing_ok=True)
        if not isinstance(error, (OSError, urllib.error.URLError)):
            raise
        print(f"  ERROR downloading ({type(error).__name__}): {error}")
        return None

    print(f"  Extracting GPKG from {archive_name}...", flush=True)
    temporaire = cache_dir / (
        f"_extract_{os.getpid()}_{uuid.uuid4().hex[:12]}.part"
    )
    try:
        with py7zr.SevenZipFile(archive_part, mode="r") as archive:
            membres = [
                nom for nom in archive.getnames() if nom.lower().endswith(".gpkg")
            ]
            if not membres:
                print("  ERROR: no .gpkg in the 7z archive")
                return None
            if len(membres) > 1:
                print(f"  ({len(membres)} .gpkg in archive - using {membres[0]})")
            temporaire.mkdir(parents=True, exist_ok=True)
            archive.extract(targets=[membres[0]], path=temporaire)

        extracted = temporaire / membres[0]
        if not extracted.exists():
            print("  ERROR: .gpkg not found after extraction")
            return None
        if extracted.stat().st_size < 10_000_000:
            print(
                f"  ERROR: extracted GPKG too small ({extracted.stat().st_size} B) "
                "- discarded"
            )
            return None
        try:
            connexion = sqlite3.connect(f"file:{extracted}?mode=ro", uri=True)
            try:
                connexion.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
            finally:
                connexion.close()
        except Exception as error:
            print(f"  ERROR: extracted GPKG unreadable ({error}) - discarded")
            return None
        extracted.replace(gpkg_path)
        print(
            f"  ✓ GPKG extrait : {gpkg_path.name} "
            f"({gpkg_path.stat().st_size / 1e6:.0f} MB)",
            flush=True,
        )
        return gpkg_path
    except BaseException as error:
        if not isinstance(error, Exception):
            raise
        print(f"  ERROR .7z extraction ({type(error).__name__}): {error}")
        return None
    finally:
        archive_part.unlink(missing_ok=True)
        shutil.rmtree(temporaire, ignore_errors=True)
