# Full spec: force numpy/pandas/openpyxl; exclude numpy source markers.
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
)
import os

block_cipher = None

hiddenimports = (
    collect_submodules('numpy')
    + collect_submodules('pandas')
    + collect_submodules('openpyxl')
)

# Data files for pandas/openpyxl only; skip setup/pyproject.
datas = []
for src, dest in collect_data_files('pandas') + collect_data_files('openpyxl'):
    base = os.path.basename(src)
    if base in ('setup.py', 'pyproject.toml'):
        continue
    datas.append((src, dest))

# Dynamic libs (include numpy libs explicitly)
binaries = (
    collect_dynamic_libs('numpy')
    + collect_dynamic_libs('pandas')
    + collect_dynamic_libs('openpyxl')
)

a = Analysis(
    ['bomdiff_application_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=['runtime_fix_numpy.py'],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BomDiff',
    console=True,   # keep True for diagnostics; switch to False after success
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='BomDiff'
)
app = BUNDLE(
    coll,
    name='BomDiff.app',
    icon=None,
    bundle_identifier=None
)