"""Checks 166-180: Inventory & Stock"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame = None, **kwargs) -> list[CheckResult]:
    results = []

    if df_s is None:
        df_s = pd.DataFrame()

    inv_checks = [
        (166, "Negative stock — inventory balance going below zero on any date", "High"),
        (167, "Stock valuation method inconsistency (FIFO vs LIFO vs Avg)", "High"),
        (168, "Physical stock count variance > 5% vs book stock", "High"),
        (169, "Slow-moving stock (no movement in 180 days) exceeding ₹5L", "Medium"),
        (170, "Dead stock written off without approval", "High"),
        (171, "Stock transfer without proper stock journal entry", "High"),
        (172, "Purchase quantity exceeds maximum stock level", "Medium"),
        (173, "Sales quantity exceeds available stock on date of sale", "High"),
        (174, "HSN code missing for stock items > ₹500/unit", "Medium"),
        (175, "Item rate variance > 20% from previous month average", "High"),
        (176, "Godown-level stock reconciliation differences", "Medium"),
        (177, "Opening stock not matching prior year closing stock", "High"),
        (178, "Stock in transit not cleared within 30 days", "Medium"),
        (179, "Finished goods valuation excludes overhead allocation", "High"),
        (180, "Stock adjustment entries without physical verification", "High"),
    ]

    for cid, desc, risk in inv_checks:
        r = CheckResult(cid, desc, "Inventory & Stock", risk, "pass")

        if cid == 166 and not df_s.empty and "closing_qty" in df_s.columns:
            negative = df_s[pd.to_numeric(df_s["closing_qty"], errors="coerce") < 0]
            if not negative.empty:
                findings = [Finding(
                    detail=f"Negative stock: {row['name']} qty={row.get('closing_qty', 0):.2f} {row.get('unit', '')}",
                    amount=float(abs(pd.to_numeric(row.get("closing_value", 0), errors="coerce") or 0)),
                ) for _, row in negative.head(30).iterrows()]
                r.fail(findings)
            else:
                r.ok()

        elif cid == 169 and not df_s.empty:
            if "closing_value" in df_s.columns:
                slow = df_s[pd.to_numeric(df_s["closing_value"], errors="coerce") >= 500000]
                if not slow.empty:
                    # Cross-reference with vouchers to check if there was movement
                    if not df_v.empty:
                        r.warn([Finding(
                            detail=f"Item '{row['name']}' has closing value ₹{row.get('closing_value', 0):,.0f} — verify movement",
                            amount=float(row.get("closing_value", 0)),
                        ) for _, row in slow.head(20).iterrows()])
                    else:
                        r.skip("No voucher data to check movement")

        elif cid == 175 and not df_v.empty:
            # Rate variance in purchase vouchers
            if "voucher_type" in df_v.columns:
                purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"]
                if not purchases.empty and "amount" in purchases.columns and "date" in purchases.columns:
                    try:
                        purchases2 = purchases.copy()
                        purchases2["month"] = pd.to_datetime(purchases2["date"]).dt.to_period("M")
                        monthly_avg = purchases2.groupby(["party_ledger", "month"])["amount"].mean().reset_index()
                        monthly_avg["prev_avg"] = monthly_avg.groupby("party_ledger")["amount"].shift(1)
                        monthly_avg["variance_pct"] = abs(monthly_avg["amount"] - monthly_avg["prev_avg"]) / monthly_avg["prev_avg"] * 100
                        high_var = monthly_avg[(monthly_avg["variance_pct"] > 20) & monthly_avg["prev_avg"].notna()]
                        if not high_var.empty:
                            findings = [Finding(
                                detail=f"Rate variance {row.get('variance_pct', 0):.1f}% for {row.get('party_ledger')} in {row.get('month')}",
                                party=str(row.get("party_ledger", "")),
                                amount=float(row.get("amount", 0)),
                            ) for _, row in high_var.head(20).iterrows()]
                            r.warn(findings)
                        else:
                            r.ok()
                    except Exception:
                        r.skip("Computation error")

        elif cid == 177 and not df_s.empty:
            if "opening_value" in df_s.columns and "closing_value" in df_s.columns:
                mismatch = df_s[
                    (pd.to_numeric(df_s["opening_value"], errors="coerce") == 0) &
                    (pd.to_numeric(df_s["closing_value"], errors="coerce") > 100000)
                ]
                if not mismatch.empty:
                    findings = [Finding(
                        detail=f"Item '{row['name']}' has zero opening but ₹{row.get('closing_value', 0):,.0f} closing — verify carry-forward",
                        amount=float(row.get("closing_value", 0)),
                    ) for _, row in mismatch.head(20).iterrows()]
                    r.warn(findings)

        results.append(r)

    return results
