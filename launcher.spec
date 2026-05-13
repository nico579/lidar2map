# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller pour le LAUNCHER lidar2map.

Construit la même source lidar2map.py en mode onefile minimal :
  - excluant toutes les deps lourdes (le launcher n'utilise que stdlib)
  - embarquant build/lidar2map_bundle.zip (le onedir zippé) en ressource

Au runtime, le bloc launcher en tête de lidar2map.py détecte la présence du
bundle dans sys._MEIPASS, extrait dans %LOCALAPPDATA%\\lidar2map, puis
spawn l'exe interne avec la sentinelle --__lidar2map_inner__.

Prérequis (orchestré par build.ps1) :
  1. pyinstaller lidar2map.spec   → dist/lidar2map/...
  2. zip dist/lidar2map → build/lidar2map_bundle.zip
  3. pyinstaller launcher.spec    → dist/lidar2map.exe   (livrable final)
"""

from pathlib import Path

BUNDLE_ZIP = Path(SPECPATH) / "build" / "lidar2map_bundle.zip"
if not BUNDLE_ZIP.exists():
    raise SystemExit(
        f"[launcher.spec] Bundle introuvable : {BUNDLE_ZIP}\n"
        "Exécute d'abord :\n"
        "  pyinstaller lidar2map.spec --clean --noconfirm\n"
        "  Compress dist/lidar2map → build/lidar2map_bundle.zip\n"
    )

# Bundle zippé inclus comme ressource. Au runtime accessible via sys._MEIPASS.
datas = [(str(BUNDLE_ZIP), ".")]

# Aucun hidden import — le launcher n'utilise que stdlib (os, sys, hashlib,
# zipfile, subprocess, shutil, pathlib).
hiddenimports = []

# EXCLURE agressivement toutes les deps lourdes que lidar2map.py importe
# (à l'intérieur de fonctions qui ne s'exécutent jamais en mode launcher).
# Sans ça, PyInstaller les analyse statiquement et les embarque → exe énorme.
excludes = [
    "rasterio", "fiona", "shapely", "pyproj",
    "scipy", "numba", "llvmlite",
    "numpy",
    "PIL", "Pillow",
    "webview", "clr_loader", "pythonnet", "clr",
    "osmium",
    "mapbox_vector_tile", "google.protobuf",
    "ijson",
    "requests", "urllib3", "charset_normalizer", "certifi",
    "pandas",
    # tk + qt + matplotlib (jamais utilisés)
    "tkinter", "matplotlib",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    # tests stdlib
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
    console=True,                # héritage console = stdout du child visible
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
