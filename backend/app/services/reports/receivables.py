from datetime import date
from sqlalchemy.orm import Session
from app.models.ledger import Ledger
from app.models.voucher import Voucher
from app.schemas.report import AgingReport, AgingBucket


def get_aging_report(dump_id: int, report_type: str, db: Session) -> AgingReport:
    """report_type: 'receivable' or 'payable'"""

    if report_type == "receivable":
        group_keywords = ["debtor", "receivable", "sundry debtor"]
    else:
        group_keywords = ["creditor", "payable", "sundry creditor"]

    ledgers = db.query(Ledger).filter(Ledger.dump_id == dump_id).all()
    party_ledgers = [
        l for l in ledgers
        if any(k in (l.group_name or "").lower() for k in group_keywords)
    ]

    if not party_ledgers:
        return AgingReport(
            dump_id=dump_id, report_type=report_type,
            total_outstanding=0, overdue_amount=0, buckets=[],
        )

    today = db.query(Voucher).filter(Voucher.dump_id == dump_id).order_by(Voucher.date.desc()).first()
    ref_date = today.date if today else date.today()

    vouchers = db.query(Voucher).filter(Voucher.dump_id == dump_id).all()
    party_names = {l.name for l in party_ledgers}

    # Build party-wise outstanding using closing balance from ledger master
    # (simplified: use closing balance + approximate aging by last transaction date)
    party_data: dict[str, dict] = {}
    for l in party_ledgers:
        bal = float(l.closing_balance or 0)
        if abs(bal) < 0.01:
            continue
        party_data[l.name] = {
            "balance": abs(bal),
            "last_date": None,
        }

    # Find last transaction date per party
    for v in vouchers:
        party = v.party_ledger
        if party in party_data:
            if party_data[party]["last_date"] is None or v.date > party_data[party]["last_date"]:
                party_data[party]["last_date"] = v.date

    buckets = []
    total_outstanding = 0.0
    overdue_amount = 0.0

    for name, data in party_data.items():
        bal = data["balance"]
        last = data["last_date"]

        if last is None:
            days_old = 999
        else:
            days_old = (ref_date - last).days

        current = days_1_30 = days_31_60 = days_61_90 = days_90_plus = 0.0

        if days_old <= 0:
            current = bal
        elif days_old <= 30:
            days_1_30 = bal
        elif days_old <= 60:
            days_31_60 = bal
        elif days_old <= 90:
            days_61_90 = bal
        else:
            days_90_plus = bal

        overdue = days_31_60 + days_61_90 + days_90_plus
        total_outstanding += bal
        overdue_amount += overdue

        buckets.append(AgingBucket(
            party=name,
            current=current,
            days_1_30=days_1_30,
            days_31_60=days_31_60,
            days_61_90=days_61_90,
            days_90_plus=days_90_plus,
            total=bal,
            oldest_date=last,
        ))

    buckets.sort(key=lambda b: b.total, reverse=True)

    return AgingReport(
        dump_id=dump_id,
        report_type=report_type,
        total_outstanding=round(total_outstanding, 2),
        overdue_amount=round(overdue_amount, 2),
        buckets=buckets[:200],  # top 200 parties
    )
