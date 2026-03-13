"""
Dispatcher: routes file to the correct parser, then persists data to DB.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.dump import DataDump
from app.models.ledger import Ledger
from app.models.voucher import Voucher, VoucherLine
from app.models.stock import StockItem, StockVoucherLine
from app.services.parser.normalize import ParseResult, NLedger, NVoucher, NStockItem
from app.database import SessionLocal


def parse_dump(dump_id: int):
    """Entry point called by background task."""
    db = SessionLocal()
    try:
        dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
        if not dump:
            return
        dump.status = "processing"
        db.commit()

        result = _parse_file(dump.file_path, dump.file_format)
        _persist(result, dump, db)

        dump.status = "processed"
        dump.processed_at = datetime.utcnow()
        dump.voucher_count = len(result.vouchers)
        dump.ledger_count = len(result.ledgers)
        if result.period_from and not dump.period_from:
            dump.period_from = result.period_from
        if result.period_to and not dump.period_to:
            dump.period_to = result.period_to
        db.commit()

    except Exception as e:
        db.rollback()
        dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
        if dump:
            dump.status = "failed"
            dump.error_message = str(e)[:1000]
            db.commit()
        raise
    finally:
        db.close()


def _parse_file(file_path: str, fmt: str) -> ParseResult:
    if fmt == "xml":
        from app.services.parser.xml_parser import parse_xml
        return parse_xml(file_path)
    elif fmt == "excel":
        from app.services.parser.excel_parser import parse_excel
        return parse_excel(file_path)
    elif fmt == "csv":
        from app.services.parser.csv_parser import parse_csv
        return parse_csv(file_path)
    elif fmt == "json":
        from app.services.parser.json_parser import parse_json
        return parse_json(file_path)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def _persist(result: ParseResult, dump: DataDump, db: Session):
    # Build ledger name->id map for linking voucher lines
    ledger_map: dict[str, int] = {}

    # Bulk insert ledgers
    BATCH = 500
    ledger_objs = []
    for nl in result.ledgers:
        g = nl.group_name.lower()
        obj = Ledger(
            dump_id=dump.id,
            tally_id=nl.tally_id,
            name=nl.name,
            group_name=nl.group_name,
            opening_balance=nl.opening_balance,
            closing_balance=nl.closing_balance,
            gstin=nl.gstin,
            pan=nl.pan,
            address=nl.address,
            is_bank=nl.is_bank,
            is_cash=nl.is_cash,
            is_revenue=_is_revenue(g),
            is_expense=_is_expense(g),
            is_asset=_is_asset(g),
            is_liability=_is_liability(g),
        )
        ledger_objs.append(obj)
        if len(ledger_objs) >= BATCH:
            db.add_all(ledger_objs)
            db.flush()
            for o in ledger_objs:
                ledger_map[o.name.lower()] = o.id
            ledger_objs = []

    if ledger_objs:
        db.add_all(ledger_objs)
        db.flush()
        for o in ledger_objs:
            ledger_map[o.name.lower()] = o.id

    # Stock items
    stock_map: dict[str, int] = {}
    for ns in result.stock_items:
        obj = StockItem(
            dump_id=dump.id,
            name=ns.name,
            group_name=ns.group_name,
            unit=ns.unit,
            hsn_code=ns.hsn_code,
            gst_rate=ns.gst_rate,
            opening_qty=ns.opening_qty,
            opening_value=ns.opening_value,
            closing_qty=ns.closing_qty,
            closing_value=ns.closing_value,
        )
        db.add(obj)
        db.flush()
        stock_map[ns.name.lower()] = obj.id

    # Vouchers (batched)
    voucher_batch = []
    for nv in result.vouchers:
        amount = nv.amount
        if amount == 0 and nv.lines:
            amount = sum(l.amount for l in nv.lines if l.is_debit)

        vobj = Voucher(
            dump_id=dump.id,
            voucher_number=nv.voucher_number,
            voucher_type=nv.voucher_type,
            date=nv.date,
            party_ledger=nv.party_ledger,
            narration=nv.narration,
            amount=amount,
            is_cancelled=nv.is_cancelled,
            is_optional=nv.is_optional,
            posted_by=nv.posted_by,
            altered_by=nv.altered_by,
            altered_date=nv.altered_date,
            reference=nv.reference,
            gstin=nv.gstin,
            place_of_supply=nv.place_of_supply,
            is_reverse_charge=nv.is_reverse_charge,
            employee_name=nv.employee_name,
        )
        voucher_batch.append((vobj, nv))

        if len(voucher_batch) >= BATCH:
            _flush_vouchers(voucher_batch, ledger_map, stock_map, db)
            voucher_batch = []

    if voucher_batch:
        _flush_vouchers(voucher_batch, ledger_map, stock_map, db)

    db.commit()


def _flush_vouchers(batch, ledger_map, stock_map, db: Session):
    db.add_all([v for v, _ in batch])
    db.flush()
    line_objs = []
    stock_line_objs = []
    for vobj, nv in batch:
        for nl in nv.lines:
            line_objs.append(VoucherLine(
                voucher_id=vobj.id,
                ledger_id=ledger_map.get(nl.ledger_name.lower()),
                ledger_name=nl.ledger_name,
                amount=nl.amount,
                is_debit=nl.is_debit,
                gst_type=nl.gst_type or None,
                gst_rate=nl.gst_rate or None,
            ))
        for sl in nv.stock_lines:
            stock_line_objs.append(StockVoucherLine(
                voucher_id=vobj.id,
                stock_item_id=stock_map.get(sl.item_name.lower()),
                item_name=sl.item_name,
                qty=sl.qty,
                rate=sl.rate,
                amount=sl.amount,
                godown=sl.godown or None,
                is_inward=sl.is_inward,
            ))
    if line_objs:
        db.add_all(line_objs)
    if stock_line_objs:
        db.add_all(stock_line_objs)
    db.flush()


def _is_revenue(g: str) -> bool:
    return any(k in g for k in ["sales", "income", "revenue", "turnover"])


def _is_expense(g: str) -> bool:
    return any(k in g for k in ["purchase", "expense", "cost", "manufacturing"])


def _is_asset(g: str) -> bool:
    return any(k in g for k in ["asset", "cash", "bank", "debtor", "stock", "deposit", "investment", "loan"])


def _is_liability(g: str) -> bool:
    return any(k in g for k in ["liability", "capital", "creditor", "duty", "tax", "reserve", "provision"])
