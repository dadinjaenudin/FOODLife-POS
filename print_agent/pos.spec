# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pos_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\YOGYA-Kiosk\\pos-django-htmx-main\\pos_fnb', 'pos_fnb'), ('D:\\YOGYA-Kiosk\\pos-django-htmx-main\\apps', 'apps'), ('D:\\YOGYA-Kiosk\\pos-django-htmx-main\\templates', 'templates'), ('D:\\YOGYA-Kiosk\\pos-django-htmx-main\\static', 'static'), ('D:\\YOGYA-Kiosk\\pos-django-htmx-main\\manage.py', '.'), ('D:\\YOGYA-Kiosk\\pos-django-htmx-main\\requirements.txt', '.')],
    hiddenimports=['django', 'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'daphne', 'channels', 'webview', 'psycopg2', 'whitenoise'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'tkinter'],
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
    name='pos',
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
    icon='NONE',
)
