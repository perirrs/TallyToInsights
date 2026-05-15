from sqlalchemy.orm import Session
from app.models.dump import DataDump
from app.schemas.report import ComparisonReport
from app.services.reports.financial import get_financial_summary


def get_comparison_report(company_id: int, dump_ids: list[int], db: Session) -> ComparisonReport:
    periods = []
    revenue = []
    expenses = []
    net_profit = []
    gross_margin = []
    total_assets = []
    total_liabilities = []

    # Key ratios
    current_ratio = []
    debt_equity = []
    gross_margin_pct = []

    for dump_id in dump_ids:
        dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
        if not dump or dump.status != "processed":
            continue

        period_label = dump.financial_year or (
            f"{dump.period_from} → {dump.period_to}" if dump.period_from else f"Dump #{dump_id}"
        )

        try:
            fs = get_financial_summary(dump_id, db)
            periods.append(period_label)
            revenue.append(round(fs.revenue, 2))
            expenses.append(round(fs.expenses, 2))
            net_profit.append(round(fs.net_profit, 2))
            gross_margin.append(round(fs.gross_margin_pct, 2))
            total_assets.append(round(fs.total_assets, 2))
            total_liabilities.append(round(fs.total_liabilities, 2))
            gross_margin_pct.append(round(fs.gross_margin_pct, 2))
            # Approximate other ratios
            ca = fs.total_assets * 0.6
            cl = fs.total_liabilities * 0.5
            current_ratio.append(round(ca / cl, 2) if cl > 0 else 0)
            equity = fs.total_assets - fs.total_liabilities
            debt_equity.append(round(fs.total_liabilities / equity, 2) if equity > 0 else 0)
        except Exception:
            continue

    return ComparisonReport(
        company_id=company_id,
        dump_ids=dump_ids,
        periods=periods,
        revenue=revenue,
        expenses=expenses,
        net_profit=net_profit,
        gross_margin=gross_margin,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        key_ratios={
            "current_ratio": current_ratio,
            "debt_equity": debt_equity,
            "gross_margin_pct": gross_margin_pct,
        },
    )
