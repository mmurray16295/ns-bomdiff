# Remove stray numpy setup sources & show brief diagnostics.
import os, sys, glob
base_paths = list(sys.path)
removed = []
for p in base_paths:
    for cand in (
        os.path.join(p, "numpy", "setup.py"),
        os.path.join(p, "numpy", "pyproject.toml"),
    ):
        if os.path.exists(cand):
            try:
                os.remove(cand)
                removed.append(cand)
            except Exception as e:
                print(f"[runtime_fix] Could not remove {cand}: {e}")
print(f"[runtime_fix] removed={removed or 'none'}")
# After cleanup, attempt a lightweight numpy core presence check.
try:
    import numpy
    import pathlib
    core_dir = pathlib.Path(numpy.__file__).parent / "core"
    so_list = list(core_dir.glob("_multiarray_umath*.so"))
    print(f"[runtime_fix] core so present={bool(so_list)} count={len(so_list)}")
except Exception as e:
    print(f"[runtime_fix] post-clean import probe failed: {e}")