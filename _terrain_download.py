"""Orchestration hors réseau du téléchargement des dalles terrain.

Les moteurs de téléchargement direct, COG et COPC restent dans la façade
``lidar2map``. Ce module choisit le moteur, borne le pool, agrège les statuts et
publie la preuve ``dalles_zone.txt``. Toutes les coutures applicatives sont
injectées afin de conserver les monkeypatches historiques.
"""

from dataclasses import dataclass
from pathlib import Path


def dalles_zone_entete(bbox, provider_code):
    """Construit l'en-tête bbox/provider d'un inventaire de zone."""
    return (
        f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}\n"
        f"# provider:{provider_code}"
    )


def dalles_zone_hdr_ok(lignes, bbox, provider_code):
    """Valide l'en-tête, en acceptant les anciens fichiers sans provider."""
    attendu = (
        f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
    )
    if not lignes or lignes[0].strip() != attendu:
        return False
    for ligne in lignes[1:3]:
        if ligne.startswith("# provider:"):
            return ligne.strip() == f"# provider:{provider_code}"
    return True


def ecrire_dalles_zone(
    path,
    bbox,
    noms,
    *,
    provider_code,
    ecrire_texte_atomique,
    creer_fichier,
):
    """Publie atomiquement la liste complète et normalisée d'une zone."""
    contenu = (
        dalles_zone_entete(bbox, provider_code)
        + "\n"
        + "\n".join(sorted(set(noms)))
    )
    ecrire_texte_atomique(path, contenu)
    creer_fichier(Path(path))


def lister_dalles_zone(
    noms_attendus,
    dossier_dalles,
    dossier_ville,
    bbox,
    *,
    hdr_ok,
    chemin_dalle,
    seuil_dalle_valide,
):
    """Retourne les dalles valides de la zone présentes sur disque."""
    noms_zone = set()
    inventaire = dossier_ville / "dalles_zone.txt"
    if inventaire.exists():
        lignes = inventaire.read_text(encoding="utf-8").splitlines()
        if hdr_ok(lignes, bbox):
            noms_zone = {
                nom.strip()
                for nom in lignes
                if nom.strip() and not nom.startswith("#")
            }
    if not noms_zone:
        noms_zone = set(noms_attendus)

    dalles = []
    for nom in noms_zone:
        try:
            chemin = chemin_dalle(dossier_dalles, nom)
            if chemin.exists() and chemin.stat().st_size > seuil_dalle_valide:
                dalles.append(chemin)
        except (OSError, ValueError):
            continue
    return sorted(dalles)


@dataclass(frozen=True)
class DependancesTelechargementTerrain:
    provider: object
    nom_dalle_sur: object
    chemin_dalle: object
    seuil_dalle_valide: int
    telecharger_cog_fenetre: object
    telecharger_copc_fenetre: object
    telecharger_dalle_directe: object
    dl_workers_effectif: object
    hms: object
    laz_prof_resume: object
    ecrire_dalles_zone: object
    creer_fichiers: object
    thread_pool_executor: object
    as_completed: object
    time: object


def dl_workers_effectif(workers, dl_cap, lp):
    """Calcule le nombre de tâches de téléchargement concurrentes.

    Un plafond provider positif gagne toujours. ``laz_parallel`` peut relever
    le parallélisme du pool partagé, mais jamais au-delà de ce plafond.
    """
    if isinstance(dl_cap, int) and dl_cap > 0:
        return min(dl_cap, max(min(workers, dl_cap), lp))
    return max(workers, lp)


def telecharger_dalles_zone(
    dalles_dict,
    bbox,
    dossier_dalles,
    dossier_ville,
    args,
    quiet=False,
    *,
    dependances,
):
    """Orchestre les téléchargements d'une zone et persiste leur preuve."""
    d = dependances
    provider = d.provider
    ok = skip = absent = erreur = 0
    a_telecharger = []

    dict_sur = {
        nom: url
        for nom, url in dalles_dict.items()
        if d.nom_dalle_sur(nom)
    }
    if len(dict_sur) < len(dalles_dict):
        nb_rejetes = len(dalles_dict) - len(dict_sur)
        print(
            f"  WARNING: {nb_rejetes} tile(s) with unsafe name(s) skipped "
            f"(path traversal guard)"
        )
    dalles_dict = dict_sur

    force_dl = bool(args.telechargement_forcer or args.telechargement_ecraser)
    for nom, url in dalles_dict.items():
        chemin = d.chemin_dalle(dossier_dalles, nom)
        if (
            force_dl
            or not chemin.exists()
            or chemin.stat().st_size < d.seuil_dalle_valide
        ):
            a_telecharger.append((nom, url))
        else:
            skip += 1

    nb_total = len(a_telecharger)
    largeur = 30
    done = 0
    debut = d.time.time()

    def afficher_barre(nb_faits):
        if quiet:
            return
        pct = int(nb_faits * 100 / max(nb_total, 1))
        bars = int(nb_faits * largeur / max(nb_total, 1))
        ecoule = int(d.time.time() - debut)
        barre = "█" * bars + "░" * (largeur - bars)
        print(
            f"\r  LiDAR tiles [{barre}] {pct:3d}%  {nb_faits}/{nb_total}  "
            f"{d.hms(ecoule)}",
            end="",
            flush=True,
        )

    cog_windowed = getattr(provider, "COG_WINDOWED", False)
    dl_cap = getattr(provider, "DOWNLOAD_WORKERS_MAX", None)
    laz_parallel = getattr(args, "laz_parallel", 1)
    dl_workers = d.dl_workers_effectif(args.workers, dl_cap, laz_parallel)

    if a_telecharger:
        if dl_workers < args.workers:
            print(
                f"  Note: capping downloads to {dl_workers} parallel "
                f"(large point-cloud tiles, avoids server throttling)"
            )
        if laz_parallel > dl_workers:
            print(
                f"  Note: --laz-parallel {laz_parallel} limited to "
                f"{dl_workers} here (provider download cap; conversion "
                f"shares the download pool)"
            )
        with d.thread_pool_executor(max_workers=dl_workers) as executor:
            if cog_windowed:
                futures = {
                    executor.submit(
                        d.telecharger_cog_fenetre,
                        nom,
                        url,
                        dossier_dalles,
                        bbox,
                        force_dl,
                    ): nom
                    for nom, url in a_telecharger
                }
            elif getattr(provider, "COPC_WINDOWED", False):
                futures = {
                    executor.submit(
                        d.telecharger_copc_fenetre,
                        nom,
                        url,
                        dossier_dalles,
                        bbox,
                        force_dl,
                    ): nom
                    for nom, url in a_telecharger
                }
            else:
                futures = {
                    executor.submit(
                        d.telecharger_dalle_directe,
                        nom,
                        url,
                        dossier_dalles,
                        force_dl,
                        args.telechargement_compresser,
                    ): nom
                    for nom, url in a_telecharger
                }
            for future in d.as_completed(futures):
                resultat = future.result()
                done += 1
                if resultat == "ok":
                    ok += 1
                elif resultat == "skip":
                    skip += 1
                elif resultat == "absent":
                    absent += 1
                else:
                    erreur += 1
                afficher_barre(done)

    if nb_total > 0:
        if not quiet:
            print()
            print(
                f"  Downloaded: {ok}  Cache: {skip}  Missing: {absent}  "
                f"Errors: {erreur}"
            )
        d.laz_prof_resume(d.time.time() - debut, dl_workers, laz_parallel)

    if erreur > 0:
        raise RuntimeError(
            f"{erreur} tile download error(s) - pipeline stopped before "
            f"shading/tiling (rerun to retry the failed tiles; successful "
            f"ones are cached)"
        )

    noms_persistance = []
    for nom in dalles_dict:
        chemin = d.chemin_dalle(dossier_dalles, nom)
        if chemin.exists() and chemin.stat().st_size > d.seuil_dalle_valide:
            noms_persistance.append(nom)
    if noms_persistance:
        d.ecrire_dalles_zone(
            dossier_ville / "dalles_zone.txt", bbox, noms_persistance
        )

    chemins = [
        d.chemin_dalle(dossier_dalles, nom) for nom in noms_persistance
    ]
    fichiers = [chemin for chemin in chemins if chemin.exists()]
    cloud_path = getattr(provider, "cloud_path", None)
    if cloud_path is not None:
        for chemin in chemins:
            nuage = cloud_path(chemin)
            if nuage is not None and nuage.exists():
                fichiers.append(nuage)
    d.creer_fichiers(fichiers)
