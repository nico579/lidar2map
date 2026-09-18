"""Reconstruction de la configuration d'historique depuis la ligne de commande.

Le module ne persiste rien : il traduit seulement un instantané d'``argv`` vers
les clés attendues par ``loadConfig()`` dans l'interface graphique.
"""

from dataclasses import dataclass
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class DependancesCfgDepuisArgv:
    """Coutures applicatives relues par la façade à chaque appel."""

    provider: Any
    svf_gamma: float
    rediger_secrets: Callable[[str], str]


def cfg_depuis_argv(argv: Sequence[str], *, dependances) -> dict:
    """Construit les 52 clés historiques depuis un instantané d'``argv``."""
    d = dependances

    # Helpers variadiques : acceptent plusieurs orthographes du même flag
    # (anglais canonique + alias français) et prennent la 1re présente dans argv.
    def _arg(*flags, default=""):
        for flag in flags:
            try:
                return argv[argv.index(flag) + 1]
            except (ValueError, IndexError):
                continue
        return default

    def _arg_int(*flags, default=0):
        value = _arg(*flags, default="")
        try:
            return int(value) if value else default
        except ValueError:
            return default

    def _arg_float(*flags, default=0.0):
        value = _arg(*flags, default="")
        try:
            return float(value) if value else default
        except ValueError:
            return default

    def _flag(*flags):
        return any(flag in argv for flag in flags)

    def _args_after(*flags):
        """Retourne les args après le 1er flag présent jusqu'au prochain ``--``."""
        for flag in flags:
            try:
                index = argv.index(flag) + 1
            except ValueError:
                continue
            result = []
            while index < len(argv) and not argv[index].startswith("--"):
                result.append(argv[index])
                index += 1
            return result
        return []

    type_run = (
        "lidar" if _flag("--lidar", "--ignlidar") else
        "scan" if _flag("--raster", "--ignraster") else
        "vecteur" if _flag("--vector", "--ignvecteur") else
        "osm" if _flag("--osm") else
        "fusion" if _flag("--merge", "--fusionner") else
        "decoupe" if _flag("--split", "--decouper") else "lidar"
    )

    mode = (
        "region" if _flag("--zone-region") else
        "dep" if _flag("--zone-department", "--zone-departement") else
        "gps" if _flag("--zone-gps") else
        "bbox" if _flag("--zone-bbox") else "ville"
    )

    formats = _args_after("--file-formats", "--formats-fichier")
    ombrages = _args_after("--shadings", "--ombrages")
    source_cli = _arg("--source")
    maintenance_cli = _flag(
        "--tiles-purge-invalid", "--dalles-purger-invalides",
        "--tiles-purge-out-of-zone", "--dalles-purger-hors-zone",
        "--shadings-compress", "--ombrages-compresser",
    )
    produit_cli = bool(
        ombrages or formats or _flag("--shading", "--shading-preset")
    )
    lidar_standard = (
        type_run == "lidar" and not source_cli
        and not (maintenance_cli and not produit_cli)
    )
    if (lidar_standard and not ombrages
            and not _flag("--shading", "--shading-preset")):
        ombrages = ["lrm"]
    if (lidar_standard and not formats
            and (ombrages and not any(v in ombrages for v in ("aucun", "none"))
                 or _flag("--shading", "--shading-preset"))):
        formats = ["mbtiles"]

    return {
        # Provider pris du global déjà résolu : --provider a quitté sys.argv.
        "provider": d.provider.CODE,
        # Zone
        "type": type_run,
        "mode": mode,
        "nom": _arg("--zone-name", "--zone-nom"),
        "dossier": _arg("--output-dir", "--dossier"),
        "cache_dir": _arg("--cache-dir", "--dossier-cache"),
        "production_dir": _arg("--production-dir", "--dossier-production"),
        "dep": _arg("--zone-department", "--zone-departement"),
        "region": _arg("--zone-region"),
        "ville": _arg("--zone-city", "--zone-ville"),
        "gps": _arg("--zone-gps"),
        "bbox": _arg("--zone-bbox"),
        "zone_width": _arg_float("--zone-width", "--zone-largeur", default=20.0),
        # LiDAR
        "tel": (
            _flag("--download", "--telechargement")
            or (lidar_standard
                and not _flag("--no-download", "--no-telechargement"))
        ),
        # Compression ON par défaut : seule la négation apparaît dans argv.
        "comp": not _flag(
            "--no-download-compress", "--no-telechargement-compresser"
        ),
        "ecraser_tel": _flag(
            "--download-overwrite", "--telechargement-ecraser"
        ),
        # --workers est unique en CLI mais la GUI a un champ par type.
        "workers_l": _arg_int("--workers", default=8) if type_run == "lidar" else 8,
        "laz_parallel": _arg_int("--laz-parallel", default=1),
        "dossier_dalles": _arg("--tiles-dir", "--dossier-dalles"),
        "no_omb": bool(ombrages) or _flag(
            "--shadings", "--ombrages", "--shading"
        ),
        "ombrages": ombrages,
        # --shading est répétable : collecter chaque occurrence anglaise.
        "shading_specs": [
            argv[index + 1]
            for index, argument in enumerate(argv)
            if argument == "--shading" and index + 1 < len(argv)
        ],
        "elevation": _arg_int(
            "--shading-elevation", "--ombrages-elevation", default=25
        ),
        "svf_conv": _arg("--svf-conv") or "flux",
        "svf_dist": _arg_float("--svf-dist", default=20.0),
        "svf_gamma": _arg_float("--svf-gamma", default=d.svf_gamma),
        "sweep_horizon": True,
        "ecraser_omb": _flag(
            "--shadings-overwrite", "--ombrages-ecraser"
        ),
        "mbtiles_l": "mbtiles" in formats,
        "rmap": "rmap" in formats,
        "sqlitedb": "sqlitedb" in formats,
        "zoom_min_l": _arg_int("--zoom-min", default=8),
        "zoom_max_l": _arg_int("--zoom-max", default=18),
        "qualite_l": _arg_int(
            "--image-quality", "--qualite-image", default=85
        ),
        "ecraser_mbt": _flag("--tiles-overwrite", "--tuiles-ecraser"),
        "cols_decoupe": _arg_int("--split-cols", "--cols-decoupe", default=1),
        "rows_decoupe": _arg_int("--split-rows", "--rows-decoupe", default=1),
        "split_width_l": _arg_float(
            "--split-width", "--split-largeur", default=0.0
        ),
        "nettoyage": _flag("--cleanup", "--nettoyage"),
        # IGN Raster
        "couche": _arg("--layer", "--couche"),
        "zoom_min_s": _arg_int("--zoom-min", default=12),
        "zoom_max_s": _arg_int("--zoom-max", default=16),
        "mbtiles_s": "mbtiles" in formats,
        "rmap_s": "rmap" in formats,
        "sqlitedb_s": "sqlitedb" in formats,
        "qualite_s": _arg_int(
            "--image-quality", "--qualite-image", default=85
        ),
        "workers_s": _arg_int("--workers", default=8) if type_run == "scan" else 8,
        # OSM
        "osm_tags_sel": (
            _args_after("--layer", "--couche") if type_run == "osm" else []
        ),
        "workers_osm": (
            _arg_int("--workers", default=4) if type_run == "osm" else 4
        ),
        # IGN Vectoriel
        "wfs_couches_sel": (
            _args_after("--layer", "--couche") if type_run == "vecteur" else []
        ),
        "workers_v": (
            min(_arg_int("--workers", default=4), 4)
            if type_run == "vecteur" else 4
        ),
        # Argv complet pour debug (clés API masquées).
        "argv": d.rediger_secrets(" ".join(argv)),
    }
