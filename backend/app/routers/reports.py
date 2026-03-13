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


@router.get("/{dump_id}/vouchers")
def vouchers(
    dump_id: int,
    voucher_type: str | None = None,
    party: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_amount: float | None = None,
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
