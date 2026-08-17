"""Orchestration hors réseau-testable du diagnostic intégré lidar2map."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


TESTS = (
    (
        "LiDAR",
        ("--ignlidar", "--telechargement", "--workers", "4", "--ombrages",
         "multi", "--formats-fichier", "mbtiles", "--zoom-min", "10",
         "--zoom-max", "13"),
        ("ign_lidar/smoke_multi_ombrage_z10-13.mbtiles",),
    ),
    (
        "WMTS (planign)",
        ("--ignraster", "--couche", "planign", "--workers", "8",
         "--formats-fichier", "mbtiles", "--zoom-min", "12", "--zoom-max", "14"),
        ("raster/smoke_planign_z12-14.mbtiles",),
    ),
    (
        "WFS (routes)",
        ("--ignvecteur", "--couche", "routes", "--formats-fichier", "gz"),
        ("ign_vecteur/smoke_ign_troncon_de_route.geojson.gz",),
    ),
    (
        "OSM (highway)",
        ("--osm", "--couche", "highway=*", "--formats-fichier", "map", "gz"),
        ("osm_vecteur/smoke.map", "osm_vecteur/smoke_osm_highway.geojson.gz"),
    ),
)


def _taille(n):
    return f"{n / 1e6:.1f} Mo" if n >= 1e6 else f"{n / 1024:.0f} Ko"


def executer_smoketest(
    *,
    frozen,
    executable,
    script_path,
    environnement,
    lancer=subprocess.run,
    supprimer_arbre=shutil.rmtree,
    maintenant=time.time,
    ecrire=print,
):
    """Exécute les cinq diagnostics et retourne ``True`` en l'absence d'échec."""
    script_path = Path(script_path).resolve()
    if frozen:
        work = Path(environnement.get("LIDAR2MAP_WORK_DIR") or Path(executable).resolve().parent)
        cmd_base = [executable]
    else:
        work = script_path.parent
        cmd_base = [executable, str(script_path)]
    projets = work / "Projets" / "smoke"
    zone = ["--zone-ville", "Gareoult", "--zone-width", "2", "--zone-nom", "smoke"]
    env = dict(environnement)
    env["LIDAR2MAP_SKIP_HIST"] = "1"

    def run(name, extra, expected, timeout=600):
        ecrire(f"\n━━━ {name} ━━━")
        debut = maintenant()
        try:
            rc = lancer(cmd_base + zone + list(extra), timeout=timeout, env=env).returncode
        except subprocess.TimeoutExpired:
            ecrire(f"  ✗ TIMEOUT (> {timeout}s)")
            return False
        duree = maintenant() - debut
        if rc != 0:
            ecrire(f"  ✗ exit={rc} en {duree:.0f}s")
            return False
        manquants, tailles = [], []
        for relatif in expected:
            chemin = projets / relatif
            if not chemin.exists():
                manquants.append(relatif + " (absent)")
            elif chemin.stat().st_size == 0:
                manquants.append(relatif + " (vide)")
            else:
                tailles.append(f"{Path(relatif).name}={_taille(chemin.stat().st_size)}")
        if manquants:
            ecrire(f"  ✗ outputs KO en {duree:.0f}s :")
            for manque in manquants:
                ecrire(f"      {manque}")
            return False
        ecrire(f"  ✓ {duree:.0f}s  ({', '.join(tailles)})")
        return True

    def fusion(timeout=120):
        source = projets / "osm_vecteur" / "smoke_osm_highway.geojson.gz"
        sortie = projets / "fusion" / "smoke_fusion.geojson.gz"
        ecrire("\n━━━ Merge ━━━")
        if not source.exists():
            ecrire(f"  ⊘ SKIP: OSM input missing ({source.name})")
            return None
        sortie.parent.mkdir(parents=True, exist_ok=True)
        debut = maintenant()
        try:
            rc = lancer(
                cmd_base + ["--fusionner", "--source", str(source), "--sortie",
                            str(sortie), "--formats-fichier", "gz"],
                timeout=timeout,
                env=env,
            ).returncode
        except subprocess.TimeoutExpired:
            ecrire(f"  ✗ TIMEOUT (> {timeout}s)")
            return False
        duree = maintenant() - debut
        if rc == 0 and sortie.exists() and sortie.stat().st_size > 0:
            ecrire(f"  ✓ {duree:.0f}s  ({_taille(sortie.stat().st_size)})")
            return True
        ecrire(f"  ✗ exit={rc} en {duree:.0f}s")
        return False

    ecrire("━━━ Smoke test: Gareoult 1 km ━━━")
    ecrire(f"  Binaire : {' '.join(cmd_base)}")
    ecrire(f"  Outputs : {projets}")
    if projets.exists():
        supprimer_arbre(projets, ignore_errors=True)
        if projets.exists():
            ecrire("  ✗ Cannot clean previous smoke outputs.")
            return False

    resultats = [(nom, run(nom, extra, attendus)) for nom, extra, attendus in TESTS]
    resultats.append(("Fusion", fusion()))
    ecrire("\n━━━ RESULTS ━━━")
    reussis = sum(ok is True for _nom, ok in resultats)
    echecs = sum(ok is False for _nom, ok in resultats)
    ignores = sum(ok is None for _nom, ok in resultats)
    for nom, ok in resultats:
        symbole = "✓" if ok is True else ("⊘" if ok is None else "✗")
        ecrire(f"  {symbole} {nom}")
    bilan = f"\n{reussis}/{len(resultats)} OK"
    if ignores:
        bilan += f"  ({ignores} skipped)"
    if echecs:
        bilan += f"  ({echecs} failed)"
    ecrire(bilan)
    return echecs == 0
