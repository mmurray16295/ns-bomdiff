# Full spec: force numpy/pandas/openpyxl; exclude numpy source markers.
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files, collect_dynamic_libs
import numpy, pathlib, os, shutil

block_cipher = None

# Collect everything for numpy
n_datas, n_binaries, n_hidden = collect_all('numpy')

# Remap any binaries (and datas just in case) from numpy/_core -> numpy/core
def remap(entries):
    out = []
    for src, dest in entries:
        if dest.startswith('numpy/_core'):
            dest = dest.replace('numpy/_core', 'numpy/core', 1)
        out.append((src, dest))
    return out

n_binaries = remap(n_binaries)
n_datas = remap(n_datas)

# Manually ensure critical core .so are included & mapped
core_dir = pathlib.Path(numpy.__file__).parent / "core"
manual_bins = []
for so in core_dir.glob("*.so"):
    name = so.name
    if any(k in name for k in ("multiarray", "umath", "linalg")):
        manual_bins.append((str(so), "numpy/core"))
# Deduplicate
seen = set()
all_n_bins = []
for t in n_binaries + manual_bins:
    if t not in seen:
        seen.add(t)
        all_n_bins.append(t)

# pandas + openpyxl
p_hidden = collect_submodules('pandas')
o_hidden = collect_submodules('openpyxl')
p_datas = collect_data_files('pandas')
o_datas = collect_data_files('openpyxl')
p_bins = collect_dynamic_libs('pandas')
o_bins = collect_dynamic_libs('openpyxl')

hiddenimports = list(set(n_hidden + p_hidden + o_hidden))
datas = n_datas + p_datas + o_datas
binaries = all_n_bins + p_bins + o_bins

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
    console=True,
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