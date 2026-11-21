# -*- mode: python ; coding: utf-8 -*-
import os

# The spec is copied around (build_tmp/ here, the open-source tree there), so the
# source root is whichever directory actually holds the launcher.
HERE = os.path.dirname(os.path.abspath(SPECPATH))
ROOT = HERE if os.path.isfile(os.path.join(HERE, "zzzcode_app.py")) else os.path.dirname(HERE)
SRC = ROOT

a = Analysis(
    [os.path.join(ROOT, 'zzzcode_app.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ROOT, "ui", "index.html"), "ui"),
           (os.path.join(ROOT, "assets", "zzz.ico"), "assets")],
    hiddenimports=['ouc_common', 'zen_proxy', 'zen_lane', 'warp_keeper', 'zen_guard',
                   'ouc_firewall', 'doctor', 'zen_hop', 'zzz_patch', 'patch_desktop',
                   'patch_gui', 'proxy_chain', 'tor_manager', 'clean_endpoint',
                   'auto_resume', 'zzz_intro'],
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
    a.binaries,
    a.datas,
    [],
    name='ZzZCode',
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
