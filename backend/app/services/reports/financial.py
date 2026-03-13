from sqlalchemy.orm import Session
from app.models.ledger import Ledger
from app.models.dump import DataDump
from app.schemas.report import FinancialSummary, LedgerBalance


REVENUE_KEYWORDS = ["sales", "income", "revenue", "turnover", "direct income", "indirect income"]
EXPENSE_KEYWORDS = ["purchase", "expense", "cost", "manufacturing", "direct expense", "indirect expense"]
ASSET_KEYWORDS = ["fixed asset", "current asset", "investment", "debtor", "cash", "bank", "stock", "deposit", "loan"]
LIABILITY_KEYWORDS = ["capital", "liability", "creditor", "duty", "reserve", "provision", "loan liability"]


def _classify(group: str, keywords: list[str]) -> bool:
    g = (group or "").lower()
    return any(k in g for k in keywords)


def _to_balances(ledgers: list[Ledger], max_items: int = 20) -> list[LedgerBalance]:
    total = sum(abs(float(l.closing_balance or 0)) for l in ledgers)
    return [
        LedgerBalance(
            name=l.name,
            group=l.group_name or "",
            amount=float(l.closing_balance or 0),
            percentage=round(abs(float(l.closing_balance or 0)) / total * 100, 2) if total else 0,
        )
        for l in sorted(ledgers, key=lambda x: abs(float(x.closing_balance or 0)), reverse=True)[:max_items]
    ]


def get_financial_summary(dump_id: int, db: Session) -> FinancialSummary:
    dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
    ledgers = db.query(Ledger).filter(Ledger.dump_id == dump_id).all()

    revenue_l = [l for l in ledgers if l.is_revenue or _classify(l.group_name or "", REVENUE_KEYWORDS)]
    expense_l = [l for l in ledgers if l.is_expense or _classify(l.group_name or "", EXPENSE_KEYWORDS)]
    asset_l = [l for l in ledgers if l.is_asset or _classify(l.group_name or "", ASSET_KEYWORDS)]
    liability_l = [l for l in ledgers if l.is_liability or _classify(l.group_name or "", LIABILITY_KEYWORDS)]

    revenue = sum(abs(float(l.closing_balance or 0)) for l in revenue_l)
    expenses = sum(abs(float(l.closing_balance or 0)) for l in expense_l)
    total_assets = sum(abs(float(l.closing_balance or 0)) for l in asset_l)
    total_liabilities = sum(abs(float(l.closing_balance or 0)) for l in liability_l)

    # Approximate COGS as direct expenses/purchases
    cogs = sum(
        abs(float(l.closing_balance or 0)) for l in expense_l
        if any(k in (l.group_name or "").lower() for k in ["purchase", "direct", "cost of goods"])
    )
    gross_profit = revenue - cogs
    net_profit = revenue - expenses

    gm_pct = round(gross_profit / revenue * 100, 2) if revenue else 0
    nm_pct = round(net_profit / revenue * 100, 2) if revenue else 0
    equity = total_assets - total_liabilities

    return FinancialSummary(
        dump_id=dump_id,
        period_from=dump.period_from,
        period_to=dump.period_to,
        revenue=round(revenue, 2),
        expenses=round(expenses, 2),
        gross_profit=round(gross_profit, 2),
        net_profit=round(net_profit, 2),
        gross_margin_pct=gm_pct,
        net_margin_pct=nm_pct,
        total_assets=round(total_assets, 2),
        total_liabilities=round(total_liabilities, 2),
        equity=round(equity, 2),
        revenue_ledgers=_to_balances(revenue_l),
        expense_ledgers=_to_balances(expense_l),
        asset_ledgers=_to_balances(asset_l),
        liability_ledgers=_to_balances(liability_l),
    )
