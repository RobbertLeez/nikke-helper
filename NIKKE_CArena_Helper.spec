# -*- mode: python ; coding: utf-8 -*-

import os

# --- Helper function to find mode modules ---
def get_hidden_imports_for_modes(modes_dir='modes'):
   hidden = []
   if os.path.isdir(modes_dir):
       for filename in os.listdir(modes_dir):
           if filename.startswith('mode') and filename.endswith('.py'):
               module_name = f"{modes_dir}.{filename[:-3]}"
               hidden.append(module_name)
   return hidden

# --- Get mode hidden imports ---
mode_hidden_imports = get_hidden_imports_for_modes()

# --- Define data files ---
data_files = [
    ('config.json', '.'),
    ('icon.ico', '.')
]

# --- Define hidden imports ---
hidden_imports = [
   'PIL._tkinter_finder',
   'PIL.ImageTk',
   'PIL.Image',
   'keyboard._winkeyboard',
   'core.constants',
   'core.utils',
   'core.match_processing',
   'core.player_processing',
   'modes.mode1',
   'modes.mode2',
   'modes.mode3',
   'modes.mode4',
   'modes.mode5',
   'modes.mode6',
   'modes.mode7',
   'modes.mode8',
   'modes.mode9',
   'modes.mode10',
   'modes.mode41',
] + mode_hidden_imports


a = Analysis(
   ['gui_app.py'],
   pathex=[],
   binaries=[],
   datas=data_files,
   hiddenimports=hidden_imports,
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
    name='NIKKE_CArena_Helper',
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
    icon='icon.ico',
    uac_admin=False)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    Tree('assets', prefix='assets'),
    Tree('modes', prefix='modes'),
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NIKKE_CArena_Helper',
)
