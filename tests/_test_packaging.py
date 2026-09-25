"""Tests sans réseau du contrat de livraison : modules suivis et couverts par
la CI, outils embarqués par les specs, préparation de VM, console Windows.

Ancien _test_patch_delivery.py : le patch des bundles sans reconstruction
(update_app.py, update.yml) a été retiré (décision D2 de
docs/preconisations_evolution.md) ; ne restent que les contrats qui valent
pour une release reconstruite."""

import ast
import fnmatch
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# Modules internes importés par le monolithe : la liste est DÉRIVÉE de l'AST de
# lidar2map.py, pas recopiée à la main, donc une phase de refonte future n'a
# rien à ajouter ici.
_source_l2m = (ROOT / "lidar2map.py").read_text(encoding="utf-8")
_modules_locaux = set()
for _node in ast.walk(ast.parse(_source_l2m)):
    if isinstance(_node, ast.Import):
        _noms = [alias.name for alias in _node.names]
    elif isinstance(_node, ast.ImportFrom):
        _noms = [_node.module] if (_node.level == 0 and _node.module) else []
    else:
        continue
    for _nom in _noms:
        _racine = _nom.split(".")[0]
        if (ROOT / f"{_racine}.py").exists() and _racine != "lidar2map":
            _modules_locaux.add(f"{_racine}.py")

assert "_split_manifest.py" in _modules_locaux      # garde-fou de la détection
assert "_raster_formats.py" in _modules_locaux
assert "_mbtiles_wmts.py" in _modules_locaux

# Un module importé mais jamais ajouté à git manquerait au clone de la CI et au
# bundle : deploy.py ne publie que les fichiers déjà suivis. Contrôle sauté
# hors dépôt git (archive des sources).
_suivis = subprocess.run(["git", "ls-files", "--", "*.py"], cwd=ROOT,
                         capture_output=True, text=True)
if _suivis.returncode == 0:
    _fichiers_suivis = set(_suivis.stdout.split())
    for _mod in sorted(_modules_locaux):
        assert _mod in _fichiers_suivis, f"{_mod} importé mais pas suivi par git"

# Les filtres `paths:` de la CI : un module non couvert ne déclencherait aucun
# job sur une modification qui ne touche que lui. Push et pull request sont
# contrôlés séparément pour empêcher qu'un motif présent dans un seul bloc ne
# masque son oubli dans l'autre.
_ci_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
_ci_patterns_by_event = {}
for _event in ("push", "pull_request"):
    _match = re.search(
        rf"(?ms)^  {_event}:\s*\n    paths:\s*\n"
        r"(?P<body>(?:      - '[^']+'[ \t]*(?:\r?\n|$))+)",
        _ci_text,
    )
    assert _match, f"bloc paths CI absent pour {_event}"
    _ci_patterns_by_event[_event] = re.findall(
        r"^[ \t]+- '([^']+)'[ \t]*$",
        _match.group("body"),
        flags=re.MULTILINE,
    )

for _mod in sorted(_modules_locaux):
    for _event, _patterns in _ci_patterns_by_event.items():
        assert any(fnmatch.fnmatch(_mod, pat) for pat in _patterns), \
            f"{_mod} n'est pas couvert par paths: pour {_event}"

# Les deux specs applicatives embarquent les contrôleurs distants
# (--remote-cli / --remote-gui).
for spec_name in ("lidar2map_win.spec", "lidar2map_mac.spec"):
    text = (ROOT / spec_name).read_text(encoding="utf-8")
    for filename in ("__init__.py", "rlidar2map_CLI.py", "rlidar2map_GUI.py",
                     "rlidar2map_GUI_vm.sh"):
        assert filename in text, f"{filename} absent de {spec_name}"

# Préparation de VM --remote-gui : depuis la 1.49.0 le GUI est une page web,
# plus aucune bibliothèque Qt. La VM doit donc fournir un navigateur, en deb
# du dépôt Mozilla (le paquet firefox d'Ubuntu n'installe que le snap, qui ne
# démarre pas dans la session xrdp), avec vérification de l'empreinte de clé.
vm_script = (ROOT / "tools" / "rlidar2map_GUI_vm.sh").read_text(encoding="utf-8")
for reliquat_qt in ("libxcb-cursor0", "QT_COMPAT_DIR", 'wmctrl -r "lidar2map v"',
                    "StartupWMClass=lidar2map"):
    assert reliquat_qt not in vm_script, f"reliquat Qt/pywebview : {reliquat_qt}"
assert "https://packages.mozilla.org/apt mozilla main" in vm_script
assert 'MOZILLA_KEY_FPR="35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3"' in vm_script
assert "Pin: origin packages.mozilla.org" in vm_script
assert 'run_apt "Firefox" install -y firefox' in vm_script
assert "export BROWSER=firefox" in vm_script
# Pas sous Windows : shutil.which peut y trouver le bash.exe de WSL (absent
# ou non configuré sur un runner) et le checkout peut convertir en CRLF.
_bash = shutil.which("bash") if sys.platform != "win32" else None
if _bash:
    _syntaxe = subprocess.run([_bash, "-n", str(ROOT / "tools" / "rlidar2map_GUI_vm.sh")],
                              capture_output=True, text=True)
    assert _syntaxe.returncode == 0, _syntaxe.stderr

# Windows : pas de console visible au double-clic, CLI inchangée depuis un
# terminal (hide_console ne masque que la console dont le programme est le
# propriétaire). L'exe interne garde une console, même masquée : l'arrêt
# propre des traitements passe par CTRL_BREAK_EVENT.
lanceur_spec = (ROOT / "lidar2map_win_launcher.spec").read_text(encoding="utf-8")
interne_spec = (ROOT / "lidar2map_win.spec").read_text(encoding="utf-8")
assert 'hide_console="hide-early" if sys.platform == "win32" else None' in lanceur_spec
assert "console=True" in lanceur_spec
assert 'HIDE_CONSOLE = "hide-early" if sys.platform == "win32" else None' in interne_spec
assert interne_spec.count("hide_console=HIDE_CONSOLE") == 2
assert "CONSOLE = True" in interne_spec
# Launcher : console réaffichée pendant une (ré)extraction si elle était
# masquée, puis remasquée ; jamais masquée si elle était visible (terminal).
bloc_lanceur = (ROOT / "lidar2map.py").read_text(encoding="utf-8")
bloc_lanceur = bloc_lanceur[:bloc_lanceur.index("# Pas de bundle.zip → exe onedir lancé directement")]
assert "IsWindowVisible" in bloc_lanceur and "ShowWindow" in bloc_lanceur
assert '_console_a_remasquer = (_need_extract\n                                    and _console_windows("masquee"))' in bloc_lanceur

print("TOUS OK — contrat de livraison")
