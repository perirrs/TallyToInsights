"""
Excel parser for Tally data exports.
Handles multiple common formats:
  1. Day Book export (Sheet: Day Book / Vouchers)
  2. Ledger-wise export (Sheet: Ledger)
  3. Trial Balance (Sheet: Trial Balance)
  4. Stock Summary (Sheet: Stock Summary)

We auto-detect columns by header names.
"""
import pandas as pd
from datetime import date, datetime
from .normalize import ParseResult, NLedger, NVoucher, NVoucherLine, NStockItem


def _safe_float(val) -> float:
    try:
        if pd.isna(val):
            return 0.0
        return float(str(val).replace(",", "").strip())
    except Exception:
        return 0.0


def _safe_date(val) -> date | None:
    if pd.isna(val):
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _find_header_row(df: pd.DataFrame, keywords: list[str]) -> int:
    for i, row in df.iterrows():
        vals = [str(v).lower().strip() for v in row.values if not pd.isna(v)]
        if sum(1 for k in keywords if any(k in v for v in vals)) >= len(keywords) // 2 + 1:
            return i
    return 0


def _normalize_col(cols):
    return [str(c).lower().strip().replace(" ", "_").replace("/", "_") for c in cols]


def parse_excel(file_path: str) -> ParseResult:
    result = ParseResult()
    xl = pd.ExcelFile(file_path)
    sheets = xl.sheet_names

    for sheet in sheets:
        df_raw = xl.parse(sheet, header=None, dtype=str)
        if df_raw.empty:
            continue

        # Try to detect what kind of sheet this is
        first_rows = " ".join(str(v).lower() for v in df_raw.iloc[:5].values.flatten() if not pd.isna(str(v)))

        if any(k in first_rows for k in ["day book", "voucher", "daybook"]):
            _parse_voucher_sheet(df_raw, result)
        elif any(k in first_rows for k in ["trial balance", "trial_balance", "trialbalance"]):
            _parse_trial_balance(df_raw, result)
        elif any(k in first_rows for k in ["ledger", "account"]):
            _parse_ledger_sheet(df_raw, result)
        elif any(k in first_rows for k in ["stock", "inventory", "item"]):
            _parse_stock_sheet(df_raw, result)
        else:
            # Attempt generic voucher detection
            _parse_voucher_sheet(df_raw, result)

    return result


def _parse_voucher_sheet(df_raw: pd.DataFrame, result: ParseResult):
    # Find header row
    header_row = 0
    for i in range(min(10, len(df_raw))):
        vals = [str(v).lower() for v in df_raw.iloc[i].values if not pd.isna(str(v)) and str(v) != "nan"]
        if any(k in " ".join(vals) for k in ["date", "voucher", "amount", "dr", "cr"]):
            header_row = i
            break

    df = df_raw.iloc[header_row:].reset_index(drop=True)
    df.columns = _normalize_col(df.iloc[0].values)
    df = df.iloc[1:].reset_index(drop=True)
    df = df.dropna(how="all")

    # Map columns
    col_map = {
        "date": ["date", "voucher_date", "vch_date"],
        "voucher_no": ["voucher_no", "vch_no", "number", "voucher_number", "no."],
        "voucher_type": ["voucher_type", "vch_type", "type"],
        "party": ["party_name", "party", "ledger_name", "account_name", "particulars"],
        "debit": ["debit", "dr", "debit_amount"],
        "credit": ["credit", "cr", "credit_amount"],
        "amount": ["amount", "net_amount", "total"],
        "narration": ["narration", "description", "remarks", "details"],
    }

    def find_col(keys):
        for k in keys:
            matches = [c for c in df.columns if k in c]
            if matches:
                return matches[0]
        return None

    date_col = find_col(col_map["date"])
    vno_col = find_col(col_map["voucher_no"])
    vtype_col = find_col(col_map["voucher_type"])
    party_col = find_col(col_map["party"])
    dr_col = find_col(col_map["debit"])
    cr_col = find_col(col_map["credit"])
    amt_col = find_col(col_map["amount"])
    nar_col = find_col(col_map["narration"])

    if not date_col:
        return

    dates = []
    for _, row in df.iterrows():
        d = _safe_date(row.get(date_col))
        if not d:
            continue

        dr = _safe_float(row.get(dr_col, 0)) if dr_col else 0
        cr = _safe_float(row.get(cr_col, 0)) if cr_col else 0
        amount = _safe_float(row.get(amt_col, 0)) if amt_col else max(dr, cr)
        if amount == 0:
            amount = max(dr, cr)

        vtype = str(row.get(vtype_col, "Journal")).strip() if vtype_col else "Journal"
        if not vtype or vtype == "nan":
            vtype = "Journal"

        party = str(row.get(party_col, "")).strip() if party_col else ""
        if party == "nan":
            party = ""

        lines = []
        if dr > 0 and party:
            lines.append(NVoucherLine(ledger_name=party, amount=dr, is_debit=True))
        if cr > 0 and party:
            lines.append(NVoucherLine(ledger_name=party, amount=cr, is_debit=False))

        vch = NVoucher(
            voucher_type=vtype,
            date=d,
            amount=amount,
            voucher_number=str(row.get(vno_col, "")).strip() if vno_col else "",
            party_ledger=party,
            narration=str(row.get(nar_col, "")).strip() if nar_col else "",
            lines=lines,
        )
        result.vouchers.append(vch)
        dates.append(d)

    if dates:
        if not result.period_from or min(dates) < result.period_from:
            result.period_from = min(dates)
        if not result.period_to or max(dates) > result.period_to:
            result.period_to = max(dates)


def _parse_trial_balance(df_raw: pd.DataFrame, result: ParseResult):
    header_row = 0
    for i in range(min(10, len(df_raw))):
        vals = [str(v).lower() for v in df_raw.iloc[i].values if str(v) != "nan"]
        if any(k in " ".join(vals) for k in ["particulars", "ledger", "account", "name"]):
            header_row = i
            break

    df = df_raw.iloc[header_row:].reset_index(drop=True)
    df.columns = _normalize_col(df.iloc[0].values)
    df = df.iloc[1:].reset_index(drop=True)
    df = df.dropna(subset=[df.columns[0]])

    name_col = df.columns[0]

    def find_col(keys):
        for k in keys:
            matches = [c for c in df.columns if k in c]
            if matches:
                return matches[0]
        return None

    closing_dr = find_col(["closing_dr", "closing_debit", "cl_dr"])
    closing_cr = find_col(["closing_cr", "closing_credit", "cl_cr"])
    opening_dr = find_col(["opening_dr", "opening_debit", "op_dr"])
    opening_cr = find_col(["opening_cr", "opening_credit", "op_cr"])
    group_col = find_col(["group", "parent", "category"])

    for _, row in df.iterrows():
        name = str(row[name_col]).strip()
        if not name or name.lower() in ("nan", "total", "grand total"):
            continue

        closing = 0.0
        if closing_dr:
            closing += _safe_float(row.get(closing_dr, 0))
        if closing_cr:
            closing -= _safe_float(row.get(closing_cr, 0))

        opening = 0.0
        if opening_dr:
            opening += _safe_float(row.get(opening_dr, 0))
        if opening_cr:
            opening -= _safe_float(row.get(opening_cr, 0))

        group = str(row.get(group_col, "")).strip() if group_col else ""

        result.ledgers.append(NLedger(
            name=name,
            group_name=group,
            opening_balance=opening,
            closing_balance=closing,
        ))


def _parse_ledger_sheet(df_raw: pd.DataFrame, result: ParseResult):
    _parse_trial_balance(df_raw, result)


def _parse_stock_sheet(df_raw: pd.DataFrame, result: ParseResult):
    header_row = 0
    for i in range(min(10, len(df_raw))):
        vals = [str(v).lower() for v in df_raw.iloc[i].values if str(v) != "nan"]
        if any(k in " ".join(vals) for k in ["item", "stock", "quantity", "rate", "value"]):
            header_row = i
            break

    df = df_raw.iloc[header_row:].reset_index(drop=True)
    df.columns = _normalize_col(df.iloc[0].values)
    df = df.iloc[1:].reset_index(drop=True)
    df = df.dropna(how="all")

    name_col = df.columns[0] if len(df.columns) > 0 else None
    if not name_col:
        return

    def find_col(keys):
        for k in keys:
            matches = [c for c in df.columns if k in c]
            if matches:
                return matches[0]
        return None

    unit_col = find_col(["unit", "uom", "measure"])
    open_qty = find_col(["opening_qty", "op_qty", "opening_quantity"])
    open_val = find_col(["opening_value", "op_value", "opening_amount"])
    close_qty = find_col(["closing_qty", "cl_qty", "closing_quantity"])
    close_val = find_col(["closing_value", "cl_value", "closing_amount"])
    group_col = find_col(["group", "category", "parent"])
    hsn_col = find_col(["hsn", "hsn_code"])

    for _, row in df.iterrows():
        name = str(row[name_col]).strip()
        if not name or name.lower() in ("nan", "total"):
            continue
        result.stock_items.append(NStockItem(
            name=name,
            group_name=str(row.get(group_col, "")).strip() if group_col else "",
            unit=str(row.get(unit_col, "")).strip() if unit_col else "",
            hsn_code=str(row.get(hsn_col, "")).strip() if hsn_col else "",
            opening_qty=_safe_float(row.get(open_qty, 0)) if open_qty else 0,
            opening_value=_safe_float(row.get(open_val, 0)) if open_val else 0,
            closing_qty=_safe_float(row.get(close_qty, 0)) if close_qty else 0,
            closing_value=_safe_float(row.get(close_val, 0)) if close_val else 0,
        ))
