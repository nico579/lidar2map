# -*- mode: python ; coding: utf-8 -*-
"""Binaire autonome du client graphique de préparation de VM."""

from pathlib import Path

tools_dir = Path(SPECPATH)
client = tools_dir / "rlidar2map_GUI.py"
server_script = tools_dir / "rlidar2map_GUI_vm.sh"
app_icon = tools_dir.parent / "lidar2map_icon.png"

a = Analysis(
    [str(client)],
    pathex=[str(tools_dir)],
    binaries=[],
    datas=[(str(server_script), "."), (str(app_icon), ".")],
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
    name="rlidar2map_GUI",
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
    icon=str(app_icon),
)
