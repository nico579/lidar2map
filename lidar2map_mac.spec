# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller pour lidar2map — macOS ARM64, onedir, JRE+osmosis+mapwriter bundlés.

Usage :
    ~/.lidar2map/venv/bin/pyinstaller lidar2map_mac.spec --clean --noconfirm

Résultat :
    dist_onedir/lidar2map/lidar2map          (exécutable interne)
    dist_onedir/lidar2map/_internal/
        jre/jdk-21.0.10+7-jre/
        osmosis/osmosis-0.49.2/
        tagmapping-min.xml
        PyQt6/
        ...

Ce build onedir est ensuite zippé et embarqué dans le launcher .app
par lidar2map_mac_build.sh (étapes 2 et 3).
"""

import os, shutil
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
    collect_all,
)

ONEFILE = False
CONSOLE = False
NAME    = "lidar2map"

SRC               = Path(SPECPATH)
STAGING           = SRC / "build" / "staging"
LIDAR2MAP_HOME    = Path.home() / ".lidar2map"

# Osmosis et JRE : d'abord dans bin/ local (comme Windows),
# sinon dans ~/.lidar2map/ où le script les télécharge automatiquement.
def _find_dir(local_rel, home_glob, label):
    local_candidates = sorted(SRC.glob(local_rel))
    if local_candidates:
        return local_candidates[-1]
    home_candidates = sorted(LIDAR2MAP_HOME.glob(home_glob))
    if home_candidates:
        print(f"  [spec] {label} trouve : {home_candidates[-1]}")
        return home_candidates[-1]
    print(f"  [WARN] {label} absent, sera telecharge au runtime")
    return None

JRE_SRC     = _find_dir("bin/jre/jdk-*",      "jre/jdk-*",      "JRE")
OSMOSIS_SRC = _find_dir("bin/osmosis/osmosis-*","osmosis/osmosis-*","osmosis")

MAPWRITER_JAR_SRC = (Path.home() / ".openstreetmap" / "osmosis" / "plugins"
                     / "mapsforge-map-writer-0.25.0-jar-with-dependencies.jar")


def _prepare_osmosis_staging():
    if not OSMOSIS_SRC or not OSMOSIS_SRC.exists():
        print(f"  [WARN] osmosis absent, sera telecharge au runtime par le script")
        return None
    staging_osmosis = STAGING / "osmosis" / OSMOSIS_SRC.name
    if staging_osmosis.exists():
        shutil.rmtree(staging_osmosis.parent)
    print(f"  [spec] Staging osmosis -> {staging_osmosis}")
    shutil.copytree(OSMOSIS_SRC, staging_osmosis)
    if MAPWRITER_JAR_SRC.exists():
        jar_dst = staging_osmosis / "lib" / MAPWRITER_JAR_SRC.name
        shutil.copy2(MAPWRITER_JAR_SRC, jar_dst)
        print(f"  [spec] mapwriter -> lib/{MAPWRITER_JAR_SRC.name}")
        # osmosis shell script Gradle utilise un CLASSPATH EXPLICITE (comme le
        # .bat) — pas un glob. Sans patch, le plugin mapwriter reste invisible
        # et la generation .map echoue avec "Task type mapfile-writer doesn't exist".
        sh_path = staging_osmosis / "bin" / "osmosis"
        if sh_path.exists():
            sh_txt = sh_path.read_text(encoding="utf-8")
            inject = f":$APP_HOME/lib/{MAPWRITER_JAR_SRC.name}"
            marker = "$APP_HOME/lib/spring-jcl-5.3.30.jar"
            if inject not in sh_txt:
                if marker not in sh_txt:
                    print(f"  [WARN] marker '{marker}' introuvable dans osmosis (Unix). "
                          "Plugin mapwriter ne sera pas charge.")
                else:
                    sh_txt = sh_txt.replace(marker, marker + inject)
                    sh_path.write_text(sh_txt, encoding="utf-8")
                    print(f"  [spec] osmosis (Unix) patche")
    else:
        print(f"  [WARN] mapwriter jar absent : {MAPWRITER_JAR_SRC}")
    sh = staging_osmosis / "bin" / "osmosis"
    if sh.exists():
        sh.chmod(sh.stat().st_mode | 0o111)
    return staging_osmosis.parent


def _add_tree(src_dir, dest_dir):
    src_dir = Path(src_dir).resolve()
    out = []
    if not src_dir.exists():
        print(f"  [WARN] repertoire absent : {src_dir}")
        return out
    for p in src_dir.rglob("*"):
        if p.is_file():
            rel_parent = p.parent.relative_to(src_dir)
            out.append((str(p), str(Path(dest_dir) / rel_parent)))
    return out


staging_osmosis_root = _prepare_osmosis_staging()

datas         = []
binaries      = []
hiddenimports = []

if (SRC / "tagmapping-min.xml").exists():
    datas += [("tagmapping-min.xml", ".")]

# Providers multi-pays (v1.2+) : tous les modules providers/*.py sont
# embarques comme data + declares hiddenimports pour que importlib les trouve
# en mode frozen (PyInstaller ne suit pas les imports dynamiques).
_providers_dir = SRC / "providers"
if _providers_dir.exists():
    for _pf in sorted(_providers_dir.glob("*.py")):
        datas += [(str(_pf), "providers")]
        if not _pf.stem.startswith("_"):
            hiddenimports.append(f"providers.{_pf.stem}")
    hiddenimports.append("providers")

if JRE_SRC and JRE_SRC.exists():
    datas += _add_tree(JRE_SRC, f"jre/{JRE_SRC.name}")
else:
    print("  [WARN] JRE absent, sera telecharge au runtime par le script")

if staging_osmosis_root:
    datas += _add_tree(staging_osmosis_root, "osmosis")

# PyQt6 + pywebview + qtpy (GUI Qt)
for lib in ("PyQt6", "pywebview", "qtpy"):
    try:
        d, b, h = collect_all(lib)
        datas += d; binaries += b; hiddenimports += h
    except Exception as e:
        print(f"  [WARN] collect_all({lib!r}) : {e}")

hiddenimports += [
    "webview.platforms.qt",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebChannel",
]

# pyproj
datas         += collect_data_files("pyproj")
hiddenimports += collect_submodules("pyproj")

# rasterio
datas         += collect_data_files("rasterio")
binaries      += collect_dynamic_libs("rasterio")
hiddenimports += collect_submodules("rasterio")
hiddenimports += [
    "rasterio._features", "rasterio._io", "rasterio._warp",
    "rasterio.sample", "rasterio.vrt", "rasterio.windows",
    "rasterio.warp", "rasterio.transform", "rasterio.enums",
    "rasterio._shim", "rasterio.control", "rasterio.crs",
]

# fiona
datas         += collect_data_files("fiona")
binaries      += collect_dynamic_libs("fiona")
hiddenimports += collect_submodules("fiona")
hiddenimports += ["fiona.schema", "fiona.transform"]

# shapely
binaries      += collect_dynamic_libs("shapely")
hiddenimports += ["shapely.geometry", "shapely.strtree", "shapely.ops"]

# scipy
hiddenimports += collect_submodules("scipy")
binaries      += collect_dynamic_libs("scipy")

# numba + llvmlite
try:
    hiddenimports += collect_submodules("numba")
    binaries      += collect_dynamic_libs("numba")
    datas         += collect_data_files("numba")
    binaries      += collect_dynamic_libs("llvmlite")
    datas         += collect_data_files("llvmlite")
except Exception:
    pass

# PIL
hiddenimports += [
    "PIL.Image", "PIL.PngImagePlugin", "PIL.JpegImagePlugin",
    "PIL.TiffImagePlugin", "PIL.WebPImagePlugin",
]

# osmium — collect_all (et pas juste submodules + dynamic_libs) :
# osmium 4.x livre des .py purs essentiels (__init__.py, helper.py, etc.)
# que collect_submodules ne capture pas → ImportError dans le bundle.
try:
    d, b, h = collect_all("osmium")
    datas += d; binaries += b; hiddenimports += h
except Exception:
    pass

# osmium.libs/ : protection défensive (no-op sur macOS car delocate met
# les dylibs dans osmium/.dylibs/ INSIDE le package, déjà attrapé par
# collect_all). Présent uniquement si une future wheel macOS adopte la
# convention auditwheel-style (sibling .libs/ avec libs hashées).
try:
    import osmium as _osmium_for_libs
    from pathlib import Path as _Path_libs
    _libs_dir = _Path_libs(_osmium_for_libs.__file__).parent.parent / "osmium.libs"
    if _libs_dir.exists():
        for _f in _libs_dir.iterdir():
            if _f.is_file():
                binaries.append((str(_f), "osmium.libs"))
        print(f"  [spec] osmium.libs/ ({len(list(_libs_dir.iterdir()))} fichiers) forces")
except Exception as _e:
    print(f"  [WARN] copie osmium.libs/ echouee : {_e}")

# laspy + lazrs (lecture LAS/LAZ — lazy dans le script)
# lazrs = backend de décompression LAZ (extension Rust) requis par laspy pour
# lire les .laz des providers LiDAR (cz, se, es…). Sans lui, le bundle lève
# "No LazBackend selected, cannot decompress data". collect_all embarque le
# binaire compilé.
for _laz_pkg in ("laspy", "lazrs"):
    try:
        d, b, h = collect_all(_laz_pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

# py7zr (BD TOPO bulk — lazy dans le script)
try:
    d, b, h = collect_all("py7zr")
    datas += d; binaries += b; hiddenimports += h
except Exception:
    pass

# mapbox_vector_tile (export MVT — lazy dans le script)
try:
    d, b, h = collect_all("mapbox_vector_tile")
    datas += d; binaries += b; hiddenimports += h
    hiddenimports += collect_submodules("google.protobuf")
except Exception:
    pass

# ijson
try:
    hiddenimports += collect_submodules("ijson")
except Exception:
    pass

# certifi
datas         += collect_data_files("certifi")
hiddenimports += ["certifi"]

# Runtime hook
_hook = SRC / "hook_mac_runtime.py"
_hook.write_text("""\
import os, sys
_base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
os.environ.setdefault('PYWEBVIEW_GUI', 'qt')
_candidates = [
    os.path.join(_base, 'PyQt6', 'Qt6', 'lib', 'QtWebEngineCore.framework',
                 'Helpers', 'QtWebEngineProcess.app', 'Contents', 'MacOS',
                 'QtWebEngineProcess'),
    os.path.join(_base, 'QtWebEngineProcess'),
    os.path.join(_base, 'PyQt6', 'QtWebEngineProcess'),
]
for _p in _candidates:
    if os.path.isfile(_p):
        os.environ.setdefault('QTWEBENGINEPROCESS_PATH', _p)
        break
_res = os.path.join(_base, 'PyQt6', 'Qt6', 'Resources')
if os.path.isdir(_res):
    os.environ.setdefault('QTWEBENGINE_RESOURCES_PATH', _res)
try:
    import certifi
    os.environ.setdefault('SSL_CERT_FILE', certifi.where())
    os.environ.setdefault('REQUESTS_CA_BUNDLE', certifi.where())
except Exception:
    pass
""")

_excludes_mac = [
    "tkinter", "matplotlib",
    "PyQt5", "PySide2", "PySide6",
    "webview.platforms.cocoa",
    "webview.platforms.gtk",
    "clr_loader", "pythonnet",
    "test", "pydoc_data",
    # "unittest" retiré : scipy.ndimage l'importe en interne → LRM/RRIM cassés
    "IPython", "jupyter",
]

# ── 2 passes PyInstaller ─────────────────────────────────────────────────────
# Passe 1 : analyse de lidar2map.py pour détecter tous ses imports
a_detect = Analysis(
    ["lidar2map.py"],
    pathex=[], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=_excludes_mac, noarchive=False, optimize=0,
)

# Passe 2 : build réel depuis _loader.py (entrées 2-tuples, pas de TOC)
a = Analysis(
    ["_loader.py"],
    pathex=[], binaries=binaries,
    datas=datas + [("lidar2map.py", ".")],
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[str(_hook)], excludes=_excludes_mac, noarchive=False, optimize=0,
)

# Fusion des TOC de sortie après les deux analyses
a.binaries += a_detect.binaries
a.datas    += a_detect.datas
a.pure     += [e for e in a_detect.pure if not e[0].startswith("lidar2map")]

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, upx_exclude=[], name=NAME,
)
