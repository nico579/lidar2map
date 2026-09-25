#!/usr/bin/env python3
"""Point d'entrée unique des tests locaux de lidar2map.

Les tests historiques sont des scripts autonomes, certains basés sur
``unittest`` et d'autres sur un petit harness d'assertions. Les lancer dans
des sous-processus conserve leur isolation (imports, globals et caches Numba)
tout en garantissant qu'aucune suite silencieusement oubliée ne sorte de la CI.

Usage :
    python tests/run_tests.py fast
    python tests/run_tests.py scientific
    python tests/run_tests.py          # toutes les suites hors réseau

Le smoke test des providers reste volontairement séparé : il contacte les
services externes et possède son propre workflow hebdomadaire.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent

FAST_SCRIPTS = (
    "_test_bootstrap.py",
    "_test_refactor_contracts.py",
    "_test_geojson_osm.py",
    "_test_geojson_raster.py",
    "_test_geojson_mapsforge.py",
    "_test_split_history.py",
    "_test_atomic_downloads.py",
    "_test_atomic_publications.py",
    "_test_docs_links.py",
    "test_cli_docs.py",
    "_test_patch_delivery.py",
    "_test_rlidar2map_CLI.py",
    "test_phone_share.py",
    "test_serve_web.py",
    "test_autostart.py",
)

SCIENTIFIC_SCRIPTS = (
    "_test_corrections.py",
    "_test_tiling.py",
    "_test_mbtiles_lidar_atomic.py",
    "_test_robustesse.py",
    "_test_interactions.py",
)

PROFILES = {
    "fast": FAST_SCRIPTS,
    "scientific": SCIENTIFIC_SCRIPTS,
    "all": FAST_SCRIPTS + SCIENTIFIC_SCRIPTS,
}


def _test_scripts_on_disk() -> set[str]:
    """Retourne les suites hors réseau qui doivent être enregistrées ici."""
    return {
        path.name
        for path in TESTS_DIR.glob("*.py")
        if path.name.startswith(("_test_", "test_"))
    }


def _validate_registry() -> list[str]:
    registered = list(PROFILES["all"])
    duplicates = sorted({name for name in registered if registered.count(name) > 1})
    missing = sorted(_test_scripts_on_disk() - set(registered))
    stale = sorted(set(registered) - _test_scripts_on_disk())
    errors = []
    if duplicates:
        errors.append("suites enregistrées plusieurs fois: " + ", ".join(duplicates))
    if missing:
        errors.append("suites non enregistrées: " + ", ".join(missing))
    if stale:
        errors.append("suites enregistrées absentes: " + ", ".join(stale))
    return errors


# Une suite qui ne rend jamais la main gelait tout le lanceur, et le tuer de
# l'extérieur laissait l'enfant orphelin (un test_serve_web.py a tenu deux
# ports quatre jours). La suite la plus lente prend ~60 s : 600 s ne coupe
# qu'un vrai blocage, qui devient un échec lisible au lieu d'une attente.
SUITE_TIMEOUT_S = 600


def _kill_tree(process: subprocess.Popen) -> None:
    """Tue la suite ET ses descendants (faux ssh, serveurs de test...)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                       capture_output=True, check=False)
    else:
        os.killpg(process.pid, 9)
    process.wait()


def _run(script: str, env: dict[str, str]) -> tuple[int, float]:
    path = TESTS_DIR / script
    started = time.perf_counter()
    print(f"\n{'=' * 72}\nTEST {script}\n{'=' * 72}", flush=True)
    process = subprocess.Popen(
        [sys.executable, str(path)],
        cwd=ROOT,
        env=env,
        start_new_session=(os.name != "nt"),   # groupe à tuer d'un bloc
    )
    try:
        returncode = process.wait(timeout=SUITE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        _kill_tree(process)
        print(f"TIMEOUT {script}: still running after {SUITE_TIMEOUT_S}s,"
              " process tree killed", flush=True)
        returncode = -1
    except KeyboardInterrupt:
        # Hors du groupe du terminal, Ctrl+C n'atteint plus la suite.
        _kill_tree(process)
        raise
    return returncode, time.perf_counter() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile",
        choices=tuple(PROFILES),
        default="all",
        nargs="?",
        help="fast, scientific, ou all (défaut)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="arrêter à la première suite en échec",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="afficher les suites du profil sans les exécuter",
    )
    args = parser.parse_args(argv)

    registry_errors = _validate_registry()
    if registry_errors:
        for error in registry_errors:
            print(f"ERROR test registry: {error}", file=sys.stderr)
        return 2

    scripts = PROFILES[args.profile]
    if args.list:
        print("\n".join(scripts))
        return 0

    env = os.environ.copy()
    env["LIDAR2MAP_BOOTSTRAP"] = "none"
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    failures = []
    durations = []
    started = time.perf_counter()
    for script in scripts:
        returncode, duration = _run(script, env)
        durations.append((script, duration))
        if returncode:
            failures.append((script, returncode))
            if args.fail_fast:
                break

    print(f"\n{'=' * 72}\nSUMMARY ({args.profile})\n{'=' * 72}")
    for script, duration in durations:
        status = "FAIL" if any(name == script for name, _ in failures) else "OK"
        print(f"{status:4}  {duration:7.1f}s  {script}")
    print(f"Total: {time.perf_counter() - started:.1f}s")

    if failures:
        print("Failures: " + ", ".join(
            f"{script} (exit {returncode})" for script, returncode in failures
        ))
        return 1
    print(f"All {len(durations)} suites passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
