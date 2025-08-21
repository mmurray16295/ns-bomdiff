# BoM Diff (A minus B) on Sales Order line items
# ===== EDIT HERE: define your two groups and outputs =====
GROUP_A_SO_IDS = [842689, 842688, 842687]  # ← Group A: Sales Order internal IDs
GROUP_B_SO_IDS = [675219, 675227, 675220]  # ← Group B: Sales Order internal IDs
OUTPUT_CSV  = "bomdiff_A_minus_B.csv"
OUTPUT_XLSX = "bomdiff_A_minus_B.xlsx"
# ========================================================

# If True, aggregate uses absolute value of each line's quantity (treat negative as positive count)
COUNT_ABSOLUTE_LINE_QTY = True

import os, requests, pandas as pd, time
from requests_oauthlib import OAuth1
from oauthlib.oauth1 import SIGNATURE_HMAC_SHA256
from dotenv import load_dotenv

load_dotenv(override=True)  # force .env to override any OS env vars

REALM  = os.getenv("NS_ACCOUNT_REALM")
DOMAIN = os.getenv("NS_REST_DOMAIN")
CK     = os.getenv("NS_CONSUMER_KEY")
CS     = os.getenv("NS_CONSUMER_SECRET")
TID    = os.getenv("NS_TOKEN_ID")
TS     = os.getenv("NS_TOKEN_SECRET")

def mask(v):
    if not v: return "(missing)"
    v = v.strip()
    return f"{v[:4]}…{v[-4:]} (len {len(v)})"

def debug_env():
    print("\n--- DEBUG ENV ---")
    print("CWD:", os.getcwd())
    print("REALM:", repr(REALM))
    print("DOMAIN:", repr(DOMAIN))
    print("CK:", mask(CK))
    print("CS:", mask(CS))
    print("TID:", mask(TID))
    print("TS:", mask(TS))
    print("--- END DEBUG ---\n")

def suiteql(sql: str, *, timeout: int = 30):
    if not all([REALM, DOMAIN, CK, CS, TID, TS]):
        raise SystemExit("Missing one or more values in .env (realm/domain/keys/tokens).")
    url = DOMAIN.rstrip("/") + "/services/rest/query/v1/suiteql"
    auth = OAuth1(
        CK.strip(), CS.strip(), TID.strip(), TS.strip(),
        signature_method=SIGNATURE_HMAC_SHA256,
        signature_type="AUTH_HEADER",
        realm=REALM.strip(),
    )
    r = requests.post(url, json={"q": sql}, auth=auth, headers={"Prefer": "transient"}, timeout=timeout)
    try:
        r.raise_for_status()
    except Exception:
        print("Status:", r.status_code)
        print("Body:", r.text[:1000])
        print("SQL:", sql.strip()[:500])
        raise
    return r.json().get("items", [])

def suiteql_df(sql: str) -> pd.DataFrame:
    rows = suiteql(sql)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# --- REST Records helpers (fallback when SuiteQL tables are unavailable) ---
def _make_auth():
    return OAuth1(
        CK.strip(), CS.strip(), TID.strip(), TS.strip(),
        signature_method=SIGNATURE_HMAC_SHA256,
        signature_type="AUTH_HEADER",
        realm=REALM.strip(),
    )

def rest_get_salesorder(so_id: int) -> dict:
    url = DOMAIN.rstrip("/") + f"/services/rest/record/v1/salesorder/{int(so_id)}?expandSubResources=true"
    r = requests.get(url, auth=_make_auth(), headers={"Prefer": "transient"}, timeout=30)
    if r.status_code == 404:
        return {"_not_found": True}
    if not r.ok:
        # Always show the server response to diagnose
        print(f"REST Records HTTP {r.status_code} for SO {so_id}. Response body:\n{r.text[:1000]}")
        raise SystemExit(
            "REST Records call was denied. Likely role access to the record is restricted. Check:\n"
            "- You are using the same 'Developer' role as the access token when testing in the UI\n"
            "- Transactions → Sales Order: View\n"
            "- Transactions → Find Transactions: View\n"
            "- Lists → Items: View and Lists → Customers: View\n"
            "- Role Subsidiaries include the SO's subsidiary (or set to All). If OneWorld, consider 'Allow Cross-Subsidiary Record Viewing'\n"
            "Open one SO in the UI with the Developer role; if it fails there, adjust the role and retry."
        )
    return r.json()

def verify_so_ids_rest(so_ids: list[int], label: str):
    if not so_ids:
        print(f"{label}: 0 IDs provided")
        return
    found = []
    missing = []
    for i in so_ids:
        data = rest_get_salesorder(int(i))
        if data.get("_not_found"):
            missing.append(i)
        else:
            tranid = data.get("tranId") or data.get("tranid") or ""
            found.append((i, tranid))
    print(f"{label} (REST): found {len(found)} Sales Orders out of {len(so_ids)} IDs")
    for i, tran in found[:10]:
        print(f"  {i} → {tran}")
    if missing:
        print("  Missing:", ", ".join(map(str, missing)))

def fetch_so_lines_rest(so_ids: list[int]) -> pd.DataFrame:
    rows = []
    for so in so_ids or []:
        data = rest_get_salesorder(int(so))
        if data.get("_not_found"):
            continue
        # Sublist may be named "item"
        sub = data.get("item") or []
        for line in sub:
            # Skip closed/description-only lines if present
            if line.get("isClosed") is True:
                continue
            itm = line.get("item") or {}
            item_id_raw = itm.get("id") or itm.get("value")
            try:
                item_id = int(item_id_raw) if item_id_raw is not None else None
            except Exception:
                item_id = None
            item_name = itm.get("refName") or itm.get("text") or itm.get("name") or ""
            qty = line.get("quantity")
            try:
                qty = float(qty) if qty is not None else 0.0
            except Exception:
                qty = 0.0
            rows.append({"so_id": int(so), "item_id": item_id, "item_name": item_name, "line_qty": qty})
    return pd.DataFrame(rows, columns=["so_id","item_id","item_name","line_qty"])

def verify_so_ids(so_ids: list[int], label: str):
    """
    Verifies that the provided Sales Order internal IDs exist and are of type 'SalesOrd'.
    """
    if not so_ids:
        print(f"{label}: 0 IDs provided")
        return
    id_list = ",".join(str(int(i)) for i in so_ids)
    sql = f"""
        SELECT id, tranid, "type"
        FROM "transaction"
        WHERE id IN ({id_list})
          AND "type" = 'SalesOrd'
    """
    df = suiteql_df(sql)
    print(f"{label}: found {len(df)} Sales Orders out of {len(so_ids)} IDs")
    if not df.empty:
        print(df[["id","tranid","type"]].to_string(index=False))

def fetch_so_lines(so_ids: list[int]) -> pd.DataFrame:
    """
    Fetch non-mainline Sales Order lines for the given internal IDs.
    Returns: so_id, item_id, item_name, line_qty
    """
    if not so_ids:
        return pd.DataFrame(columns=["so_id","item_id","item_name","line_qty"])
    id_list = ",".join(str(int(i)) for i in so_ids)
    sql = f"""
        SELECT
            tl.transaction AS so_id,
            tl.item        AS item_id,
            i.itemid       AS item_name,
            tl.quantity    AS line_qty
        FROM "transactionline" tl
        LEFT JOIN "item" i ON i.id = tl.item
        WHERE tl.transaction IN ({id_list})
          AND tl.mainline = 'F'
    """
    df = suiteql_df(sql)
    if df.empty:
        return pd.DataFrame(columns=["so_id","item_id","item_name","line_qty"])
    df["line_qty"] = pd.to_numeric(df["line_qty"], errors="coerce").fillna(0.0)
    return df

def aggregate_by_item(lines: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate total quantity per item across all provided SO lines.
    If COUNT_ABSOLUTE_LINE_QTY is True, negative line quantities are converted to positive
    before summing (useful when negative lines represent reversals/credits you still want to
    count as occurrences of the part).
    """
    if lines.empty:
        return pd.DataFrame(columns=["item_id","item_name","total_qty"])
    work = lines.copy()
    if COUNT_ABSOLUTE_LINE_QTY:
        work["line_qty_for_sum"] = work["line_qty"].abs()
    else:
        work["line_qty_for_sum"] = work["line_qty"]

    agg = (
        work.groupby(["item_id","item_name"], dropna=False, as_index=False)["line_qty_for_sum"]
        .sum()
        .rename(columns={"line_qty_for_sum":"total_qty"})
    )
    return agg

def debug_negative_lines(so_ids: list[int]):
    """
    List any transaction lines with negative quantity (before absolute normalization)
    so you can audit why they appeared.
    """
    if not so_ids:
        return
    id_list = ",".join(str(int(i)) for i in so_ids)
    sql = f"""
        SELECT
            tl.transaction AS so_id,
            tl.item        AS item_id,
            i.itemid       AS item_name,
            tl.quantity    AS line_qty
        FROM "transactionline" tl
        LEFT JOIN "item" i ON i.id = tl.item
        WHERE tl.transaction IN ({id_list})
          AND tl.mainline = 'F'
          AND tl.quantity < 0
        ORDER BY so_id, item_name
    """
    df = suiteql_df(sql)
    if df.empty:
        print("No negative line quantities in these SOs.")
    else:
        print("Negative line quantities (raw, before abs):")
        print(df.to_string(index=False))

def compare_groups_a_minus_b(group_a: list[int], group_b: list[int]) -> pd.DataFrame:
    """
    Compute (A - B) by item. Missing items count as 0. Drop zero diffs.
    """
    a_items = aggregate_by_item(fetch_so_lines(group_a)).rename(columns={"total_qty":"qty_A"})
    b_items = aggregate_by_item(fetch_so_lines(group_b)).rename(columns={"total_qty":"qty_B"})

    merged = pd.merge(a_items, b_items, on=["item_id","item_name"], how="outer").fillna({"qty_A":0.0, "qty_B":0.0})
    merged["diff_A_minus_B"] = merged["qty_A"] - merged["qty_B"]
    merged = merged[merged["diff_A_minus_B"] != 0].copy()
    # If values are whole numbers, cast to int for cleaner output
    for c in ("qty_A","qty_B","diff_A_minus_B"):
        if (merged[c] % 1 == 0).all():
            merged[c] = merged[c].astype(int)
    merged = merged.sort_values(by=["item_name","item_id"]).reset_index(drop=True)
    return merged

def compare_groups_a_minus_b_rest(group_a: list[int], group_b: list[int]) -> pd.DataFrame:
    a_items = aggregate_by_item(fetch_so_lines_rest(group_a)).rename(columns={"total_qty":"qty_A"})
    b_items = aggregate_by_item(fetch_so_lines_rest(group_b)).rename(columns={"total_qty":"qty_B"})
    merged = pd.merge(a_items, b_items, on=["item_id","item_name"], how="outer").fillna({"qty_A":0.0, "qty_B":0.0})
    merged["diff_A_minus_B"] = merged["qty_A"] - merged["qty_B"]
    merged = merged[merged["diff_A_minus_B"] != 0].copy()
    for c in ("qty_A","qty_B","diff_A_minus_B"):
        if (merged[c] % 1 == 0).all():
            merged[c] = merged[c].astype(int)
    merged = merged.sort_values(by=["item_name","item_id"]).reset_index(drop=True)
    return merged

# NEW: return a boolean instead of hard stop; we’ll fall back to REST if needed
def check_required_records(required: tuple[str, ...] = ("item","transaction","transactionline")) -> bool:
    inaccessible = []
    for rec in required:
        try:
            suiteql(f'SELECT 1 FROM "{rec}" FETCH NEXT 1 ROWS ONLY')
        except Exception:
            inaccessible.append(rec)
    if inaccessible:
        print(
            "SuiteQL record catalog not available for: " + ", ".join(inaccessible) + "\n"
            "Falling back to REST Records for Sales Order lines."
        )
        return False
    print("Record access OK for:", ", ".join(required))
    return True

def _detect_excel_engine() -> str | None:
    try:
        import openpyxl  # noqa: F401
        return "openpyxl"
    except Exception:
        try:
            import xlsxwriter  # noqa: F401
            return "xlsxwriter"
        except Exception:
            return None

def write_outputs(df: pd.DataFrame, csv_path: str, xlsx_path: str) -> None:
    # Ensure a DataFrame and sane column order
    df = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    preferred = [c for c in ["item_id","item_name","qty_A","qty_B","diff_A_minus_B"] if c in df.columns]
    if preferred:
        df = df[preferred]

    # Always write CSV (no extra deps)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Optionally write XLSX if a writer is available and a path was provided
    wrote_xlsx = False
    if xlsx_path:
        engine = _detect_excel_engine()
        if engine:
            with pd.ExcelWriter(xlsx_path, engine=engine) as xw:
                df.to_excel(xw, index=False, sheet_name="A_minus_B")
            wrote_xlsx = True

    print("Wrote outputs:")
    print(" -", os.path.abspath(csv_path))
    if wrote_xlsx:
        print(" -", os.path.abspath(xlsx_path))
    else:
        if xlsx_path:
            print(" - Skipped XLSX (install 'openpyxl' or 'xlsxwriter' to enable)")

if __name__ == "__main__":
    debug_env()
    print("SuiteQL ok →", suiteql("SELECT 1 AS ok"))
    suiteql_ok = check_required_records()

    if suiteql_ok:
        verify_so_ids(GROUP_A_SO_IDS, "Group A")
        verify_so_ids(GROUP_B_SO_IDS, "Group B")
        # Optional diagnostics (comment out later)
        print("\n-- Negative lines in Group A (raw) --")
        debug_negative_lines(GROUP_A_SO_IDS)
        print("\n-- Negative lines in Group B (raw) --")
        debug_negative_lines(GROUP_B_SO_IDS)
        result = compare_groups_a_minus_b(GROUP_A_SO_IDS, GROUP_B_SO_IDS)
    else:
        verify_so_ids_rest(GROUP_A_SO_IDS, "Group A")
        verify_so_ids_rest(GROUP_B_SO_IDS, "Group B")
        result = compare_groups_a_minus_b_rest(GROUP_A_SO_IDS, GROUP_B_SO_IDS)

    print(f"Rows in A − B with non-zero diff: {len(result)}")
    write_outputs(result, OUTPUT_CSV, OUTPUT_XLSX)
    # Optional probe:
    # probe_line_fields(GROUP_A_SO_IDS[0], limit_rows=3)


