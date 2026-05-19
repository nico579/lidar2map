# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller pour le LAUNCHER lidar2map — macOS ARM64 (.app bundle).

Construit la même source lidar2map.py en mode onefile minimal, en excluant
toutes les deps lourdes (le launcher n'utilise que stdlib).

Le bundle lidar2map_bundle.zip N'EST PAS embarqué dans le binaire : il est
copié dans LIDAR2MAP.app/Contents/Resources/ par lidar2map_mac_build.sh,
ce qui le rend remplaçable sans rebuilder (cf. update_app.py).

Au runtime, le bloc launcher en tête de lidar2map.py cherche le bundle
dans Contents/Resources/, extrait dans ~/Library/Application Support/lidar2map/,
puis spawn l'exe interne avec la sentinelle --__lidar2map_inner__.

Prérequis (orchestré par lidar2map_mac_build.sh) :
  1. pyinstaller lidar2map_mac.spec          -> dist_onedir/lidar2map/
  2. zip dist_onedir/lidar2map               -> build/lidar2map_bundle.zip
  3. pyinstaller lidar2map_mac_launcher.spec -> dist/LIDAR2MAP.app
  4. copie  lidar2map_bundle.zip             -> LIDAR2MAP.app/Contents/Resources/
"""

from pathlib import Path

BUNDLE_ZIP = Path(SPECPATH) / "build" / "lidar2map_bundle.zip"
if not BUNDLE_ZIP.exists():
    raise SystemExit(
        f"[lidar2map_mac_launcher.spec] Bundle introuvable : {BUNDLE_ZIP}\n"
        "Execute d'abord :\n"
        "  pyinstaller lidar2map_mac.spec --clean --noconfirm\n"
        "  cd dist_onedir && zip -r ../build/lidar2map_bundle.zip lidar2map/\n"
    )

datas         = []   # zip dans Contents/Resources/, pas embarqué dans le binaire
hiddenimports = []

excludes = [
    "rasterio", "fiona", "shapely", "pyproj",
    "scipy", "numba", "llvmlite",
    "numpy",
    "PIL", "Pillow",
    "webview", "clr_loader", "pythonnet", "clr",
    "PyQt6", "PyQt5", "PySide2", "PySide6", "qtpy",
    "osmium",
    "mapbox_vector_tile", "google.protobuf",
    "ijson",
    "requests", "urllib3", "charset_normalizer", "certifi",
    "pandas",
    "tkinter", "matplotlib",
    "test", "unittest", "pydoc_data", "IPython", "jupyter",
]

a = Analysis(
    ["lidar2map.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="lidar2map",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,        # double-clic sur fichier -> args forwards
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

app = BUNDLE(
    exe,
    name='LIDAR2MAP.app',
    icon=None,
    bundle_identifier='fr.nicolas.lidar2map',
    info_plist={
        'NSHighResolutionCapable':        'True',
        'NSRequiresAquaSystemAppearance':  'No',
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True,
        },
        'com.apple.security.cs.allow-jit':                        True,
        'com.apple.security.cs.allow-unsigned-executable-memory': True,
    },
)
