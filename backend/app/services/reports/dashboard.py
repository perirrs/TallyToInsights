from sqlalchemy.orm import Session
from app.models.voucher import Voucher
from app.models.ledger import Ledger
from app.models.audit_result import AuditResult
from app.models.dump import DataDump


def get_dashboard_kpis(dump_id: int, db: Session) -> dict:
    dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
    vouchers = db.query(Voucher).filter(Voucher.dump_id == dump_id).all()
    ledgers = db.query(Ledger).filter(Ledger.dump_id == dump_id).all()
    audit_results = db.query(AuditResult).filter(AuditResult.dump_id == dump_id).all()

    total_vouchers = len(vouchers)
    total_ledgers = len(ledgers)

    # Revenue and expense from ledgers
    revenue = sum(abs(float(l.closing_balance or 0)) for l in ledgers if l.is_revenue)
    expenses = sum(abs(float(l.closing_balance or 0)) for l in ledgers if l.is_expense)
    net_profit = revenue - expenses

    # Cash position
    cash_bank = sum(float(l.closing_balance or 0) for l in ledgers if l.is_cash or l.is_bank)

    # Receivables / Payables
    receivables = sum(abs(float(l.closing_balance or 0)) for l in ledgers
                     if any(k in (l.group_name or "").lower() for k in ["debtor", "receivable"]))
    payables = sum(abs(float(l.closing_balance or 0)) for l in ledgers
                  if any(k in (l.group_name or "").lower() for k in ["creditor", "payable"]))

    # Audit summary
    audit_total = len(audit_results)
    audit_fail = sum(1 for r in audit_results if r.status == "fail")
    audit_high = sum(1 for r in audit_results if r.status == "fail" and r.risk_level == "High")
    audit_score = round(((audit_total - audit_fail) / audit_total) * 100, 1) if audit_total else 100
    amount_at_risk = sum(r.amount_at_risk or 0 for r in audit_results if r.status == "fail")

    # Monthly revenue trend
    monthly_revenue: dict[str, float] = {}
    for v in vouchers:
        if v.voucher_type and v.voucher_type.lower() == "sales" and v.date:
            key = v.date.strftime("%Y-%m")
            monthly_revenue[key] = monthly_revenue.get(key, 0) + float(v.amount or 0)

    # Voucher type breakdown
    vtype_counts: dict[str, int] = {}
    for v in vouchers:
        vt = v.voucher_type or "Other"
        vtype_counts[vt] = vtype_counts.get(vt, 0) + 1

    # Top issues
    top_issues = sorted(
        [r for r in audit_results if r.status == "fail"],
        key=lambda r: (r.risk_level == "High", r.amount_at_risk or 0),
        reverse=True,
    )[:5]

    return {
        "dump_id": dump_id,
        "period_from": str(dump.period_from) if dump.period_from else None,
        "period_to": str(dump.period_to) if dump.period_to else None,
        "financial_year": dump.financial_year,
        "total_vouchers": total_vouchers,
        "total_ledgers": total_ledgers,
        "revenue": round(revenue, 2),
        "expenses": round(expenses, 2),
        "net_profit": round(net_profit, 2),
        "net_margin_pct": round(net_profit / revenue * 100, 2) if revenue else 0,
        "cash_position": round(cash_bank, 2),
        "receivables": round(receivables, 2),
        "payables": round(payables, 2),
        "audit_health_score": audit_score,
        "audit_total_checks": audit_total,
        "audit_failures": audit_fail,
        "audit_high_risk": audit_high,
        "amount_at_risk": round(amount_at_risk, 2),
        "monthly_revenue": [
            {"month": k, "revenue": round(v, 2)}
            for k, v in sorted(monthly_revenue.items())
        ],
        "voucher_breakdown": [
            {"type": k, "count": v}
            for k, v in sorted(vtype_counts.items(), key=lambda x: -x[1])
        ],
        "top_issues": [
            {
                "check_id": r.check_id,
                "description": r.check_description,
                "category": r.category,
                "risk_level": r.risk_level,
                "finding_count": r.finding_count,
                "amount_at_risk": r.amount_at_risk,
            }
            for r in top_issues
        ],
    }
