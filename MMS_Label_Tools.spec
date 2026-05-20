# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('marketplace_v12\\data', 'marketplace_v12\\data'), ('marketplace_v12\\samples', 'marketplace_v12\\samples'), ('marketplace_v12\\reference_templates', 'marketplace_v12\\reference_templates')]
binaries = []
hiddenimports = ['reportlab.graphics.barcode.code128', 'reportlab.graphics.barcode.code39', 'reportlab.graphics.barcode.code93', 'reportlab.graphics.barcode.codabar', 'reportlab.graphics.barcode.eanbc', 'reportlab.graphics.barcode.qr', 'PIL._tkinter_finder', 'win32print', 'win32api', 'win32con']
hiddenimports += collect_submodules('reportlab.graphics.barcode')
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MMS_Label_Tools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MMS_Label_Tools',
)
