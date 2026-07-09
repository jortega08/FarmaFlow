# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('configuracion', 'configuracion'),
        ('interfaz/assets', 'interfaz/assets'),
        ('persistencia/migraciones', 'persistencia/migraciones'),
        ('datos/clasificador_farmacia.db', 'datos'),
        ('alembic.ini', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Optional scientific/ML stacks present in the local Python environment.
        # FarmaFlow only needs PySide6, pandas/openpyxl/xlrd, SQLAlchemy and Alembic.
        'IPython',
        'jupyter',
        'matplotlib',
        'nbformat',
        'notebook',
        'pytest',
        'scipy',
        'sklearn',
        'tensorflow',
        'torch',
        'torchaudio',
        'torchvision',
        'tornado',
        'zmq',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FarmaFlow',
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
    icon=['interfaz\\assets\\ICONO_FARMAFLOW.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FarmaFlow',
)
