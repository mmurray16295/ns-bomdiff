import os
import tkinter as tk
from tkinter import filedialog, messagebox

core = None  # deferred import
DEFAULT_CSV_NAME = "bomdiff_A_minus_B.csv"

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
        if not ensure_core_loaded():
            return
        group_a = parse_id_list(a_text.get("1.0", "end"))
        group_b = parse_id_list(b_text.get("1.0", "end"))
        if not group_a or not group_b:
            messagebox.showwarning("Input Required", "Enter IDs for both groups.")
            return
        out_csv = output_var.get().strip() or os.path.join(os.getcwd(), DEFAULT_CSV_NAME)
        output_var.set(out_csv)
        status_var.set("Running...")
        root.update_idletasks()
        if hasattr(core, "run_diff"):
            core.run_diff(group_a, group_b, out_csv, "")
        else:
            with open(out_csv, "w", encoding="utf-8") as f:
                f.write("Demo,No run_diff\n")
        status_var.set(f"Done: {out_csv}")
        messagebox.showinfo("Complete", f"Finished.\nCSV: {out_csv}")
    except Exception as e:
        status_var.set("Error")
        messagebox.showerror("Error", str(e))

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

if __name__ == "__main__":
    launch()