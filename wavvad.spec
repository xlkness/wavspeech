# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['wavvad.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['torch'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

for d in a.datas:
    if '_C.cp36-win_amd64' in d[0]:
        print('dep datas:', d[0])
        a.datas.remove(d)
    elif '_C.pyd' in d[0]:
        print('deps1:', d[0])
        a.datas.remove(d)
    elif '_C_flatbuffer.py' in d[0]:
        print('deps2:', d[0])
        a.datas.remove(d)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wavvad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
