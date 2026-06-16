#!/usr/bin/env python3
"""deploy.py — Déploiement unifié lidar2map (cross-platform Windows/macOS/Linux).

Un seul script pour tout :
  • push des sources vers le repo GitHub
  • détection automatique de ce qui a changé
  • action :
        - docs / meta seulement                 -> push seul
        - lidar2map.py seul                     -> push + patch des 3 bundles (sans rebuild)
        - .spec / _loader / build.* / xml       -> push puis STOP : rebuild via release.yml
                                                   (via --new-tag, choix de version humain)

Deux voies pour le patch :
  --mode cloud (défaut)  déclenche update.yml sur le runner GitHub
                         -> les ~1,5 Go transitent sur le réseau GitHub
  --mode local           lance update_app.py --release ici
                         -> les ~1,5 Go transitent par TA connexion

Usage :
  python deploy.py -m "mon correctif"                         # cloud, dernière release
  python deploy.py -m "..." --mode local                      # patch local
  python deploy.py -m "..." --patch-tag v1.3.0                # cibler un tag existant
  python deploy.py -m "..." --new-tag v1.4.0                  # créer nouveau tag → rebuild
  python deploy.py -m "..." --skip-push                       # patch direct (pas de push)
  python deploy.py -m "..." --dry-run                         # voir le diff sans push

Prérequis :
  python (>=3.8), git, gh (authentifié : gh auth status).
  --mode local : GH_TOKEN/GITHUB_TOKEN dans l'env (ou gh auth token disponible).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Force UTF-8 sur stdout/stderr : sous Windows, le défaut cp1252 fait planter
# print() dès qu'on écrit un caractère non-Latin1 (flèches →, accents corrompus
# dans certaines variantes, etc.). reconfigure() est dispo dès Python 3.7.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# === CONFIG (à adapter par projet) ===========================================

PROJECT = "lidar2map"
APP_PY = "lidar2map.py"
REPO_DEFAULT = "nico579/lidar2map"

SRC = Path(__file__).resolve().parent
CLONE = Path(tempfile.gettempdir()) / f"{PROJECT}_gh"
REPO_URL = f"https://github.com/{REPO_DEFAULT}"

# Mapping fichier local -> chemin dans le repo GitHub
MAP = {
    # Source
    "lidar2map.py":                  "lidar2map.py",
    "_loader.py":                    "_loader.py",
    "update_app.py":                 "update_app.py",
    "tagmapping-min.xml":            "tagmapping-min.xml",
    "deploy.py":                     "deploy.py",
    "coverage_map.py":               "coverage_map.py",
    "coverage.geojson":              "coverage.geojson",
    "coverage.png":                  "coverage.png",
    "coverage.fr.png":               "coverage.fr.png",
    # Build Windows / Linux
    "lidar2map_win.spec":            "lidar2map_win.spec",
    "lidar2map_win_launcher.spec":   "lidar2map_win_launcher.spec",
    "lidar2map_win_build.ps1":       "lidar2map_win_build.ps1",
    "setup_build_windows.ps1":       "setup_build_windows.ps1",
    "setup_build_linux.sh":          "setup_build_linux.sh",
    "lidar2map_linux_build.sh":      "lidar2map_linux_build.sh",
    # Build macOS
    "lidar2map_mac.spec":            "lidar2map_mac.spec",
    "lidar2map_mac_launcher.spec":   "lidar2map_mac_launcher.spec",
    "lidar2map_mac_build.sh":        "lidar2map_mac_build.sh",
    "setup_build_mac.sh":            "setup_build_mac.sh",
    # Doc + CI + meta
    "README_Github.md":              "README.md",
    "README_Github.fr.md":           "README.fr.md",
    "README_LIDAR2MAP.md":           "BUILD.md",
    "ci_github.yml":                 ".github/workflows/ci.yml",
    "release_github.yml":            ".github/workflows/release.yml",
    "update_github.yml":             ".github/workflows/update.yml",
    "cross_platform_github.yml":     ".github/workflows/cross_platform.yml",
    "smoke_github.yml":              ".github/workflows/smoke.yml",
    "LICENSE":                       "LICENSE",
    ".gitignore":                    ".gitignore",
}

# Dossiers à synchroniser récursivement (mirror local -> remote)
FOLDERS = {
    "screenshots": "screenshots",
    "providers":   "providers",   # implémentations LiDAR par pays (fr-ign, nl-ahn, ch-swisstopo, etc.)
    "Tests":       "tests",       # tests de régression (calculs scientifiques, tuilage)
}

# Anciens chemins sur GitHub à supprimer (renommages + scripts PS1 obsolètes)
REMOVE = [
    "lidar2map.spec",
    "lidar2map_launcher.spec",
    "lidar2map_build.ps1",
    "build_lidar2map.ps1",
    "launcher.spec",
    "push_github.ps1",       # remplacé par deploy.py
    "deploy_update.ps1",     # remplacé par deploy.py
    "TEST_LINUX_MAC.md",     # contenu utile fondu dans BUILD.md (section Dépannage)
]

# Patterns "rebuild requis" : si l'un de ces fichiers a changé, le patch ne
# suffit pas. tagmapping-min.xml = donnée bundlée (PAS patchable par update_app.py
# qui ne touche que _internal/lidar2map.py).
def is_rebuild_file(name: str) -> bool:
    return (
        name == "_loader.py"
        or name == "tagmapping-min.xml"
        or name.endswith(".spec")
        or name.endswith("_build.ps1")
        or name.endswith("_build.sh")
        or name.startswith("setup_build_")
    )

# === COLOR / IO HELPERS ======================================================

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
if os.name == "nt" and _USE_COLOR:
    # Active la séquence ANSI sur les terminaux Windows récents.
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(h, ctypes.byref(mode))
        kernel32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        _USE_COLOR = False

_COLORS = {"cyan": "\033[36m", "yellow": "\033[33m",
           "red": "\033[31m", "green": "\033[32m"}

def cprint(msg: str, color: str = "") -> None:
    if _USE_COLOR and color in _COLORS:
        print(f"{_COLORS[color]}{msg}\033[0m")
    else:
        print(msg)

def fail(msg: str) -> "NoReturn":
    cprint(f"\nERREUR : {msg}", "red")
    sys.exit(1)

# === SHELL HELPERS ===========================================================

def run(cmd, cwd=None, check=True, capture=False, env=None, timeout=120):
    """Wrapper subprocess.run. capture=True -> renvoie stdout (texte).

    timeout : secondes avant abandon. 120s suffit pour la majorité des git/gh
    opérations. Pour les commandes longues par nature (git clone d'un repo
    avec gros assets, gh run watch sur update.yml, update_app.py --release
    qui upload ~1,5 Go), passer un timeout explicite plus large au call site."""
    try:
        result = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            check=False, text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        fail(f"{' '.join(cmd)} a dépassé le timeout ({timeout}s) — réseau bloqué ou commande hangée ?")
    if check and result.returncode != 0:
        cmd_str = " ".join(cmd)
        err = (result.stderr or result.stdout or "").strip()
        fail(f"{cmd_str} a échoué (code {result.returncode})" + (f"\n{err}" if err else ""))
    return result

def git(*args, check=True, capture=False):
    """git -C <CLONE> <args>"""
    return run(["git", "-C", str(CLONE), *args], check=check, capture=capture)

def gh_json(*args):
    """gh ... --json X (renvoie le JSON parsé)."""
    res = run(["gh", *args], capture=True)
    return json.loads(res.stdout)

def get_latest_tag(repo: str) -> str:
    res = run(["gh", "release", "view", "--repo", repo, "--json", "tagName"],
              capture=True, check=False)
    if res.returncode != 0:
        fail(f"aucune release sur {repo} (crée-en une via release.yml, ou passe --patch-tag)")
    data = json.loads(res.stdout)
    tag = data.get("tagName", "")
    if not tag:
        fail(f"aucune release sur {repo}")
    return tag

def find_python() -> str:
    for name in ("python", "python3", "py"):
        if shutil.which(name):
            return name
    fail("python introuvable dans le PATH (requis pour --mode local)")

# === PUSH PHASE ==============================================================

def clone_or_pull():
    if (CLONE / ".git").exists():
        cprint(f"==> Pull du repo existant : {CLONE}", "cyan")
        # fetch non-fatal : le clone temp peut être corrompu (nettoyage
        # périodique de %TEMP% par Windows, copie interrompue, .git tronqué).
        # Dans ce cas on supprime et on re-clone au lieu d'échouer sec.
        r = git("fetch", "origin", check=False, capture=True)
        if r.returncode == 0:
            git("reset", "--hard", "origin/main")
            git("clean", "-fd")
            return
        cprint(f"    Clone temp corrompu (fetch code {r.returncode}) — "
               f"suppression + re-clone.", "yellow")
        shutil.rmtree(CLONE, ignore_errors=True)
    cprint(f"==> Clone {REPO_URL} -> {CLONE}", "cyan")
    if CLONE.exists():
        shutil.rmtree(CLONE)
    # Clone initial : peut prendre 1-2 min (assets binaires, screenshots).
    run(["git", "clone", REPO_URL, str(CLONE)], timeout=300)

def remove_obsolete():
    cprint("\n==> Suppression des anciens chemins renommés", "cyan")
    for f in REMOVE:
        p = CLONE / f
        if p.exists():
            p.unlink()
            print(f"    SUPPR {f}")

def copy_files():
    cprint("\n==> Copie des fichiers source", "cyan")
    for src_name, dst_name in MAP.items():
        s = SRC / src_name
        d = CLONE / dst_name
        if s.exists():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            print(f"    OK  {src_name:<32} -> {dst_name}")
        else:
            cprint(f"    -- {src_name:<32} (introuvable, ignoré)", "yellow")

def mirror_folders():
    cprint("\n==> Copie des dossiers (mirror)", "cyan")
    # Exclure les artefacts Python : __pycache__/, .pyc, .pyo. Sans ça,
    # copytree copierait le bytecode au temp clone et seul le .gitignore
    # empêcherait le commit — fragile si la règle change.
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    def _is_artefact(p): return "__pycache__" in p.parts or p.suffix in (".pyc", ".pyo")
    for src_name, dst_name in FOLDERS.items():
        s = SRC / src_name
        d = CLONE / dst_name
        if s.exists():
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(s, d, ignore=ignore)
            count = sum(1 for p in s.rglob("*") if p.is_file() and not _is_artefact(p))
            print(f"    OK  {src_name:<32} -> {dst_name}  ({count} fichiers)")
        else:
            cprint(f"    -- {src_name:<32} (introuvable, ignoré)", "yellow")

def compute_diff():
    cprint("\n==> Modifications :", "cyan")
    git("add", "-A")
    status = git("status", "--short", capture=True).stdout.strip()
    if not status:
        cprint("    Aucun changement. Rien à pousser.", "yellow")
        return []
    for line in status.splitlines():
        print(f"    {line}")
    print()
    git("diff", "--cached", "--stat")
    changed = git("diff", "--cached", "--name-only", capture=True).stdout.strip().splitlines()
    return [c.strip() for c in changed if c.strip()]

def commit_and_push(message: str, new_tag: str = ""):
    cprint("\n==> Commit", "cyan")
    msg_file = CLONE / "COMMIT_MSG.txt"
    # UTF-8 SANS BOM par défaut sur Python.
    msg_file.write_text(message, encoding="utf-8")
    try:
        git("commit", "-F", str(msg_file))
    finally:
        try:
            msg_file.unlink()
        except FileNotFoundError:
            pass
    cprint("\n==> Push origin main", "cyan")
    git("push", "origin", "main")
    if new_tag:
        cprint(f"\n==> Tag {new_tag}", "cyan")
        git("tag", "-a", new_tag, "-m", message)
        git("push", "origin", new_tag)

# === RELEASE PHASE (patch d'une release existante) ===========================

def invoke_cloud(repo: str, target_tag: str):
    cprint(f"\n==> Déclenchement de update.yml sur {target_tag} (voie cloud)", "cyan")
    run(["gh", "workflow", "run", "update.yml", "--repo", repo, "-f", f"tag={target_tag}"])

    run_id = None
    for _ in range(6):
        time.sleep(5)
        runs = gh_json("run", "list", "--repo", repo, "--workflow", "update.yml",
                       "--limit", "1", "--json", "databaseId")
        if runs:
            run_id = runs[0]["databaseId"]
            break
    if not run_id:
        fail("run introuvable (voir l'onglet Actions du repo)")
    print(f"    Run : https://github.com/{repo}/actions/runs/{run_id}")

    cprint("==> Surveillance du run (~6-7 min)", "cyan")
    # update.yml dure typiquement 5-7 min ; on tolère jusqu'à 20 min pour rester
    # robuste si le runner GitHub est lent ce jour-là.
    res = run(["gh", "run", "watch", str(run_id), "--repo", repo,
               "--exit-status", "--interval", "20"], check=False, timeout=1200)
    if res.returncode != 0:
        fail(f"le run update.yml a échoué : gh run view {run_id} --repo {repo} --log-failed")

    cprint(f"\n==> OK. Bundles de {target_tag} patchés sans rebuild (cloud).", "green")
    print(f"    Release : https://github.com/{repo}/releases/tag/{target_tag}")

def invoke_local(target_tag: str):
    cprint(f"\n==> Patch local via update_app.py --release sur {target_tag} (voie locale)", "cyan")
    cprint("    Les ~1,5 Go d'assets transitent par TA connexion (upload vers GitHub).", "yellow")

    py = find_python()

    env = os.environ.copy()
    if "GH_TOKEN" not in env and "GITHUB_TOKEN" not in env:
        # Récupère le token de gh CLI si dispo, pour éviter à update_app.py
        # le détour par git credential (qui peut prompter).
        tok = run(["gh", "auth", "token"], capture=True, check=False)
        if tok.returncode == 0 and tok.stdout.strip():
            env["GH_TOKEN"] = tok.stdout.strip()
        else:
            cprint("    Note : aucun token dans l'env ni via gh ; update_app.py tentera git credential.", "yellow")

    update_app = SRC / "update_app.py"
    if not update_app.exists():
        fail(f"update_app.py introuvable à côté ({update_app})")

    # update_app.py --release : download 3 assets + patch + upload ~1,5 Go
    # depuis la connexion locale. Tolère jusqu'à 40 min pour les connexions lentes.
    run([py, str(update_app), "--release", "--tag", target_tag], env=env, timeout=2400)
    cprint(f"\n==> OK. Bundles de {target_tag} patchés sans rebuild (local).", "green")
    print(f"    Release : https://github.com/{REPO_DEFAULT}/releases/tag/{target_tag}")

def invoke_patch(mode: str, repo: str, target_tag: str):
    if mode == "local":
        invoke_local(target_tag)
    else:
        invoke_cloud(repo, target_tag)

# === MAIN ====================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="deploy.py",
        description=f"Déploiement unifié {PROJECT} — push + patch cloud/local + tag.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Voir le docstring en tête du fichier pour les exemples.",
    )
    parser.add_argument("-m", "--message", required=True,
                        help="message de commit")
    parser.add_argument("--mode", choices=["cloud", "local"], default="cloud",
                        help="voie de patch (défaut: cloud = update.yml sur GitHub)")
    parser.add_argument("--patch-tag", default="",
                        help="tag existant à patcher (défaut: dernière release)")
    parser.add_argument("--new-tag", default="",
                        help="nouveau tag git à créer → déclenche release.yml (rebuild complet)")
    parser.add_argument("--skip-push", action="store_true",
                        help="sauter push+détection, patcher directement la release")
    parser.add_argument("--push-only", action="store_true",
                        help="pousser les sources sur main SANS patcher les bundles "
                             "(itération debug/mesure : récup via git pull + run direct)")
    parser.add_argument("--dry-run", action="store_true",
                        help="afficher le diff sans commit ni push")
    parser.add_argument("--repo", default=REPO_DEFAULT,
                        help=f"repo GitHub cible (défaut: {REPO_DEFAULT})")
    args = parser.parse_args()

    # --- Validation ---
    if args.new_tag and args.skip_push:
        fail("--new-tag et --skip-push sont contradictoires")
    if args.new_tag and args.patch_tag:
        fail("--new-tag et --patch-tag sont contradictoires (rebuild vs patch existant)")
    if args.dry_run and args.skip_push:
        fail("--dry-run et --skip-push sont contradictoires")
    if args.push_only and args.skip_push:
        fail("--push-only et --skip-push sont contradictoires (pousser sans patcher vs patcher sans pousser)")
    if args.push_only and args.new_tag:
        fail("--push-only et --new-tag sont contradictoires (push seul vs rebuild via tag)")

    # --- Mode --skip-push : patch direct, pas de push ni de détection ---
    if args.skip_push:
        cprint(f"==> --skip-push : pas de push ni de détection, déclenchement direct ({args.mode}).", "yellow")
        tag = args.patch_tag or get_latest_tag(args.repo)
        invoke_patch(args.mode, args.repo, tag)
        return 0

    # --- Phase 1 : push + détection ---
    cprint("==> [1/2] Push des sources sur main + détection du diff", "cyan")
    clone_or_pull()
    remove_obsolete()
    copy_files()
    mirror_folders()
    changed = compute_diff()

    if not changed:
        return 0  # message déjà affiché par compute_diff

    if args.dry_run:
        cprint("\n==> --dry-run : pas de commit ni de push.", "yellow")
        return 0

    commit_and_push(args.message, args.new_tag)

    if args.new_tag:
        cprint(f"\n==> Nouveau tag {args.new_tag} poussé → release.yml va se déclencher (rebuild ~30 min sur 3 OS).", "green")
        print(f"    Suivi : https://github.com/{args.repo}/actions/workflows/release.yml")
        return 0

    cprint("\n==> Fichiers modifiés et poussés :", "cyan")
    for c in changed:
        print(f"    {c}")

    # --- Mode --push-only : sources poussées, on saute le patch des bundles ---
    if args.push_only:
        cprint("\n==> --push-only : sources sur main, patch des bundles sauté.", "green")
        cprint("    Récup : git pull && python lidar2map.py ...", "cyan")
        return 0

    # --- Phase 2 : catégorisation -> action ---
    rebuild = [c for c in changed if is_rebuild_file(c)]
    # providers/*.py comptent comme du code : update_app.py les injecte dans
    # les bundles lors du patch (extras _internal/providers/). Sans ce test,
    # un nouveau provider serait poussé sur main mais jamais livré aux bundles.
    code_changed = (APP_PY in changed
                    or any(c.startswith("providers/") for c in changed))

    if rebuild:
        cprint("\n==> [2/2] REBUILD requis (fichiers impactant le binaire) :", "yellow")
        for f in rebuild:
            cprint(f"      {f}", "yellow")
        print()
        print(f"    Le patch (cloud ou local) ne change que _internal/{APP_PY} :")
        print("    il ne peut PAS livrer ces changements. Il faut un vrai rebuild")
        print("    via release.yml, déclenché par un NOUVEAU tag (choix de version à toi) :")
        cur = get_latest_tag(args.repo)
        print()
        cprint(f"      python deploy.py -m \"{args.message}\" --new-tag <vX.Y.Z>    # dernière release : {cur}", "cyan")
        print()
        cprint("    Sources déjà poussées ; il ne reste qu'à tagger pour lancer release.yml.", "yellow")
        return 0

    if code_changed:
        tag = args.patch_tag or get_latest_tag(args.repo)
        cprint(f"\n==> [2/2] {APP_PY} modifié → patch via --mode {args.mode} sur {tag}", "cyan")
        cprint(f"    Avertissement : si tu as touché au BLOC LAUNCHER ou aux DEPS dans", "yellow")
        cprint(f"    {APP_PY}, le patch ne suffit pas → rebuild via release.yml.", "yellow")
        invoke_patch(args.mode, args.repo, tag)
        return 0

    cprint("\n==> [2/2] Docs / meta seulement → aucun binaire à patcher, push suffit. Terminé.", "green")
    return 0

if __name__ == "__main__":
    sys.exit(main())
