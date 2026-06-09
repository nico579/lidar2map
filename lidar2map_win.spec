# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller pour lidar2map — Windows, onedir, JRE+osmosis+mapwriter bundlés.

Usage :
    %USERPROFILE%\.lidar2map\venv\Scripts\pyinstaller.exe lidar2map_win.spec --clean --noconfirm

Résultat :
    dist_onedir/lidar2map/lidar2map.exe
    dist_onedir/lidar2map/_internal/
        jre/jdk-21.0.10+7-jre/       JRE Temurin 21
        osmosis/osmosis-0.49.2/       osmosis + mapwriter en lib/
        tagmapping-min.xml
        ...

Le plugin mapsforge-map-writer est copié dans osmosis/lib/ et osmosis.bat
est patché pour l'inclure dans son CLASSPATH.
"""

import os, shutil, sys
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
    collect_all,           # ajout vs version originale
)

# Cette spec sert AUSSI pour Linux (cf. lidar2map_linux_build.sh).
# Windows  : pywebview -> WinForms / Edge WebView2 (pas de Qt)
# Linux    : pywebview -> PyQt6 + WebEngine (seul backend pip viable)
IS_LINUX = sys.platform.startswith("linux")

ONEFILE = False
CONSOLE = True
NAME    = "lidar2map"

SRC               = Path(SPECPATH)
STAGING           = SRC / "build" / "staging"
LIDAR2MAP_HOME    = Path.home() / ".lidar2map"
MAPWRITER_JAR_SRC = (Path.home() / ".openstreetmap" / "osmosis" / "plugins"
                     / "mapsforge-map-writer-0.25.0-jar-with-dependencies.jar")


def _find_dir(local_rel, home_glob, label):
    """Cherche d'abord dans bin/ local, puis dans ~/.lidar2map/."""
    local_candidates = sorted(SRC.glob(local_rel))
    if local_candidates:
        return local_candidates[-1]
    home_candidates = sorted(LIDAR2MAP_HOME.glob(home_glob))
    if home_candidates:
        print(f"  [spec] {label} trouvé : {home_candidates[-1]}")
        return home_candidates[-1]
    print(f"  [WARN] {label} absent, sera téléchargé au runtime")
    return None

JRE_SRC     = _find_dir("bin/jre/jdk-*",       "jre/jdk-*",       "JRE")
OSMOSIS_SRC = _find_dir("bin/osmosis/osmosis-*","osmosis/osmosis-*","osmosis")


def _prepare_osmosis_staging():
    if not OSMOSIS_SRC or not OSMOSIS_SRC.exists():
        print("  [WARN] osmosis absent — sera téléchargé au runtime")
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

        # osmosis utilise un CLASSPATH explicite (généré par Gradle) — il faut
        # injecter le jar mapwriter dans la liste, sinon Java ne le charge pas
        # et le plugin reste invisible ("Task type mapfile-writer doesn't exist").
        # On patche les DEUX launchers (Windows .bat + Unix shell) parce qu'on
        # build Linux avec le même spec.

        # 1. Windows : bin/osmosis.bat (séparateur ';', chemins '\', %APP_HOME%)
        bat_path = staging_osmosis / "bin" / "osmosis.bat"
        if bat_path.exists():
            bat_txt = bat_path.read_text(encoding="utf-8")
            inject  = f";%APP_HOME%\\lib\\{MAPWRITER_JAR_SRC.name}"
            marker  = r"%APP_HOME%\lib\spring-jcl-5.3.30.jar"
            if inject not in bat_txt:
                if marker not in bat_txt:
                    raise RuntimeError(
                        f"Marker introuvable dans osmosis.bat : {marker!r}. "
                        "Adapter le spec à la version osmosis."
                    )
                bat_txt = bat_txt.replace(marker, marker + inject)
                bat_path.write_text(bat_txt, encoding="utf-8")
                print(f"  [spec] osmosis.bat patché")

        # 2. Linux/Mac : bin/osmosis (séparateur ':', chemins '/', $APP_HOME)
        sh_path = staging_osmosis / "bin" / "osmosis"
        if sh_path.exists():
            sh_txt = sh_path.read_text(encoding="utf-8")
            inject = f":$APP_HOME/lib/{MAPWRITER_JAR_SRC.name}"
            marker = "$APP_HOME/lib/spring-jcl-5.3.30.jar"
            if inject not in sh_txt:
                if marker not in sh_txt:
                    print(f"  [WARN] marker '{marker}' introuvable dans osmosis (Unix). "
                          "Plugin mapwriter ne sera pas chargé.")
                else:
                    sh_txt = sh_txt.replace(marker, marker + inject)
                    sh_path.write_text(sh_txt, encoding="utf-8")
                    print(f"  [spec] osmosis (Unix) patché")
    else:
        print(f"  [WARN] mapwriter jar absent : {MAPWRITER_JAR_SRC}")

    return staging_osmosis.parent


def _add_tree(src_dir, dest_dir):
    src_dir = Path(src_dir).resolve()
    out = []
    if not src_dir.exists():
        print(f"  [WARN] répertoire absent : {src_dir}")
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

# ── Ressources statiques ──────────────────────────────────────────────────────
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

# ── JRE ───────────────────────────────────────────────────────────────────────
if JRE_SRC and JRE_SRC.exists():
    datas += _add_tree(JRE_SRC, f"jre/{JRE_SRC.name}")

# ── osmosis + mapwriter ───────────────────────────────────────────────────────
if staging_osmosis_root:
    datas += _add_tree(staging_osmosis_root, "osmosis")

# ── pyproj ────────────────────────────────────────────────────────────────────
datas         += collect_data_files("pyproj")
hiddenimports += collect_submodules("pyproj")

# ── rasterio ──────────────────────────────────────────────────────────────────
datas         += collect_data_files("rasterio")
binaries      += collect_dynamic_libs("rasterio")
hiddenimports += collect_submodules("rasterio")
hiddenimports += [
    "rasterio._features", "rasterio._io", "rasterio._warp",
    "rasterio.sample", "rasterio.vrt", "rasterio.windows",
    "rasterio.warp", "rasterio.transform", "rasterio.enums",
    "rasterio._shim", "rasterio.control", "rasterio.crs",   # ajout
]

# ── fiona ─────────────────────────────────────────────────────────────────────
datas         += collect_data_files("fiona")
binaries      += collect_dynamic_libs("fiona")
hiddenimports += collect_submodules("fiona")
hiddenimports += ["fiona.schema", "fiona.transform"]

# ── shapely ───────────────────────────────────────────────────────────────────
binaries      += collect_dynamic_libs("shapely")
hiddenimports += ["shapely.geometry", "shapely.strtree", "shapely.ops"]

# ── scipy ─────────────────────────────────────────────────────────────────────
hiddenimports += collect_submodules("scipy")
binaries      += collect_dynamic_libs("scipy")

# ── numba + llvmlite ──────────────────────────────────────────────────────────
try:
    hiddenimports += collect_submodules("numba")
    binaries      += collect_dynamic_libs("numba")
    datas         += collect_data_files("numba")
    binaries      += collect_dynamic_libs("llvmlite")
    datas         += collect_data_files("llvmlite")
except Exception:
    pass

# ── pywebview : backend Qt forcé (Windows ET Linux) ──────────────────────────
# Cette spec sert Windows et Linux ; les deux utilisent désormais le backend Qt
# (PyQt6 + QtWebEngine). Sous Windows ça remplace WinForms/WebView2+pythonnet
# (régression pythonnet 3.1.0 : récursion infinie sérialisation .NET -> bridge
# JS<->Python cassé -> GUI gelée + freezes WinForms) -> plus de couche .NET,
# moteur Chromium identique sur les 3 OS.
datas         += collect_data_files("webview")
hiddenimports += collect_submodules("webview")
for _lib in ("PyQt6", "qtpy"):
    try:
        d, b, h = collect_all(_lib)
        datas += d; binaries += b; hiddenimports += h
    except Exception as _e:
        print(f"  [WARN] collect_all({_lib}) a échoué : {_e}")
hiddenimports += [
    "webview.platforms.qt",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebChannel",
]

# ── PIL ───────────────────────────────────────────────────────────────────────
hiddenimports += [
    "PIL.Image", "PIL.PngImagePlugin", "PIL.JpegImagePlugin",
    "PIL.TiffImagePlugin", "PIL.WebPImagePlugin",
]

# ── laspy + lazrs (lecture LAS/LAZ — lazy) ───────────────────────────────────
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

# ── py7zr (BD TOPO bulk — lazy) ──────────────────────────────────────────────
try:
    d, b, h = collect_all("py7zr")
    datas += d; binaries += b; hiddenimports += h
except Exception:
    pass

# ── osmium ────────────────────────────────────────────────────────────────────
# collect_all (et pas juste collect_submodules + collect_dynamic_libs) :
# osmium 4.x livre des .py purs essentiels (__init__.py, helper.py,
# simple_handler.py, file_processor.py, version.py) qui ne sont pas
# capturés par collect_submodules sur Windows. Sans datas = collect_data_files,
# le bundle a les .pyd mais pas __init__.py → ImportError au runtime.
try:
    d, b, h = collect_all("osmium")
    datas += d; binaries += b; hiddenimports += h
except Exception:
    pass

# osmium.libs/ : delvewheel bundle ses DLL Boost/expat/zlib/bzip2/MSVC++
# avec un suffixe de hash (msvcp140-<hash>.dll). collect_dynamic_libs
# dédupliqe contre msvcp140.dll système et laisse tomber le fichier
# hashé → _osmium.pyd cherche par nom exact au runtime et plante avec
# "DLL load failed". On force la copie complète du dossier sœur.
try:
    import osmium as _osmium_for_libs
    from pathlib import Path as _Path_libs
    _libs_dir = _Path_libs(_osmium_for_libs.__file__).parent.parent / "osmium.libs"
    if _libs_dir.exists():
        for _dll in _libs_dir.iterdir():
            if _dll.is_file():
                binaries.append((str(_dll), "osmium.libs"))
        print(f"  [spec] osmium.libs/ ({len(list(_libs_dir.iterdir()))} fichiers) forcés")
except Exception as _e:
    print(f"  [WARN] copie osmium.libs/ échouée : {_e}")

# ── mapbox_vector_tile (export MVT — lazy) ───────────────────────────────────
try:
    d, b, h = collect_all("mapbox_vector_tile")    # collect_all vs collect_submodules
    datas += d; binaries += b; hiddenimports += h
    hiddenimports += collect_submodules("google.protobuf")
except Exception:
    pass

# ── ijson ─────────────────────────────────────────────────────────────────────
try:
    hiddenimports += collect_submodules("ijson")
except Exception:
    pass

# ── certifi ───────────────────────────────────────────────────────────────────
datas         += collect_data_files("certifi")
hiddenimports += ["urllib3", "charset_normalizer", "idna", "certifi"]

# ── 2 passes PyInstaller ─────────────────────────────────────────────────────
# lidar2map.py est un fichier texte (data) → PyInstaller ne l'analyse pas
# via _loader.py. On lance une Analysis séparée sur lidar2map.py pour
# détecter tous ses imports (sqlite3, ssl, xml…), puis on fusionne les
# TOC résultants APRÈS les deux analyses.
# Important : les binaries/datas d'ENTRÉE d'Analysis sont des 2-tuples.
# Les TOC de SORTIE (a.binaries, a.datas, a.pure) sont des 3-tuples internes.
# On ne peut passer des TOC de sortie en entrée d'une nouvelle Analysis
# → erreur "too many values to unpack". La fusion se fait après.
_excludes = [
    "tkinter", "matplotlib",
    "PyQt5", "PySide2", "PySide6",
    "test", "pydoc_data",
    # "unittest" retiré : scipy.ndimage l'importe en interne → LRM/RRIM cassés
    "IPython", "jupyter",
]
# Backend Qt sur Windows+Linux : on garde PyQt6, on exclut WinForms/Cocoa et
# toute la couche .NET (plus utilisée).
_excludes += ["webview.platforms.winforms", "webview.platforms.cocoa",
              "clr", "clr_loader", "clr_loader.netfx", "pythonnet"]

# ── Runtime hook : forcer PYWEBVIEW_GUI=qt + chemins QtWebEngine ─────────────
# S'applique Windows ET Linux (backend Qt sur les deux). Les gardes os.path
# rendent les chemins inexistants inoffensifs sur l'OS qui ne les a pas.
_hook = SRC / "build" / "_runtime_hook_qt.py"
_hook.parent.mkdir(parents=True, exist_ok=True)
_hook.write_text("""\
import os, sys
_base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
os.environ.setdefault('PYWEBVIEW_GUI', 'qt')
# Qt plugins (xcb platform plugin etc.)
_plugins = os.path.join(_base, 'PyQt6', 'Qt6', 'plugins')
if os.path.isdir(_plugins):
    os.environ.setdefault('QT_PLUGIN_PATH', _plugins)
# QtWebEngineProcess
for _cand in (
    os.path.join(_base, 'PyQt6', 'Qt6', 'bin', 'QtWebEngineProcess.exe'),   # Windows
    os.path.join(_base, 'PyQt6', 'Qt6', 'libexec', 'QtWebEngineProcess'),   # Linux
    os.path.join(_base, 'PyQt6', 'QtWebEngineProcess'),
):
    if os.path.isfile(_cand):
        os.environ.setdefault('QTWEBENGINEPROCESS_PATH', _cand)
        break
_res = os.path.join(_base, 'PyQt6', 'Qt6', 'resources')
if os.path.isdir(_res):
    os.environ.setdefault('QTWEBENGINE_RESOURCES_PATH', _res)
_loc = os.path.join(_base, 'PyQt6', 'Qt6', 'translations')
if os.path.isdir(_loc):
    os.environ.setdefault('QTWEBENGINE_LOCALES_PATH',
                          os.path.join(_loc, 'qtwebengine_locales'))
""")
_runtime_hooks = [str(_hook)]

# Passe 1 : analyse de lidar2map.py pour la détection des imports
a_detect = Analysis(
    ["lidar2map.py"],
    pathex=[], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=_runtime_hooks, excludes=_excludes, noarchive=False, optimize=0,
)

# Passe 2 : build réel depuis _loader.py (même entrées 2-tuples)
a = Analysis(
    ["_loader.py"],
    pathex=[], binaries=binaries,
    datas=datas + [("lidar2map.py", ".")],  # lidar2map.py en clair dans _internal/
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=_runtime_hooks, excludes=_excludes, noarchive=False, optimize=0,
)

# Fusion des TOC de sortie (3-tuples) — après les deux analyses
a.binaries += a_detect.binaries
a.datas    += a_detect.datas
a.pure     += [e for e in a_detect.pure if not e[0].startswith("lidar2map")]

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
