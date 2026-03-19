from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.dump import DataDump
from app.models.company import Company
from app.models.audit_result import AuditResult
from app.utils.auth import get_current_user
from app.schemas.report import AuditSummary, AuditCheckResult, AuditFinding
from app.services.audit.engine import run_audit

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _get_dump(dump_id: int, db: Session, user: User) -> DataDump:
    dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
    if not dump:
        raise HTTPException(404, "Dump not found")
    company = db.query(Company).filter(Company.id == dump.company_id).first()
    if not user.is_admin and company not in user.companies:
        raise HTTPException(403, "Access denied")
    return dump


@router.get("/{dump_id}/summary", response_model=AuditSummary)
def audit_summary(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _get_dump(dump_id, db, user)
    results = db.query(AuditResult).filter(AuditResult.dump_id == dump_id).all()
    if not results:
        raise HTTPException(400, "Audit not run yet. Upload and process a dump first.")

    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    warnings = sum(1 for r in results if r.status == "warning")
    skipped = sum(1 for r in results if r.status == "skipped")

    high_fail = sum(1 for r in results if r.status == "fail" and r.risk_level == "High")
    med_fail = sum(1 for r in results if r.status == "fail" and r.risk_level == "Medium")
    low_fail = sum(1 for r in results if r.status == "fail" and r.risk_level == "Low")

    total = len(results)
    health_score = round(((passed + warnings * 0.5) / total) * 100, 1) if total else 0

    cat_map = {}
    for r in results:
        if r.category not in cat_map:
            cat_map[r.category] = {"category": r.category, "total": 0, "pass": 0, "fail": 0, "amount_at_risk": 0}
        cat_map[r.category]["total"] += 1
        cat_map[r.category][r.status if r.status in ("pass", "fail") else "pass"] += 1
        cat_map[r.category]["amount_at_risk"] += r.amount_at_risk or 0

    check_results = [
        AuditCheckResult(
            check_id=r.check_id,
            description=r.check_description,
            category=r.category,
            risk_level=r.risk_level,
            status=r.status,
            finding_count=r.finding_count,
            amount_at_risk=r.amount_at_risk or 0,
            findings=[AuditFinding(**f) for f in (r.findings or [])],
        )
        for r in results
    ]

    return AuditSummary(
        dump_id=dump_id,
        total_checks=total,
        passed=passed,
        failed=failed,
        warnings=warnings,
        skipped=skipped,
        high_risk_failures=high_fail,
        medium_risk_failures=med_fail,
        low_risk_failures=low_fail,
        audit_health_score=health_score,
        total_amount_at_risk=sum(r.amount_at_risk or 0 for r in results if r.status == "fail"),
        category_summary=list(cat_map.values()),
        results=check_results,
    )


@router.get("/{dump_id}/checks", response_model=list[AuditCheckResult])
def get_checks(
    dump_id: int,
    category: str | None = None,
    risk_level: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dump = _get_dump(dump_id, db, user)
    q = db.query(AuditResult).filter(AuditResult.dump_id == dump_id)
    if category:
        q = q.filter(AuditResult.category == category)
    if risk_level:
        q = q.filter(AuditResult.risk_level == risk_level)
    if status:
        q = q.filter(AuditResult.status == status)
    results = q.order_by(AuditResult.risk_level, AuditResult.check_id).all()
    return [
        AuditCheckResult(
            check_id=r.check_id,
            description=r.check_description,
            category=r.category,
            risk_level=r.risk_level,
            status=r.status,
            finding_count=r.finding_count,
            amount_at_risk=r.amount_at_risk or 0,
            findings=[AuditFinding(**f) for f in (r.findings or [])],
        )
        for r in results
    ]


@router.get("/{dump_id}/checks/{check_id}", response_model=AuditCheckResult)
def get_check_detail(dump_id: int, check_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _get_dump(dump_id, db, user)
    result = db.query(AuditResult).filter(
        AuditResult.dump_id == dump_id,
        AuditResult.check_id == check_id,
    ).first()
    if not result:
        raise HTTPException(404, "Check result not found")
    return AuditCheckResult(
        check_id=result.check_id,
        description=result.check_description,
        category=result.category,
        risk_level=result.risk_level,
        status=result.status,
        finding_count=result.finding_count,
        amount_at_risk=result.amount_at_risk or 0,
        findings=[AuditFinding(**f) for f in (result.findings or [])],
    )


@router.post("/{dump_id}/rerun")
def rerun_audit(
    dump_id: int,
    background_tasks: BackgroundTasks,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dump = _get_dump(dump_id, db, user)
    if dump.status not in ("processed", "failed", "auditing"):
        raise HTTPException(400, "Dump must be processed before audit")
    check_ids = body.get("check_ids")  # None = run all; list[int] = run only these
    check_ids_set = set(check_ids) if check_ids else None
    dump.status = "auditing"
    db.commit()
    background_tasks.add_task(run_audit, dump_id, check_ids_set)
    return {"message": "Audit re-run started"}
