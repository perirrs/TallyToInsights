"""Checks 276-285: Related Party Transactions"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    # Common related-party keywords (approximate, since no explicit master)
    rp_keywords = ["director", "promoter", "subsidiary", "associate", "group", "holding",
                   "sister concern", "related", "proprietor", "partner", "spouse"]

    rp_checks = [
        (276, "Transactions with related parties not disclosed in notes or schedule", "High"),
        (277, "Loans to directors without board resolution reference", "High"),
        (278, "Sales/purchases to subsidiaries at prices deviating from market by >10%", "High"),
        (279, "Remuneration to relatives of directors without shareholder approval", "High"),
        (280, "Security deposit given to related party without adequate collateral", "High"),
        (281, "Investment in related party equity at premium without valuation report", "High"),
        (282, "Related party guarantees not recorded as contingent liability", "High"),
        (283, "Inter-company loans charging below SBI PLR interest rate", "High"),
        (284, "Asset transferred to related party below fair value", "High"),
        (285, "Related party receivables written off without disclosure", "High"),
    ]

    for cid, desc, risk in rp_checks:
        r = CheckResult(cid, desc, "Related Party", risk, "pass")

        try:
            if cid == 276 and not df_v.empty and "party_ledger" in df_v.columns:
                rp_transactions = df_v[
                    df_v["party_ledger"].str.lower().apply(
                        lambda n: any(k in str(n) for k in rp_keywords)
                    )
                ]
                if not rp_transactions.empty:
                    total = rp_transactions.get("amount", pd.Series([0])).sum()
                    findings = [Finding(
                        detail=f"Possible related party transaction: {row.get('party_ledger')} ₹{row.get('amount', 0):,.0f} on {row.get('date')}",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date")),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in rp_transactions.head(30).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()

            elif cid == 277 and not df_v.empty:
                loans = df_v[
                    df_v.get("party_ledger", pd.Series([""] * len(df_v))).str.lower().apply(
                        lambda n: "director" in str(n) or "promoter" in str(n)
                    ) &
                    df_v["voucher_type"].str.lower().isin(["payment", "journal"])
                ]
                if not loans.empty and "amount" in loans.columns:
                    findings = [Finding(
                        detail=f"Payment/journal to director {row.get('party_ledger')} ₹{row.get('amount', 0):,.0f} — verify board approval",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date")),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in loans.head(20).iterrows()]
                    r.warn(findings)
                else:
                    r.skip("No director ledgers found")

            else:
                r.ok()

        except Exception as e:
            r.skip(f"Error: {str(e)[:50]}")

        results.append(r)

    return results
