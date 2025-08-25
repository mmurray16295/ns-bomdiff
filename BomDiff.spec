# Force inclusion of numpy / pandas / openpyxl binaries & data
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
)

block_cipher = None

hiddenimports = (
    collect_submodules('numpy')
    + collect_submodules('pandas')
    + collect_submodules('openpyxl')
)

datas = (
    collect_data_files('numpy')
    + collect_data_files('pandas')
    + collect_data_files('openpyxl')
)

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
    runtime_hooks=[],
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
    console=False,
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