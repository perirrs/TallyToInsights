# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for TallyInsights backend
#
# Build from backend/ directory:
#   pip install pyinstaller
#   pyinstaller TallyInsights.spec
#
# Output: dist/backend/ (copy this folder to the Electron app's resources/backend/)

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# Collect all hidden imports and data for key packages
datas = []
binaries = []
hiddenimports = []

for pkg in ['uvicorn', 'starlette', 'fastapi', 'anyio', 'h11']:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# App modules
hiddenimports += collect_submodules('app')

# Additional explicit hidden imports
hiddenimports += [
    'email_validator',
    'email_validator.syntax',
    'email_validator.deliverability',
    'multipart',
    'multipart.multipart',
    'python_multipart',
    'aiofiles',
    'aiofiles.os',
    'aiofiles.threadpool',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.reader.excel',
    'xlsxwriter',
    'reportlab',
    'reportlab.lib',
    'reportlab.platypus',
    'numpy',
    'pandas',
    'pandas.core.arrays.arrow',
    'lxml',
    'lxml.etree',
    'lxml._elementpath',
    'sqlalchemy',
    'sqlalchemy.dialects.sqlite',
    'bcrypt',
    'pydantic',
    'pydantic_settings',
    'httpx',
    'httpcore',
    'sniffio',
    'python_dateutil',
    'dateutil',
]

a = Analysis(
    ['desktop_entry.py'],
    pathex=['.'],
    binaries=binaries,
    datas=[
        ('app', 'app'),
        *datas,
        *collect_data_files('openpyxl'),
        *collect_data_files('reportlab'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['celery', 'redis', 'tkinter', 'PyQt5', 'PyQt6', 'wx', 'matplotlib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window in production
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='backend',
)
