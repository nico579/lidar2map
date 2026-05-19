# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller pour le LAUNCHER lidar2map — Windows onefile.

Construit la même source lidar2map.py en mode onefile minimal, en excluant
toutes les deps lourdes (le launcher n'utilise que stdlib).

Le bundle lidar2map_bundle.zip N'EST PAS embarqué dans le binaire : il est
copié à côté du .exe par lidar2map_build.ps1, ce qui le rend remplaçable
sans rebuilder (cf. update_app.py / 7-Zip).

Au runtime, le bloc launcher en tête de lidar2map.py cherche le bundle
à côté de l'exe, puis spawn l'exe interne avec la sentinelle
--__lidar2map_inner__ qui désactive ce même bloc côté inner.

Prérequis (orchestré par lidar2map_build.ps1) :
  1. pyinstaller lidar2map.spec          -> dist_onedir/lidar2map/...
  2. zip dist_onedir/lidar2map           -> build/lidar2map_bundle.zip
  3. pyinstaller lidar2map_launcher.spec -> dist/lidar2map.exe  (livrable final)
  4. copie  lidar2map_bundle.zip         -> dist/  (à côté du .exe)
"""

from pathlib import Path

BUNDLE_ZIP = Path(SPECPATH) / "build" / "lidar2map_bundle.zip"
if not BUNDLE_ZIP.exists():
    raise SystemExit(
        f"[lidar2map_launcher.spec] Bundle introuvable : {BUNDLE_ZIP}\n"
        "Exécute d'abord :\n"
        "  pyinstaller lidar2map.spec --clean --noconfirm\n"
        "  Compress-Archive dist_onedir\\lidar2map\\* build\\lidar2map_bundle.zip\n"
    )

# Le zip N'EST PAS embarqué dans le binaire launcher.
# Il sera copié à côté du .exe par lidar2map_build.ps1.
# → Remplaçable depuis Windows sans rebuilder : ouvrir le zip, remplacer _internal/lidar2map.py
datas         = []
hiddenimports = []

# Exclure agressivement toutes les deps lourdes — le launcher n'utilise
# que stdlib (os, sys, hashlib, zipfile, subprocess, shutil, pathlib).
# Sans ça PyInstaller les analyse statiquement → exe énorme.
excludes = [
    "rasterio", "fiona", "shapely", "pyproj",
    "scipy", "numba", "llvmlite",
    "numpy",
    "PIL", "Pillow",
    "webview", "clr_loader", "pythonnet", "clr",
    "osmium",
    "laspy",                            # ajout
    "py7zr",                            # ajout
    "mapbox_vector_tile", "google.protobuf",
    "ijson",
    "requests", "urllib3", "charset_normalizer", "certifi",
    "pandas",
    "tkinter", "matplotlib",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
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
    console=True,       # stdout du child visible dans le terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
