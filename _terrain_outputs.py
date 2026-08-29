"""Production des ombrages et livrables raster du passage terrain monolithique."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable


_SEUIL_COMPRESSION_OCTETS = 500e6


@dataclass(frozen=True)
class DependancesSortiesTerrain:
    """Coutures nécessaires à la production terrain hors découpage."""

    resoudre_choix_ombrages: Callable[..., Any]
    elevation_soleil: float
    generer_ombrages: Callable[..., Any]
    mbtiles_a_regenerer: Callable[..., Any]
    generer_mbtiles_lidar: Callable[..., Any]
    tile_workers_defaut: Callable[..., Any]
    convertir_formats: Callable[..., Any]
    lister_tifs_ombrages: Callable[..., Any]
    tuiler_tifs_ombrages: Callable[..., Any]
    charger_rasterio: Callable[[], Any]
    chemin_part: Callable[..., Path]
    publier_tif_atomique: Callable[..., Any]
    maintenant: Callable[[], float]
    formater_duree: Callable[[Any], str]
    imprimer: Callable[..., Any] = print


def _compresser_ombrages_existants(args, dossier_ville, dependances):
    """Recompresse en staging les grands TIFF déjà présents dans le dossier."""

    if not args.ombrages_compresser:
        return

    d = dependances
    try:
        rasterio = d.charger_rasterio()
    except ImportError:
        d.imprimer("  ERROR: rasterio missing, run pip install rasterio")
        return

    tifs_bruts = [
        tif
        for tif in dossier_ville.glob("*.tif")
        if not tif.name.startswith("_")
        and not re.search(r"_tuilage_z\d+\.tif$", tif.name)
    ]
    tifs_a_compresser = [
        tif
        for tif in tifs_bruts
        if tif.stat().st_size > _SEUIL_COMPRESSION_OCTETS
    ]
    if not tifs_a_compresser:
        d.imprimer("  No raw shading found (> 500 MB) to compress.")
        return

    d.imprimer(f"  {len(tifs_a_compresser)} file(s) to compress:")
    for chemin_out in sorted(tifs_a_compresser):
        taille_brut = chemin_out.stat().st_size / 1e6
        chemin_part = d.chemin_part(chemin_out)
        debut = d.maintenant()
        try:
            # L'ancien final reste lisible jusqu'à la publication atomique de la
            # copie recompressée.
            with rasterio.open(str(chemin_out)) as source:
                profile = source.profile.copy()
                for cle in (
                    "driver",
                    "BIGTIFF",
                    "bigtiff",
                    "NODATA",
                    "nodata",
                ):
                    profile.pop(cle, None)
                profile.update(
                    {
                        "driver": "GTiff",
                        "compress": "deflate",
                        "predictor": 2,
                        "tiled": True,
                        "blockxsize": 512,
                        "blockysize": 512,
                        "BIGTIFF": "IF_SAFER",
                    }
                )
                if source.nodata is not None:
                    profile["nodata"] = source.nodata
                with rasterio.open(str(chemin_part), "w", **profile) as destination:
                    # Copie fenêtrée, bande par bande, pour borner la RAM.
                    for _index, window in source.block_windows(1):
                        for bande in range(1, source.count + 1):
                            destination.write(
                                source.read(bande, window=window),
                                bande,
                                window=window,
                            )
            d.publier_tif_atomique(chemin_part, chemin_out)
            duree = d.maintenant() - debut
            taille_compressee = chemin_out.stat().st_size / 1e6
            gain = int((1 - taille_compressee / taille_brut) * 100)
            d.imprimer(
                "  "
                + chemin_out.name.ljust(56)
                + str(round(taille_brut)).rjust(6)
                + " MB -> "
                + str(round(taille_compressee)).rjust(5)
                + " MB  (-"
                + str(gain)
                + "%)  "
                + d.formater_duree(duree)
            )
        except BaseException as exc:
            chemin_part.unlink(missing_ok=True)
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            d.imprimer(f"  ERROR compressing {chemin_out.name}: {exc}")


def produire_sorties_terrain(
    args,
    dalles_ombrages,
    dossier_ville,
    nom_zone,
    bbox,
    annoncer_etape,
    *,
    dependances,
):
    """Produit les ombrages puis les formats raster et agrège leur succès."""
    d = dependances
    dossier_ville = Path(dossier_ville)

    _compresser_ombrages_existants(args, dossier_ville, d)

    choix_ombrages, spec_insts = d.resoudre_choix_ombrages(args)
    if not dalles_ombrages:
        choix_ombrages = []

    tifs_run = None
    if choix_ombrages or spec_insts:
        surface_km2 = len(dalles_ombrages)
        libelles = choix_ombrages + [
            type_ombrage
            + (
                ":"
                + ",".join(
                    f"{key}={value:g}"
                    if isinstance(value, float)
                    else f"{key}={value}"
                    for key, value in params.items()
                )
                if params
                else ""
            )
            for type_ombrage, params in spec_insts
        ]
        annoncer_etape("Shadings " + ", ".join(libelles))
        d.imprimer(f"  Shadings : {', '.join(libelles)}")
        elevation = (
            args.ombrages_elevation
            if args.ombrages_elevation is not None
            else d.elevation_soleil
        )
        d.imprimer(f"  Sun angle : {elevation}°")
        estimation = (
            "5-10 min"
            if surface_km2 < 100
            else "15-45 min"
            if surface_km2 < 500
            else "1h+"
        )
        d.imprimer(
            f"  Area: ~{surface_km2} km²  |  Estimated duration: {estimation}"
            " (depends on the shading type and machine)",
            flush=True,
        )
        tifs_run = d.generer_ombrages(
            dalles_ombrages,
            dossier_ville,
            choix_ombrages,
            elevation_soleil=elevation,
            nom_zone=nom_zone,
            ecraser_ombrages=args.ombrages_ecraser,
            use_sweep=args.sweep_horizon,
            svf_gamma=args.svf_gamma,
            svf_conv=args.svf_conv,
            svf_dist=args.svf_dist,
            bbox_natif=tuple(bbox),
            instances=spec_insts or None,
        )

    livrables_ok = True
    if args.mbtiles or args.rmap or args.sqlitedb:
        if args.source and Path(args.source).suffix.lower() in (".tif", ".tiff"):
            tif_source = Path(args.source).resolve()
            libelle = "RMAP" if args.rmap and not args.mbtiles else "MBTiles"
            annoncer_etape(f"{libelle} depuis {tif_source.name}")
            d.imprimer(f"  Source : {tif_source}")
            d.imprimer(
                f"  Zone   : bbox natif {bbox[0]:.0f},{bbox[1]:.0f}"
                f" → {bbox[2]:.0f},{bbox[3]:.0f}"
            )
            suffixes = (
                "multi_ombrage",
                "315_ombrage",
                "045_ombrage",
                "135_ombrage",
                "225_ombrage",
                "slope_ombrage",
                "svf_ombrage",
                "svf_100m_ombrage",
                "lrm_ombrage",
                "rrim_ombrage",
            )
            suffixe = next(
                (item for item in suffixes if item in tif_source.stem),
                tif_source.stem,
            )
            nom_base = f"{nom_zone}_{suffixe}"
            nom_mbtiles = (
                f"{nom_base}_z{args.zoom_min}-{args.zoom_max}"
            )
            mbtiles_path = dossier_ville / f"{nom_mbtiles}.mbtiles"
            ecraser = args.tuiles_ecraser
            mbtiles_requis = d.mbtiles_a_regenerer(
                mbtiles_path,
                ecraser,
                source=tif_source,
            )
            mbtiles_sortie = None
            if mbtiles_requis:
                mbtiles_sortie = d.generer_mbtiles_lidar(
                    tif_source,
                    dossier_ville,
                    nom_base,
                    zoom_min=args.zoom_min,
                    zoom_max=args.zoom_max,
                    format_tuiles=args.formats_image,
                    jpeg_quality=args.qualite_image,
                    bbox_natif=bbox,
                    source_already_warped=getattr(
                        args,
                        "_source_already_warped",
                        False,
                    ),
                    ecraser_tuiles=ecraser,
                    tile_workers=d.tile_workers_defaut(),
                )
            elif mbtiles_path.exists():
                d.imprimer(
                    f"  Existing MBTiles: {mbtiles_path.name}, "
                    "direct split/conversion"
                )
                mbtiles_sortie = mbtiles_path
            livrables_ok = (
                bool(
                    d.convertir_formats(
                        mbtiles_sortie,
                        args,
                        mbtiles_neuf=mbtiles_requis,
                    )
                )
                and livrables_ok
            )
        else:
            ombrages_tifs = d.lister_tifs_ombrages(
                dossier_ville,
                tifs_run,
            )
            if ombrages_tifs:
                annoncer_etape("MBTiles")
                livrables_ok = (
                    bool(
                        d.tuiler_tifs_ombrages(
                            args,
                            ombrages_tifs,
                            dossier_ville,
                            nom_zone,
                            bbox,
                            verbose=True,
                        )
                    )
                    and livrables_ok
                )
            else:
                d.imprimer(
                    "  No shading found for MBTiles "
                    "(generate --shadings first)"
                )
                livrables_ok = False

    return livrables_ok
