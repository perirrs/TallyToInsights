"""
Excel / CSV parser for Tally data exports.

Handles:
  1. Day Book — one or more rows per voucher (Dr/Cr lines in separate rows)
  2. Trial Balance — ledger-wise opening/closing balances
  3. Ledger Report — per-ledger transaction history
  4. Stock Summary — item-wise opening/closing stock
"""
import pandas as pd
from datetime import date, datetime
from .normalize import ParseResult, NLedger, NVoucher, NVoucherLine, NStockItem


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val) -> float:
    try:
        if pd.isna(val):
            return 0.0
    except (TypeError, ValueError):
        pass
    try:
        return float(str(val).replace(",", "").replace("(", "-").replace(")", "").strip())
    except Exception:
        return 0.0


def _safe_date(val) -> date | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s or s.lower() in ("nan", "nat", "none", ""):
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y",
                "%d %b %Y", "%Y%m%d", "%d-%b-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _normalize_col(cols) -> list[str]:
    return [str(c).lower().strip()
            .replace(" ", "_").replace("/", "_").replace(".", "_") for c in cols]


def _find_col(df_cols: list[str], *keys: str) -> str | None:
    for k in keys:
        for c in df_cols:
            if k in c:
                return c
    return None


def _find_header_row(df_raw: pd.DataFrame, keywords: list[str]) -> int:
    for i in range(min(15, len(df_raw))):
        vals = " ".join(
            str(v).lower() for v in df_raw.iloc[i].values
            if str(v) not in ("nan", "None", "")
        )
        if sum(1 for k in keywords if k in vals) >= max(1, len(keywords) // 2):
            return i
    return 0


# ── Main entry ────────────────────────────────────────────────────────────────

def parse_excel(file_path: str) -> ParseResult:
    result = ParseResult()
    try:
        xl = pd.ExcelFile(file_path)
    except Exception as e:
        raise ValueError(f"Cannot open file: {e}")

    for sheet in xl.sheet_names:
        try:
            df_raw = xl.parse(sheet, header=None, dtype=str)
        except Exception:
            continue
        if df_raw.empty or len(df_raw) < 2:
            continue

        # Detect sheet type from first 8 rows
        first_text = " ".join(
            str(v).lower() for v in df_raw.iloc[:8].values.flatten()
            if str(v) not in ("nan", "None", "")
        )

        if any(k in first_text for k in ("day book", "daybook", "voucher register")):
            _parse_daybook(df_raw, result)
        elif any(k in first_text for k in ("trial balance",)):
            _parse_trial_balance(df_raw, result)
        elif any(k in first_text for k in ("stock summary", "stock item", "inventory summary")):
            _parse_stock(df_raw, result)
        elif any(k in first_text for k in ("ledger", "account statement")):
            _parse_ledger(df_raw, result)
        else:
            # Unknown — try Day Book first, then Trial Balance
            before = len(result.vouchers)
            _parse_daybook(df_raw, result)
            if len(result.vouchers) == before:
                _parse_trial_balance(df_raw, result)

    return result


# ── Day Book / Voucher sheet ──────────────────────────────────────────────────

def _parse_daybook(df_raw: pd.DataFrame, result: ParseResult):
    """
    Handles both single-row-per-voucher and multi-row formats.
    In Tally Day Book, a voucher may span multiple rows with the same
    voucher number — first row has the date/type, subsequent rows have
    additional ledger lines (blank date = continuation).
    """
    header_row = _find_header_row(df_raw, ["date", "voucher", "amount"])

    df = df_raw.iloc[header_row:].reset_index(drop=True)
    df.columns = _normalize_col(df.iloc[0].values)
    df = df.iloc[1:].reset_index(drop=True)
    df = df.dropna(how="all")

    cols = list(df.columns)
    date_col   = _find_col(cols, "date", "vch_date", "voucher_date")
    vno_col    = _find_col(cols, "vch_no", "voucher_no", "voucher_number", "no_")
    vtype_col  = _find_col(cols, "voucher_type", "vch_type", "type")
    party_col  = _find_col(cols, "party_name", "party", "particulars",
                            "ledger_name", "account_name", "name")
    dr_col     = _find_col(cols, "debit", "_dr", "dr_")
    cr_col     = _find_col(cols, "credit", "_cr", "cr_")
    amt_col    = _find_col(cols, "amount", "net_amount", "total_amount")
    nar_col    = _find_col(cols, "narration", "description", "remarks")

    if not date_col:
        return

    # Build vouchers by grouping rows with same voucher number
    # (Tally's multi-row Day Book format)
    pending: dict | None = None
    dates: list[date] = []

    def flush():
        nonlocal pending
        if pending:
            result.vouchers.append(NVoucher(**pending))
            dates.append(pending["date"])
        pending = None

    rows = df.to_dict("records")

    for row in rows:
        d = _safe_date(row.get(date_col))
        vno = str(row.get(vno_col, "")).strip() if vno_col else ""
        vno = "" if vno in ("nan", "None") else vno
        vtype = str(row.get(vtype_col, "")).strip() if vtype_col else ""
        vtype = "" if vtype in ("nan", "None") else vtype
        party = str(row.get(party_col, "")).strip() if party_col else ""
        party = "" if party in ("nan", "None") else party
        narration = str(row.get(nar_col, "")).strip() if nar_col else ""
        narration = "" if narration in ("nan", "None") else narration

        dr = _safe_float(row.get(dr_col, 0)) if dr_col else 0
        cr = _safe_float(row.get(cr_col, 0)) if cr_col else 0
        amt = _safe_float(row.get(amt_col, 0)) if amt_col else 0

        # A new voucher starts when we see a date (or a new voucher number)
        is_new = d is not None

        if is_new:
            flush()
            amount = amt or max(dr, cr)
            lines = []
            if party and (dr > 0 or cr > 0):
                lines.append(NVoucherLine(
                    ledger_name=party,
                    amount=dr if dr > 0 else cr,
                    is_debit=dr > 0,
                ))
            pending = dict(
                voucher_type=vtype or "Journal",
                date=d,
                amount=amount,
                voucher_number=vno,
                party_ledger=party,
                narration=narration,
                lines=lines,
            )
        elif pending and party and (dr > 0 or cr > 0):
            # Continuation row — add ledger line to current voucher
            pending["lines"].append(NVoucherLine(
                ledger_name=party,
                amount=dr if dr > 0 else cr,
                is_debit=dr > 0,
            ))
            # Update amount if this gives us a better figure
            if pending["amount"] == 0:
                pending["amount"] = dr if dr > 0 else cr
            if not pending["party_ledger"] and party:
                pending["party_ledger"] = party
            if not pending["narration"] and narration:
                pending["narration"] = narration

    flush()

    if dates:
        if not result.period_from or min(dates) < result.period_from:
            result.period_from = min(dates)
        if not result.period_to or max(dates) > result.period_to:
            result.period_to = max(dates)


# ── Trial Balance ─────────────────────────────────────────────────────────────

def _parse_trial_balance(df_raw: pd.DataFrame, result: ParseResult):
    header_row = _find_header_row(df_raw, ["particulars", "ledger", "name", "account"])

    df = df_raw.iloc[header_row:].reset_index(drop=True)
    df.columns = _normalize_col(df.iloc[0].values)
    df = df.iloc[1:].reset_index(drop=True)
    df = df.dropna(subset=[df.columns[0]])

    cols = list(df.columns)
    name_col    = cols[0]
    group_col   = _find_col(cols, "group", "parent", "category")
    cl_dr_col   = _find_col(cols, "closing_dr", "cl__dr", "closing_debit")
    cl_cr_col   = _find_col(cols, "closing_cr", "cl__cr", "closing_credit")
    op_dr_col   = _find_col(cols, "opening_dr", "op__dr", "opening_debit")
    op_cr_col   = _find_col(cols, "opening_cr", "op__cr", "opening_credit")
    cl_bal_col  = _find_col(cols, "closing_balance", "closing_bal", "cl_bal")
    op_bal_col  = _find_col(cols, "opening_balance", "opening_bal", "op_bal")

    seen: set[str] = set()
    for row in df.to_dict("records"):
        name = str(row[name_col]).strip()
        if not name or name.lower() in ("nan", "none", "total", "grand total", ""):
            continue
        if name in seen:
            continue
        seen.add(name)

        closing = 0.0
        if cl_bal_col:
            closing = _safe_float(row.get(cl_bal_col, 0))
        else:
            if cl_dr_col:
                closing += _safe_float(row.get(cl_dr_col, 0))
            if cl_cr_col:
                closing -= _safe_float(row.get(cl_cr_col, 0))

        opening = 0.0
        if op_bal_col:
            opening = _safe_float(row.get(op_bal_col, 0))
        else:
            if op_dr_col:
                opening += _safe_float(row.get(op_dr_col, 0))
            if op_cr_col:
                opening -= _safe_float(row.get(op_cr_col, 0))

        group = str(row.get(group_col, "")).strip() if group_col else ""
        if group in ("nan", "None"):
            group = ""

        result.ledgers.append(NLedger(
            name=name,
            group_name=group,
            opening_balance=opening,
            closing_balance=closing,
        ))


# ── Ledger report (per-account statement) ────────────────────────────────────

def _parse_ledger(df_raw: pd.DataFrame, result: ParseResult):
    """
    A single-ledger statement has a header with the ledger name,
    then transaction rows. We extract the transactions as vouchers.
    """
    # Try to get ledger name from first few rows
    ledger_name = ""
    for i in range(min(5, len(df_raw))):
        vals = [str(v).strip() for v in df_raw.iloc[i].values if str(v) not in ("nan", "None", "")]
        if vals and len(vals) == 1:
            ledger_name = vals[0]
            break

    _parse_daybook(df_raw, result)

    # If no ledger name found from voucher rows, use what we guessed
    if ledger_name and result.vouchers:
        for v in result.vouchers:
            if not v.party_ledger:
                v.party_ledger = ledger_name


# ── Stock Summary ─────────────────────────────────────────────────────────────

def _parse_stock(df_raw: pd.DataFrame, result: ParseResult):
    header_row = _find_header_row(df_raw, ["item", "stock", "quantity", "value"])

    df = df_raw.iloc[header_row:].reset_index(drop=True)
    df.columns = _normalize_col(df.iloc[0].values)
    df = df.iloc[1:].reset_index(drop=True)
    df = df.dropna(how="all")

    if df.empty:
        return

    cols = list(df.columns)
    name_col  = cols[0]
    unit_col  = _find_col(cols, "unit", "uom", "measure")
    oq_col    = _find_col(cols, "opening_qty", "op_qty", "opening_quantity", "opening__qty")
    ov_col    = _find_col(cols, "opening_value", "op_value", "opening_amount", "opening__value")
    cq_col    = _find_col(cols, "closing_qty", "cl_qty", "closing_quantity", "closing__qty")
    cv_col    = _find_col(cols, "closing_value", "cl_value", "closing_amount", "closing__value")
    group_col = _find_col(cols, "group", "category", "parent")
    hsn_col   = _find_col(cols, "hsn", "hsn_code")

    seen: set[str] = set()
    for row in df.to_dict("records"):
        name = str(row[name_col]).strip()
        if not name or name.lower() in ("nan", "none", "total", ""):
            continue
        if name in seen:
            continue
        seen.add(name)

        result.stock_items.append(NStockItem(
            name=name,
            group_name=str(row.get(group_col, "")).strip() if group_col else "",
            unit=str(row.get(unit_col, "")).strip() if unit_col else "",
            hsn_code=str(row.get(hsn_col, "")).strip() if hsn_col else "",
            opening_qty=abs(_safe_float(row.get(oq_col, 0))) if oq_col else 0.0,
            opening_value=abs(_safe_float(row.get(ov_col, 0))) if ov_col else 0.0,
            closing_qty=abs(_safe_float(row.get(cq_col, 0))) if cq_col else 0.0,
            closing_value=abs(_safe_float(row.get(cv_col, 0))) if cv_col else 0.0,
        ))
