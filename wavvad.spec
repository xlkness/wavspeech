# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

lib_dir="H:/likun/study/python/virtualenv/audio_env_37/Lib/site-packages/"
stdlib_dir="C:/Program Files/Python38/Lib/"
datas = [(lib_dir + "torchaudio/lib", '.'),
    (lib_dir + "librosa/util", 'librosa/util'),
    (lib_dir + "speechbrain", 'speechbrain'),
    (lib_dir + "pyannote", 'pyannote'),
    (lib_dir + "asteroid_filterbanks", 'asteroid_filterbanks'),
    (lib_dir + "pytorch_lightning", 'pytorch_lightning'),
    (lib_dir + "pytorch_metric_learning", 'pytorch_metric_learning'),
    (lib_dir + "tqdm", 'tqdm'),
    (lib_dir + "ruamel", 'ruamel'),
    (lib_dir + "hyperpyyaml", 'hyperpyyaml'),
    (stdlib_dir + "logging", 'logging'),
    (lib_dir + "singledispatchmethod*", '.')]

a = Analysis(
    ['wavvad.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=['.'],
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
    if '_C.cp37-win_amd64' in d[0]:
        print('dep datas:', d[0])
        a.datas.remove(d)
    if '_C.cp38-win_amd64' in d[0]:
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
