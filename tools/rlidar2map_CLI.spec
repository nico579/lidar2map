# -*- mode: python ; coding: utf-8 -*-
"""Binaire autonome du client CLI d'exécution distante."""

from pathlib import Path

tools_dir = Path(SPECPATH)
client = tools_dir / "rlidar2map_CLI.py"

a = Analysis(
    [str(client)],
    pathex=[str(tools_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="rlidar2map_CLI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
