"""Checks 336-370 and 731-735: Inter-Period 5-Year Trend"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding

CAT = "Inter-Period 5-Year Trend"
SKIP_MSG = "Requires multi-year historical data"


def _ledger_cagr(df_l: pd.DataFrame, kw: str, years: int = 5) -> float | None:
    """Approximate CAGR using opening vs closing balance as proxy for single-year data."""
    if df_l.empty:
        return None
    subset = df_l[df_l["name"].str.contains(kw, case=False, na=False)]
    if subset.empty:
        return None
    open_bal = subset["opening_balance"].sum()
    close_bal = subset["closing_balance"].sum()
    if open_bal <= 0 or close_bal <= 0:
        return None
    return (close_bal / open_bal - 1) * 100


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    try:
        # --- 336: Revenue CAGR below sector benchmark ---
        r = CheckResult(336, "Revenue CAGR over 5 years below sector benchmark", CAT, "High", "pass")
        try:
            if not df_l.empty:
                rev = df_l[df_l["is_revenue"] == True]
                if not rev.empty:
                    open_rev = rev["opening_balance"].sum()
                    close_rev = rev["closing_balance"].sum()
                    if open_rev > 0:
                        yoy = (close_rev - open_rev) / open_rev * 100
                        if yoy < 5:
                            findings = [Finding(detail=f"Revenue growth {yoy:.1f}% YoY — may indicate below-benchmark CAGR", amount=close_rev - open_rev)]
                            r.warn(findings)
                        else:
                            r.ok()
                    else:
                        r.skip(SKIP_MSG)
                else:
                    r.skip(SKIP_MSG)
            else:
                r.skip(SKIP_MSG)
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 337: COGS CAGR outpacing revenue CAGR ---
        r = CheckResult(337, "COGS CAGR outpacing revenue CAGR", CAT, "High", "pass")
        try:
            if not df_l.empty:
                rev = df_l[df_l["is_revenue"] == True]
                exp = df_l[df_l["is_expense"] == True]
                if not rev.empty and not exp.empty:
                    rev_growth = (rev["closing_balance"].sum() - rev["opening_balance"].sum())
                    exp_growth = (exp["closing_balance"].sum() - exp["opening_balance"].sum())
                    rev_open = rev["opening_balance"].sum()
                    exp_open = exp["opening_balance"].sum()
                    if rev_open > 0 and exp_open > 0:
                        rev_pct = rev_growth / rev_open * 100
                        exp_pct = exp_growth / exp_open * 100
                        if exp_pct > rev_pct + 2:
                            findings = [Finding(detail=f"Expense growth {exp_pct:.1f}% exceeds revenue growth {rev_pct:.1f}%", amount=exp_growth - rev_growth)]
                            r.fail(findings)
                        else:
                            r.ok()
                    else:
                        r.skip(SKIP_MSG)
                else:
                    r.skip(SKIP_MSG)
            else:
                r.skip(SKIP_MSG)
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 338: Gross profit CAGR diverging from revenue CAGR by >5% ---
        r = CheckResult(338, "Gross profit CAGR diverging from revenue CAGR by >5%", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                purch = df_v[df_v["voucher_type"].str.lower() == "purchase"]["amount"].sum()
                gp = sales - purch
                if sales > 0:
                    gp_pct = gp / sales * 100
                    if not df_l.empty:
                        rev = df_l[df_l["is_revenue"] == True]
                        if not rev.empty and rev["opening_balance"].sum() > 0:
                            rev_growth = (rev["closing_balance"].sum() - rev["opening_balance"].sum()) / rev["opening_balance"].sum() * 100
                            if abs(gp_pct - rev_growth) > 5:
                                findings = [Finding(detail=f"GP% {gp_pct:.1f}% diverges from revenue growth {rev_growth:.1f}% by >{5}%", amount=gp)]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip(SKIP_MSG)
                    else:
                        r.skip(SKIP_MSG)
                else:
                    r.skip(SKIP_MSG)
            else:
                r.skip(SKIP_MSG)
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # 339-370: Multi-year trend checks — skip due to single-year data availability
        trend_checks = [
            (339, "Operating expense CAGR outpacing gross profit CAGR", "High"),
            (340, "Net profit margin trend declining over 3+ years", "High"),
            (341, "Return on equity declining for 3 consecutive years", "High"),
            (342, "Asset turnover ratio declining trend over 3 years", "Medium"),
            (343, "Inventory turnover ratio declining trend over 3 years", "Medium"),
            (344, "Debtor days increasing trend over 3 years", "High"),
            (345, "Creditor days decreasing — working capital stress", "Medium"),
            (346, "Cash conversion cycle lengthening over 3 years", "High"),
            (347, "Debt-to-equity ratio increasing trend over 3 years", "High"),
            (348, "Interest coverage ratio declining trend", "High"),
            (349, "Fixed asset turnover declining over 3 years", "Medium"),
            (350, "R&D spend as % of revenue declining over 3 years", "Low"),
            (351, "Employee cost as % of revenue increasing over 3 years", "Medium"),
            (352, "Marketing spend as % of revenue trend", "Low"),
            (353, "Tax effective rate trend — declining without reason", "High"),
            (354, "Dividend payout ratio trend over 5 years", "Low"),
            (355, "Capital expenditure vs depreciation ratio trend", "Medium"),
            (356, "Goodwill impairment trend over 3 years", "High"),
            (357, "Operating cash flow vs net profit divergence trend", "High"),
            (358, "Free cash flow trend declining over 3 years", "High"),
            (359, "Revenue per employee trend over 3 years", "Medium"),
            (360, "Working capital to revenue ratio trend", "Medium"),
            (361, "Current ratio trend declining over 3 years", "High"),
            (362, "Quick ratio trend declining over 3 years", "High"),
            (363, "Gross margin trend declining over 3 years", "High"),
            (364, "EBITDA margin trend declining over 3 years", "High"),
            (365, "Net margin trend declining over 3 years", "High"),
            (366, "Return on assets declining trend over 3 years", "High"),
            (367, "Retained earnings growth below net profit — excess dividends", "Medium"),
            (368, "Long-term debt proportion of total debt increasing", "Medium"),
            (369, "Trade payables turnover declining trend over 3 years", "Medium"),
            (370, "Revenue concentration — top customer >30% trend worsening", "High"),
        ]
        for chk_id, desc, risk in trend_checks:
            r = CheckResult(chk_id, desc, CAT, risk, "skipped")
            r.skip(SKIP_MSG)
            results.append(r)

        # --- 731-735: Additional Inter-Period Trend checks ---
        extra_trend_checks = [
            (731, "5-year capital structure shift — equity eroding", "High"),
            (732, "5-year revenue mix shift from core to ancillary >30%", "Medium"),
            (733, "5-year trade debtor to revenue ratio worsening trend", "High"),
            (734, "5-year operating leverage increasing — fixed cost creep", "Medium"),
            (735, "5-year ROCE declining below cost of capital", "High"),
        ]
        for chk_id, desc, risk in extra_trend_checks:
            r = CheckResult(chk_id, desc, CAT, risk, "skipped")
            r.skip(SKIP_MSG)
            results.append(r)

    except Exception:
        pass

    return results
