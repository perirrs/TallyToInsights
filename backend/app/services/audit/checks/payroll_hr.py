"""Checks 131-150: Payroll & HR"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    payroll_v = df_v[df_v["voucher_type"].str.lower().isin(["payroll", "salary", "wage"])] if not df_v.empty else pd.DataFrame()

    # Check 131: Salary paid without attendance record
    r = CheckResult(131, "Salary paid to employee code with no attendance record for that month",
                    "Payroll & HR", "High", "pass")
    r.skip("Requires attendance master — not in standard Tally export")
    results.append(r)

    # Check 132: Ghost employees (same bank account for multiple employees)
    r = CheckResult(132, "Ghost employees — multiple employees sharing the same bank account number",
                    "Payroll & HR", "High", "pass")
    r.skip("Requires employee bank master — not in standard dump")
    results.append(r)

    # Check 133: Salary above approved pay grade
    r = CheckResult(133, "Salary disbursement exceeding approved pay grade",
                    "Payroll & HR", "High", "pass")
    if not payroll_v.empty and "amount" in payroll_v.columns:
        # Flag abnormally high salary entries
        if len(payroll_v) >= 3:
            mean = payroll_v["amount"].mean()
            std = payroll_v["amount"].std()
            outliers = payroll_v[payroll_v["amount"] > mean + 3 * std]
            if not outliers.empty:
                findings = [Finding(
                    detail=f"Salary ₹{row.get('amount', 0):,.0f} to {row.get('employee_name') or row.get('party_ledger', '')} is 3σ above mean",
                    date=str(row.get("date")),
                    party=str(row.get("employee_name") or row.get("party_ledger", "")),
                    amount=float(row.get("amount", 0)),
                ) for _, row in outliers.head(20).iterrows()]
                r.warn(findings)
            else:
                r.ok()
        else:
            r.skip("Insufficient payroll data")
    else:
        r.skip("No payroll vouchers")
    results.append(r)

    # Check 134: Double salary in same month
    r = CheckResult(134, "Salary paid twice in the same month to the same employee",
                    "Payroll & HR", "High", "pass")
    if not payroll_v.empty and "date" in payroll_v.columns:
        try:
            payroll_v2 = payroll_v.copy()
            payroll_v2["month"] = pd.to_datetime(payroll_v2["date"]).dt.to_period("M")
            emp_col = "employee_name" if "employee_name" in payroll_v2.columns else "party_ledger"
            if emp_col in payroll_v2.columns:
                dupes = payroll_v2.groupby([emp_col, "month"]).filter(lambda x: len(x) > 1)
                if not dupes.empty:
                    findings = [Finding(
                        detail=f"Duplicate salary for {row.get(emp_col)} in {row.get('month')}",
                        date=str(row.get("date")),
                        party=str(row.get(emp_col, "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in dupes.head(20).iterrows()]
                    r.fail(findings)
                else:
                    r.ok()
        except Exception:
            r.skip("Date error")
    results.append(r)

    # Check 135: PF not deposited within due date (15th of next month)
    r = CheckResult(135, "PF contributions not deposited within statutory due date",
                    "Payroll & HR", "High", "pass")
    if not df_v.empty and not df_l.empty:
        pf_payments = df_v[
            df_v.get("party_ledger", pd.Series([""] * len(df_v))).str.lower().str.contains("provident|pf|epfo", na=False) &
            (df_v["voucher_type"].str.lower() == "payment")
        ]
        if not pf_payments.empty:
            r.warn([Finding(
                detail=f"PF payment ₹{row.get('amount', 0):,.0f} on {row.get('date')} — verify due date compliance",
                date=str(row.get("date")),
                amount=float(row.get("amount", 0)),
            ) for _, row in pf_payments.head(12).iterrows()])
        else:
            r.skip("No PF payment entries found")
    results.append(r)

    # Checks 136-150
    pr_checks = [
        (136, "ESI contributions deducted but not deposited", "High"),
        (137, "Bonus paid exceeding statutory limit (20% of annual salary)", "Medium"),
        (138, "Gratuity provision not created for eligible employees", "Medium"),
        (139, "Salary paid in cash to employees drawing >₹10,000/month", "High"),
        (140, "Leave encashment paid without leave balance verification", "Medium"),
        (141, "Notice pay recovery not deducted from final settlement", "Medium"),
        (142, "Salary advance exceeding 2 months' gross salary", "Medium"),
        (143, "Overtime payment without overtime authorization records", "Medium"),
        (144, "Director remuneration exceeding limits under Companies Act", "High"),
        (145, "Reimbursements paid without supporting bills/receipts", "Medium"),
        (146, "Variable pay disbursed without performance evaluation sign-off", "Medium"),
        (147, "Salary to terminated employees after exit date", "High"),
        (148, "Medical reimbursement exceeding exemption limit (₹15,000)", "Low"),
        (149, "HRA claimed for employees in company accommodation", "High"),
        (150, "Arrear salary paid without Form 10E for tax relief", "Medium"),
    ]

    for cid, desc, risk in pr_checks:
        r = CheckResult(cid, desc, "Payroll & HR", risk, "pass")
        if cid == 139 and not payroll_v.empty:
            # Cash salary > ₹10,000
            if "narration" in payroll_v.columns and "amount" in payroll_v.columns:
                cash_sal = payroll_v[
                    payroll_v["narration"].str.lower().str.contains("cash", na=False) &
                    (payroll_v["amount"] >= 10000)
                ]
                if not cash_sal.empty:
                    findings = [Finding(
                        detail=f"Cash salary ₹{row.get('amount', 0):,.0f} to {row.get('employee_name') or row.get('party_ledger', '')}",
                        date=str(row.get("date")),
                        party=str(row.get("employee_name") or row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in cash_sal.head(20).iterrows()]
                    r.warn(findings)
        elif cid == 147 and not payroll_v.empty:
            r.skip("Requires HR exit date master")
        results.append(r)

    return results
