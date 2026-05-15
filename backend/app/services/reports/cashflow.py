from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.voucher import Voucher
from app.models.ledger import Ledger
from app.schemas.report import CashFlowReport, CashFlowItem


def get_cash_flow_report(dump_id: int, db: Session) -> CashFlowReport:
    # Get cash and bank ledger names
    cash_bank = db.query(Ledger).filter(
        Ledger.dump_id == dump_id,
        (Ledger.is_cash == True) | (Ledger.is_bank == True),
    ).all()
    cash_bank_names = {l.name.lower() for l in cash_bank}

    # Opening and closing balances from ledger master
    opening_balance = sum(float(l.opening_balance or 0) for l in cash_bank)
    closing_balance = sum(float(l.closing_balance or 0) for l in cash_bank)

    # All receipts and payments
    inflow_types = ["receipt", "contra"]
    outflow_types = ["payment", "contra"]

    vouchers = db.query(Voucher).filter(Voucher.dump_id == dump_id).order_by(Voucher.date).all()

    # Build daily cash flow
    daily: dict[date, dict] = {}
    total_inflow = 0.0
    total_outflow = 0.0

    for v in vouchers:
        vtype = (v.voucher_type or "").lower()
        party = (v.party_ledger or "").lower()
        amount = float(v.amount or 0)

        is_cash = party in cash_bank_names or "cash" in party or "bank" in party

        if not is_cash and vtype not in inflow_types + outflow_types:
            continue

        key = v.date
        if key not in daily:
            daily[key] = {"inflow": 0.0, "outflow": 0.0}

        if vtype == "receipt":
            daily[key]["inflow"] += amount
            total_inflow += amount
        elif vtype == "payment":
            daily[key]["outflow"] += amount
            total_outflow += amount
        elif vtype == "contra":
            daily[key]["inflow"] += amount
            daily[key]["outflow"] += amount
            total_inflow += amount
            total_outflow += amount

    # Build monthly summary
    monthly: dict[str, dict] = {}
    for d, flows in sorted(daily.items()):
        month_key = d.strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = {"month": month_key, "inflow": 0, "outflow": 0, "net": 0}
        monthly[month_key]["inflow"] += flows["inflow"]
        monthly[month_key]["outflow"] += flows["outflow"]
        monthly[month_key]["net"] = monthly[month_key]["inflow"] - monthly[month_key]["outflow"]

    # Daily items with running balance
    daily_items = []
    running = opening_balance
    for d in sorted(daily.keys()):
        inflow = daily[d]["inflow"]
        outflow = daily[d]["outflow"]
        running += inflow - outflow
        daily_items.append(CashFlowItem(
            date=d,
            description="",
            inflow=round(inflow, 2),
            outflow=round(outflow, 2),
            balance=round(running, 2),
        ))

    return CashFlowReport(
        dump_id=dump_id,
        opening_balance=round(opening_balance, 2),
        closing_balance=round(closing_balance, 2),
        total_inflow=round(total_inflow, 2),
        total_outflow=round(total_outflow, 2),
        net_flow=round(total_inflow - total_outflow, 2),
        monthly_summary=list(monthly.values()),
        daily_items=daily_items[-365:],  # last 365 days
    )
