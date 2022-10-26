# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['wavvad.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[
                "vad.hubconf", 'importlib._bootstrap', 'pkg_resources.py2_warn', 'pkg_resources.markers', 'tornado', 'torch', 'torchaudio',
                'pyannote.audio.models', 'pyannote.audio.models.segmentation'
             ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

for d in a.datas:
    if '_C.cp36-win_amd64' in d[0]:
        a.datas.remove(d)
        break

exe = EXE(pyz,
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
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
