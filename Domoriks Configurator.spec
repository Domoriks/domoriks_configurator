# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[('/mnt/c/Users/Jorik/LocalProjects/901-PersonalGit/domoriks_keep_old/app/.venv/lib/python3.12/site-packages/PyQt5/Qt5/plugins/platforms/libqxcb.so', 'PyQt5/Qt5/plugins/platforms/'), ('/mnt/c/Users/Jorik/LocalProjects/901-PersonalGit/domoriks_keep_old/app/.venv/lib/python3.12/site-packages/PyQt5/Qt5/plugins/platforms/libqwayland-generic.so', 'PyQt5/Qt5/plugins/platforms/'), ('/mnt/c/Users/Jorik/LocalProjects/901-PersonalGit/domoriks_keep_old/app/.venv/lib/python3.12/site-packages/PyQt5/Qt5/plugins/platforms/libqwayland-egl.so', 'PyQt5/Qt5/plugins/platforms/'), ('/mnt/c/Users/Jorik/LocalProjects/901-PersonalGit/domoriks_keep_old/app/.venv/lib/python3.12/site-packages/PyQt5/Qt5/plugins/platforms/libqwayland-xcomposite-egl.so', 'PyQt5/Qt5/plugins/platforms/'), ('/mnt/c/Users/Jorik/LocalProjects/901-PersonalGit/domoriks_keep_old/app/.venv/lib/python3.12/site-packages/PyQt5/Qt5/plugins/platforms/libqwayland-xcomposite-glx.so', 'PyQt5/Qt5/plugins/platforms/')],
    datas=[('domoriks.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5.Qt3D', 'PyQt5.QtMultimedia', 'PyQt5.QtWebEngine', 'PyQt5.QtBluetooth', 'PyQt5.QtNfc', 'PyQt5.QtSensors', 'PyQt5.QtSerialPort', 'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtTextToSpeech'],
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
    name='Domoriks Configurator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['domoriks.ico'],
)
