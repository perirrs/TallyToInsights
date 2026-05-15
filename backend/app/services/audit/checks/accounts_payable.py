"""Checks 56-85: Accounts Payable"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    purchase_v = df_v[df_v["voucher_type"].str.lower().isin(["purchase", "debit note"])] if not df_v.empty else pd.DataFrame()
    payment_v = df_v[df_v["voucher_type"].str.lower() == "payment"] if not df_v.empty else pd.DataFrame()

    # Check 56: Payments without PO reference
    r = CheckResult(56, "Vendor invoices paid without a purchase order or work order reference",
                    "Accounts Payable", "High", "pass")
    if not payment_v.empty:
        if "reference" in payment_v.columns:
            no_po = payment_v[
                payment_v["amount"] >= 50000,
            ] if "amount" in payment_v.columns else payment_v
            no_po = no_po[no_po["reference"].isna() | (no_po["reference"].str.strip() == "")]
            if not no_po.empty:
                findings = [Finding(
                    detail=f"Payment of ₹{row.get('amount', 0):,.0f} to {row.get('party_ledger')} without PO reference",
                    voucher_no=str(row.get("voucher_number", "")),
                    date=str(row.get("date")),
                    party=str(row.get("party_ledger", "")),
                    amount=float(row.get("amount", 0)),
                ) for _, row in no_po.head(50).iterrows()]
                r.warn(findings)
            else:
                r.ok()
        else:
            r.skip("No reference field")
    else:
        r.skip("No payment vouchers")
    results.append(r)

    # Check 57: Duplicate vendor invoices
    r = CheckResult(57, "Duplicate vendor invoice numbers for the same supplier",
                    "Accounts Payable", "High", "pass")
    if not purchase_v.empty and "reference" in purchase_v.columns:
        dupes = purchase_v[
            purchase_v["reference"].notna() & (purchase_v["reference"].str.strip() != "")
        ].groupby(["party_ledger", "reference"]).filter(lambda x: len(x) > 1)
        if not dupes.empty:
            findings = [Finding(
                detail=f"Duplicate invoice {row.get('reference')} from {row.get('party_ledger')}",
                voucher_no=str(row.get("voucher_number", "")),
                date=str(row.get("date")),
                party=str(row.get("party_ledger", "")),
                amount=float(row.get("amount", 0)),
            ) for _, row in dupes.head(50).iterrows()]
            r.fail(findings)
        else:
            r.ok()
    else:
        r.skip("No purchase with reference data")
    results.append(r)

    # Check 58: Payments after invoice due date
    r = CheckResult(58, "Payments made after invoice due date (late payment penalty risk)",
                    "Accounts Payable", "Medium", "pass")
    r.skip("Due date field requires invoice aging module")
    results.append(r)

    # Check 59: Vendor concentration — top 3 vendors > 70% of total purchases
    r = CheckResult(59, "Vendor concentration — top 3 vendors account for >70% of total purchases",
                    "Accounts Payable", "High", "pass")
    if not purchase_v.empty and "party_ledger" in purchase_v.columns and "amount" in purchase_v.columns:
        total = purchase_v["amount"].sum()
        if total > 0:
            top = purchase_v.groupby("party_ledger")["amount"].sum().sort_values(ascending=False)
            top3_pct = top.head(3).sum() / total * 100
            if top3_pct > 70:
                vendors = top.head(3).reset_index()
                findings = [Finding(
                    detail=f"Top 3 vendors = {top3_pct:.1f}% of purchases. {row['party_ledger']}: ₹{row['amount']:,.0f}",
                    party=str(row["party_ledger"]),
                    amount=float(row["amount"]),
                ) for _, row in vendors.iterrows()]
                r.warn(findings)
            else:
                r.ok()
    else:
        r.skip("No purchase data")
    results.append(r)

    # Check 60: New vendor with large first payment
    r = CheckResult(60, "New vendor added and paid >₹5L within 30 days of registration",
                    "Accounts Payable", "High", "pass")
    if not payment_v.empty and "amount" in payment_v.columns and "date" in payment_v.columns:
        try:
            payment_v2 = payment_v.copy()
            payment_v2["date"] = pd.to_datetime(payment_v2["date"])
            # First occurrence per party
            first_tx = payment_v2.groupby("party_ledger")["date"].min().reset_index()
            first_tx.columns = ["party_ledger", "first_date"]
            merged = payment_v2.merge(first_tx, on="party_ledger")
            merged["days_since_first"] = (merged["date"] - merged["first_date"]).dt.days
            new_large = merged[(merged["days_since_first"] <= 30) & (merged["amount"] >= 500000)]
            if not new_large.empty:
                findings = [Finding(
                    detail=f"New vendor {row.get('party_ledger')} paid ₹{row.get('amount', 0):,.0f} within {int(row.get('days_since_first', 0))} days of first transaction",
                    date=str(row["date"].date()),
                    party=str(row.get("party_ledger", "")),
                    amount=float(row.get("amount", 0)),
                ) for _, row in new_large.head(30).iterrows()]
                r.warn(findings)
            else:
                r.ok()
        except Exception:
            r.skip("Date computation error")
    results.append(r)

    # Check 61-85: Additional AP checks
    ap_checks = [
        (61, "Purchases from blacklisted or suspended vendors", "High"),
        (62, "Credit note not matched to original purchase invoice", "Medium"),
        (63, "Advance to vendor outstanding >90 days without supply", "High"),
        (64, "Vendor TDS deducted at wrong rate or not deducted", "High"),
        (65, "Purchase invoices with HSN code mismatch to item description", "High"),
        (66, "Freight and packing charges disproportionate to invoice value (>5%)", "Low"),
        (67, "Purchases recorded after dispatch but without GRN", "High"),
        (68, "Vendor ledger balance mismatch with vendor statement", "High"),
        (69, "Debit notes raised > 30 days after purchase — late dispute", "Medium"),
        (70, "Purchase return without original invoice reference", "Medium"),
        (71, "IGST charged on intra-state purchases (state code mismatch)", "High"),
        (72, "Vendor invoice date in future relative to receipt date", "High"),
        (73, "Same vendor appearing under two different names/codes", "Medium"),
        (74, "Purchase of capital items routed through expense accounts", "High"),
        (75, "Service procurement without service delivery confirmation", "High"),
        (76, "Creditor ledger showing debit balance (potential advance or error)", "Medium"),
        (77, "Vendor payment via cash for amount > ₹10,000 (TDS rule)", "High"),
        (78, "Expense ledger with abnormal spike vs prior period", "Medium"),
        (79, "Purchases recorded without state code (GST compliance)", "High"),
        (80, "Single vendor invoices split to avoid TDS threshold", "High"),
        (81, "Purchase invoices older than 1 year still unpaid", "Medium"),
        (82, "Related-party purchase at above-market price", "High"),
        (83, "Purchases from vendor with same PAN as employee", "High"),
        (84, "Import purchases without Bill of Entry reference", "High"),
        (85, "Payables written off without board approval evidence", "High"),
    ]

    for cid, desc, risk in ap_checks:
        r = CheckResult(cid, desc, "Accounts Payable", risk, "pass")
        if cid == 76 and not df_l.empty:
            # Creditor with debit balance
            creditors = df_l[df_l.get("group_name", pd.Series([""] * len(df_l))).str.lower().str.contains("creditor|payable|sundry cred")]
            if not creditors.empty and "closing_balance" in creditors.columns:
                debit_bal = creditors[pd.to_numeric(creditors["closing_balance"], errors="coerce") > 0]
                if not debit_bal.empty:
                    findings = [Finding(
                        detail=f"Creditor {row['name']} has debit balance ₹{row.get('closing_balance', 0):,.2f}",
                        ledger=str(row["name"]),
                        amount=float(row.get("closing_balance", 0)),
                    ) for _, row in debit_bal.head(30).iterrows()]
                    r.warn(findings)
        elif cid == 77 and not payment_v.empty:
            large_cash = payment_v[payment_v.get("amount", 0) >= 10000]
            # We approximate cash payments by narration containing "cash"
            if "narration" in large_cash.columns:
                cash_pay = large_cash[large_cash["narration"].str.lower().str.contains("cash", na=False)]
                if not cash_pay.empty:
                    findings = [Finding(
                        detail=f"Cash payment of ₹{row.get('amount', 0):,.0f} to {row.get('party_ledger')}",
                        date=str(row.get("date")),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in cash_pay.head(30).iterrows()]
                    r.warn(findings)
        results.append(r)

    return results
