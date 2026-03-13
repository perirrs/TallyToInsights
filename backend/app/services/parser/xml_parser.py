"""
Tally XML parser — handles the standard Tally Prime / Tally ERP 9 export format.
Tally exports follow a structure like:
  <ENVELOPE>
    <HEADER>...</HEADER>
    <BODY>
      <IMPORTDATA>
        <REQUESTDATA>
          <TALLYMESSAGE>
            <LEDGER NAME="...">...</LEDGER>
            <VOUCHER>...</VOUCHER>
            <STOCKITEM>...</STOCKITEM>
          </TALLYMESSAGE>
        </REQUESTDATA>
      </IMPORTDATA>
    </BODY>
  </ENVELOPE>
"""
from lxml import etree
from datetime import date, datetime
from .normalize import ParseResult, NLedger, NVoucher, NVoucherLine, NStockLine, NStockItem

CASH_GROUPS = {"cash-in-hand", "cash"}
BANK_GROUPS = {"bank accounts", "bank od accounts", "bank o/d accounts"}

INCOME_GROUPS = {
    "sales accounts", "direct incomes", "indirect incomes",
    "income (direct)", "income (indirect)", "revenue",
}
EXPENSE_GROUPS = {
    "purchase accounts", "direct expenses", "indirect expenses",
    "expense (direct)", "expense (indirect)", "manufacturing expenses",
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


def _text(el, tag: str, default: str = "") -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else default


def _amount(el, tag: str) -> float:
    val = _text(el, tag, "0")
    val = val.replace(",", "").replace(" Cr", "").replace(" Dr", "").strip()
    try:
        return float(val) if val else 0.0
    except ValueError:
        return 0.0


def _tally_date(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%Y%m%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
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
        "is_revenue": any(g.startswith(x) or g == x for x in INCOME_GROUPS),
        "is_expense": any(g.startswith(x) or g == x for x in EXPENSE_GROUPS),
        "is_asset": any(g.startswith(x) or g == x for x in ASSET_GROUPS),
        "is_liability": any(g.startswith(x) or g == x for x in LIABILITY_GROUPS),
    }


def parse_xml(file_path: str) -> ParseResult:
    result = ParseResult()
    try:
        tree = etree.parse(file_path, etree.XMLParser(recover=True))
    except Exception as e:
        raise ValueError(f"XML parse error: {e}")

    root = tree.getroot()

    # Try to extract company/period info
    company_el = root.find(".//COMPANY")
    if company_el is not None:
        from_str = _text(company_el, "FROMDATE") or _text(company_el, "STARTINGFROM")
        to_str = _text(company_el, "TODATE") or _text(company_el, "ENDINGAT")
        result.period_from = _tally_date(from_str)
        result.period_to = _tally_date(to_str)

    # --- LEDGERS ---
    for led_el in root.iter("LEDGER"):
        name = led_el.get("NAME", "").strip() or _text(led_el, "NAME")
        if not name:
            continue
        group = _text(led_el, "PARENT") or _text(led_el, "GROUP")
        opening = _amount(led_el, "OPENINGBALANCE")
        closing = _amount(led_el, "CLOSINGBALANCE")

        # Tally uses Dr/Cr suffix for sign
        ob_raw = _text(led_el, "OPENINGBALANCE", "0")
        cb_raw = _text(led_el, "CLOSINGBALANCE", "0")
        if "Dr" in ob_raw:
            opening = abs(opening)
        elif "Cr" in ob_raw:
            opening = -abs(opening)
        if "Dr" in cb_raw:
            closing = abs(closing)
        elif "Cr" in cb_raw:
            closing = -abs(closing)

        cl = _classify_ledger(group)
        result.ledgers.append(NLedger(
            name=name,
            group_name=group,
            opening_balance=opening,
            closing_balance=closing,
            gstin=_text(led_el, "GSTREGISTRATIONNUMBER"),
            pan=_text(led_el, "INCOMETAXNUMBER"),
            address=_text(led_el, "ADDRESS"),
            tally_id=led_el.get("GUID", ""),
            **cl,
        ))

    # --- STOCK ITEMS ---
    for si_el in root.iter("STOCKITEM"):
        name = si_el.get("NAME", "").strip() or _text(si_el, "NAME")
        if not name:
            continue
        result.stock_items.append(NStockItem(
            name=name,
            group_name=_text(si_el, "PARENT"),
            unit=_text(si_el, "BASEUNITS"),
            hsn_code=_text(si_el, "HSNDETAILS.LIST.HSNCODE") or _text(si_el, "HSNCODE"),
            gst_rate=_amount(si_el, "GSTRATE"),
            opening_qty=_amount(si_el, "OPENINGBALANCE"),
            opening_value=_amount(si_el, "OPENINGVALUE"),
            closing_qty=_amount(si_el, "CLOSINGBALANCE"),
            closing_value=_amount(si_el, "CLOSINGVALUE"),
        ))

    # --- VOUCHERS ---
    dates = []
    for vch_el in root.iter("VOUCHER"):
        vtype = vch_el.get("VCHTYPE", "").strip() or _text(vch_el, "VOUCHERTYPENAME")
        if not vtype:
            continue

        date_str = _text(vch_el, "DATE") or _text(vch_el, "VOUCHERDATE")
        vdate = _tally_date(date_str)
        if not vdate:
            continue

        altered_date_str = _text(vch_el, "LASTALTEREDDATE")
        altered_date = _tally_date(altered_date_str)

        # Calculate total amount from ledger entries
        amount = 0.0
        lines = []
        for le in vch_el.iter("ALLLEDGERENTRIES.LIST"):
            lname = _text(le, "LEDGERNAME")
            lamount = _amount(le, "AMOUNT")
            is_debit = lamount > 0
            gst_type = _text(le, "GSTLEDGERTYPE") or _text(le, "TAXTYPE")
            gst_rate = _amount(le, "GSTRATE")
            if lname:
                lines.append(NVoucherLine(
                    ledger_name=lname,
                    amount=abs(lamount),
                    is_debit=is_debit,
                    gst_type=gst_type,
                    gst_rate=gst_rate,
                ))
                if is_debit:
                    amount += abs(lamount)

        if amount == 0:
            amount = abs(_amount(vch_el, "AMOUNT"))

        # Stock lines
        stock_lines = []
        for sl in vch_el.iter("INVENTORYENTRIES.LIST"):
            iname = _text(sl, "STOCKITEMNAME")
            if iname:
                qty = _amount(sl, "ACTUALQTY") or _amount(sl, "BILLEDQTY")
                rate = _amount(sl, "RATE")
                amt = _amount(sl, "AMOUNT")
                if amt == 0:
                    amt = qty * rate
                stock_lines.append(NStockLine(
                    item_name=iname,
                    qty=abs(qty),
                    rate=abs(rate),
                    amount=abs(amt),
                    godown=_text(sl, "GODOWNNAME"),
                    is_inward=vtype.lower() in ("purchase", "receipt note", "stock journal"),
                ))

        cancelled_str = _text(vch_el, "ISCANCELLED", "No")
        optional_str = _text(vch_el, "ISOPTIONAL", "No")

        voucher = NVoucher(
            voucher_type=vtype,
            date=vdate,
            amount=amount,
            voucher_number=_text(vch_el, "VOUCHERNUMBER"),
            party_ledger=_text(vch_el, "PARTYLEDGERNAME"),
            narration=_text(vch_el, "NARRATION"),
            is_cancelled=cancelled_str.lower() in ("yes", "true", "1"),
            is_optional=optional_str.lower() in ("yes", "true", "1"),
            posted_by=_text(vch_el, "ENTEREDBY") or _text(vch_el, "POSTEDBY"),
            altered_by=_text(vch_el, "LASTALTEREDBY"),
            altered_date=altered_date,
            reference=_text(vch_el, "REFERENCE"),
            gstin=_text(vch_el, "GSTREGISTRATIONNUMBER"),
            place_of_supply=_text(vch_el, "PLACEOFSUPPLY") or _text(vch_el, "STATENAME"),
            is_reverse_charge=_text(vch_el, "ISREVERSECHARGE", "No").lower() in ("yes", "true"),
            employee_name=_text(vch_el, "EMPLOYEENAME"),
            lines=lines,
            stock_lines=stock_lines,
        )
        result.vouchers.append(voucher)
        dates.append(vdate)

    if dates and not result.period_from:
        result.period_from = min(dates)
    if dates and not result.period_to:
        result.period_to = max(dates)

    return result
