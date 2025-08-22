import os, sys, platform
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

core = None  # deferred import
DEFAULT_CSV_NAME = "bomdiff_A_minus_B.csv"

APP_VERSION = "v0.1.0"

def parse_id_list(text: str) -> list[int]:
    ids: list[int] = []
    for part in text.replace("\n", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            raise ValueError(f"Invalid ID: {part}")
        ids.append(int(part))
    return ids

def choose_output_file():
    path = filedialog.asksaveasfilename(
        title="Select CSV output",
        defaultextension=".csv",
        initialfile=DEFAULT_CSV_NAME,
        filetypes=[("CSV Files","*.csv"),("All Files","*.*")]
    )
    if path:
        output_var.set(path)

def ensure_core_loaded() -> bool:
    global core
    if core is not None:
        return True
    try:
        # Load .env first (optional if you rely on it)
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # fine if not present
        import so_bomdiff_application as core_mod
        core = core_mod
        return True
    except Exception as e:
        messagebox.showerror("Import Error", f"Could not load core module:\n{e}")
        return False

def run_clicked():
    try:
        # TODO: put the logic you previously had here
        perform_diff()
    except Exception as e:
        import traceback, io
        buf = io.StringIO()
        traceback.print_exc(file=buf)
        messagebox.showerror("Error", f"Run failed:\n{e}\n\n{buf.getvalue()[:1500]}")

def launch():
    global root, a_text, b_text, output_var, status_var
    root = tk.Tk()
    root.title("BoM Diff (A - B)")

    defaults_a = defaults_b = []
    try:
        if ensure_core_loaded():
            defaults_a = getattr(core, "GROUP_A_SO_IDS", []) or []
            defaults_b = getattr(core, "GROUP_B_SO_IDS", []) or []
    except:
        pass

    tk.Label(root, text="Group A SO Internal IDs (comma or newline separated):").grid(row=0, column=0, sticky="w", padx=8, pady=(8,2))
    a_text = tk.Text(root, width=55, height=4); a_text.grid(row=1, column=0, padx=8, pady=2)
    if defaults_a: a_text.insert("1.0", ",".join(str(i) for i in defaults_a))

    tk.Label(root, text="Group B SO Internal IDs:").grid(row=2, column=0, sticky="w", padx=8, pady=(10,2))
    b_text = tk.Text(root, width=55, height=4); b_text.grid(row=3, column=0, padx=8, pady=2)
    if defaults_b: b_text.insert("1.0", ",".join(str(i) for i in defaults_b))

    tk.Label(root, text="Output CSV File:").grid(row=4, column=0, sticky="w", padx=8, pady=(10,2))
    frame = tk.Frame(root); frame.grid(row=5, column=0, padx=8, pady=2, sticky="we")
    global output_var
    output_var = tk.StringVar(value=os.path.join(os.getcwd(), DEFAULT_CSV_NAME))
    tk.Entry(frame, textvariable=output_var, width=42).pack(side="left", fill="x", expand=True)
    tk.Button(frame, text="Browse…", command=choose_output_file).pack(side="left", padx=4)

    tk.Button(root, text="Run Diff", command=run_clicked, width=20).grid(row=6, column=0, pady=12)

    global status_var
    status_var = tk.StringVar(value="Idle")
    tk.Label(root, textvariable=status_var, anchor="w", fg="blue").grid(row=7, column=0, sticky="we", padx=8, pady=(0,8))

    root.resizable(False, False)
    root.mainloop()

def load_env():
    """
    Load first config file found (priority order):
      1. .env inside bundle
      2. default.env inside bundle
      3. .env alongside the .app
      4. default.env alongside the .app
      5. .env in current working directory
      6. default.env in current working directory
    """
    exe = Path(sys.executable).resolve()
    names = [".env", "default.env"]
    candidates = []
    if ".app/Contents/MacOS" in str(exe):
        macos_dir = exe.parent                  # .../Contents/MacOS
        app_dir = macos_dir.parent.parent       # .../BomDiff.app
        outer_dir = app_dir.parent
        for n in names:
            candidates.append(macos_dir / n)
        for n in names:
            candidates.append(outer_dir / n)
    for n in names:
        candidates.append(Path(".") / n)

    for p in candidates:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    if not line or line.lstrip().startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
                print(f"[env] Loaded {p}")
                break
            except Exception as e:
                print(f"[env] Failed loading {p}: {e}")

load_env()

print(f"[startup] BomDiff {APP_VERSION} python={platform.python_version()} "
      f"arch={platform.machine()} sys.executable={sys.executable}")

# Quick numpy availability check (helps confirm PyInstaller collected binaries)
try:
    import numpy as _np  # noqa
    print(f"[check] numpy OK version={_np.__version__}")
except Exception as e:
    print(f"[check] numpy import failed: {e}")

# Retrieve env vars (keep fallback names if you had older naming)
ACCOUNT_ID = os.getenv("NS_ACCOUNT_REALM") or os.getenv("NETSUITE_ACCOUNT_ID")
REST_DOMAIN = os.getenv("NS_REST_DOMAIN")
CONSUMER_KEY = os.getenv("NS_CONSUMER_KEY") or os.getenv("NETSUITE_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("NS_CONSUMER_SECRET") or os.getenv("NETSUITE_CONSUMER_SECRET")
TOKEN_ID = os.getenv("NS_TOKEN_ID") or os.getenv("NETSUITE_TOKEN_ID")
TOKEN_SECRET = os.getenv("NS_TOKEN_SECRET") or os.getenv("NETSUITE_TOKEN_SECRET")

def perform_diff():
    """
    Parse inputs, call core diff, write CSV, update status.
    Tries several possible core function names; adjust once you know the real one.
    """
    if not ensure_core_loaded():
        return
    out_path = output_var.get().strip()
    if not out_path:
        messagebox.showerror("Output Required", "Please choose an output CSV file.")
        return

    try:
        group_a = parse_id_list(a_text.get("1.0", "end"))
        group_b = parse_id_list(b_text.get("1.0", "end"))
    except ValueError as ve:
        messagebox.showerror("Invalid IDs", str(ve))
        return

    if not group_a:
        messagebox.showerror("Input Required", "Group A list is empty.")
        return
    if not group_b:
        messagebox.showerror("Input Required", "Group B list is empty.")
        return

    status_var.set("Running...")
    root.update_idletasks()

    try:
        # Try to locate a core diff function (adjust to the real one in so_bomdiff_application.py)
        fn = None
        for name in ("run_diff", "bomdiff", "perform_diff", "diff_boms", "main"):
            if hasattr(core, name):
                cand = getattr(core, name)
                if callable(cand):
                    fn = cand
                    break
        if fn is None:
            raise RuntimeError("No diff function found in core module (expected one of run_diff/bomdiff/perform_diff/diff_boms/main).")

        # Call the core function.
        # Adapt signature if needed; this assumes (group_a_ids, group_b_ids, output_path)
        result = fn(group_a, group_b, out_path)

        status_var.set(f"Done: {out_path}")
        messagebox.showinfo("Success", f"Diff written to:\n{out_path}")
    except Exception as e:
        import traceback, io
        buf = io.StringIO()
        traceback.print_exc(file=buf)
        status_var.set("Error")
        messagebox.showerror("Error",
            f"Diff failed:\n{e}\n\nTraceback (truncated):\n{buf.getvalue()[:1500]}")

if __name__ == "__main__":
    launch()