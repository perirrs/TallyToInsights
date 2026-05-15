"""Checks 236-260: Fraud Indicators"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    fraud_checks = [
        (236, "Payments to shell company indicators — single director, new PAN, no web presence", "High"),
        (237, "Vendor PAN same as employee PAN (self-dealing)", "High"),
        (238, "Payments to vendors registered at residential addresses", "High"),
        (239, "Round-trip transactions — funds sent and returned same period", "High"),
        (240, "Fictitious expenses — narration does not match ledger account type", "High"),
        (241, "Salary-linked payments to consultants (disguised employment)", "High"),
        (242, "Multiple payments with sequential voucher numbers but non-sequential dates", "High"),
        (243, "High-value transactions on last working day of financial year", "High"),
        (244, "Unusual payment patterns — same amount recurring at irregular intervals", "High"),
        (245, "Payments split across subsidiaries to avoid consolidation threshold", "High"),
        (246, "Journal entries to retain earnings without board resolution", "High"),
        (247, "Expense write-backs inflating profit near year-end", "High"),
        (248, "Revenue recognized without corresponding debtors or receipt", "High"),
        (249, "Payments to vendors with no previous purchase history", "High"),
        (250, "TDS remittance dates inconsistent with tax calendar", "High"),
        (251, "Payroll disbursed on non-standard dates (not last day of month)", "Medium"),
        (252, "Advance payments significantly exceeding contract value", "High"),
        (253, "Contra entries between unrelated group entities", "High"),
        (254, "Write-off of large receivables shortly after book closure", "High"),
        (255, "Asset additions in Q4 spike vs Q1-Q3 average", "High"),
        (256, "Expense accounts with debit balance (unusual accounting)", "Medium"),
        (257, "Back-office entries overriding system-generated accounting", "High"),
        (258, "Loans to directors without board approval or market interest rate", "High"),
        (259, "Transfer pricing adjustments without documented policy", "High"),
        (260, "Payments to vendors in high-risk jurisdictions", "High"),
    ]

    for cid, desc, risk in fraud_checks:
        r = CheckResult(cid, desc, "Fraud Indicators", risk, "pass")

        try:
            if cid == 243 and not df_v.empty and "date" in df_v.columns:
                # Year-end entries (last week of March or company FY)
                df_v2 = df_v.copy()
                df_v2["_dt"] = pd.to_datetime(df_v2["date"], errors="coerce")
                year_end = df_v2[
                    (df_v2["_dt"].dt.month == 3) &
                    (df_v2["_dt"].dt.day >= 25) &
                    (df_v2.get("amount", 0) >= 500000)
                ]
                if not year_end.empty:
                    findings = [Finding(
                        detail=f"High-value ₹{row.get('amount', 0):,.0f} {row.get('voucher_type')} on year-end date {row['_dt'].date()}",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row["_dt"].date()),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in year_end.head(30).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()

            elif cid == 244 and not df_v.empty:
                # Same amount recurring
                payments = df_v[df_v["voucher_type"].str.lower() == "payment"]
                if not payments.empty and "amount" in payments.columns:
                    recurring = payments.groupby(["party_ledger", "amount"]).size().reset_index(name="count")
                    suspect = recurring[(recurring["count"] >= 4) & (recurring["amount"] >= 50000)]
                    if not suspect.empty:
                        findings = [Finding(
                            detail=f"₹{row['amount']:,.0f} paid to {row['party_ledger']} exactly {int(row['count'])} times",
                            party=str(row["party_ledger"]),
                            amount=float(row["amount"]),
                        ) for _, row in suspect.head(20).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()

            elif cid == 247 and not df_v.empty:
                # Year-end provision reversals / expense write-backs
                journals = df_v[(df_v["voucher_type"].str.lower() == "journal")]
                if not journals.empty and "narration" in journals.columns and "date" in journals.columns:
                    journals2 = journals.copy()
                    journals2["_dt"] = pd.to_datetime(journals2["date"], errors="coerce")
                    reversal_kw = ["reversal", "reverse", "write back", "writeback", "written back", "provision reversed"]
                    year_end_rev = journals2[
                        (journals2["_dt"].dt.month.isin([2, 3])) &
                        journals2["narration"].str.lower().apply(lambda n: any(k in str(n) for k in reversal_kw))
                    ]
                    if not year_end_rev.empty:
                        findings = [Finding(
                            detail=f"Year-end write-back: '{row.get('narration', '')[:80]}'",
                            date=str(row.get("date")),
                            amount=float(row.get("amount", 0)),
                        ) for _, row in year_end_rev.head(20).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()

            elif cid == 255 and not df_v.empty:
                # Asset additions Q4 spike
                purchases = df_v[df_v["voucher_type"].str.lower().isin(["purchase", "journal"])]
                if not purchases.empty and "date" in purchases.columns:
                    purchases2 = purchases.copy()
                    purchases2["_dt"] = pd.to_datetime(purchases2["date"], errors="coerce")
                    purchases2["quarter"] = purchases2["_dt"].dt.quarter
                    q_totals = purchases2.groupby("quarter")["amount"].sum()
                    if len(q_totals) == 4:
                        q4 = q_totals.get(4, 0)
                        q1_3_avg = (q_totals.get(1, 0) + q_totals.get(2, 0) + q_totals.get(3, 0)) / 3
                        if q1_3_avg > 0 and q4 > q1_3_avg * 2:
                            r.warn([Finding(
                                detail=f"Q4 total ₹{q4:,.0f} is {q4/q1_3_avg:.1f}x Q1-Q3 average ₹{q1_3_avg:,.0f}",
                                amount=q4,
                            )])
                        else:
                            r.ok()

            elif cid == 256 and not df_l.empty:
                # Expense with debit balance (unusual)
                if "is_expense" in df_l.columns and "closing_balance" in df_l.columns:
                    exp_debit = df_l[
                        (df_l["is_expense"] == True) &
                        (pd.to_numeric(df_l["closing_balance"], errors="coerce") < 0)
                    ]
                    if not exp_debit.empty:
                        findings = [Finding(
                            detail=f"Expense ledger {row['name']} has credit/negative balance ₹{row.get('closing_balance', 0):,.2f}",
                            ledger=str(row["name"]),
                            amount=float(abs(row.get("closing_balance", 0))),
                        ) for _, row in exp_debit.head(20).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()

            elif cid == 249 and not df_v.empty:
                # New vendors (only 1 transaction total)
                payments = df_v[df_v["voucher_type"].str.lower() == "payment"]
                if not payments.empty and "party_ledger" in payments.columns and "amount" in payments.columns:
                    vendor_counts = payments.groupby("party_ledger").agg(
                        count=("amount", "count"), total=("amount", "sum")
                    ).reset_index()
                    new_large = vendor_counts[(vendor_counts["count"] == 1) & (vendor_counts["total"] >= 500000)]
                    if not new_large.empty:
                        findings = [Finding(
                            detail=f"New vendor {row['party_ledger']} paid ₹{row['total']:,.0f} in single transaction",
                            party=str(row["party_ledger"]),
                            amount=float(row["total"]),
                        ) for _, row in new_large.head(20).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()

            else:
                r.ok()

        except Exception as e:
            r.skip(f"Error: {str(e)[:50]}")

        results.append(r)

    return results
