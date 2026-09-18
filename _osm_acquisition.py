"""Résolution et acquisition atomique d'une source PBF OSM.

Ce module choisit une source explicite ou un extrait Geofabrik, applique la
politique de cache et publie un téléchargement complet. Il ne calcule aucune
emprise de sortie et ne génère aucun livrable OSM.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
import urllib.error


# ── Geofabrik : département → région (URL slug) ──────────────────────────────
# Table statique (135 entries) construite une seule fois à l'import au lieu
# d'être recréée à chaque appel d'`if args.osm:` dans main().
GEOFABRIK = {
    # !! Geofabrik utilise les ANCIENNES régions administratives (pré-réforme 2016).
    # Les nouvelles régions (Occitanie, Nouvelle-Aquitaine, Grand Est, etc.)
    # n'existent PAS sur Geofabrik — chaque département pointe vers son ancienne région.
    # Source : https://download.geofabrik.de/europe/france.html

    # Rhône-Alpes (≠ Auvergne-Rhône-Alpes)
    "01": "rhone-alpes",           # Ain
    "07": "rhone-alpes",           # Ardèche
    "26": "rhone-alpes",           # Drôme
    "38": "rhone-alpes",           # Isère
    "42": "rhone-alpes",           # Loire
    "69": "rhone-alpes",           # Rhône
    "73": "rhone-alpes",           # Savoie
    "74": "rhone-alpes",           # Haute-Savoie
    # Auvergne (≠ Auvergne-Rhône-Alpes)
    "03": "auvergne",              # Allier
    "15": "auvergne",              # Cantal
    "43": "auvergne",              # Haute-Loire
    "63": "auvergne",              # Puy-de-Dôme
    # Bourgogne (≠ Bourgogne-Franche-Comté)
    "21": "bourgogne",             # Côte-d'Or
    "58": "bourgogne",             # Nièvre
    "71": "bourgogne",             # Saône-et-Loire
    "89": "bourgogne",             # Yonne
    # Franche-Comté (≠ Bourgogne-Franche-Comté)
    "25": "franche-comte",         # Doubs
    "39": "franche-comte",         # Jura
    "70": "franche-comte",         # Haute-Saône
    "90": "franche-comte",         # Territoire de Belfort
    # Bretagne (inchangée)
    "22": "bretagne",              # Côtes-d'Armor
    "29": "bretagne",              # Finistère
    "35": "bretagne",              # Ille-et-Vilaine
    "56": "bretagne",              # Morbihan
    # Centre (Geofabrik utilise "centre", pas "centre-val-de-loire")
    "18": "centre",                # Cher
    "28": "centre",                # Eure-et-Loir
    "36": "centre",                # Indre
    "37": "centre",                # Indre-et-Loire
    "41": "centre",                # Loir-et-Cher
    "45": "centre",                # Loiret
    # Corse (inchangée)
    "2A": "corse",                 # Corse-du-Sud
    "2B": "corse",                 # Haute-Corse
    # Alsace (≠ Grand Est)
    "67": "alsace",                # Bas-Rhin
    "68": "alsace",                # Haut-Rhin
    # Champagne-Ardenne (≠ Grand Est)
    "08": "champagne-ardenne",     # Ardennes
    "10": "champagne-ardenne",     # Aube
    "51": "champagne-ardenne",     # Marne
    "52": "champagne-ardenne",     # Haute-Marne
    # Lorraine (≠ Grand Est)
    "54": "lorraine",              # Meurthe-et-Moselle
    "55": "lorraine",              # Meuse
    "57": "lorraine",              # Moselle
    "88": "lorraine",              # Vosges
    # Nord-Pas-de-Calais (≠ Hauts-de-France)
    "59": "nord-pas-de-calais",    # Nord
    "62": "nord-pas-de-calais",    # Pas-de-Calais
    # Picardie (≠ Hauts-de-France)
    "02": "picardie",              # Aisne
    "60": "picardie",              # Oise
    "80": "picardie",              # Somme
    # Île-de-France (inchangée)
    "75": "ile-de-france",         # Paris
    "77": "ile-de-france",         # Seine-et-Marne
    "78": "ile-de-france",         # Yvelines
    "91": "ile-de-france",         # Essonne
    "92": "ile-de-france",         # Hauts-de-Seine
    "93": "ile-de-france",         # Seine-Saint-Denis
    "94": "ile-de-france",         # Val-de-Marne
    "95": "ile-de-france",         # Val-d'Oise
    # Haute-Normandie (≠ Normandie)
    "27": "haute-normandie",       # Eure
    "76": "haute-normandie",       # Seine-Maritime
    # Basse-Normandie (≠ Normandie)
    "14": "basse-normandie",       # Calvados
    "50": "basse-normandie",       # Manche
    "61": "basse-normandie",       # Orne
    # Aquitaine (≠ Nouvelle-Aquitaine)
    "24": "aquitaine",             # Dordogne
    "33": "aquitaine",             # Gironde
    "40": "aquitaine",             # Landes
    "47": "aquitaine",             # Lot-et-Garonne
    "64": "aquitaine",             # Pyrénées-Atlantiques
    # Limousin (≠ Nouvelle-Aquitaine)
    "19": "limousin",              # Corrèze
    "23": "limousin",              # Creuse
    "87": "limousin",              # Haute-Vienne
    # Poitou-Charentes (≠ Nouvelle-Aquitaine)
    "16": "poitou-charentes",      # Charente
    "17": "poitou-charentes",      # Charente-Maritime
    "79": "poitou-charentes",      # Deux-Sèvres
    "86": "poitou-charentes",      # Vienne
    # Languedoc-Roussillon (≠ Occitanie)
    "11": "languedoc-roussillon",  # Aude
    "30": "languedoc-roussillon",  # Gard
    "34": "languedoc-roussillon",  # Hérault
    "48": "languedoc-roussillon",  # Lozère
    "66": "languedoc-roussillon",  # Pyrénées-Orientales
    # Midi-Pyrénées (≠ Occitanie)
    "09": "midi-pyrenees",         # Ariège
    "12": "midi-pyrenees",         # Aveyron
    "31": "midi-pyrenees",         # Haute-Garonne
    "32": "midi-pyrenees",         # Gers
    "46": "midi-pyrenees",         # Lot
    "65": "midi-pyrenees",         # Hautes-Pyrénées
    "81": "midi-pyrenees",         # Tarn
    "82": "midi-pyrenees",         # Tarn-et-Garonne
    # Pays de la Loire (inchangé)
    "44": "pays-de-la-loire",      # Loire-Atlantique
    "49": "pays-de-la-loire",      # Maine-et-Loire
    "53": "pays-de-la-loire",      # Mayenne
    "72": "pays-de-la-loire",      # Sarthe
    "85": "pays-de-la-loire",      # Vendée
    # Provence-Alpes-Côte d'Azur (inchangée)
    "04": "provence-alpes-cote-d-azur",  # Alpes-de-Haute-Provence
    "05": "provence-alpes-cote-d-azur",  # Hautes-Alpes
    "06": "provence-alpes-cote-d-azur",  # Alpes-Maritimes
    "13": "provence-alpes-cote-d-azur",  # Bouches-du-Rhône
    "83": "provence-alpes-cote-d-azur",  # Var
    "84": "provence-alpes-cote-d-azur",  # Vaucluse
    # DOM/TOM (extraits Geofabrik séparés)
    "971": "guadeloupe",
    "972": "martinique",
    "973": "guyane",
    "974": "reunion",
    "976": "mayotte",
}
GEOFABRIK_BASE_URL = "https://download.geofabrik.de/europe/france"
GEOFABRIK_BASE_URL_ROOT = "https://download.geofabrik.de/europe"


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
