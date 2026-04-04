from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.dump import DataDump
from app.models.company import Company
from app.utils.auth import get_current_user
from app.services.reports.financial import get_financial_summary
from app.services.reports.cashflow import get_cash_flow_report
from app.services.reports.receivables import get_aging_report
from app.services.reports.gst import get_gst_report
from app.services.reports.comparison import get_comparison_report
from app.services.reports.dashboard import get_dashboard_kpis
from app.schemas.report import (
    FinancialSummary, CashFlowReport, AgingReport,
    GSTReport, ComparisonReport,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _get_dump(dump_id: int, db: Session, user: User) -> DataDump:
    dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
    if not dump:
        raise HTTPException(404, "Dump not found")
    if dump.status != "processed":
        raise HTTPException(400, f"Dump not ready: {dump.status}")
    company = db.query(Company).filter(Company.id == dump.company_id).first()
    if not user.is_admin and company not in user.companies:
        raise HTTPException(403, "Access denied")
    return dump


@router.get("/{dump_id}/dashboard")
def dashboard(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _get_dump(dump_id, db, user)
    return get_dashboard_kpis(dump_id, db)


@router.get("/{dump_id}/financial", response_model=FinancialSummary)
def financial(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _get_dump(dump_id, db, user)
    return get_financial_summary(dump_id, db)


@router.get("/{dump_id}/cashflow", response_model=CashFlowReport)
def cashflow(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _get_dump(dump_id, db, user)
    return get_cash_flow_report(dump_id, db)


@router.get("/{dump_id}/receivables", response_model=AgingReport)
def receivables(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _get_dump(dump_id, db, user)
    return get_aging_report(dump_id, "receivable", db)


@router.get("/{dump_id}/payables", response_model=AgingReport)
def payables(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _get_dump(dump_id, db, user)
    return get_aging_report(dump_id, "payable", db)


@router.get("/{dump_id}/gst", response_model=GSTReport)
def gst(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _get_dump(dump_id, db, user)
    return get_gst_report(dump_id, db)


@router.get("/{dump_id}/inventory")
def inventory(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.reports.inventory import get_inventory_report
    dump = _get_dump(dump_id, db, user)
    return get_inventory_report(dump_id, db)


@router.get("/{dump_id}/payroll")
def payroll(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.reports.payroll import get_payroll_report
    dump = _get_dump(dump_id, db, user)
    return get_payroll_report(dump_id, db)


@router.get("/compare/{company_id}", response_model=ComparisonReport)
def compare(
    company_id: int,
    dump_ids: list[int] = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")
    if not user.is_admin and company not in user.companies:
        raise HTTPException(403, "Access denied")
    return get_comparison_report(company_id, dump_ids, db)


def _voucher_dict(v, with_lines: bool = False) -> dict:
    d = {
        "id": v.id,
        "voucher_number": v.voucher_number,
        "voucher_type": v.voucher_type,
        "date": str(v.date),
        "party_ledger": v.party_ledger,
        "narration": v.narration,
        "amount": float(v.amount or 0),
        "is_cancelled": v.is_cancelled,
        "is_optional": v.is_optional,
        "reference": v.reference,
        "posted_by": v.posted_by,
        "altered_by": v.altered_by,
        "altered_date": str(v.altered_date) if v.altered_date else None,
        "gstin": v.gstin,
        "place_of_supply": v.place_of_supply,
        "is_reverse_charge": v.is_reverse_charge,
        "employee_name": v.employee_name,
    }
    if with_lines:
        d["lines"] = [
            {
                "ledger_name": ln.ledger_name,
                "amount": float(ln.amount or 0),
                "is_debit": ln.is_debit,
                "gst_type": ln.gst_type,
                "gst_rate": float(ln.gst_rate) if ln.gst_rate else None,
            }
            for ln in (v.lines or [])
        ]
    return d


@router.get("/{dump_id}/drill/voucher/{voucher_id}")
def drill_voucher_detail(
    dump_id: int,
    voucher_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Full voucher detail with all Dr/Cr lines."""
    dump = _get_dump(dump_id, db, user)
    from app.models.voucher import Voucher
    v = db.query(Voucher).filter(Voucher.id == voucher_id, Voucher.dump_id == dump_id).first()
    if not v:
        raise HTTPException(404, "Voucher not found")
    return _voucher_dict(v, with_lines=True)


@router.get("/{dump_id}/drill/vouchers")
def drill_vouchers(
    dump_id: int,
    ledger_name: str | None = None,
    voucher_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_amount: float | None = None,
    narration: str | None = None,
    page: int = 1,
    page_size: int = 30,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Universal drill-down: flexible voucher search used by all reports."""
    dump = _get_dump(dump_id, db, user)
    from app.models.voucher import Voucher, VoucherLine
    from sqlalchemy import or_
    from datetime import datetime as _dt

    q = db.query(Voucher).filter(Voucher.dump_id == dump_id)

    if ledger_name:
        sub = db.query(VoucherLine.voucher_id).filter(
            VoucherLine.ledger_name.ilike(f"%{ledger_name}%")
        ).scalar_subquery()
        q = q.filter(or_(
            Voucher.party_ledger.ilike(f"%{ledger_name}%"),
            Voucher.id.in_(sub),
        ))
    if voucher_type:
        q = q.filter(Voucher.voucher_type.ilike(f"%{voucher_type}%"))
    if date_from:
        q = q.filter(Voucher.date >= _dt.strptime(date_from, "%Y-%m-%d").date())
    if date_to:
        q = q.filter(Voucher.date <= _dt.strptime(date_to, "%Y-%m-%d").date())
    if min_amount:
        q = q.filter(Voucher.amount >= min_amount)
    if narration:
        q = q.filter(Voucher.narration.ilike(f"%{narration}%"))

    total = q.count()
    items = q.order_by(Voucher.date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_voucher_dict(v) for v in items],
    }


@router.get("/{dump_id}/drill/monthly-pl")
def monthly_pl(
    dump_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Month-by-month revenue vs expense trend from voucher data."""
    import calendar
    dump = _get_dump(dump_id, db, user)
    from app.models.voucher import Voucher

    vouchers = db.query(Voucher).filter(
        Voucher.dump_id == dump_id,
        Voucher.is_cancelled == False,
    ).all()

    monthly: dict[str, dict] = {}
    for v in vouchers:
        if not v.date:
            continue
        key = v.date.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"month": key, "revenue": 0.0, "expenses": 0.0}
        vtype = (v.voucher_type or "").lower()
        amt = float(v.amount or 0)
        if any(k in vtype for k in ["sales", "credit note", "direct income"]):
            monthly[key]["revenue"] += amt
        elif any(k in vtype for k in ["purchase", "debit note", "payment", "expense"]):
            monthly[key]["expenses"] += amt

    result = sorted(monthly.values(), key=lambda x: x["month"])
    for m in result:
        m["profit"] = round(m["revenue"] - m["expenses"], 2)
        m["revenue"] = round(m["revenue"], 2)
        m["expenses"] = round(m["expenses"], 2)
        y, mo = m["month"].split("-")
        m["label"] = f"{calendar.month_abbr[int(mo)]} '{y[2:]}"
    return result


@router.get("/{dump_id}/drill/gst-rates")
def gst_rate_breakdown(
    dump_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """GST breakdown by tax rate (5%, 12%, 18%, 28%) with party-wise top contributors."""
    dump = _get_dump(dump_id, db, user)
    from app.models.voucher import Voucher, VoucherLine
    from sqlalchemy import func

    v_ids = [v.id for v in db.query(Voucher.id).filter(
        Voucher.dump_id == dump_id, Voucher.is_cancelled == False
    ).all()]

    if not v_ids:
        return {"rates": [], "top_parties": []}

    # Rate-wise aggregation
    rate_rows = db.query(
        VoucherLine.gst_rate,
        VoucherLine.gst_type,
        func.sum(VoucherLine.amount).label("tax_amount"),
        func.count(VoucherLine.voucher_id.distinct()).label("voucher_count"),
    ).filter(
        VoucherLine.voucher_id.in_(v_ids),
        VoucherLine.gst_type.isnot(None),
        VoucherLine.gst_rate > 0,
    ).group_by(VoucherLine.gst_rate, VoucherLine.gst_type).all()

    # Group into rate buckets: {rate: {cgst, sgst, igst, total}}
    rate_map: dict[float, dict] = {}
    for row in rate_rows:
        rate = float(row.gst_rate or 0)
        if rate not in rate_map:
            rate_map[rate] = {"rate": rate, "cgst": 0.0, "sgst": 0.0, "igst": 0.0,
                              "total_tax": 0.0, "voucher_count": 0}
        amt = float(row.tax_amount or 0)
        gtype = (row.gst_type or "").upper()
        if gtype == "CGST":
            rate_map[rate]["cgst"] += amt
        elif gtype == "SGST":
            rate_map[rate]["sgst"] += amt
        elif gtype == "IGST":
            rate_map[rate]["igst"] += amt
        rate_map[rate]["total_tax"] += amt
        rate_map[rate]["voucher_count"] = max(rate_map[rate]["voucher_count"], row.voucher_count)

    rates = sorted(rate_map.values(), key=lambda x: x["rate"])
    for r in rates:
        # Approximate taxable amount from tax amount and rate
        r["taxable_amount"] = round(r["total_tax"] / (r["rate"] / 100), 2) if r["rate"] else 0
        r["total_tax"] = round(r["total_tax"], 2)
        r["cgst"] = round(r["cgst"], 2)
        r["sgst"] = round(r["sgst"], 2)
        r["igst"] = round(r["igst"], 2)

    # Top parties by GST (from party_ledger on vouchers with GST lines)
    from app.models.voucher import Voucher as V2
    party_rows = db.query(
        V2.party_ledger,
        func.sum(V2.amount).label("total_amount"),
        func.count(V2.id).label("voucher_count"),
    ).filter(
        V2.dump_id == dump_id,
        V2.is_cancelled == False,
        V2.voucher_type.ilike("%sales%"),
        V2.party_ledger.isnot(None),
    ).group_by(V2.party_ledger).order_by(func.sum(V2.amount).desc()).limit(15).all()

    top_parties = [
        {"party": r.party_ledger, "total_amount": round(float(r.total_amount or 0), 2),
         "voucher_count": r.voucher_count}
        for r in party_rows
    ]

    return {"rates": rates, "top_parties": top_parties}


@router.get("/{dump_id}/vouchers")
def vouchers(
    dump_id: int,
    voucher_type: str | None = None,
    party: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.voucher import Voucher
    from datetime import datetime
    dump = _get_dump(dump_id, db, user)
    q = db.query(Voucher).filter(Voucher.dump_id == dump_id)
    if voucher_type:
        q = q.filter(Voucher.voucher_type.ilike(f"%{voucher_type}%"))
    if party:
        q = q.filter(Voucher.party_ledger.ilike(f"%{party}%"))
    if date_from:
        q = q.filter(Voucher.date >= datetime.strptime(date_from, "%Y-%m-%d").date())
    if date_to:
        q = q.filter(Voucher.date <= datetime.strptime(date_to, "%Y-%m-%d").date())
    if min_amount:
        q = q.filter(Voucher.amount >= min_amount)
    if max_amount:
        q = q.filter(Voucher.amount <= max_amount)
    total = q.count()
    items = q.order_by(Voucher.date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": v.id, "voucher_number": v.voucher_number,
                "voucher_type": v.voucher_type, "date": str(v.date),
                "party_ledger": v.party_ledger, "narration": v.narration,
                "amount": float(v.amount), "is_cancelled": v.is_cancelled,
                "posted_by": v.posted_by,
            }
            for v in items
        ],
    }
