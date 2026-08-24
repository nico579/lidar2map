"""Découverte et téléchargement des dalles d'un morceau terrain."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class DependancesMorceauTerrain:
    """Coutures applicatives relues par la façade avant chaque opération."""

    provider: object
    get_transformer: Callable
    bbox_enveloppe_transform: Callable
    dossier_cache: Path
    dossier_travail: Path
    lidar_subdir: Path
    dossier_dalles_actif: Callable
    contexte_manifeste: Callable
    telecharger_dalles_zone: Callable
    decouvrir_et_telecharger_ombrage: Callable
    resoudre_choix_ombrages: Callable
    lister_dalles_zone: Callable
    generer_ombrages: Callable
    elevation_soleil: float
    supprimer_fichiers: Callable


@dataclass(frozen=True)
class DependancesTuilageMorceau:
    """Coutures de la transaction de tuilage d'un morceau glissant."""

    dossier_travail: Path
    lidar_subdir: Path
    voisins_dossiers: Callable
    contexte_manifeste: Callable
    lister_tifs_ombrages: Callable
    build_vrt_xml: Callable
    creer_fichier: Callable
    mbtiles_a_regenerer: Callable
    generer_mbtiles_lidar: Callable
    tile_workers_defaut: Callable
    convertir_formats: Callable
    resultat_chunk: Callable
    imprimer: Callable = print


@dataclass(frozen=True)
class DependancesWmtsMorceau:
    """Coutures de la transaction raster WMTS d'un morceau."""

    dossier_travail: Path
    dossier_cache: Path
    contexte_manifeste: Callable
    calculer_grille_xyz: Callable
    compter_tuiles_xyz: Callable
    jpeg_quality_sortie: Callable
    nom_mbtiles_wmts: Callable
    mbtiles_a_regenerer: Callable
    generer_mbtiles_wmts: Callable
    convertir_formats: Callable
    resultat_chunk: Callable


@dataclass(frozen=True)
class DependancesLidarClassique:
    """Coutures de la transaction LiDAR autonome utilisée par ``--block``."""

    provider: object
    dossier_travail: Path
    dossier_cache: Path
    lidar_subdir: Path
    get_transformer: Callable
    bbox_enveloppe_transform: Callable
    dossier_dalles_actif: Callable
    contexte_manifeste: Callable
    telecharger_dalles_zone: Callable
    resoudre_choix_ombrages: Callable
    lister_dalles_zone: Callable
    generer_ombrages: Callable
    elevation_soleil: float
    lister_tifs_ombrages: Callable
    tuiler_tifs_ombrages: Callable
    resultat_chunk: Callable


@dataclass(frozen=True)
class DependancesTuilageOmbrages:
    """Coutures du tuilage commun des TIFF d'ombrage."""

    mbtiles_a_regenerer: Callable
    generer_mbtiles_lidar: Callable
    tile_workers_defaut: Callable
    convertir_formats: Callable
    imprimer: Callable = print


def _bbox_wgs_elargie(bbox_natif, dependances):
    bx1, by1, bx2, by2 = bbox_natif
    transformeur = dependances.get_transformer(
        dependances.provider.CRS_NATIF, "EPSG:4326"
    )
    lo1, la1, lo2, la2 = dependances.bbox_enveloppe_transform(
        transformeur.transform, bx1, by1, bx2, by2
    )
    return (lo1 - 0.05, la1 - 0.05, lo2 + 0.05, la2 + 0.05)


def dalles_zone_lookahead(bbox_natif, *, dependances):
    """Découvre au mieux les noms nécessaires au prochain morceau."""
    try:
        bbox = tuple(bbox_natif)
        bbox_wgs = _bbox_wgs_elargie(bbox, dependances)
        cache_discover = (
            Path(dependances.dossier_cache)
            / f"discover_{dependances.provider.CODE}.json"
        )
        dalles = dependances.provider.discover_dalles(
            bbox_wgs, bbox, cache_discover
        )
        return set(dalles) if dalles else None
    except Exception:
        return None


def decouvrir_et_telecharger_ombrage(
    args,
    bbox_natif,
    nom_z,
    nom_zone_base,
    manifeste,
    cle,
    quiet=False,
    *,
    dependances,
):
    """Prépare les dossiers puis découvre et télécharge les dalles du morceau."""
    bbox = tuple(bbox_natif)
    racine = (
        Path(args.dossier).resolve()
        if args.dossier
        else Path(dependances.dossier_travail)
        / "Projets"
        / nom_zone_base
        / dependances.lidar_subdir
    )
    dossier_ville = racine / nom_z
    dossier_dalles = dependances.dossier_dalles_actif(args, dossier_ville)
    dossier_ville.mkdir(parents=True, exist_ok=True)
    dossier_dalles.mkdir(parents=True, exist_ok=True)

    with dependances.contexte_manifeste(manifeste, cle + "_dl"):
        bbox_wgs = _bbox_wgs_elargie(bbox, dependances)
        cache_discover = (
            Path(dependances.dossier_cache)
            / f"discover_{dependances.provider.CODE}.json"
        )
        try:
            dalles = dependances.provider.discover_dalles(
                bbox_wgs, bbox, cache_discover
            )
        except Exception as exc:
            raise RuntimeError(
                f"tile discovery failed ({type(exc).__name__}: {exc})"
                " - rerun to resume this chunk"
            ) from exc
        if dalles is None:
            raise RuntimeError(
                "tile discovery unavailable (network/endpoint)"
                " - rerun to resume this chunk"
            )
        if args.telechargement:
            dependances.telecharger_dalles_zone(
                dalles,
                bbox,
                dossier_dalles,
                dossier_ville,
                args,
                quiet=quiet,
            )
    return dalles, dossier_dalles, dossier_ville


def tuiler_tifs_ombrages(
    args,
    tifs,
    dossier_ville,
    nom_zone,
    bbox,
    decoupe_sortie=True,
    verbose=False,
    tampon_coin_max_m=0,
    mbtiles_attendus=None,
    *,
    dependances,
):
    """Produit et convertit chaque famille d'ombrage sans court-circuit."""
    ok = True
    for tif in tifs:
        if verbose:
            dependances.imprimer("  " + tif.name)
        stem = re.sub(r"_tuilage_z\d+$", "", tif.stem)
        suffix = (
            stem[len(nom_zone) + 1 :]
            if stem.startswith(nom_zone + "_")
            else stem
        )
        nom_base = f"{nom_zone}_{suffix}"
        mbtiles = (
            dossier_ville
            / f"{nom_base}_z{args.zoom_min}-{args.zoom_max}.mbtiles"
        )
        if mbtiles_attendus is not None:
            mbtiles_attendus.append(mbtiles)
        mbtiles_neuf = dependances.mbtiles_a_regenerer(
            mbtiles, args.tuiles_ecraser, source=tif
        )
        if mbtiles_neuf:
            sortie = dependances.generer_mbtiles_lidar(
                tif,
                dossier_ville,
                nom_base,
                zoom_min=args.zoom_min,
                zoom_max=args.zoom_max,
                format_tuiles=args.formats_image,
                jpeg_quality=args.qualite_image,
                bbox_natif=bbox,
                tampon_coin_max_m=tampon_coin_max_m,
                ecraser_tuiles=args.tuiles_ecraser,
                tile_workers=dependances.tile_workers_defaut(),
            )
        else:
            dependances.imprimer(
                f"  Existing MBTiles: {mbtiles.name}, direct split/conversion"
            )
            sortie = mbtiles
        ok = (
            dependances.convertir_formats(
                sortie,
                args,
                decoupe_sortie=decoupe_sortie,
                mbtiles_neuf=mbtiles_neuf,
            )
            and ok
        )
    return ok


def traiter_bbox_lidar(
    args,
    bbox_natif,
    nom_z,
    nom_zone_base,
    manifeste,
    cle,
    *,
    dependances,
):
    """Traite de façon autonome un morceau LiDAR distribué par ``--block``."""
    bx1, by1, bx2, by2 = bbox_natif
    bbox_orig = args.zone_bbox
    nom_orig = args.zone_nom
    args.zone_bbox = f"{bx1:.2f},{by1:.2f},{bx2:.2f},{by2:.2f}"
    args.zone_nom = nom_z
    marge_halo_m = max(300.0, 0.1 * min(bx2 - bx1, by2 - by1))
    traitement_ok = True
    mbtiles_attendus = []
    try:
        with dependances.contexte_manifeste(manifeste, cle):
            bbox = (bx1, by1, bx2, by2)
            bbox_marge = (
                bx1 - marge_halo_m,
                by1 - marge_halo_m,
                bx2 + marge_halo_m,
                by2 + marge_halo_m,
            )
            racine = (
                Path(args.dossier).resolve()
                if args.dossier
                else Path(dependances.dossier_travail)
                / "Projets"
                / nom_zone_base
                / dependances.lidar_subdir
            )
            dossier_ville = racine / nom_z
            dossier_dalles = dependances.dossier_dalles_actif(
                args, dossier_ville
            )
            dossier_ville.mkdir(parents=True, exist_ok=True)
            dossier_dalles.mkdir(parents=True, exist_ok=True)

            transformeur = dependances.get_transformer(
                dependances.provider.CRS_NATIF, "EPSG:4326"
            )
            lo1, la1, lo2, la2 = dependances.bbox_enveloppe_transform(
                transformeur.transform, *bbox_marge
            )
            bbox_wgs = (lo1 - 0.05, la1 - 0.05, lo2 + 0.05, la2 + 0.05)
            cache_discover = (
                Path(dependances.dossier_cache)
                / f"discover_{dependances.provider.CODE}.json"
            )
            try:
                dalles = dependances.provider.discover_dalles(
                    bbox_wgs, bbox_marge, cache_discover
                )
            except Exception as exc:
                raise RuntimeError(
                    f"tile discovery failed ({type(exc).__name__}: {exc})"
                    " - rerun to resume this chunk"
                ) from exc
            if dalles is None:
                raise RuntimeError(
                    "tile discovery unavailable (network/endpoint)"
                    " - rerun to resume this chunk"
                )

            if args.telechargement:
                dependances.telecharger_dalles_zone(
                    dalles,
                    bbox_marge,
                    dossier_dalles,
                    dossier_ville,
                    args,
                )

            tifs_run = None
            if args.ombrages:
                choix, instances = dependances.resoudre_choix_ombrages(args)
                if choix or instances:
                    dalles_ombrages = dependances.lister_dalles_zone(
                        dalles.keys(),
                        dossier_dalles,
                        dossier_ville,
                        bbox_marge,
                    )
                    elevation = (
                        args.ombrages_elevation
                        if args.ombrages_elevation is not None
                        else dependances.elevation_soleil
                    )
                    tifs_run = dependances.generer_ombrages(
                        dalles_ombrages,
                        dossier_ville,
                        choix,
                        elevation_soleil=elevation,
                        nom_zone=nom_z,
                        ecraser_ombrages=args.ombrages_ecraser,
                        use_sweep=args.sweep_horizon,
                        svf_gamma=args.svf_gamma,
                        svf_conv=args.svf_conv,
                        svf_dist=args.svf_dist,
                        bbox_natif=bbox_marge,
                        instances=instances or None,
                    )

            if args.mbtiles or args.rmap or args.sqlitedb:
                traitement_ok = dependances.tuiler_tifs_ombrages(
                    args,
                    dependances.lister_tifs_ombrages(
                        dossier_ville, tifs_run
                    ),
                    dossier_ville,
                    nom_z,
                    bbox,
                    decoupe_sortie=False,
                    tampon_coin_max_m=marge_halo_m,
                    mbtiles_attendus=mbtiles_attendus,
                )
    finally:
        args.zone_bbox = bbox_orig
        args.zone_nom = nom_orig
    return dependances.resultat_chunk(traitement_ok, mbtiles_attendus)


def traiter_bbox_lidar_ombrage(
    args,
    bbox_natif,
    nom_z,
    nom_zone_base,
    manifeste,
    cle,
    dalles_precharge=None,
    on_download_done=None,
    noms_dalles_a_garder=None,
    *,
    dependances,
):
    """Orchestre téléchargement, ombrage et nettoyage d'un morceau glissant."""
    bx1, by1, bx2, by2 = bbox_natif
    bbox_orig = args.zone_bbox
    nom_orig = args.zone_nom
    args.zone_bbox = f"{bx1:.2f},{by1:.2f},{bx2:.2f},{by2:.2f}"
    args.zone_nom = nom_z
    try:
        bbox = (bx1, by1, bx2, by2)
        if dalles_precharge is not None:
            dalles_dict, dossier_dalles, dossier_ville = dalles_precharge
        else:
            dalles_dict, dossier_dalles, dossier_ville = (
                dependances.decouvrir_et_telecharger_ombrage(
                    args, bbox, nom_z, nom_zone_base, manifeste, cle
                )
            )
        if on_download_done:
            on_download_done()

        if args.ombrages:
            choix, instances = dependances.resoudre_choix_ombrages(args)
            if choix or instances:
                with dependances.contexte_manifeste(manifeste, cle):
                    dalles_ombrages = dependances.lister_dalles_zone(
                        dalles_dict.keys(),
                        dossier_dalles,
                        dossier_ville,
                        bbox,
                    )
                    elevation = (
                        args.ombrages_elevation
                        if args.ombrages_elevation is not None
                        else dependances.elevation_soleil
                    )
                    dependances.generer_ombrages(
                        dalles_ombrages,
                        dossier_ville,
                        choix,
                        elevation_soleil=elevation,
                        nom_zone=nom_z,
                        ecraser_ombrages=args.ombrages_ecraser,
                        use_sweep=args.sweep_horizon,
                        svf_gamma=args.svf_gamma,
                        svf_conv=args.svf_conv,
                        svf_dist=args.svf_dist,
                        bbox_natif=bbox,
                        instances=instances or None,
                    )

        if args.telechargement and getattr(args, "nettoyage", False):
            if getattr(args, "nettoyage_garder_dalles", False):
                garder = [dependances.dossier_dalles_actif(args)]
                cloud_cache = getattr(args, "_cloud_cache_dir", None)
                if cloud_cache is not None:
                    garder.append(cloud_cache)
            else:
                garder = None
            dependances.supprimer_fichiers(
                manifeste.fichiers_morceau(cle + "_dl"),
                garder,
                noms_garder=noms_dalles_a_garder,
            )
    finally:
        args.zone_bbox = bbox_orig
        args.zone_nom = nom_orig


def traiter_bbox_lidar_tuilage(
    args,
    bbox_natif,
    nom_z,
    nom_zone_base,
    manifeste,
    cle,
    i_lat,
    i_lon,
    n_lat,
    n_lon,
    *,
    dependances,
):
    """Fusionne les voisins disponibles puis produit les livrables du morceau."""
    bx1, by1, bx2, by2 = bbox_natif
    tampon_max_m = min(bx2 - bx1, by2 - by1) / 3.0
    bbox_orig = args.zone_bbox
    nom_orig = args.zone_nom
    args.zone_bbox = f"{bx1:.2f},{by1:.2f},{bx2:.2f},{by2:.2f}"
    args.zone_nom = nom_z
    conversion_ok = True
    mbtiles_attendus = []
    try:
        if not (args.mbtiles or args.rmap or args.sqlitedb):
            return None
        bbox = (bx1, by1, bx2, by2)
        racine = (
            Path(args.dossier).resolve()
            if args.dossier
            else Path(dependances.dossier_travail)
            / "Projets"
            / nom_zone_base
            / dependances.lidar_subdir
        )
        dossier_ville = racine / nom_z
        voisins = dependances.voisins_dossiers(
            racine, nom_zone_base, i_lat, i_lon, n_lat, n_lon
        )

        with dependances.contexte_manifeste(manifeste, cle + "_t"):
            for tif in dependances.lister_tifs_ombrages(dossier_ville, None):
                stem = re.sub(r"_tuilage_z\d+$", "", tif.stem)
                suffix = (
                    stem[len(nom_z) + 1 :]
                    if stem.startswith(nom_z + "_")
                    else stem
                )
                nom_base = f"{nom_z}_{suffix}"

                cogs = [tif]
                for voisin in voisins:
                    candidat = voisin / f"{voisin.name}_{suffix}.tif"
                    if candidat.exists():
                        cogs.append(candidat)

                if len(cogs) > 1:
                    import rasterio

                    with rasterio.open(str(tif)) as dataset:
                        resolution = dataset.transform.a
                    vrt_path = dossier_ville / f"_voisins_{suffix}.vrt"
                    dependances.build_vrt_xml(cogs, vrt_path, resolution)
                    dependances.creer_fichier(vrt_path)
                    tif_source = vrt_path
                else:
                    tif_source = tif

                mbt_path = (
                    dossier_ville
                    / f"{nom_base}_z{args.zoom_min}-{args.zoom_max}.mbtiles"
                )
                mbtiles_attendus.append(mbt_path)
                mbt_neuf = dependances.mbtiles_a_regenerer(
                    mbt_path, args.tuiles_ecraser, source=tif
                )
                if mbt_neuf:
                    mbt_out = dependances.generer_mbtiles_lidar(
                        tif_source,
                        dossier_ville,
                        nom_base,
                        zoom_min=args.zoom_min,
                        zoom_max=args.zoom_max,
                        format_tuiles=args.formats_image,
                        jpeg_quality=args.qualite_image,
                        bbox_natif=bbox,
                        tampon_coin_max_m=tampon_max_m,
                        ecraser_tuiles=args.tuiles_ecraser,
                        tile_workers=dependances.tile_workers_defaut(),
                    )
                else:
                    dependances.imprimer(
                        f"  Existing MBTiles: {mbt_path.name}, "
                        "direct split/conversion"
                    )
                    mbt_out = mbt_path
                conversion_ok = (
                    dependances.convertir_formats(
                        mbt_out,
                        args,
                        decoupe_sortie=False,
                        mbtiles_neuf=mbt_neuf,
                    )
                    and conversion_ok
                )
    finally:
        args.zone_bbox = bbox_orig
        args.zone_nom = nom_orig
    return dependances.resultat_chunk(conversion_ok, mbtiles_attendus)


def traiter_bbox_wmts(
    args,
    bbox_wgs84,
    nom_z,
    nom_zone_base,
    layer,
    style,
    img_fmt,
    fmt_ext,
    apikey_requis,
    manifeste,
    cle,
    *,
    dependances,
):
    """Produit puis convertit le MBTiles WMTS d'un morceau raster."""
    lon_w, lat_s, lon_e, lat_n = bbox_wgs84
    nom_orig = args.zone_nom
    args.zone_nom = nom_z
    traitement_ok = True
    mbtiles_attendus = []
    try:
        with dependances.contexte_manifeste(manifeste, cle):
            zoom_min = min(args.zoom_min, args.zoom_max)
            zoom_max = max(args.zoom_min, args.zoom_max)
            tuiles = dependances.calculer_grille_xyz(
                lat_s, lon_w, lat_n, lon_e, zoom_min, zoom_max
            )
            total_tuiles = dependances.compter_tuiles_xyz(
                lat_s, lon_w, lat_n, lon_e, zoom_min, zoom_max
            )
            racine_base = (
                Path(args.dossier).resolve()
                if args.dossier
                else Path(dependances.dossier_travail)
                / "Projets"
                / nom_zone_base
                / "raster"
            )
            dossier = racine_base / nom_z
            dossier.mkdir(parents=True, exist_ok=True)
            jpeg_quality = dependances.jpeg_quality_sortie(
                img_fmt, args.formats_image, args.qualite_image
            )
            nom_fichier = dependances.nom_mbtiles_wmts(
                nom_z, args.couche, zoom_min, zoom_max, jpeg_quality
            )
            chemin_mbtiles = dossier / f"{nom_fichier}.mbtiles"
            mbtiles_attendus.append(chemin_mbtiles)
            dossier_cache = Path(dependances.dossier_cache) / "ign_raster"
            dossier_cache.mkdir(parents=True, exist_ok=True)
            mbtiles_neuf = dependances.mbtiles_a_regenerer(
                chemin_mbtiles, args.tuiles_ecraser
            )
            if mbtiles_neuf:
                dependances.generer_mbtiles_wmts(
                    chemin=chemin_mbtiles,
                    tuiles_iter=tuiles,
                    total=total_tuiles,
                    nom_zone=nom_z,
                    fmt_ext=fmt_ext,
                    zoom_min=zoom_min,
                    zoom_max=zoom_max,
                    layer=layer,
                    style=style,
                    img_fmt=img_fmt,
                    apikey=args.apikey,
                    apikey_requis=apikey_requis,
                    workers=args.workers,
                    bbox_wgs84=(lon_w, lat_s, lon_e, lat_n),
                    jpeg_quality=jpeg_quality,
                    dossier_cache=dossier_cache,
                    ecraser_tuiles=args.tuiles_ecraser,
                    ecraser_dalles=args.telechargement_ecraser,
                )
            if chemin_mbtiles.exists():
                traitement_ok = dependances.convertir_formats(
                    chemin_mbtiles,
                    args,
                    decoupe_sortie=False,
                    mbtiles_neuf=mbtiles_neuf,
                )
            else:
                traitement_ok = False
    finally:
        args.zone_nom = nom_orig
    return dependances.resultat_chunk(traitement_ok, mbtiles_attendus)
