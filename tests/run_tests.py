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
    "_test_refactor_contracts.py",
    "_test_split_history.py",
    "_test_atomic_downloads.py",
    "_test_atomic_publications.py",
    "_test_docs_links.py",
    "_test_patch_delivery.py",
    "_test_rlidar2map_CLI.py",
    "test_phone_share.py",
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


def _run(script: str, env: dict[str, str]) -> tuple[int, float]:
    path = TESTS_DIR / script
    started = time.perf_counter()
    print(f"\n{'=' * 72}\nTEST {script}\n{'=' * 72}", flush=True)
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        env=env,
        check=False,
    )
    return completed.returncode, time.perf_counter() - started


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
