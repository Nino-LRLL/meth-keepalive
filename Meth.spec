# -*- mode: python ; coding: utf-8 -*-
"""Meth — spec PyInstaller (portable exe).

Build:  pyinstaller --noconfirm Meth.spec
Output: dist/Meth/Meth.exe  (one-folder, portable)
"""

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=[('assets/icon.ico', 'assets')],
    hiddenimports=[
        # pystray charge son backend Windows dynamiquement.
        'pystray._win32',
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test', 'unittest', 'pydoc'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Meth',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # fenêtre cachée, pas de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Meth',
)
