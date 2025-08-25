# Runtime numpy diagnostics & relocation of misplaced core .so files.
import os, sys, pathlib, shutil

removed = []
for p in sys.path:
    for fname in ("setup.py","pyproject.toml"):
        cand = os.path.join(p,"numpy",fname)
        if os.path.exists(cand):
            try:
                os.remove(cand); removed.append(cand)
            except Exception as e:
                print(f"[runtime_fix] cannot remove {cand}: {e}")

# If _core dir exists but core dir has no compiled libs, move them.
for p in sys.path:
    root = pathlib.Path(p) / "numpy"
    d_core = root / "core"
    d__core = root / "_core"
    if d__core.is_dir():
        so_files = list(d__core.glob("_multiarray_umath*.so")) + list(d__core.glob("*umath*.so"))
        if so_files:
            d_core.mkdir(exist_ok=True)
            # Only move if not already present
            for so in so_files:
                target = d_core / so.name
                if not target.exists():
                    try:
                        shutil.copy2(so, target)
                        print(f"[runtime_fix] copied {so.name} -> core")
                    except Exception as e:
                        print(f"[runtime_fix] copy failed {so} -> core: {e}")

print(f"[runtime_fix] removed={removed or 'none'}")

try:
    import numpy
    loc = pathlib.Path(numpy.__file__).parent
    core_dir = loc / "core"
    sos = list(core_dir.glob("*multiarray*umath*.so")) or list(core_dir.glob("_multiarray_umath*.so"))
    print(f"[runtime_fix] numpy.__file__={numpy.__file__}")
    print(f"[runtime_fix] core so present={bool(sos)} count={len(sos)} names={[s.name for s in sos]}")
except Exception as e:
    print(f"[runtime_fix] numpy probe failed: {e}")