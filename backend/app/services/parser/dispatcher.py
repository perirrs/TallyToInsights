"""
Dispatcher: routes file to the correct parser, then persists data to DB.
Uses SQLAlchemy Core bulk inserts with pre-allocated IDs for maximum throughput.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, insert as sa_insert
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
        try:
            dump2 = db.query(DataDump).filter(DataDump.id == dump_id).first()
            if dump2:
                dump2.status = "failed"
                dump2.error_message = str(e)[:1000]
                db.commit()
        except Exception:
            pass
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


def _next_id(db: Session, table: str) -> int:
    row = db.execute(text(f"SELECT MAX(id) FROM {table}")).fetchone()
    return (row[0] or 0) + 1


def _persist(result: ParseResult, dump: DataDump, db: Session):
    did = dump.id

    # ── Ledgers (bulk insert, build name→id map) ──────────────────────
    ledger_map: dict[str, int] = {}
    if result.ledgers:
        lid = _next_id(db, "ledgers")
        ledger_rows = []
        for nl in result.ledgers:
            g = nl.group_name.lower()
            ledger_rows.append({
                "id": lid,
                "dump_id": did,
                "tally_id": nl.tally_id,
                "name": nl.name,
                "group_name": nl.group_name,
                "opening_balance": nl.opening_balance,
                "closing_balance": nl.closing_balance,
                "gstin": nl.gstin,
                "pan": nl.pan,
                "address": nl.address,
                "is_bank": nl.is_bank,
                "is_cash": nl.is_cash,
                "is_revenue": _is_revenue(g),
                "is_expense": _is_expense(g),
                "is_asset": _is_asset(g),
                "is_liability": _is_liability(g),
            })
            ledger_map[nl.name.lower()] = lid
            lid += 1
        _bulk_insert(db, Ledger.__table__, ledger_rows)

    # ── Stock items ───────────────────────────────────────────────────
    stock_map: dict[str, int] = {}
    if result.stock_items:
        sid = _next_id(db, "stock_items")
        stock_rows = []
        for ns in result.stock_items:
            stock_rows.append({
                "id": sid,
                "dump_id": did,
                "name": ns.name,
                "group_name": ns.group_name,
                "unit": ns.unit,
                "hsn_code": ns.hsn_code,
                "gst_rate": ns.gst_rate,
                "opening_qty": ns.opening_qty,
                "opening_value": ns.opening_value,
                "closing_qty": ns.closing_qty,
                "closing_value": ns.closing_value,
            })
            stock_map[ns.name.lower()] = sid
            sid += 1
        _bulk_insert(db, StockItem.__table__, stock_rows)

    # ── Vouchers + lines (pre-allocated IDs, single bulk insert each) ─
    if result.vouchers:
        vid = _next_id(db, "vouchers")
        vlid = _next_id(db, "voucher_lines")
        svlid = _next_id(db, "stock_voucher_lines")

        voucher_rows = []
        line_rows = []
        stock_line_rows = []

        for nv in result.vouchers:
            amount = nv.amount
            if amount == 0 and nv.lines:
                amount = sum(l.amount for l in nv.lines if l.is_debit)

            voucher_rows.append({
                "id": vid,
                "dump_id": did,
                "voucher_number": nv.voucher_number,
                "voucher_type": nv.voucher_type,
                "date": nv.date,
                "party_ledger": nv.party_ledger,
                "narration": nv.narration,
                "amount": amount,
                "is_cancelled": nv.is_cancelled,
                "is_optional": nv.is_optional,
                "posted_by": nv.posted_by,
                "altered_by": nv.altered_by,
                "altered_date": nv.altered_date,
                "reference": nv.reference,
                "gstin": nv.gstin,
                "place_of_supply": nv.place_of_supply,
                "is_reverse_charge": nv.is_reverse_charge,
                "employee_name": nv.employee_name,
            })

            for nl in nv.lines:
                line_rows.append({
                    "id": vlid,
                    "voucher_id": vid,
                    "ledger_id": ledger_map.get(nl.ledger_name.lower()),
                    "ledger_name": nl.ledger_name,
                    "amount": nl.amount,
                    "is_debit": nl.is_debit,
                    "gst_type": nl.gst_type or None,
                    "gst_rate": nl.gst_rate or None,
                })
                vlid += 1

            for sl in nv.stock_lines:
                stock_line_rows.append({
                    "id": svlid,
                    "voucher_id": vid,
                    "stock_item_id": stock_map.get(sl.item_name.lower()),
                    "item_name": sl.item_name,
                    "qty": sl.qty,
                    "rate": sl.rate,
                    "amount": sl.amount,
                    "godown": sl.godown or None,
                    "is_inward": sl.is_inward,
                })
                svlid += 1

            vid += 1

        CHUNK = 5000  # Insert in 5K-row chunks to avoid SQLite parameter limit
        _bulk_insert(db, Voucher.__table__, voucher_rows, chunk=CHUNK)
        _bulk_insert(db, VoucherLine.__table__, line_rows, chunk=CHUNK)
        if stock_line_rows:
            _bulk_insert(db, StockVoucherLine.__table__, stock_line_rows, chunk=CHUNK)

    db.commit()


def _bulk_insert(db: Session, table, rows: list[dict], chunk: int = 5000):
    """Insert rows using SQLAlchemy Core — much faster than ORM flush per batch."""
    if not rows:
        return
    for i in range(0, len(rows), chunk):
        db.execute(sa_insert(table), rows[i: i + chunk])


def _is_revenue(g: str) -> bool:
    return any(k in g for k in ["sales", "income", "revenue", "turnover"])


def _is_expense(g: str) -> bool:
    return any(k in g for k in ["purchase", "expense", "cost", "manufacturing"])


def _is_asset(g: str) -> bool:
    return any(k in g for k in ["asset", "cash", "bank", "debtor", "stock", "deposit", "investment", "loan"])


def _is_liability(g: str) -> bool:
    return any(k in g for k in ["liability", "capital", "creditor", "duty", "tax", "reserve", "provision"])
