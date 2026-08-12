"""Tests sans réseau du contrat deploy.py ↔ update_app.py ↔ specs."""

import ast
import fnmatch
import importlib.util
import io
import re
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def workflow_path(name):
    """Résout un workflow dans le workspace ou dans le clone déployé."""
    candidates = (
        ROOT / f"{name}_github.yml",
        ROOT / ".github" / "workflows" / f"{name}.yml",
    )
    matches = [path for path in candidates if path.is_file()]
    assert len(matches) == 1, \
        f"workflow {name!r} introuvable ou ambigu : {candidates}"
    return matches[0]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


deploy = load("deploy_contract", ROOT / "deploy.py")
update = load("update_contract", ROOT / "update_app.py")

# Modules internes importés par le monolithe : la liste est DÉRIVÉE de l'AST de
# lidar2map.py, pas recopiée à la main. Un module extrait lors d'une phase de
# refonte et oublié dans deploy.MAP produirait un bundle où lidar2map.py importe
# un fichier absent ; oublié dans is_rebuild_file, il serait livré par simple
# patch de _internal/lidar2map.py (que update_app.py est seul à réécrire) et le
# bundle casserait de la même façon. Le contrat est donc vérifié par
# construction, et une phase 7/8 future n'a rien à ajouter ici.
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

# Les filtres `paths:` de la CI : un module non couvert ne déclencherait aucun
# job sur une modification qui ne touche que lui. Push et pull request sont
# contrôlés séparément pour empêcher qu'un motif présent dans un seul bloc ne
# masque son oubli dans l'autre.
_ci_text = workflow_path("ci").read_text(encoding="utf-8")
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
    assert deploy.MAP.get(_mod) == _mod, f"{_mod} absent de deploy.MAP"
    assert deploy.is_rebuild_file(_mod), f"{_mod} n'est pas rebuild-gated"
    for _event, _patterns in _ci_patterns_by_event.items():
        assert any(fnmatch.fnmatch(_mod, pat) for pat in _patterns), \
            f"{_mod} n'est pas couvert par paths: pour {_event}"

assert deploy.is_rebuild_file("_split_future.py")
assert not deploy.is_rebuild_file("split_future.py")

expected_sources = {
    "tools/__init__.py",
    "tools/rlidar2map_CLI.py",
    "tools/rlidar2map_GUI.py",
    "tools/rlidar2map_GUI_vm.sh",
}

assert deploy.PATCHABLE_TOOL_FILES == expected_sources
assert set(update.PATCHABLE_TOOL_TARGETS) == expected_sources
assert update.PATCHABLE_TOOL_TARGETS["tools/rlidar2map_GUI_vm.sh"] \
       == "_internal/rlidar2map_GUI_vm.sh"

# La collecte doit prendre exactement les bytes des contrôleurs présents.
extras = update._collect_patch_extras()
for source_rel, target in update.PATCHABLE_TOOL_TARGETS.items():
    assert target in extras, target
    assert extras[target] == (ROOT / source_rel).read_bytes(), source_rel

# Les deux specs applicatives doivent embarquer le même contrat de fichiers.
for spec_name in ("lidar2map_win.spec", "lidar2map_mac.spec"):
    text = (ROOT / spec_name).read_text(encoding="utf-8")
    for filename in ("__init__.py", "rlidar2map_CLI.py", "rlidar2map_GUI.py",
                     "rlidar2map_GUI_vm.sh"):
        assert filename in text, f"{filename} absent de {spec_name}"

# ZIP interne synthétique : remplacement du cœur et d'un outil existant,
# ajout d'un outil absent, puis détection exacte de l'état à jour.
old = io.BytesIO()
with zipfile.ZipFile(old, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr(update.TARGET, b"old core")
    archive.writestr("_internal/tools/rlidar2map_CLI.py", b"old remote")
    archive.writestr("_internal/tools/rlidar2map_GUI_vm.sh", b"stale shell")
    archive.writestr("_internal/providers/removed_provider.py", b"stale provider")
    archive.writestr("_internal/gui/removed.js", b"stale gui")
    archive.writestr("_internal/untouched.txt", b"keep")

new_script = b"print('new core')\n"
small_extras = {
    "_internal/tools/rlidar2map_CLI.py": b"new remote",
    "_internal/tools/rlidar2map_GUI.py": b"new gui remote",
}
patched = update._patch_inner_bundle(old.getvalue(), new_script, small_extras)
with zipfile.ZipFile(io.BytesIO(patched), "r") as archive:
    assert archive.read(update.TARGET) == new_script
    assert archive.read("_internal/tools/rlidar2map_CLI.py") == b"new remote"
    assert archive.read("_internal/tools/rlidar2map_GUI.py") == b"new gui remote"
    assert archive.read("_internal/untouched.txt") == b"keep"
    assert "_internal/tools/rlidar2map_GUI_vm.sh" not in archive.namelist()
    assert "_internal/providers/removed_provider.py" not in archive.namelist()
    assert "_internal/gui/removed.js" not in archive.namelist()

with tempfile.TemporaryDirectory() as tmp:
    bundle = Path(tmp) / "lidar2map_bundle.zip"
    bundle.write_bytes(patched)
    assert update._inner_bundle_is_current(bundle, new_script, small_extras)
    assert not update._inner_bundle_is_current(
        bundle, new_script, {**small_extras,
                             "_internal/tools/rlidar2map_CLI.py": b"newer"})

print("TOUS OK — contrat de patch des outils distants")
