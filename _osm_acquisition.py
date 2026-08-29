"""Résolution et acquisition atomique d'une source PBF OSM.

Ce module choisit une source explicite ou un extrait Geofabrik, applique la
politique de cache et publie un téléchargement complet. Il ne calcule aucune
emprise de sortie et ne génère aucun livrable OSM.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
import urllib.error


@dataclass(frozen=True)
class DependancesAcquisitionOsm:
    """Coutures nécessaires à la résolution et au téléchargement du PBF."""

    provider: Any
    geofabrik: Mapping[str, str]
    geofabrik_base_url: str
    geofabrik_base_url_root: str
    dossier_cache: Path
    lamb93_vers_wgs84: Callable[[float, float], Any]
    urlopen: Callable[..., Any]
    charger_json: Callable[[Any], Any]
    maintenant: Callable[[], float]
    arret_demande: Callable[[], bool]
    journaliser_requete: Callable[..., Any]
    formater_duree: Callable[[float], str]
    sortie: Any
    ouvrir_fichier: Callable[..., Any]
    imprimer: Callable[..., Any] = print


def acquerir_source_osm(args, cx, cy, *, dependances):
    """Retourne le PBF utilisable, ou ``None`` si l'acquisition échoue."""
    d = dependances
    pbf = None

    if args.source and Path(args.source).suffix.lower() in (".pbf", ".osm"):
        pbf = Path(args.source)
        if not pbf.exists():
            d.imprimer(f"  ERROR: PBF file not found: {pbf}")
            pbf = None
        return pbf

    provider_country = (
        getattr(d.provider, "COUNTRY", "fr") or "fr"
    ).lower()
    if provider_country != "fr":
        d.imprimer(
            "  OSM auto-download is France-only for now "
            f"(provider country: {provider_country})."
        )
        d.imprimer(
            "  The department lookup and the Geofabrik URL table are "
            "French; the fallback would fetch a 4 GB FRENCH PBF and "
            "produce an overlay with no feature in your area."
        )
        d.imprimer(
            "  Workaround: grab the PBF for your area at "
            "https://download.geofabrik.de/ then pass it with "
            "--source <file>.pbf"
        )
        return None

    zone_region = getattr(args, "zone_region", None)
    num_dep = getattr(args, "zone_departement", None)
    if zone_region:
        region_slug = zone_region.strip().lower()
    else:
        if not num_dep:
            try:
                clon, clat = d.lamb93_vers_wgs84(cx, cy)
                url_rev = (
                    "https://geo.api.gouv.fr/communes"
                    f"?lon={clon:.5f}&lat={clat:.5f}"
                    "&fields=codeDepartement&format=json"
                )
                with d.urlopen(url_rev, timeout=10) as response:
                    reverse_data = d.charger_json(response.read())
                if reverse_data:
                    num_dep = reverse_data[0].get("codeDepartement")
                    d.imprimer(
                        f"  Department detected: {num_dep}",
                        flush=True,
                    )
            except Exception as exc:
                d.imprimer(f"  Reverse geocoding failed ({exc})")
        region_slug = d.geofabrik.get(num_dep) if num_dep else None

    if not region_slug:
        d.imprimer(f"  Department {num_dep} not found in the Geofabrik table.")
        d.imprimer("  Falling back to the national France PBF (~4 GB).")
        url_pbf = f"{d.geofabrik_base_url_root}/france-latest.osm.pbf"
        pbf_name = "france-latest.osm.pbf"
    else:
        url_pbf = f"{d.geofabrik_base_url}/{region_slug}-latest.osm.pbf"
        pbf_name = f"{region_slug}-latest.osm.pbf"

    osm_dir = d.dossier_cache / "osm_vecteur"
    osm_dir.mkdir(parents=True, exist_ok=True)
    pbf = osm_dir / pbf_name

    seuil_pbf = 1_000_000
    force_pbf = bool(getattr(args, "telechargement_ecraser", False))
    pbf_age_j = (
        (d.maintenant() - pbf.stat().st_mtime) / 86400.0
        if pbf.exists()
        else 0.0
    )
    if pbf.exists() and pbf.stat().st_size >= seuil_pbf and not force_pbf:
        d.imprimer(
            f"  Existing PBF: {pbf.name}  "
            f"({pbf.stat().st_size / 1e9:.1f} GB, {pbf_age_j:.0f} days old)"
        )
        if pbf_age_j > 30:
            d.imprimer(
                "  Note: Geofabrik '-latest' is refreshed daily; this "
                f"cache is {pbf_age_j:.0f} days old. Pass "
                "--download-overwrite to refresh the OSM data."
            )
        return pbf

    if pbf.exists() and force_pbf and pbf.stat().st_size >= seuil_pbf:
        d.imprimer(
            f"  --download-overwrite: refreshing PBF {pbf.name} "
            f"({pbf_age_j:.0f} days old)"
        )
        pbf.unlink()
    elif pbf.exists():
        d.imprimer(
            f"  Truncated PBF ({pbf.stat().st_size} bytes) - re-downloading."
        )
        pbf.unlink()

    d.journaliser_requete(str(url_pbf), "Geofabrik")
    d.imprimer(f"  Downloading {url_pbf}...")
    d.imprimer(f"  Destination : {pbf}", flush=True)
    pbf_part = pbf.parent / (pbf.name + ".part")
    try:
        taille_dl = 0
        t0_dl = d.maintenant()
        pct_last = -1
        with d.urlopen(url_pbf, timeout=60) as response, d.ouvrir_fichier(
            pbf_part,
            "wb",
        ) as output:
            total_size = int(response.headers.get("content-length", 0))
            chunk = 65536
            while True:
                if d.arret_demande():
                    raise KeyboardInterrupt(
                        "PBF Geofabrik download interrupted"
                    )
                data = response.read(chunk)
                if not data:
                    break
                output.write(data)
                taille_dl += len(data)
                if total_size:
                    pct = taille_dl * 100 // total_size
                    mb = taille_dl / 1e6
                    total_mb = total_size / 1e6
                    if pct >= pct_last + 5:
                        pct_last = pct
                        line = f"  {mb:.0f} / {total_mb:.0f} MB  {pct}%"
                        d.sortie.write(f"\r{line}")
                        d.sortie.flush()

        d.sortie.write("\r" + " " * 40 + "\r")
        d.imprimer(
            f"  Telecharge : {pbf.name}  "
            f"({taille_dl / 1e6:.0f} MB)  "
            f"{d.formater_duree(d.maintenant() - t0_dl)}"
        )
        if (
            taille_dl < seuil_pbf
            or (total_size and taille_dl != total_size)
        ):
            d.imprimer(
                f"  ERROR: incomplete PBF ({taille_dl} bytes"
                + (f" / {total_size} expected" if total_size else "")
                + ") : download failed (network? Geofabrik access?)."
            )
            pbf_part.unlink(missing_ok=True)
            return None
        pbf_part.replace(pbf)
        return pbf
    except KeyboardInterrupt:
        pbf_part.unlink(missing_ok=True)
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        d.imprimer(
            f"\n  ERROR downloading PBF ({type(exc).__name__}) : {exc}"
        )
        pbf_part.unlink(missing_ok=True)
        return None
