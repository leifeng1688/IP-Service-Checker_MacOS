# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['ip-service_check_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'webview.js_bridge',
        'webview.util',
        'webview.platforms.mshtml',
        'clr',
        'clr_loader',
        'requests',
        'urllib3',
        'urllib3.util',
        'urllib3.util.retry',
        'urllib3.util.ssl_',
        'certifi',
        'charset_normalizer',
        'idna',
        'ssl',
        'socket',
        'concurrent.futures',
        'threading',
        'json',
        'csv',
        'tempfile',
        'subprocess',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'test'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,       # ← 單一 exe 必須包含
    a.zipfiles,
    a.datas,
    [],
    name='IP Service Checker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # ← 關閉 UPX，避免防毒誤報 + 部分 DLL 壓縮後無法載入
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,    # ← 不顯示黑色 CMD 視窗
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon_windows.ico',
    version='version_info.txt',
)
