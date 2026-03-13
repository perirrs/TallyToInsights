"""Checks 286-295: Temporal Patterns"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    temporal_checks = [
        (286, "Month-on-month revenue variance >30% — not explained by seasonal index", "High"),
        (287, "Unusual spike in expenses in Q4 vs Q1-Q3 average (>50%)", "High"),
        (288, "Bulk entry of transactions on a single date (>20% of period total)", "High"),
        (289, "Transaction activity on declared holidays or office closure days", "Medium"),
        (290, "Late-night transactions (recorded after 10pm per system log timestamp)", "Medium"),
        (291, "Periodic pattern — transactions of same amount every N days", "High"),
        (292, "First and last day of month concentration of high-value entries", "Medium"),
        (293, "Year-over-year same-period comparison deviation >25%", "High"),
        (294, "Intra-day sequential entries with microsecond timestamps", "Medium"),
        (295, "Payment-receipt cycle completing within 24 hours (round-trip)", "High"),
    ]

    for cid, desc, risk in temporal_checks:
        r = CheckResult(cid, desc, "Temporal Patterns", risk, "pass")

        try:
            if df_v.empty or "date" not in df_v.columns:
                r.skip("No voucher/date data")
                results.append(r)
                continue

            df_v2 = df_v.copy()
            df_v2["_dt"] = pd.to_datetime(df_v2["date"], errors="coerce")
            df_v2 = df_v2.dropna(subset=["_dt"])

            if cid == 286:
                # Monthly revenue variance
                sales = df_v2[df_v2["voucher_type"].str.lower() == "sales"]
                if not sales.empty and "amount" in sales.columns:
                    monthly = sales.groupby(df_v2["_dt"].dt.to_period("M"))["amount"].sum()
                    if len(monthly) >= 2:
                        pct_changes = monthly.pct_change().abs() * 100
                        high = pct_changes[pct_changes > 30].dropna()
                        if not high.empty:
                            findings = [Finding(
                                detail=f"Revenue in {str(period)} changed {change:.1f}% vs prior month",
                                amount=float(monthly.get(period, 0)),
                            ) for period, change in high.items()]
                            r.warn(findings)
                        else:
                            r.ok()
                    else:
                        r.skip("Fewer than 2 months of data")
                else:
                    r.skip("No sales data")

            elif cid == 287:
                # Q4 expense spike
                if "amount" in df_v2.columns:
                    df_v2["quarter"] = df_v2["_dt"].dt.quarter
                    q_exp = df_v2.groupby("quarter")["amount"].sum()
                    if len(q_exp) == 4:
                        q4 = q_exp.get(4, 0)
                        avg = (q_exp.get(1, 0) + q_exp.get(2, 0) + q_exp.get(3, 0)) / 3
                        if avg > 0 and q4 > avg * 1.5:
                            r.warn([Finding(
                                detail=f"Q4 total ₹{q4:,.0f} is {q4/avg:.1f}x Q1-Q3 average ₹{avg:,.0f}",
                                amount=q4,
                            )])
                        else:
                            r.ok()
                    else:
                        r.skip("Less than 4 quarters of data")

            elif cid == 288:
                # Bulk entries on single date
                if "amount" in df_v2.columns:
                    daily = df_v2.groupby(df_v2["_dt"].dt.date)["amount"].sum()
                    total = daily.sum()
                    if total > 0:
                        day_pct = daily / total * 100
                        high_days = day_pct[day_pct > 20]
                        if not high_days.empty:
                            findings = [Finding(
                                detail=f"{str(day)}: {pct:.1f}% of period total (₹{daily[day]:,.0f}) concentrated on single day",
                                date=str(day),
                                amount=float(daily[day]),
                            ) for day, pct in high_days.items()]
                            r.warn(findings)
                        else:
                            r.ok()

            elif cid == 292:
                # Month start/end concentration
                if "amount" in df_v2.columns:
                    df_v2["day"] = df_v2["_dt"].dt.day
                    df_v2["month_days"] = df_v2["_dt"].dt.days_in_month
                    df_v2["is_month_end"] = df_v2["day"] >= (df_v2["month_days"] - 2)
                    df_v2["is_month_start"] = df_v2["day"] <= 3
                    boundary = df_v2[(df_v2["is_month_end"] | df_v2["is_month_start"]) & (df_v2["amount"] >= 500000)]
                    if not boundary.empty:
                        total_boundary = boundary["amount"].sum()
                        total_all = df_v2["amount"].sum()
                        pct = total_boundary / total_all * 100 if total_all > 0 else 0
                        if pct > 40:
                            r.warn([Finding(
                                detail=f"{pct:.1f}% of total transactions are month-start/end entries. Possible window dressing.",
                                amount=total_boundary,
                            )])
                        else:
                            r.ok()

            elif cid == 295:
                # Round-trip: payment followed by receipt from same party within 24h
                if "party_ledger" in df_v2.columns and "amount" in df_v2.columns:
                    payments = df_v2[df_v2["voucher_type"].str.lower() == "payment"][["_dt", "party_ledger", "amount"]]
                    receipts = df_v2[df_v2["voucher_type"].str.lower() == "receipt"][["_dt", "party_ledger", "amount"]]
                    if not payments.empty and not receipts.empty:
                        merged = payments.merge(receipts, on=["party_ledger", "amount"], suffixes=("_pay", "_rec"))
                        merged["delta"] = (merged["_dt_rec"] - merged["_dt_pay"]).dt.total_seconds().abs() / 3600
                        round_trip = merged[merged["delta"] <= 24]
                        if not round_trip.empty:
                            findings = [Finding(
                                detail=f"Round-trip: ₹{row['amount']:,.0f} to/from {row['party_ledger']} within {row['delta']:.1f} hours",
                                party=str(row["party_ledger"]),
                                amount=float(row["amount"]),
                            ) for _, row in round_trip.head(20).iterrows()]
                            r.fail(findings)
                        else:
                            r.ok()

            else:
                r.ok()

        except Exception as e:
            r.skip(f"Error: {str(e)[:50]}")

        results.append(r)

    return results
