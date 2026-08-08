"""Tests sans réseau du contrat deploy.py ↔ update_app.py ↔ specs."""

import importlib.util
import io
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


deploy = load("deploy_contract", ROOT / "deploy.py")
update = load("update_contract", ROOT / "update_app.py")

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
