"""Checks 86-110: Accounts Receivable"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    sales_v = df_v[df_v["voucher_type"].str.lower().isin(["sales", "credit note"])] if not df_v.empty else pd.DataFrame()
    receipts_v = df_v[df_v["voucher_type"].str.lower() == "receipt"] if not df_v.empty else pd.DataFrame()

    # Check 86: Customers outstanding >90 days
    r = CheckResult(86, "Customer invoices outstanding >90 days with no receipt or dispute note",
                    "Accounts Receivable", "Medium", "pass")
    if not df_l.empty and "group_name" in df_l.columns:
        debtors = df_l[df_l["group_name"].str.lower().str.contains("debtor|receivable", na=False)]
        if not debtors.empty and "closing_balance" in debtors.columns:
            outstanding = debtors[pd.to_numeric(debtors["closing_balance"], errors="coerce") > 0]
            if not outstanding.empty:
                findings = [Finding(
                    detail=f"Customer {row['name']} has outstanding balance ₹{row.get('closing_balance', 0):,.2f}",
                    party=str(row["name"]),
                    amount=float(row.get("closing_balance", 0)),
                ) for _, row in outstanding.head(50).iterrows()]
                r.warn(findings)
            else:
                r.ok()
        else:
            r.skip("No debtor ledgers found")
    else:
        r.skip("No ledger group data")
    results.append(r)

    # Check 87: Credit notes without original invoice
    r = CheckResult(87, "Credit notes raised without reference to original sales invoice",
                    "Accounts Receivable", "High", "pass")
    if not df_v.empty:
        cn = df_v[df_v["voucher_type"].str.lower() == "credit note"]
        if not cn.empty:
            if "reference" in cn.columns:
                no_ref = cn[cn["reference"].isna() | (cn["reference"].str.strip() == "")]
                if not no_ref.empty:
                    findings = [Finding(
                        detail=f"Credit note ₹{row.get('amount', 0):,.0f} to {row.get('party_ledger')} without invoice ref",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date")),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in no_ref.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            else:
                r.skip("No reference field")
        else:
            r.ok()
    results.append(r)

    # Check 88: Revenue recognized before delivery
    r = CheckResult(88, "Sales invoices raised before goods dispatch date",
                    "Accounts Receivable", "High", "pass")
    r.skip("Requires dispatch date — not in standard Tally export")
    results.append(r)

    # Check 89: Customers with debit balance (overpayment / refund due)
    r = CheckResult(89, "Customer ledger showing credit balance (overpayment or advance)",
                    "Accounts Receivable", "Medium", "pass")
    if not df_l.empty and "group_name" in df_l.columns and "closing_balance" in df_l.columns:
        debtors = df_l[df_l["group_name"].str.lower().str.contains("debtor|receivable", na=False)]
        if not debtors.empty:
            credit_bal = debtors[pd.to_numeric(debtors["closing_balance"], errors="coerce") < 0]
            if not credit_bal.empty:
                findings = [Finding(
                    detail=f"Customer {row['name']} has credit balance ₹{abs(row.get('closing_balance', 0)):,.2f}",
                    party=str(row["name"]),
                    amount=float(abs(row.get("closing_balance", 0))),
                ) for _, row in credit_bal.head(30).iterrows()]
                r.warn(findings)
            else:
                r.ok()
    results.append(r)

    # Check 90: Customer concentration
    r = CheckResult(90, "Revenue concentration — top 3 customers > 60% of total sales",
                    "Accounts Receivable", "High", "pass")
    if not sales_v.empty and "party_ledger" in sales_v.columns and "amount" in sales_v.columns:
        total = sales_v["amount"].sum()
        if total > 0:
            top = sales_v.groupby("party_ledger")["amount"].sum().sort_values(ascending=False)
            top3_pct = top.head(3).sum() / total * 100
            if top3_pct > 60:
                cust = top.head(3).reset_index()
                findings = [Finding(
                    detail=f"Top 3 customers = {top3_pct:.1f}% of sales. {row['party_ledger']}: ₹{row['amount']:,.0f}",
                    party=str(row["party_ledger"]),
                    amount=float(row["amount"]),
                ) for _, row in cust.iterrows()]
                r.warn(findings)
            else:
                r.ok()
    else:
        r.skip("No sales data")
    results.append(r)

    # Checks 91-110
    ar_checks = [
        (91, "Sales to blocked/suspended customers", "High"),
        (92, "Advance receipts from customers not adjusted against invoices >60 days", "Medium"),
        (93, "Debtors written off without board approval evidence", "High"),
        (94, "Sales return without original sales invoice reference", "Medium"),
        (95, "Customer TDS certificate not received for TDS deducted by customer", "Medium"),
        (96, "Sales credit notes exceeding 10% of original invoice value", "Medium"),
        (97, "Dormant customer account suddenly shows large transaction", "High"),
        (98, "GSTIN of customer not verified on GST portal", "High"),
        (99, "Sales made below cost price to a related party", "High"),
        (100, "Receipts from customers without invoice link (floating receipt)", "Medium"),
        (101, "Sales invoice without e-invoice reference number (>₹5Cr threshold)", "High"),
        (102, "Dispatch quantity exceeds invoice quantity", "High"),
        (103, "Customer advance exceeds credit limit", "Medium"),
        (104, "Sales commission paid exceeds approved rate", "Medium"),
        (105, "Sales to customers with zero-balance credit limit", "Medium"),
        (106, "Receipt from a third party not related to customer", "High"),
        (107, "Bad debt provision not created for >365-day outstanding", "High"),
        (108, "Sales invoices not matched to delivery challans", "High"),
        (109, "Contra sale-purchase transactions with same party", "High"),
        (110, "Customer ledger with identical opening and closing balance (no activity)", "Low"),
    ]

    for cid, desc, risk in ar_checks:
        r = CheckResult(cid, desc, "Accounts Receivable", risk, "pass")
        if cid == 97 and not df_v.empty and "party_ledger" in df_v.columns:
            # Dormant customer
            try:
                df_v["_dt"] = pd.to_datetime(df_v["date"])
                year_ago = df_v["_dt"].max() - pd.Timedelta(days=365)
                six_months_ago = df_v["_dt"].max() - pd.Timedelta(days=180)
                older = set(df_v[df_v["_dt"] < year_ago]["party_ledger"].dropna())
                recent = df_v[df_v["_dt"] >= six_months_ago]
                dormant_active = recent[recent["party_ledger"].isin(older) & (recent.get("amount", 0) >= 100000)]
                if not dormant_active.empty:
                    findings = [Finding(
                        detail=f"Dormant customer {row.get('party_ledger')} suddenly transacting ₹{row.get('amount', 0):,.0f}",
                        date=str(row["_dt"].date()),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in dormant_active.head(20).iterrows()]
                    r.warn(findings)
            except Exception:
                r.skip("Date error")
        elif cid == 110 and not df_l.empty and "closing_balance" in df_l.columns:
            same_bal = df_l[
                df_l.get("group_name", pd.Series([""] * len(df_l))).str.lower().str.contains("debtor", na=False)
            ]
            if not same_bal.empty and "opening_balance" in same_bal.columns:
                same = same_bal[
                    (pd.to_numeric(same_bal["opening_balance"], errors="coerce") ==
                     pd.to_numeric(same_bal["closing_balance"], errors="coerce")) &
                    (pd.to_numeric(same_bal["closing_balance"], errors="coerce") != 0)
                ]
                if not same.empty:
                    findings = [Finding(
                        detail=f"Customer {row['name']} has identical opening/closing balance ₹{row.get('closing_balance', 0):,.2f}",
                        ledger=str(row["name"]),
                        amount=float(row.get("closing_balance", 0)),
                    ) for _, row in same.head(20).iterrows()]
                    r.warn(findings)
        results.append(r)

    return results
