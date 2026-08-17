"""Téléchargement WFS paginé et publication GeoJSON atomique."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependancesWfs:
    wfs_url: object
    http_ua: str
    page_size: int
    chemin_part: object
    stop_event: object
    gunzip_vers_fichier: object
    gzip_depuis_fichier: object
    log_req: object
    formater_duree: object


def _sorties_wfs(typename, nom_zone, dossier_sortie):
    """Calcule le stem sans collision et les deux chemins de sortie."""
    namespace, separateur, suffixe = typename.partition(":")
    if separateur and namespace.strip().upper() != "BDTOPO_V3":
        empreinte = hashlib.md5(typename.encode("utf-8")).hexdigest()[:6]
        court = re.sub(
            r"[^a-z0-9]+", "_", f"{namespace}_{suffixe}".lower()
        ).strip("_") + f"_{empreinte}"
    else:
        court = (suffixe or namespace).lower()
    sortie = Path(dossier_sortie) / f"{nom_zone}_ign_{court}.geojson"
    return court, sortie, Path(str(sortie) + ".gz")


def telecharger_wfs(typename, lon_min, lat_min, lon_max, lat_max,
                    nom_zone, dossier_sortie, ecraser_telechargement=False,
                    formats=None, *, dependances):
    """Télécharge un flux WFS paginé vers GeoJSON gzip et/ou brut."""
    wfs_url = dependances.wfs_url
    http_ua = dependances.http_ua
    page_size = dependances.page_size
    chemin_part = dependances.chemin_part
    stop_event = dependances.stop_event
    gunzip_vers_fichier = dependances.gunzip_vers_fichier
    gzip_depuis_fichier = dependances.gzip_depuis_fichier
    log_req = dependances.log_req
    formater_duree = dependances.formater_duree

    dossier_sortie = Path(dossier_sortie)
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    if formats is None:
        formats = ["gz"]
    formats = [f.lower() for f in formats if f.lower() in ("gz", "geojson")]
    if not formats:
        formats = ["gz"]
    ecrire_gz = "gz" in formats
    ecrire_geojson = "geojson" in formats
    layer_short, sortie, sortie_gz = _sorties_wfs(
        typename, nom_zone, dossier_sortie
    )

    if ecraser_telechargement:
        for path in (sortie_gz, sortie):
            if path.exists():
                print(f"  {path.name} -> overwrite")

    if not ecraser_telechargement:
        manque_gz = ecrire_gz and not sortie_gz.exists()
        manque_raw = ecrire_geojson and not sortie.exists()
        if not manque_gz and not manque_raw:
            present = sortie_gz if sortie_gz.exists() else sortie
            print(f"  {present.name} -> already present")
            return present
        if sortie_gz.exists() or sortie.exists():
            try:
                if manque_raw and sortie_gz.exists():
                    gunzip_vers_fichier(sortie_gz, sortie)
                    print(f"  {sortie.name} -> rebuilt from {sortie_gz.name}")
                if manque_gz and sortie.exists():
                    gzip_depuis_fichier(sortie, sortie_gz)
                    print(f"  {sortie_gz.name} -> rebuilt from {sortie.name}")
                return sortie_gz if sortie_gz.exists() else sortie
            except OSError as error:
                print(f"  ⚠ Local rebuild failed ({error}) - WFS re-download")

    print(f"  WFS {typename}...", flush=True)
    log_req(f"{wfs_url}?SERVICE=WFS&TYPENAMES={typename}&...", "WFS IGN")
    startindex = 0
    n_features = 0
    n_pages = 0
    total_attendu = None
    debut = time.time()
    bbox = f"{lon_min},{lat_min},{lon_max},{lat_max},EPSG:4326"

    params_hits = {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": typename, "RESULTTYPE": "hits", "COUNT": "0",
        "BBOX": bbox,
    }
    try:
        url_hits = wfs_url + "?" + urllib.parse.urlencode(params_hits)
        req_hits = urllib.request.Request(
            url_hits, headers={"User-Agent": http_ua}
        )
        with urllib.request.urlopen(req_hits, timeout=15) as response:
            donnees = json.loads(response.read())
        nombre = donnees.get("numberMatched", donnees.get("totalFeatures"))
        if nombre is not None:
            total_attendu = int(nombre)
            n_pages = max(1, (total_attendu + page_size - 1) // page_size)
            print(
                f"  WFS {typename.split(':')[-1]} : {total_attendu} "
                f"features attendues ({n_pages} page{'s' if n_pages > 1 else ''})",
                flush=True,
            )
    except Exception:
        pass

    sortie_gz_part = chemin_part(sortie_gz)
    sortie_gz_part.parent.mkdir(parents=True, exist_ok=True)
    crs_obj = {
        "type": "name",
        "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
    }
    header = (
        '{"type":"FeatureCollection","name":'
        + json.dumps(layer_short, ensure_ascii=False)
        + ',"crs":' + json.dumps(crs_obj, ensure_ascii=False, separators=(",", ":"))
        + ',"features":['
    ).encode("utf-8")

    sortie_ouverte = None
    try:
        sortie_ouverte = gzip.open(sortie_gz_part, "wb", compresslevel=6)
        sortie_ouverte.write(header)
        premiere = True
        while True:
            if stop_event.is_set():
                if n_features:
                    print(
                        f"  WFS interrupted - {n_features} features retrieved "
                        "(partial .gz output)"
                    )
                raise KeyboardInterrupt(f"WFS {typename} interrompu")

            params = {
                "SERVICE": "WFS", "VERSION": "2.0.0",
                "REQUEST": "GetFeature", "TYPENAMES": typename,
                "OUTPUTFORMAT": "application/json", "SRSNAME": "EPSG:4326",
                "BBOX": bbox, "COUNT": str(page_size),
                "STARTINDEX": str(startindex),
            }
            url = wfs_url + "?" + urllib.parse.urlencode(params)
            requete = urllib.request.Request(
                url, headers={"User-Agent": http_ua}
            )
            donnees = None
            for tentative in range(3):
                try:
                    with urllib.request.urlopen(requete, timeout=60) as response:
                        donnees = json.loads(response.read())
                    break
                except (
                    urllib.error.URLError,
                    urllib.error.HTTPError,
                    json.JSONDecodeError,
                    TimeoutError,
                    OSError,
                ) as error:
                    if tentative < 2:
                        time.sleep(3)
                    else:
                        print(
                            f"\n  ERROR WFS ({typename}): "
                            f"{type(error).__name__}: {error}"
                        )

            if donnees is None:
                print(
                    f"  ✗ WFS {typename}: page failed after {n_features} "
                    "features - output discarded (rerun to retry)"
                )
                sortie_ouverte.close()
                sortie_ouverte = None
                sortie_gz_part.unlink(missing_ok=True)
                return None

            page = donnees.get("features", [])
            if not page:
                break
            if total_attendu is None:
                nombre = donnees.get(
                    "numberMatched", donnees.get("totalFeatures")
                )
                if nombre is not None:
                    try:
                        total_attendu = int(nombre)
                    except (ValueError, TypeError):
                        pass

            for feature in page:
                if not premiere:
                    sortie_ouverte.write(b",")
                premiere = False
                sortie_ouverte.write(
                    json.dumps(
                        feature, ensure_ascii=False, separators=(",", ":")
                    ).encode("utf-8")
                )
                n_features += 1

            ecoule = int(time.time() - debut)
            n_pages += 1
            if total_attendu:
                pct = min(n_features * 100 // total_attendu, 99)
                barre = ("█" * (pct // 5)).ljust(20)
                print(
                    f"  WFS  [{barre}] {pct:3d}%  {n_features}/{total_attendu}  "
                    f"page {n_pages}  {formater_duree(ecoule)}",
                    flush=True,
                )
            else:
                print(
                    f"  WFS  page {n_pages}  {n_features} features  "
                    f"{formater_duree(ecoule)}",
                    flush=True,
                )

            startindex += len(page)
            if total_attendu is not None:
                if n_features >= total_attendu:
                    break
            elif len(page) < page_size:
                break
            time.sleep(0.2)

        if total_attendu is not None and n_features < total_attendu:
            print(
                f"  ✗ WFS {typename}: {n_features}/{total_attendu} features "
                "- truncated output discarded (rerun to retry)"
            )
            sortie_ouverte.close()
            sortie_ouverte = None
            sortie_gz_part.unlink(missing_ok=True)
            return None
        sortie_ouverte.write(b"]}")
        sortie_ouverte.close()
        sortie_ouverte = None
    except BaseException:
        if sortie_ouverte is not None:
            try:
                sortie_ouverte.close()
            except Exception:
                pass
        sortie_gz_part.unlink(missing_ok=True)
        raise

    source_gz = sortie_gz_part
    if ecrire_gz:
        try:
            sortie_gz_part.replace(sortie_gz)
        except BaseException:
            sortie_gz_part.unlink(missing_ok=True)
            raise
        source_gz = sortie_gz

    principal = None
    if ecrire_gz:
        taille_ko = sortie_gz.stat().st_size // 1024
        print(
            f"  {sortie_gz.name} : {n_features} features  ({taille_ko} Ko)  "
            f"{formater_duree(int(time.time() - debut))}"
        )
        principal = sortie_gz
    if ecrire_geojson:
        try:
            gunzip_vers_fichier(source_gz, sortie)
        except BaseException:
            if not ecrire_gz:
                sortie_gz_part.unlink(missing_ok=True)
            raise
        taille_ko = sortie.stat().st_size // 1024
        print(f"  {sortie.name} : {n_features} features  ({taille_ko} Ko)")
        if principal is None:
            principal = sortie
    if not ecrire_gz:
        sortie_gz_part.unlink(missing_ok=True)
    return principal
