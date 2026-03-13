"""
Audit Engine — runs all 300 checks across 16 modules.
Loads data from DB into DataFrames and dispatches to each module.
"""
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.dump import DataDump
from app.models.voucher import Voucher, VoucherLine
from app.models.ledger import Ledger
from app.models.stock import StockItem
from app.models.audit_result import AuditResult
from app.services.audit.base import CheckResult


def _load_dataframes(dump_id: int, db: Session) -> dict:
    """Load all relevant tables into pandas DataFrames."""

    vouchers = db.query(Voucher).filter(Voucher.dump_id == dump_id).all()
    df_v = pd.DataFrame([{
        "id": v.id, "voucher_number": v.voucher_number, "voucher_type": v.voucher_type,
        "date": v.date, "party_ledger": v.party_ledger, "narration": v.narration,
        "amount": float(v.amount or 0), "is_cancelled": v.is_cancelled,
        "posted_by": v.posted_by, "altered_by": v.altered_by, "altered_date": v.altered_date,
        "reference": v.reference, "gstin": v.gstin, "place_of_supply": v.place_of_supply,
        "is_reverse_charge": v.is_reverse_charge, "employee_name": v.employee_name,
    } for v in vouchers]) if vouchers else pd.DataFrame()

    # Filter out cancelled vouchers for most checks
    if not df_v.empty and "is_cancelled" in df_v.columns:
        df_v = df_v[~df_v["is_cancelled"]]

    ledgers = db.query(Ledger).filter(Ledger.dump_id == dump_id).all()
    df_l = pd.DataFrame([{
        "id": l.id, "name": l.name, "group_name": l.group_name,
        "opening_balance": float(l.opening_balance or 0),
        "closing_balance": float(l.closing_balance or 0),
        "is_cash": l.is_cash, "is_bank": l.is_bank,
        "is_revenue": l.is_revenue, "is_expense": l.is_expense,
        "is_asset": l.is_asset, "is_liability": l.is_liability,
        "gstin": l.gstin, "pan": l.pan,
    } for l in ledgers]) if ledgers else pd.DataFrame()

    vlines = db.query(VoucherLine).filter(
        VoucherLine.voucher_id.in_([v.id for v in vouchers[:5000]])  # cap for performance
    ).all() if vouchers else []
    df_vl = pd.DataFrame([{
        "id": vl.id, "voucher_id": vl.voucher_id, "ledger_id": vl.ledger_id,
        "ledger_name": vl.ledger_name, "amount": float(vl.amount or 0),
        "is_debit": vl.is_debit, "gst_type": vl.gst_type, "gst_rate": float(vl.gst_rate or 0),
    } for vl in vlines]) if vlines else pd.DataFrame()

    stock_items = db.query(StockItem).filter(StockItem.dump_id == dump_id).all()
    df_s = pd.DataFrame([{
        "id": s.id, "name": s.name, "group_name": s.group_name,
        "unit": s.unit, "hsn_code": s.hsn_code, "gst_rate": float(s.gst_rate or 0),
        "opening_qty": float(s.opening_qty or 0), "opening_value": float(s.opening_value or 0),
        "closing_qty": float(s.closing_qty or 0), "closing_value": float(s.closing_value or 0),
    } for s in stock_items]) if stock_items else pd.DataFrame()

    return {"df_v": df_v, "df_l": df_l, "df_vl": df_vl, "df_s": df_s}


def run_audit(dump_id: int):
    db = SessionLocal()
    try:
        dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
        if not dump or dump.status != "processed":
            return

        # Clear previous audit results
        db.query(AuditResult).filter(AuditResult.dump_id == dump_id).delete()
        db.commit()

        data = _load_dataframes(dump_id, db)
        all_results: list[CheckResult] = []

        modules = [
            ("financial_integrity", "app.services.audit.checks.financial_integrity"),
            ("cash_bank", "app.services.audit.checks.cash_bank"),
            ("accounts_payable", "app.services.audit.checks.accounts_payable"),
            ("accounts_receivable", "app.services.audit.checks.accounts_receivable"),
            ("statutory_tax", "app.services.audit.checks.statutory_tax"),
            ("payroll_hr", "app.services.audit.checks.payroll_hr"),
            ("fixed_assets", "app.services.audit.checks.fixed_assets"),
            ("inventory_stock", "app.services.audit.checks.inventory_stock"),
            ("gst_forensics", "app.services.audit.checks.gst_forensics"),
            ("benfords_law", "app.services.audit.checks.benfords_law"),
            ("ratio_analysis", "app.services.audit.checks.ratio_analysis"),
            ("fraud_indicators", "app.services.audit.checks.fraud_indicators"),
            ("data_quality", "app.services.audit.checks.data_quality"),
            ("related_party", "app.services.audit.checks.related_party"),
            ("temporal_patterns", "app.services.audit.checks.temporal_patterns"),
            ("user_it_audit", "app.services.audit.checks.user_it_audit"),
        ]

        for module_name, module_path in modules:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                results: list[CheckResult] = mod.run(**data)
                all_results.extend(results)
            except Exception as e:
                # Don't let one module failure break the rest
                print(f"Audit module {module_name} failed: {e}")

        # Persist results
        now = datetime.utcnow()
        db_results = [
            AuditResult(
                dump_id=dump_id,
                check_id=r.check_id,
                check_description=r.description,
                category=r.category,
                risk_level=r.risk_level,
                status=r.status,
                finding_count=r.finding_count,
                findings=[f.to_dict() for f in r.findings],
                amount_at_risk=r.amount_at_risk,
                run_at=now,
            )
            for r in all_results
        ]

        BATCH = 100
        for i in range(0, len(db_results), BATCH):
            db.add_all(db_results[i:i + BATCH])
            db.flush()
        db.commit()

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()
