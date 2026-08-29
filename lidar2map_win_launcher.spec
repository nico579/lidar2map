# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller pour le LAUNCHER lidar2map — Windows onefile.

Construit la même source lidar2map.py en mode onefile minimal, en excluant
toutes les deps lourdes (le launcher n'utilise que stdlib).

Le bundle lidar2map_bundle.zip N'EST PAS embarqué dans le binaire : il est
copié à côté du .exe par lidar2map_win_build.ps1, ce qui le rend remplaçable
sans rebuilder (cf. update_app.py / 7-Zip).

Au runtime, le bloc launcher en tête de lidar2map.py cherche le bundle
à côté de l'exe, puis spawn l'exe interne avec la sentinelle
--__lidar2map_inner__ qui désactive ce même bloc côté inner.

Prérequis (orchestré par lidar2map_win_build.ps1) :
  1. pyinstaller lidar2map_win.spec          -> dist_onedir/lidar2map/...
  2. zip dist_onedir/lidar2map           -> build/lidar2map_bundle.zip
  3. pyinstaller lidar2map_win_launcher.spec -> dist/lidar2map.exe  (livrable final)
  4. copie  lidar2map_bundle.zip         -> dist/  (à côté du .exe)
"""

import re
from pathlib import Path

SRC = Path(SPECPATH)

BUNDLE_ZIP = SRC / "build" / "lidar2map_bundle.zip"
APP_ICON = SRC / "lidar2map_icon.png"
if not BUNDLE_ZIP.exists():
    raise SystemExit(
        f"[lidar2map_win_launcher.spec] Bundle introuvable : {BUNDLE_ZIP}\n"
        "Exécute d'abord :\n"
        "  pyinstaller lidar2map_win.spec --clean --noconfirm\n"
        "  Compress-Archive dist_onedir\\lidar2map\\* build\\lidar2map_bundle.zip\n"
    )

# Le zip N'EST PAS embarqué dans le binaire launcher.
# Il sera copié à côté du .exe par lidar2map_win_build.ps1.
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
    "CSF",                              # socle DFM csf (lazy dans common)
    "py7zr",                            # ajout
    "mapbox_vector_tile", "google.protobuf",
    "ijson",
    "requests", "urllib3", "charset_normalizer", "certifi",
    "pandas",
    "tkinter", "matplotlib",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "test", "unittest", "pydoc_data", "IPython", "jupyter",
]

# Ressource VERSIONINFO du binaire Windows. Un PE PyInstaller sans editeur,
# description ni copyright renseignes ressemble statistiquement aux
# echantillons malveillants des jeux d'entrainement de plusieurs moteurs
# antivirus a heuristique ML : confirme directement sur ce projet, VirusTotal
# donne le meme verdict "trojan"/"compte-gouttes" que blink2video (6/71,
# Wacatac.C!ml, SentinelOne ML statique) malgre un comportement totalement
# different (pas d'autostart, pas de fenetre cachee). C'est ce launcher qui
# est le binaire reellement distribue aux utilisateurs.
def _version_info(version: str) -> str:
    parties = (version.split(".") + ["0", "0", "0"])[:3]
    tuple_version = tuple(int(p) for p in parties) + (0,)
    chemin = SRC / ".version_info.txt"
    chemin.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tuple_version},
    prodvers={tuple_version},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'nico579'),
         StringStruct(u'FileDescription', u'lidar2map - cartographie a partir de releves LIDAR'),
         StringStruct(u'FileVersion', u'{version}'),
         StringStruct(u'InternalName', u'lidar2map'),
         StringStruct(u'LegalCopyright', u'GPLv3 - nico579'),
         StringStruct(u'OriginalFilename', u'lidar2map.exe'),
         StringStruct(u'ProductName', u'lidar2map'),
         StringStruct(u'ProductVersion', u'{version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")
    return str(chemin)


_texte_version = (SRC / "lidar2map.py").read_text(encoding="utf-8")
_m_version = re.search(r'^VERSION\s*=\s*"([^"]+)"', _texte_version, re.M)
VERSION = _m_version.group(1) if _m_version else "0.0.0"

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
    icon=str(APP_ICON),
    version=_version_info(VERSION),
)
