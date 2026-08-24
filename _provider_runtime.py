"""Catalogue et chargement dynamique des providers LiDAR.

Le module principal conserve la mutation du provider actif et fournit toutes
les coutures d'import, d'environnement, de sortie d'erreur et d'arrêt.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Callable


@dataclass(frozen=True)
class DependancesCatalogueProviders:
    importer: Callable
    ecrire: Callable = print
    stderr: object = sys.stderr


@dataclass(frozen=True)
class DependancesChargementProvider:
    importer: Callable
    ecrire: Callable = print
    stderr: object = sys.stderr
    quitter: Callable = sys.exit


def discover_providers(
    providers_dir,
    *,
    dependances: DependancesCatalogueProviders,
):
    """Construit le catalogue GUI des providers primaires disponibles."""
    try:
        common_provider = dependances.importer("providers", "common")
        country_info = common_provider.COUNTRY_INFO
    except Exception:
        country_info = {}
    providers_dir = Path(providers_dir)
    result = []
    if not providers_dir.exists():
        return result
    for provider_file in sorted(providers_dir.glob("*.py")):
        if provider_file.stem.startswith("_"):
            continue
        if provider_file.stem.endswith("_laz"):
            continue
        try:
            module = dependances.importer("providers", provider_file.stem)
            if not hasattr(module, "CODE"):
                continue
            country = getattr(module, "COUNTRY", "")
            rank, country_en, country_fr = country_info.get(
                country, (9999, country.upper(), country.upper())
            )
            entry = {
                "code": getattr(module, "CODE", provider_file.stem),
                "name": getattr(module, "NAME", provider_file.stem),
                "country": country,
                "country_rank": rank,
                "country_fr": country_fr,
                "country_en": country_en,
                "apikey_requise": bool(
                    getattr(module, "APIKEY_REQUISE", False)
                ),
                "resolution_m": float(getattr(module, "RESOLUTION_M", 0.5)),
            }
            if (providers_dir / f"{provider_file.stem}_laz.py").exists():
                try:
                    twin = dependances.importer(
                        "providers", f"{provider_file.stem}_laz"
                    )
                    entry["laz"] = {
                        "hmin": float(getattr(twin, "LAZ_HMIN", 0.4)),
                        "hmax": float(getattr(twin, "LAZ_HMAX", 2.5)),
                        "classes": ",".join(
                            str(value)
                            for value in getattr(
                                twin, "LAZ_CLASSES", (1, 3, 4)
                            )
                        ),
                        "ground": str(
                            getattr(twin, "LAZ_GROUND", "classes")
                        ),
                        "csf_threshold": float(
                            getattr(twin, "LAZ_CSF_THRESHOLD", 0.5)
                        ),
                        "csf_resolution": float(
                            getattr(twin, "LAZ_CSF_RESOLUTION", 0.5)
                        ),
                        "csf_rigidness": int(
                            getattr(twin, "LAZ_CSF_RIGIDNESS", 1)
                        ),
                        "download_workers_max": int(
                            getattr(twin, "DOWNLOAD_WORKERS_MAX", 0)
                        ),
                    }
                except Exception:
                    pass
            result.append(entry)
        except Exception as error:
            dependances.ecrire(
                f"  [provider scan] {provider_file.name} skipped: "
                f"{type(error).__name__}: {error}",
                file=dependances.stderr,
            )
    return result


def pre_valeur_suivante(argv, index):
    """Retourne la valeur d'un pré-flag s'il ne s'agit pas d'un autre flag."""
    if index + 1 < len(argv) and not argv[index + 1].startswith("--"):
        return argv[index + 1]
    return None


def _provider_france_inline():
    provider = SimpleNamespace(
        CODE="fr-ign",
        NAME="France IGN LiDAR HD",
        COUNTRY="fr",
        CRS_NATIF="EPSG:2154",
        RESOLUTION_M=0.5,
        DALLE_KM=1,
        PX_PAR_DALLE=2000,
        SEUIL_DALLE_VALIDE=50_000,
        APIKEY_REQUISE=False,
        WMS_URL=None,
        WMS_LAYER=None,
        WFS_URL=None,
    )
    provider.discover_dalles = (
        lambda bbox_wgs84, bbox_natif, cache_path, workers=1: {}
    )
    provider.subdir_from_name = lambda nom: None
    provider.post_download = lambda chemin: None
    provider.post_fetch = None
    provider.set_apikey = lambda key: None
    return provider


def load_provider(
    argv,
    environnement,
    providers_dir,
    cli_explicit=False,
    *,
    dependances: DependancesChargementProvider,
):
    """Consomme les pré-flags et charge le provider demandé.

    Retourne ``(provider, cli_explicit)``. ``argv`` est volontairement modifié
    en place afin que les parseurs propres à chaque mode ne voient pas ces
    pré-flags globaux.
    """
    code = None
    laz_mode = False
    laz_params = {}
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--provider":
            value = pre_valeur_suivante(argv, index)
            if value is None:
                dependances.ecrire(
                    "  ERROR: --provider requires a code "
                    "(e.g. --provider us-tnm).",
                    file=dependances.stderr,
                )
                dependances.quitter(1)
            code = value
            cli_explicit = True
            del argv[index:index + 2]
            continue
        if argument.startswith("--provider="):
            code = argument.split("=", 1)[1]
            cli_explicit = True
            del argv[index]
            continue
        if argument == "--laz":
            laz_mode = True
            del argv[index]
            continue
        matched = False
        for key in (
            "hmin",
            "hmax",
            "classes",
            "ground",
            "csf-threshold",
            "csf-resolution",
            "csf-rigidness",
        ):
            if argument == f"--laz-{key}":
                value = pre_valeur_suivante(argv, index)
                if value is None:
                    dependances.ecrire(
                        f"  ERROR: --laz-{key} requires a value.",
                        file=dependances.stderr,
                    )
                    dependances.quitter(1)
                laz_params[key] = value
                del argv[index:index + 2]
                matched = True
                break
            if argument.startswith(f"--laz-{key}="):
                laz_params[key] = argument.split("=", 1)[1]
                del argv[index]
                matched = True
                break
        if matched:
            continue
        index += 1

    code = code or environnement.get("LIDAR2MAP_PROVIDER") or "fr-ign"
    if (laz_mode or laz_params) and not code.endswith("-laz"):
        code += "-laz"
    module_name = code.replace("-", "_")
    providers_dir = Path(providers_dir)
    try:
        module = dependances.importer("providers", module_name)
        if laz_params:
            setter = getattr(module, "set_laz_params", None)
            if setter is None:
                dependances.ecrire(
                    f"  ERROR: provider '{code}' has no LAZ settings "
                    "(set_laz_params).",
                    file=dependances.stderr,
                )
                dependances.quitter(1)
            try:
                setter(
                    hmin=(
                        float(laz_params["hmin"])
                        if "hmin" in laz_params
                        else None
                    ),
                    hmax=(
                        float(laz_params["hmax"])
                        if "hmax" in laz_params
                        else None
                    ),
                    classes=(
                        tuple(
                            int(value)
                            for value in laz_params["classes"].split(",")
                        )
                        if "classes" in laz_params
                        else None
                    ),
                    ground=laz_params.get("ground"),
                    csf_threshold=laz_params.get("csf-threshold"),
                    csf_resolution=laz_params.get("csf-resolution"),
                    csf_rigidness=laz_params.get("csf-rigidness"),
                )
            except ValueError as error:
                dependances.ecrire(
                    f"  ERROR: invalid --laz-* value: {error}",
                    file=dependances.stderr,
                )
                dependances.quitter(1)
        return module, cli_explicit
    except ModuleNotFoundError as error:
        missing = getattr(error, "name", "") or ""
        package = f"providers.{module_name}"
        if (
            missing == package
            and providers_dir.exists()
            and code.endswith("-laz")
            and laz_mode
        ):
            available = ", ".join(
                sorted(
                    path.stem[:-4].replace("_", "-")
                    for path in providers_dir.glob("*_laz.py")
                )
            )
            dependances.ecrire(
                f"  ERROR: provider '{code[:-4]}' has no LAZ mode (no module "
                f"providers/{module_name}.py). LAZ is available for: {available}",
                file=dependances.stderr,
            )
            dependances.quitter(1)
        if missing == package and providers_dir.exists():
            available = sorted(
                path.stem.replace("_", "-")
                for path in providers_dir.glob("*.py")
                if not path.stem.startswith("_")
            )
            dependances.ecrire(
                f"  ERROR: unknown provider '{code}'. Available: "
                f"{', '.join(available)}",
                file=dependances.stderr,
            )
            dependances.quitter(1)
        if missing not in ("providers", package):
            dependances.ecrire(
                f"  ERROR: provider '{code}' failed to load: missing "
                f"dependency '{missing}'. Install it or choose another "
                "provider.",
                file=dependances.stderr,
            )
            dependances.quitter(1)
        return _provider_france_inline(), cli_explicit
    except ImportError as error:
        dependances.ecrire(
            f"  ERROR loading provider '{code}': "
            f"{type(error).__name__}: {error}",
            file=dependances.stderr,
        )
        dependances.quitter(1)

