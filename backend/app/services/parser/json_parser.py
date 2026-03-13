"""JSON parser for custom Tally exports or API-based dumps."""
import json
from datetime import date, datetime
from .normalize import ParseResult, NLedger, NVoucher, NVoucherLine, NStockLine, NStockItem


def _to_date(val) -> date | None:
    if not val:
        return None
    if isinstance(val, date):
        return val
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y%m%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _to_float(val) -> float:
    try:
        return float(str(val).replace(",", "").strip())
    except Exception:
        return 0.0


def parse_json(file_path: str) -> ParseResult:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = ParseResult()

    # Support both top-level arrays and nested objects
    # Format 1: {"ledgers": [...], "vouchers": [...], "stock_items": [...]}
    # Format 2: {"data": {"LEDGER": [...], "VOUCHER": [...], "STOCKITEM": [...]}}
    # Format 3: flat array of vouchers

    if isinstance(data, list):
        # Flat voucher list
        _parse_voucher_list(data, result)
        return result

    # Nested
    ledgers = (
        data.get("ledgers") or data.get("LEDGER") or
        data.get("data", {}).get("ledgers") or data.get("data", {}).get("LEDGER") or []
    )
    vouchers = (
        data.get("vouchers") or data.get("VOUCHER") or
        data.get("data", {}).get("vouchers") or data.get("data", {}).get("VOUCHER") or []
    )
    stocks = (
        data.get("stock_items") or data.get("STOCKITEM") or
        data.get("data", {}).get("stock_items") or []
    )

    for l in ledgers:
        _parse_ledger(l, result)

    _parse_voucher_list(vouchers, result)

    for s in stocks:
        _parse_stock_item(s, result)

    return result


def _parse_ledger(l: dict, result: ParseResult):
    name = l.get("name") or l.get("NAME") or l.get("ledger_name", "")
    if not name:
        return
    result.ledgers.append(NLedger(
        name=str(name),
        group_name=str(l.get("group") or l.get("PARENT") or ""),
        opening_balance=_to_float(l.get("opening_balance") or l.get("OPENINGBALANCE") or 0),
        closing_balance=_to_float(l.get("closing_balance") or l.get("CLOSINGBALANCE") or 0),
        gstin=str(l.get("gstin") or l.get("GSTREGISTRATIONNUMBER") or ""),
        pan=str(l.get("pan") or l.get("INCOMETAXNUMBER") or ""),
    ))


def _parse_voucher_list(vouchers: list, result: ParseResult):
    dates = []
    for v in vouchers:
        vtype = str(v.get("voucher_type") or v.get("VOUCHERTYPENAME") or v.get("type") or "Journal")
        d = _to_date(v.get("date") or v.get("DATE") or v.get("voucher_date"))
        if not d:
            continue

        lines = []
        for le in v.get("lines", []) or v.get("ledger_entries", []) or v.get("ALLLEDGERENTRIES.LIST", []):
            lname = str(le.get("ledger_name") or le.get("LEDGERNAME") or "")
            lamount = _to_float(le.get("amount") or le.get("AMOUNT") or 0)
            is_debit = le.get("is_debit", lamount > 0)
            lines.append(NVoucherLine(
                ledger_name=lname,
                amount=abs(lamount),
                is_debit=bool(is_debit),
                gst_type=str(le.get("gst_type") or ""),
                gst_rate=_to_float(le.get("gst_rate") or 0),
            ))

        stock_lines = []
        for sl in v.get("stock_lines", []) or v.get("inventory_entries", []) or []:
            stock_lines.append(NStockLine(
                item_name=str(sl.get("item_name") or sl.get("STOCKITEMNAME") or ""),
                qty=_to_float(sl.get("qty") or sl.get("ACTUALQTY") or 0),
                rate=_to_float(sl.get("rate") or sl.get("RATE") or 0),
                amount=_to_float(sl.get("amount") or sl.get("AMOUNT") or 0),
                godown=str(sl.get("godown") or ""),
                is_inward=bool(sl.get("is_inward", True)),
            ))

        amount = _to_float(v.get("amount") or v.get("AMOUNT") or 0)
        if amount == 0 and lines:
            amount = sum(l.amount for l in lines if l.is_debit)

        altered_date_val = v.get("altered_date") or v.get("LASTALTEREDDATE")
        result.vouchers.append(NVoucher(
            voucher_type=vtype,
            date=d,
            amount=amount,
            voucher_number=str(v.get("voucher_number") or v.get("VOUCHERNUMBER") or ""),
            party_ledger=str(v.get("party") or v.get("PARTYLEDGERNAME") or ""),
            narration=str(v.get("narration") or v.get("NARRATION") or ""),
            is_cancelled=bool(v.get("is_cancelled") or v.get("ISCANCELLED") or False),
            posted_by=str(v.get("posted_by") or v.get("ENTEREDBY") or ""),
            altered_by=str(v.get("altered_by") or v.get("LASTALTEREDBY") or ""),
            altered_date=_to_date(altered_date_val),
            reference=str(v.get("reference") or v.get("REFERENCE") or ""),
            gstin=str(v.get("gstin") or ""),
            place_of_supply=str(v.get("place_of_supply") or ""),
            is_reverse_charge=bool(v.get("is_reverse_charge") or False),
            lines=lines,
            stock_lines=stock_lines,
        ))
        dates.append(d)

    if dates:
        if not result.period_from or min(dates) < result.period_from:
            result.period_from = min(dates)
        if not result.period_to or max(dates) > result.period_to:
            result.period_to = max(dates)


def _parse_stock_item(s: dict, result: ParseResult):
    name = str(s.get("name") or s.get("NAME") or "")
    if not name:
        return
    result.stock_items.append(NStockItem(
        name=name,
        group_name=str(s.get("group") or ""),
        unit=str(s.get("unit") or ""),
        hsn_code=str(s.get("hsn_code") or ""),
        gst_rate=_to_float(s.get("gst_rate") or 0),
        opening_qty=_to_float(s.get("opening_qty") or 0),
        opening_value=_to_float(s.get("opening_value") or 0),
        closing_qty=_to_float(s.get("closing_qty") or 0),
        closing_value=_to_float(s.get("closing_value") or 0),
    ))
