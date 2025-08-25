# Full spec: force numpy/pandas/openpyxl; exclude numpy source markers.
from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
)

block_cipher = None

# Full numpy (all datas/binaries/hiddenimports)
n_datas, n_binaries, n_hidden = collect_all('numpy')

# pandas + openpyxl
p_hidden = collect_submodules('pandas')
o_hidden = collect_submodules('openpyxl')
p_datas = collect_data_files('pandas')
o_datas = collect_data_files('openpyxl')
p_bins = collect_dynamic_libs('pandas')
o_bins = collect_dynamic_libs('openpyxl')

hiddenimports = list(set(n_hidden + p_hidden + o_hidden))
datas = n_datas + p_datas + o_datas
binaries = n_binaries + p_bins + o_bins

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
    console=True,  # turn False after numpy works
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