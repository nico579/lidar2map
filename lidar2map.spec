# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller pour lidar2map — Windows, onedir, JRE+osmosis+mapwriter bundlés.

Usage :
    C:\\Users\\Nico\\.lidar2map\\venv\\Scripts\\pyinstaller.exe lidar2map.spec --clean --noconfirm

Résultat :
    dist/lidar2map/lidar2map.exe
    dist/lidar2map/_internal/
        jre/jdk-21.0.10+7-jre/       JRE Temurin 21 (~144 Mo)
        osmosis/osmosis-0.49.2/      osmosis + mapwriter en lib/ (~22 Mo)
        tagmapping-min.xml
        ... (Python + wheels natives)

Le plugin mapsforge-map-writer-0.25.0 est copié dans osmosis/lib/ et le
fichier osmosis.bat bundlé est patché pour l'inclure dans son CLASSPATH —
osmosis le découvre alors via Java SPI sans toucher à %USERPROFILE%\\.openstreetmap.
"""

import os, shutil
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
)

ONEFILE = False
CONSOLE = True
NAME    = "lidar2map"

SRC          = Path(SPECPATH)
STAGING      = SRC / "build" / "staging"
JRE_SRC      = SRC / "bin" / "jre" / "jdk-21.0.10+7-jre"
OSMOSIS_SRC  = SRC / "bin" / "osmosis" / "osmosis-0.49.2"
MAPWRITER_JAR_SRC = (Path.home() / ".openstreetmap" / "osmosis" / "plugins"
                    / "mapsforge-map-writer-0.25.0-jar-with-dependencies.jar")

# ── Préparation de l'osmosis staging (osmosis + mapwriter + bat patché) ─────
def _prepare_osmosis_staging():
    """Copie osmosis dans build/staging/osmosis/, injecte mapwriter jar dans
    lib/, patche osmosis.bat pour ajouter ce jar à son CLASSPATH."""
    staging_osmosis = STAGING / "osmosis" / "osmosis-0.49.2"
    if staging_osmosis.exists():
        shutil.rmtree(staging_osmosis.parent)
    print(f"  [spec] Staging osmosis -> {staging_osmosis}")
    shutil.copytree(OSMOSIS_SRC, staging_osmosis)

    # Injecter le jar mapwriter dans lib/
    jar_dst = staging_osmosis / "lib" / MAPWRITER_JAR_SRC.name
    shutil.copy2(MAPWRITER_JAR_SRC, jar_dst)
    print(f"  [spec] Plugin mapwriter copié dans {jar_dst.relative_to(staging_osmosis)}")

    # Patcher osmosis.bat : ajouter le jar mapwriter au CLASSPATH
    bat_path = staging_osmosis / "bin" / "osmosis.bat"
    bat_txt  = bat_path.read_text(encoding="utf-8")
    inject   = f";%APP_HOME%\\lib\\{MAPWRITER_JAR_SRC.name}"
    marker   = r"%APP_HOME%\lib\spring-jcl-5.3.30.jar"
    if inject not in bat_txt:
        if marker not in bat_txt:
            raise RuntimeError(
                f"Marker introuvable dans osmosis.bat : {marker!r}. "
                "Adapter le spec à la version osmosis."
            )
        bat_txt = bat_txt.replace(marker, marker + inject)
        bat_path.write_text(bat_txt, encoding="utf-8")
        print(f"  [spec] osmosis.bat patché (CLASSPATH += {MAPWRITER_JAR_SRC.name})")

    # Patcher osmosis (shell script Linux/Mac) idem — au cas où on cross-bundle
    sh_path = staging_osmosis / "bin" / "osmosis"
    if sh_path.exists():
        sh_txt = sh_path.read_text(encoding="utf-8")
        sh_marker = "spring-jcl-5.3.30.jar"
        sh_inject = f":$APP_HOME/lib/{MAPWRITER_JAR_SRC.name}"
        # Le shell script a un format différent (build CLASSPATH via boucle).
        # On préfère ajouter une ligne après la construction du CLASSPATH.
        # Mais comme osmosis.sh utilise un glob lib/*.jar (à vérifier), le jar
        # est probablement déjà inclus automatiquement. Skip pour Windows-only.

    return staging_osmosis.parent  # -> build/staging/osmosis


def _add_tree(src_dir, dest_dir):
    """Renvoie une liste de (src_file, dest_subdir) pour PyInstaller.datas."""
    src_dir = Path(src_dir).resolve()
    out = []
    for p in src_dir.rglob("*"):
        if p.is_file():
            rel_parent = p.parent.relative_to(src_dir)
            out.append((str(p), str(Path(dest_dir) / rel_parent)))
    return out


# Stagger osmosis (avec mapwriter inclus)
staging_osmosis_root = _prepare_osmosis_staging()

datas         = []
binaries      = []
hiddenimports = []

# ── Ressources statiques du projet ───────────────────────────────────────────
datas += [("tagmapping-min.xml", ".")]

# ── JRE Temurin 21 (~144 Mo) ─────────────────────────────────────────────────
datas += _add_tree(JRE_SRC, "jre/jdk-21.0.10+7-jre")

# ── osmosis + mapwriter (~22 Mo) ─────────────────────────────────────────────
datas += _add_tree(staging_osmosis_root, "osmosis")

# ── pyproj ───────────────────────────────────────────────────────────────────
datas         += collect_data_files("pyproj")
hiddenimports += collect_submodules("pyproj")

# ── rasterio ─────────────────────────────────────────────────────────────────
datas         += collect_data_files("rasterio")
binaries      += collect_dynamic_libs("rasterio")
hiddenimports += collect_submodules("rasterio")
hiddenimports += [
    "rasterio._features", "rasterio._io", "rasterio._warp",
    "rasterio.sample", "rasterio.vrt", "rasterio.windows",
    "rasterio.warp", "rasterio.transform", "rasterio.enums",
]

# ── fiona ────────────────────────────────────────────────────────────────────
datas         += collect_data_files("fiona")
binaries      += collect_dynamic_libs("fiona")
hiddenimports += collect_submodules("fiona")
hiddenimports += ["fiona.schema", "fiona.transform"]

# ── shapely ──────────────────────────────────────────────────────────────────
binaries      += collect_dynamic_libs("shapely")
hiddenimports += ["shapely.geometry", "shapely.strtree", "shapely.ops"]

# ── scipy ────────────────────────────────────────────────────────────────────
hiddenimports += collect_submodules("scipy")
binaries      += collect_dynamic_libs("scipy")

# ── numba + llvmlite ─────────────────────────────────────────────────────────
try:
    hiddenimports += collect_submodules("numba")
    binaries      += collect_dynamic_libs("numba")
    datas         += collect_data_files("numba")
    binaries      += collect_dynamic_libs("llvmlite")
    datas         += collect_data_files("llvmlite")
except Exception:
    pass

# ── pywebview ────────────────────────────────────────────────────────────────
datas         += collect_data_files("webview")
hiddenimports += collect_submodules("webview")
hiddenimports += [
    "webview.platforms.winforms",
    "clr_loader",
    "clr_loader.netfx",
    "pythonnet",
]

# ── PIL ──────────────────────────────────────────────────────────────────────
hiddenimports += [
    "PIL.Image", "PIL.PngImagePlugin", "PIL.JpegImagePlugin",
    "PIL.TiffImagePlugin", "PIL.WebPImagePlugin",
]

# ── osmium ───────────────────────────────────────────────────────────────────
try:
    hiddenimports += collect_submodules("osmium")
    binaries      += collect_dynamic_libs("osmium")
except Exception:
    pass

# ── mapbox_vector_tile ───────────────────────────────────────────────────────
try:
    hiddenimports += collect_submodules("mapbox_vector_tile")
    hiddenimports += collect_submodules("google.protobuf")
except Exception:
    pass

# ── ijson ────────────────────────────────────────────────────────────────────
try:
    hiddenimports += collect_submodules("ijson")
except Exception:
    pass

# ── requests / certifi ───────────────────────────────────────────────────────
datas         += collect_data_files("certifi")
hiddenimports += ["urllib3", "charset_normalizer", "idna", "certifi"]


a = Analysis(
    ["lidar2map.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib",
        "PyQt5", "PyQt6", "PySide2", "PySide6",
        "test", "unittest", "pydoc_data",
        "IPython", "jupyter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name=NAME, debug=False,
        bootloader_ignore_signals=False, strip=False, upx=False,
        upx_exclude=[], runtime_tmpdir=None, console=CONSOLE,
        disable_windowed_traceback=False, argv_emulation=False,
        target_arch=None, codesign_identity=None, entitlements_file=None,
        icon=None,
    )
else:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True, name=NAME, debug=False,
        bootloader_ignore_signals=False, strip=False, upx=False,
        console=CONSOLE, disable_windowed_traceback=False,
        argv_emulation=False, target_arch=None,
        codesign_identity=None, entitlements_file=None, icon=None,
    )
    coll = COLLECT(
        exe, a.binaries, a.datas,
        strip=False, upx=False, upx_exclude=[], name=NAME,
    )
