# Fix numpy packaging: copy compiled libs from Frameworks/numpy/_core -> Resources/numpy/_core
import os, sys, pathlib, shutil

removed = []
for p in sys.path:
    for fname in ("setup.py", "pyproject.toml"):
        cand = os.path.join(p, "numpy", fname)
        if os.path.exists(cand):
            try:
                os.remove(cand); removed.append(cand)
            except Exception as e:
                print(f"[runtime_fix] cannot remove {cand}: {e}")

exe = pathlib.Path(sys.executable).resolve()
contents = exe.parents[1]  # .../BomDiff.app/Contents
fw_core = contents / "Frameworks" / "numpy" / "_core"
res_numpy = contents / "Resources" / "numpy"
res_core = res_numpy / "_core"
res_core.mkdir(parents=True, exist_ok=True)

moved = []
if fw_core.is_dir():
    for so in fw_core.glob("*.so"):
        target = res_core / so.name
        if not target.exists():
            try:
                shutil.copy2(so, target)
                moved.append(so.name)
            except Exception as e:
                print(f"[runtime_fix] copy failed {so} -> {target}: {e}")

print(f"[runtime_fix] removed={removed or 'none'} moved={moved or 'none'}")

try:
    import numpy
    # Verify presence of compiled extension in the expected underscore dir
    so_files = list((res_core).glob("_multiarray_umath*.so"))
    print(f"[runtime_fix] numpy.__file__={numpy.__file__}")
    print(f"[runtime_fix] _core so present={bool(so_files)} count={len(so_files)} names={[s.name for s in so_files]}")
except Exception as e:
    print(f"[runtime_fix] numpy probe failed: {e}")