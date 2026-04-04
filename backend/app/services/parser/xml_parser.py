"""
Tally XML parser — handles all common Tally Prime / Tally ERP 9 export formats:

  Format 1 — TALLYMESSAGE (Sync / Data Exchange)
    ENVELOPE > BODY > IMPORTDATA > REQUESTDATA > TALLYMESSAGE > LEDGER/VOUCHER/STOCKITEM

  Format 2 — Day Book / Report XML
    ENVELOPE > BODY > DATA > TALLYMESSAGE > VOUCHER

  Format 3 — Collection XML (multiple COLLECTION nodes)
    ENVELOPE > BODY > DATA > COLLECTION > LEDGER/VOUCHER/STOCKITEM

Handles both Tally ERP 9 and Tally Prime tag naming differences.
"""
from lxml import etree
from datetime import date, datetime
from .normalize import ParseResult, NLedger, NVoucher, NVoucherLine, NStockLine, NStockItem

CASH_GROUPS = {"cash-in-hand", "cash"}
BANK_GROUPS = {"bank accounts", "bank od accounts", "bank o/d accounts"}

INCOME_GROUPS = {
    "sales accounts", "direct incomes", "indirect incomes",
    "income (direct)", "income (indirect)", "revenue",
    "other incomes", "sales",
}
EXPENSE_GROUPS = {
    "purchase accounts", "direct expenses", "indirect expenses",
    "expense (direct)", "expense (indirect)", "manufacturing expenses",
    "other expenses", "purchases",
}
ASSET_GROUPS = {
    "fixed assets", "current assets", "investments",
    "loans & advances (asset)", "misc. expenses (asset)",
    "sundry debtors", "stock-in-hand", "bank accounts",
    "cash-in-hand", "deposits (asset)",
}
LIABILITY_GROUPS = {
    "capital account", "loans (liability)", "current liabilities",
    "sundry creditors", "bank od accounts", "bank o/d accounts",
    "duties & taxes", "provisions", "reserves & surplus",
}


def _text(el, *tags, default: str = "") -> str:
    """Try multiple tag names and return the first non-empty value."""
    for tag in tags:
        child = el.find(tag)
        if child is not None and child.text:
            return child.text.strip()
    return default


def _attr(el, *attrs, default: str = "") -> str:
    for attr in attrs:
        v = el.get(attr, "")
        if v:
            return v.strip()
    return default


def _parse_amount(val: str) -> float:
    """Parse Tally amount strings like '1,23,456.78 Dr' or '-5000.00 Cr'."""
    if not val:
        return 0.0
    val = val.replace(",", "").strip()
    negative = False
    if val.endswith(" Cr"):
        negative = True
        val = val[:-3].strip()
    elif val.endswith(" Dr"):
        val = val[:-3].strip()
    try:
        result = float(val)
        return -result if negative else result
    except ValueError:
        return 0.0


def _amount(el, *tags) -> float:
    for tag in tags:
        child = el.find(tag)
        if child is not None and child.text:
            return _parse_amount(child.text)
    return 0.0


def _tally_date(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%Y%m%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _classify_ledger(group: str) -> dict:
    g = group.lower().strip()
    return {
        "is_cash": g in CASH_GROUPS,
        "is_bank": g in BANK_GROUPS,
        "is_revenue": any(g == x or g.startswith(x) for x in INCOME_GROUPS),
        "is_expense": any(g == x or g.startswith(x) for x in EXPENSE_GROUPS),
        "is_asset": any(g == x or g.startswith(x) for x in ASSET_GROUPS),
        "is_liability": any(g == x or g.startswith(x) for x in LIABILITY_GROUPS),
    }


def _parse_ledger_element(led_el) -> NLedger | None:
    name = _attr(led_el, "NAME") or _text(led_el, "NAME", "LEDGERNAME")
    if not name:
        return None
    group = _text(led_el, "PARENT", "GROUP", "LEDGERGROUP")

    ob_raw = _text(led_el, "OPENINGBALANCE", default="0")
    cb_raw = _text(led_el, "CLOSINGBALANCE", default="0")
    opening = _parse_amount(ob_raw)
    closing = _parse_amount(cb_raw)

    cl = _classify_ledger(group)
    return NLedger(
        name=name,
        group_name=group,
        opening_balance=opening,
        closing_balance=closing,
        gstin=_text(led_el, "GSTREGISTRATIONNUMBER", "GSTIN"),
        pan=_text(led_el, "INCOMETAXNUMBER", "PAN"),
        address=_text(led_el, "ADDRESS"),
        tally_id=_attr(led_el, "GUID"),
        **cl,
    )


def _parse_stock_element(si_el) -> NStockItem | None:
    name = _attr(si_el, "NAME") or _text(si_el, "NAME", "STOCKITEMNAME")
    if not name:
        return None
    return NStockItem(
        name=name,
        group_name=_text(si_el, "PARENT", "GROUP"),
        unit=_text(si_el, "BASEUNITS", "UNITS"),
        hsn_code=_text(si_el, "HSNCODE") or _text(si_el, "HSNDETAILS.LIST.HSNCODE"),
        gst_rate=_amount(si_el, "GSTRATE"),
        opening_qty=abs(_amount(si_el, "OPENINGBALANCE")),
        opening_value=abs(_amount(si_el, "OPENINGVALUE")),
        closing_qty=abs(_amount(si_el, "CLOSINGBALANCE")),
        closing_value=abs(_amount(si_el, "CLOSINGVALUE")),
    )


def _parse_voucher_element(vch_el) -> NVoucher | None:
    # Voucher type — try attribute first (ERP9), then element (Prime)
    vtype = (
        _attr(vch_el, "VCHTYPE")
        or _text(vch_el, "VOUCHERTYPENAME", "VCHTYPE", "VTYPE")
    )
    if not vtype:
        return None

    date_str = _text(vch_el, "DATE", "VOUCHERDATE", "DSPVCHDATE")
    vdate = _tally_date(date_str)
    if not vdate:
        return None

    # Ledger entry lines — Tally uses several list tag names
    lines: list[NVoucherLine] = []
    amount = 0.0
    for list_tag in ("ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST",
                     "LEDGERENTRY.LIST", "ALLLEDGERENTRY.LIST"):
        for le in vch_el.findall(list_tag):
            lname = _text(le, "LEDGERNAME")
            if not lname:
                continue
            raw_amt = _amount(le, "AMOUNT")
            is_debit = raw_amt >= 0  # positive = debit in Tally's convention
            line_amt = abs(raw_amt)
            gst_type = _text(le, "GSTLEDGERTYPE", "TAXTYPE", "GSTCLASS")
            gst_rate = _amount(le, "GSTRATE")
            lines.append(NVoucherLine(
                ledger_name=lname,
                amount=line_amt,
                is_debit=is_debit,
                gst_type=gst_type,
                gst_rate=gst_rate,
            ))
            if is_debit:
                amount += line_amt

    # Fallback: use AMOUNT tag on voucher itself
    if amount == 0:
        amount = abs(_amount(vch_el, "AMOUNT"))

    # Stock / inventory lines
    stock_lines: list[NStockLine] = []
    for list_tag in ("INVENTORYENTRIES.LIST", "ALLINVENTORYENTRIES.LIST",
                     "INVENTORYENTRY.LIST"):
        for sl in vch_el.findall(list_tag):
            iname = _text(sl, "STOCKITEMNAME", "ITEMNAME")
            if not iname:
                continue
            qty = abs(_amount(sl, "ACTUALQTY", "BILLEDQTY", "QTY"))
            rate = abs(_amount(sl, "RATE"))
            amt = abs(_amount(sl, "AMOUNT"))
            if amt == 0:
                amt = qty * rate
            stock_lines.append(NStockLine(
                item_name=iname,
                qty=qty,
                rate=rate,
                amount=amt,
                godown=_text(sl, "GODOWNNAME"),
                is_inward=vtype.lower() in (
                    "purchase", "receipt note", "stock journal",
                    "credit note", "debit note",
                ),
            ))

    return NVoucher(
        voucher_type=vtype,
        date=vdate,
        amount=amount,
        voucher_number=_text(vch_el, "VOUCHERNUMBER", "VCHNO"),
        party_ledger=_text(vch_el, "PARTYLEDGERNAME", "PARTY"),
        narration=_text(vch_el, "NARRATION", "DESCRIPTION"),
        is_cancelled=_text(vch_el, "ISCANCELLED", default="No").lower() in ("yes", "true", "1"),
        is_optional=_text(vch_el, "ISOPTIONAL", default="No").lower() in ("yes", "true", "1"),
        posted_by=_text(vch_el, "ENTEREDBY", "POSTEDBY"),
        altered_by=_text(vch_el, "LASTALTEREDBY"),
        altered_date=_tally_date(_text(vch_el, "LASTALTEREDDATE")),
        reference=_text(vch_el, "REFERENCE", "REFNO"),
        gstin=_text(vch_el, "GSTREGISTRATIONNUMBER", "GSTIN"),
        place_of_supply=_text(vch_el, "PLACEOFSUPPLY", "STATENAME"),
        is_reverse_charge=_text(vch_el, "ISREVERSECHARGE", default="No").lower() in ("yes", "true"),
        employee_name=_text(vch_el, "EMPLOYEENAME"),
        lines=lines,
        stock_lines=stock_lines,
    )


def parse_xml(file_path: str) -> ParseResult:
    result = ParseResult()

    try:
        tree = etree.parse(file_path, etree.XMLParser(recover=True, huge_tree=True))
    except Exception as e:
        raise ValueError(f"XML parse error: {e}")

    root = tree.getroot()

    # ── Period from COMPANY / HEADER ────────────────────────────────────────
    for company_el in root.iter("COMPANY"):
        from_str = _text(company_el, "FROMDATE", "STARTINGFROM")
        to_str = _text(company_el, "TODATE", "ENDINGAT")
        if from_str:
            result.period_from = _tally_date(from_str)
        if to_str:
            result.period_to = _tally_date(to_str)
        break

    # Also try HEADER block (Tally Prime reports)
    for header_el in root.iter("HEADER"):
        from_str = _text(header_el, "FROMDATE")
        to_str = _text(header_el, "TODATE")
        if from_str and not result.period_from:
            result.period_from = _tally_date(from_str)
        if to_str and not result.period_to:
            result.period_to = _tally_date(to_str)
        break

    # ── Ledgers ─────────────────────────────────────────────────────────────
    seen_ledgers: set[str] = set()
    for led_el in root.iter("LEDGER"):
        led = _parse_ledger_element(led_el)
        if led and led.name not in seen_ledgers:
            seen_ledgers.add(led.name)
            result.ledgers.append(led)

    # ── Stock Items ─────────────────────────────────────────────────────────
    seen_stocks: set[str] = set()
    for si_el in root.iter("STOCKITEM"):
        si = _parse_stock_element(si_el)
        if si and si.name not in seen_stocks:
            seen_stocks.add(si.name)
            result.stock_items.append(si)

    # ── Vouchers ────────────────────────────────────────────────────────────
    dates: list[date] = []
    for vch_el in root.iter("VOUCHER"):
        vch = _parse_voucher_element(vch_el)
        if vch:
            result.vouchers.append(vch)
            dates.append(vch.date)

    # Auto-detect period from voucher dates if not set
    if dates:
        if not result.period_from:
            result.period_from = min(dates)
        if not result.period_to:
            result.period_to = max(dates)

    return result
