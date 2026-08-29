"""Orchestration hors réseau du téléchargement des dalles terrain.

Le moteur COG reste dans la façade ``lidar2map``. Ce module porte les moteurs
direct et COPC, leur staging et le cache LAZ, choisit le moteur par zone, borne
le pool, agrège les statuts et publie la preuve ``dalles_zone.txt``. Toutes les
coutures applicatives sont injectées afin de conserver les monkeypatches
historiques.
"""

import os
import shutil
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


# Codes HTTP typiques d'un throttle/WAF serveur (ex. EA gb-england sous forte
# concurrence) plutôt que d'une erreur définitive : méritent un backoff plus
# large que le linéaire standard pour laisser le temps au serveur de retomber.
CODES_RATE_LIMIT = frozenset({403, 429, 503})
DELAI_RATE_LIMIT_S = 30  # secondes, multiplié par le numéro de tentative


def _delai_avant_retry(erreur, tentative, delai_retry):
    """Backoff avant la prochaine tentative : escaladé, plus large si le
    serveur a répondu un code de throttle (403/429/503)."""
    if getattr(erreur, "http_code", None) in CODES_RATE_LIMIT:
        return DELAI_RATE_LIMIT_S * tentative
    return delai_retry * tentative


def nom_dalle_sur(nom):
    """Retourne ``True`` pour un basename sans traversée de chemin."""
    if not nom or nom in (".", ".."):
        return False
    texte = str(nom)
    if "\x00" in texte or "/" in texte or "\\" in texte:
        return False
    if os.path.isabs(texte) or os.path.splitdrive(texte)[0]:
        return False
    return os.path.basename(texte) == texte


def chemin_dalle(dossier_dalles, nom, *, provider, nom_dalle_sur):
    """Résout une dalle sûre, avec priorité à l'ancienne structure racine."""
    if not nom_dalle_sur(nom):
        raise ValueError(f"unsafe tile name (path traversal): {nom!r}")
    chemin_racine = Path(dossier_dalles) / nom
    if chemin_racine.exists():
        return chemin_racine
    sous_dossier = provider.subdir_from_name(nom)
    if sous_dossier:
        return Path(dossier_dalles) / sous_dossier / nom
    return chemin_racine


def dossier_dalles_actif(
    args,
    dossier_ville=None,
    *,
    provider,
    dossier_production,
    dossier_cache,
    lidar_subdir,
):
    """Choisit la racine projet, production ou cache selon la nature des dalles."""
    if args.dossier_dalles:
        return Path(args.dossier_dalles).resolve()
    if dossier_ville is not None and (
        getattr(provider, "COG_WINDOWED", False)
        or getattr(provider, "COPC_WINDOWED", False)
    ):
        return Path(dossier_ville)
    if provider.CODE.endswith("-laz"):
        return Path(dossier_production) / lidar_subdir
    return Path(dossier_cache) / lidar_subdir


def configurer_cloud_cache(args, *, provider, dossier_cache, lidar_subdir):
    """Configure le cache du nuage LAZ et mémorise la valeur sur ``args``."""
    setter = getattr(provider, "set_cloud_cache_dir", None)
    if not setter:
        return
    windowed = getattr(provider, "COG_WINDOWED", False) or getattr(
        provider, "COPC_WINDOWED", False
    )
    valeur = (
        None
        if args.dossier_dalles or windowed
        else Path(dossier_cache) / lidar_subdir
    )
    setter(valeur)
    args._cloud_cache_dir = valeur


def rglob_tif_robuste(dossier, *, imprimer=print):
    """Liste les TIFF de la racine et de ses sous-dossiers accessibles."""
    resultats = []
    try:
        for sous_dossier in sorted(Path(dossier).iterdir()):
            try:
                if sous_dossier.is_dir():
                    resultats.extend(sous_dossier.glob("*.tif"))
                elif sous_dossier.suffix.lower() == ".tif":
                    resultats.append(sous_dossier)
            except OSError as exc:
                imprimer(
                    f"  WARNING: inaccessible directory {sous_dossier.name} "
                    f"({exc}) - skipped"
                )
    except OSError as exc:
        imprimer(f"  WARNING: tiles folder inaccessible ({exc})")
    return resultats


def laz_prof_add(dl_s=None, conv_s=None, *, enabled, lock, profile):
    """Accumule les durées LAZ dans un état injecté et protégé par verrou."""
    if not enabled:
        return
    with lock:
        if dl_s is not None:
            profile["dl_n"] += 1
            profile["dl_s"] += dl_s
        if conv_s is not None:
            profile["conv_n"] += 1
            profile["conv_s"] += conv_s
            profile["conv_max"] = max(profile["conv_max"], conv_s)


def laz_prof_resume(
    wall_s,
    n_dl_workers,
    laz_parallel,
    *,
    enabled,
    lock,
    profile,
    imprimer=print,
):
    """Affiche le résumé et la borne théorique du pipeline LAZ."""
    if not enabled:
        return
    with lock:
        donnees = dict(profile)
    if donnees["dl_n"] == 0 and donnees["conv_n"] == 0:
        return
    dl, conv = donnees["dl_s"], donnees["conv_s"]
    borne = max(dl / max(n_dl_workers, 1), conv / max(laz_parallel, 1))
    imprimer(
        f"  [PROFILE R1#6] download {donnees['dl_n']} dalles, cumul {dl:.0f}s "
        f"({dl / max(donnees['dl_n'], 1):.1f}s/dalle) | conversion "
        f"{donnees['conv_n']}, cumul {conv:.0f}s "
        f"({conv / max(donnees['conv_n'], 1):.1f}s/dalle, "
        f"max {donnees['conv_max']:.1f}s)"
    )
    imprimer(
        f"  [PROFILE R1#6] mur actuel {wall_s:.0f}s @ {n_dl_workers} "
        f"dl-workers, laz_parallel={laz_parallel} | borne découplé "
        f"~{borne:.0f}s (gain potentiel x{wall_s / max(borne, 1e-9):.1f})"
    )


def valider_tif_dalle(chemin):
    """Valide le magic TIFF puis les métadonnées et un bloc de données."""
    try:
        with open(chemin, "rb") as fichier:
            magic = fichier.read(4)
        if magic[:2] not in (b"II", b"MM"):
            return False
        if magic[2:4] not in (
            b"\x2a\x00",
            b"\x00\x2a",
            b"\x2b\x00",
            b"\x00\x2b",
        ):
            return False
    except OSError:
        return False

    try:
        import rasterio
    except ImportError:
        return True
    try:
        with rasterio.open(str(chemin)) as source:
            if source.width == 0 or source.height == 0 or source.count < 1:
                return False
            resolution_x, resolution_y = source.res
            if not (0 < resolution_x < 1e9) or not (
                0 < resolution_y < 1e9
            ):
                return False
            source.read(
                1,
                window=rasterio.windows.Window(
                    0,
                    0,
                    min(64, source.width),
                    min(64, source.height),
                ),
            )
    except Exception:
        return False
    return True


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
class DependancesTelechargementDirect:
    provider: object
    chemin_dalle: object
    seuil_dalle_valide: int
    max_tentatives: int
    delai_retry: float
    stage_dalle_part: object
    lier_nuage_existant_au_stage: object
    download_to_tmp: object
    laz_prof_add: object
    post_fetch_si_besoin: object
    valider_tif_dalle: object
    comprimer_dalle_deflate: object
    publier_nuage_stage: object
    creer_fichier: object
    time: object


@contextmanager
def stage_dalle_part(chemin_final, *, chemin_part):
    """Crée et nettoie un dossier staging voisin finissant par ``.part``."""
    chemin_final = Path(chemin_final)
    dossier_part = chemin_part(chemin_final)
    dossier_part.mkdir(parents=False, exist_ok=False)
    chemin_stage = dossier_part / chemin_final.name
    try:
        yield chemin_stage
    finally:
        shutil.rmtree(dossier_part, ignore_errors=True)


def chemins_nuage_stage(chemin_final, chemin_stage, *, provider):
    """Retourne les chemins final/staging du nuage co-localisé éventuel."""
    cloud_path = getattr(provider, "cloud_path", None)
    if not callable(cloud_path):
        return None, None
    try:
        final = cloud_path(Path(chemin_final))
        stage = cloud_path(Path(chemin_stage))
        return (
            Path(final) if final is not None else None,
            Path(stage) if stage is not None else None,
        )
    except Exception:
        return None, None


def lier_nuage_existant_au_stage(
    chemin_final, chemin_stage, *, chemins_nuage
):
    """Expose par hardlink un nuage existant au hook ``pre_download``."""
    nuage_final, nuage_stage = chemins_nuage(chemin_final, chemin_stage)
    if (
        nuage_final is None
        or nuage_stage is None
        or nuage_final == nuage_stage
        or not nuage_final.exists()
        or nuage_stage.exists()
    ):
        return
    try:
        nuage_stage.parent.mkdir(parents=True, exist_ok=True)
        os.link(nuage_final, nuage_stage)
    except OSError:
        pass


def publier_nuage_stage(chemin_final, chemin_stage, *, chemins_nuage):
    """Publie le nuage complet, ou retire son hardlink de staging."""
    nuage_final, nuage_stage = chemins_nuage(chemin_final, chemin_stage)
    if (
        nuage_final is None
        or nuage_stage is None
        or nuage_final == nuage_stage
        or not nuage_stage.exists()
    ):
        return
    nuage_final.parent.mkdir(parents=True, exist_ok=True)
    try:
        if nuage_final.exists() and os.path.samefile(nuage_stage, nuage_final):
            nuage_stage.unlink(missing_ok=True)
            return
    except OSError:
        pass
    nuage_stage.replace(nuage_final)


def comprimer_dalle_deflate(chemin, *, chemin_part):
    """Recomprime en DEFLATE une dalle GeoTIFF, en place et best-effort."""
    chemin = Path(chemin)
    temporaire = chemin_part(chemin)
    try:
        import rasterio

        with rasterio.open(str(chemin)) as source:
            if (source.profile.get("compress") or "").lower() in (
                "deflate",
                "lzw",
            ):
                return
            profil = source.profile.copy()
            profil.update(
                {
                    "compress": "deflate",
                    "predictor": (
                        3 if source.dtypes[0].startswith("float") else 2
                    ),
                    "tiled": True,
                    "blockxsize": 256,
                    "blockysize": 256,
                    "BIGTIFF": "IF_SAFER",
                }
            )
            with rasterio.open(str(temporaire), "w", **profil) as destination:
                for _index, fenetre in source.block_windows(1):
                    for bande in range(1, source.count + 1):
                        destination.write(
                            source.read(bande, window=fenetre),
                            bande,
                            window=fenetre,
                        )
        temporaire.replace(chemin)
    except Exception as erreur:
        temporaire.unlink(missing_ok=True)
        print(
            f"  ⚠ compression skipped for {chemin.name}: "
            f"{type(erreur).__name__}: {erreur}",
            flush=True,
        )


def telecharger_dalle_directe(
    nom,
    url_wms,
    dossier,
    ecraser=False,
    compresser=False,
    *,
    dependances,
):
    """Télécharge, transforme, valide puis publie atomiquement une dalle."""
    d = dependances
    provider = d.provider
    chemin = d.chemin_dalle(dossier, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists() and chemin.stat().st_size > d.seuil_dalle_valide:
        if not ecraser:
            return "skip"

    for tentative in range(1, d.max_tentatives + 1):
        with d.stage_dalle_part(chemin) as chemin_stage:
            try:
                pre_download = (
                    getattr(provider, "pre_download", None)
                    if tentative == 1 and not ecraser
                    else None
                )
                materialise = False
                if pre_download is not None:
                    d.lier_nuage_existant_au_stage(chemin, chemin_stage)
                    try:
                        materialise = bool(pre_download(chemin_stage)) and (
                            chemin_stage.exists()
                        )
                    except Exception as erreur_pre:
                        print(
                            f"  WARN pre_download {nom}: "
                            f"{type(erreur_pre).__name__}: {erreur_pre}",
                            flush=True,
                        )
                if not materialise:
                    debut_download = d.time.time()
                    codes_absence = getattr(
                        provider, "NO_COVERAGE_HTTP_CODES", frozenset({404})
                    )
                    taille = d.download_to_tmp(
                        url_wms, chemin_stage, timeout=(10, 45),
                        codes_absence=codes_absence,
                    )
                    d.laz_prof_add(dl_s=d.time.time() - debut_download)
                    if taille == 0:
                        if getattr(provider, "DISCOVER_EXACT", False):
                            raise IOError(
                                "HTTP 404 sur dalle indexée "
                                "(provider à découverte exacte)"
                            )
                        return "absent"
                    if taille < d.seuil_dalle_valide:
                        with open(chemin_stage, "rb") as fichier:
                            entete = fichier.read(200)
                        if (
                            entete.lstrip().startswith(b"{")
                            and b'"error"' in entete
                        ):
                            raise IOError(
                                f"server error payload: {entete[:120]!r}"
                            )
                        return "absent"
                    debut_conversion = d.time.time()
                    d.post_fetch_si_besoin(chemin_stage)
                    d.laz_prof_add(
                        conv_s=d.time.time() - debut_conversion
                    )
                if not d.valider_tif_dalle(chemin_stage):
                    raise IOError(
                        "GeoTIFF invalide après écriture "
                        "(fichier tronqué ou corrompu)"
                    )
                if hasattr(provider, "post_download"):
                    try:
                        provider.post_download(chemin_stage)
                    except Exception as erreur_post:
                        raise IOError(
                            f"post_download {nom}: "
                            f"{type(erreur_post).__name__}: {erreur_post}"
                        )
                    if not d.valider_tif_dalle(chemin_stage):
                        raise IOError(
                            f"GeoTIFF invalide après post_download ({nom})"
                        )
                if compresser:
                    d.comprimer_dalle_deflate(chemin_stage)
                    if not d.valider_tif_dalle(chemin_stage):
                        raise IOError(
                            f"GeoTIFF invalide après compression ({nom})"
                        )

                d.publier_nuage_stage(chemin, chemin_stage)
                chemin_stage.replace(chemin)
                d.creer_fichier(chemin)
                return "ok"
            except KeyboardInterrupt:
                raise
            except Exception as erreur:
                if tentative < d.max_tentatives:
                    d.time.sleep(_delai_avant_retry(erreur, tentative, d.delai_retry))
                else:
                    print(
                        f"\n  ERROR {nom} ({type(erreur).__name__}, "
                        f"attempt {tentative}): {erreur}"
                    )
                    return "erreur"
    return "erreur"


COPC_CRS_LOCK = threading.Lock()


@dataclass(frozen=True)
class DependancesTelechargementCopc:
    provider: object
    chemin_dalle: object
    seuil_dalle_valide: int
    bbox_enveloppe_transform: object
    natif_vers_wgs84: object
    copc_window_to_las: object
    stage_dalle_part: object
    copc_post_fetch_crs: object
    valider_tif_dalle: object
    publier_nuage_stage: object
    creer_fichier: object


def copc_post_fetch_crs(
    epsg,
    chemin_part,
    *,
    provider,
    lock,
    post_fetch_si_besoin,
):
    """Pose le CRS UTM et convertit sous un même verrou multi-zone.

    Le provider est partagé entre les workers et son ``set_crs`` modifie le CRS
    lu ensuite par ``post_fetch``. Le verrou rend ce couple atomique sans
    sérialiser la lecture COPC distante, qui reste le principal goulot.
    """
    definir_crs = getattr(provider, "set_crs", None)
    with lock:
        if definir_crs and epsg:
            definir_crs(int(epsg))
        post_fetch_si_besoin(chemin_part)


def telecharger_copc_fenetre(
    nom,
    url,
    dossier_dalles,
    bbox,
    ecraser=False,
    *,
    dependances,
):
    """Lit et publie atomiquement une fenêtre d'un COPC distant.

    Seuls les points de la bbox sont lus par range requests, puis le sous-ensemble
    est converti par le provider en GeoTIFF. Le CRS UTM propre à la tuile est
    appliqué sous verrou avant la conversion. ``bbox`` est exprimée dans le CRS
    natif du provider. La fonction retourne ``ok``, ``skip``, ``absent`` ou
    ``erreur`` et propage toujours ``KeyboardInterrupt``.
    """
    d = dependances
    chemin = d.chemin_dalle(dossier_dalles, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    seuil = getattr(d.provider, "SEUIL_DALLE_VALIDE", d.seuil_dalle_valide)
    if chemin.exists() and chemin.stat().st_size > seuil and not ecraser:
        return "skip"

    with d.stage_dalle_part(chemin) as chemin_part:
        try:
            bx1, by1, bx2, by2 = bbox
            lo1, la1, lo2, la2 = d.bbox_enveloppe_transform(
                d.natif_vers_wgs84, bx1, by1, bx2, by2
            )
            signer = getattr(d.provider, "sign_url", None)
            url_signee = signer(url) if callable(signer) else url
            nombre_points, epsg = d.copc_window_to_las(
                url_signee, (lo1, la1, lo2, la2), chemin_part
            )
            if not nombre_points or nombre_points < 50_000:
                return "absent"

            d.copc_post_fetch_crs(epsg, chemin_part)
            if not d.valider_tif_dalle(chemin_part):
                raise IOError(
                    f"GeoTIFF COPC invalide après post_fetch ({nom})"
                )
            d.publier_nuage_stage(chemin, chemin_part)
            chemin_part.replace(chemin)
            d.creer_fichier(chemin)
            return "ok"
        except KeyboardInterrupt:
            raise
        except Exception as erreur:
            print(
                f"\n  ERROR COPC {nom} "
                f"({type(erreur).__name__}): {erreur}"
            )
            return "erreur"


def cog_cache_couvre(
    chemin,
    bbox_natif,
    *,
    provider,
    get_transformer,
    bbox_enveloppe_transform,
):
    """Vérifie qu'un fragment COG en cache couvre toute la bbox demandée."""
    try:
        import rasterio

        with rasterio.open(str(chemin)) as source:
            bornes = source.bounds
            epsg_fichier = source.crs.to_epsg() if source.crs else None
        x1, y1, x2, y2 = bbox_natif
        crs_natif = getattr(provider, "CRS_NATIF", "")
        epsg_natif = int(crs_natif.split(":")[1]) if ":" in crs_natif else None
        if epsg_fichier and epsg_natif and epsg_fichier != epsg_natif:
            transformeur = get_transformer(
                crs_natif, f"EPSG:{epsg_fichier}"
            )
            x1, y1, x2, y2 = bbox_enveloppe_transform(
                transformeur.transform, x1, y1, x2, y2
            )
        tolerance = 1.0
        return (
            bornes.left - tolerance <= min(x1, x2)
            and bornes.right + tolerance >= max(x1, x2)
            and bornes.bottom - tolerance <= min(y1, y2)
            and bornes.top + tolerance >= max(y1, y2)
        )
    except Exception:
        return False


@dataclass(frozen=True)
class DependancesTelechargementCog:
    provider: object
    chemin_dalle: object
    seuil_dalle_valide: int
    max_tentatives: int
    delai_retry: float
    max_cog_window_px: int
    stage_dalle_part: object
    cog_cache_couvre: object
    get_transformer: object
    valider_tif_dalle: object
    creer_fichier: object
    time: object


def telecharger_cog_fenetre(
    nom,
    url,
    dossier_dalles,
    bbox,
    ecraser=False,
    *,
    dependances,
):
    """Lit une fenêtre COG distante et la publie atomiquement en GeoTIFF.

    Les fenêtres dépassant ``max_cog_window_px`` sont copiées par bandes de
    1 024 lignes. La fonction retourne ``ok``, ``skip``, ``absent`` ou
    ``erreur`` et propage toujours ``KeyboardInterrupt``.
    """
    import rasterio
    from rasterio.windows import Window, from_bounds as win_from_bounds

    d = dependances
    chemin = d.chemin_dalle(dossier_dalles, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists() and chemin.stat().st_size > d.seuil_dalle_valide:
        if not ecraser and d.cog_cache_couvre(chemin, bbox):
            return "skip"

    bx1, by1, bx2, by2 = bbox
    vsi = "/vsicurl/" + url
    for tentative in range(1, d.max_tentatives + 1):
        with d.stage_dalle_part(chemin) as chemin_part:
            try:
                options_provider = getattr(d.provider, "gdal_env_options", None)
                options_supplementaires = (
                    options_provider() if callable(options_provider) else {}
                )
                options_gdal = {
                    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
                    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff",
                    "VSI_CACHE": True,
                    "GDAL_HTTP_TIMEOUT": "60",
                }
                options_gdal.update(options_supplementaires)
                with rasterio.Env(**options_gdal):
                    with rasterio.open(vsi) as source:
                        rbx1, rby1, rbx2, rby2 = bx1, by1, bx2, by2
                        try:
                            epsg_source = (
                                source.crs.to_epsg() if source.crs else None
                            )
                            crs_natif = getattr(d.provider, "CRS_NATIF", "")
                            epsg_natif = (
                                int(crs_natif.split(":")[1])
                                if ":" in crs_natif
                                else None
                            )
                            if (
                                epsg_source
                                and epsg_natif
                                and epsg_source != epsg_natif
                            ):
                                transformeur = d.get_transformer(
                                    crs_natif, f"EPSG:{epsg_source}"
                                )
                                xs, ys = [], []
                                for px, py in (
                                    (bx1, by1),
                                    (bx1, by2),
                                    (bx2, by1),
                                    (bx2, by2),
                                ):
                                    tx, ty = transformeur.transform(px, py)
                                    xs.append(tx)
                                    ys.append(ty)
                                rbx1, rby1 = min(xs), min(ys)
                                rbx2, rby2 = max(xs), max(ys)
                        except Exception:
                            pass

                        bornes = source.bounds
                        gauche = max(rbx1, bornes.left)
                        droite = min(rbx2, bornes.right)
                        bas = max(rby1, bornes.bottom)
                        haut = min(rby2, bornes.top)
                        if gauche >= droite or bas >= haut:
                            return "absent"
                        fenetre = win_from_bounds(
                            gauche, bas, droite, haut, source.transform
                        )
                        fenetre_entiere = fenetre.round_offsets(
                            op="floor"
                        ).round_lengths(op="ceil")
                        hauteur = int(fenetre_entiere.height)
                        largeur = int(fenetre_entiere.width)
                        if hauteur <= 0 or largeur <= 0:
                            return "absent"

                        if hauteur * largeur > d.max_cog_window_px:
                            profil = source.profile.copy()
                            profil.update(
                                driver="GTiff",
                                height=hauteur,
                                width=largeur,
                                transform=source.window_transform(
                                    fenetre_entiere
                                ),
                                compress="deflate",
                                predictor=2,
                                tiled=True,
                                blockxsize=256,
                                blockysize=256,
                                bigtiff="IF_SAFER",
                            )
                            with rasterio.open(
                                chemin_part, "w", **profil
                            ) as destination:
                                ligne = 0
                                while ligne < hauteur:
                                    bloc_hauteur = min(1024, hauteur - ligne)
                                    sous_fenetre = Window(
                                        fenetre_entiere.col_off,
                                        fenetre_entiere.row_off + ligne,
                                        largeur,
                                        bloc_hauteur,
                                    )
                                    destination.write(
                                        source.read(window=sous_fenetre),
                                        window=Window(
                                            0,
                                            ligne,
                                            largeur,
                                            bloc_hauteur,
                                        ),
                                    )
                                    ligne += bloc_hauteur
                        else:
                            donnees = source.read(window=fenetre)
                            if donnees.size == 0:
                                return "absent"
                            profil = source.profile.copy()
                            profil.update(
                                driver="GTiff",
                                height=donnees.shape[1],
                                width=donnees.shape[2],
                                transform=source.window_transform(fenetre),
                                compress="deflate",
                                predictor=2,
                                tiled=True,
                                blockxsize=256,
                                blockysize=256,
                                bigtiff="IF_SAFER",
                            )
                            with rasterio.open(
                                chemin_part, "w", **profil
                            ) as destination:
                                destination.write(donnees)

                if not d.valider_tif_dalle(chemin_part):
                    raise IOError("COG fenêtré invalide après écriture")
                if hasattr(d.provider, "post_download"):
                    try:
                        d.provider.post_download(chemin_part)
                    except Exception as erreur_post:
                        raise IOError(
                            f"post_download {nom}: "
                            f"{type(erreur_post).__name__}: {erreur_post}"
                        )
                    if not d.valider_tif_dalle(chemin_part):
                        raise IOError(
                            f"GeoTIFF invalide après post_download ({nom})"
                        )
                chemin_part.replace(chemin)
                d.creer_fichier(chemin)
                return "ok"
            except KeyboardInterrupt:
                raise
            except Exception as erreur:
                if tentative < d.max_tentatives:
                    d.time.sleep(_delai_avant_retry(erreur, tentative, d.delai_retry))
                else:
                    print(
                        f"\n  ERROR window {nom} "
                        f"({type(erreur).__name__}): {erreur}"
                    )
                    return "erreur"
    return "erreur"


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
