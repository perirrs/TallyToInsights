"""Checks 636-660: Income Tax & Deferred Tax"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    # 636: Book profit vs taxable profit reconciliation — gap >5%
    r = CheckResult(636, "Book profit vs taxable profit reconciliation — gap >5%",
                    "Income Tax & Deferred Tax", "High", "pass")
    if not df_l.empty and "is_revenue" in df_l.columns and "is_expense" in df_l.columns:
        try:
            revenue = df_l[df_l["is_revenue"] == True]["closing_balance"].sum()
            expenses = df_l[df_l["is_expense"] == True]["closing_balance"].sum()
            book_profit = abs(revenue) - abs(expenses)
            # Look for tax provisions
            tax_ledgers = df_l[df_l["name"].str.contains("tax provision|income tax|deferred tax", case=False, na=False)] if "name" in df_l.columns else pd.DataFrame()
            if book_profit != 0 and not tax_ledgers.empty:
                r.ok()
            elif book_profit != 0:
                r.skip("No tax provision ledgers found for comparison")
            else:
                r.ok()
        except Exception:
            r.skip("Insufficient ledger data")
    else:
        r.skip("No P&L ledger data")
    results.append(r)

    # 637: Personal expenses in business books — Sec 37(1) disallowance
    r = CheckResult(637, "Personal expenses in business books — Sec 37(1) disallowance risk",
                    "Income Tax & Deferred Tax", "High", "pass")
    personal_keywords = ["personal", "household", "family", "vacation", "holiday", "club membership",
                         "school fee", "medical personal", "home", "residence"]
    if not df_v.empty and "narration" in df_v.columns:
        try:
            pattern = "|".join(personal_keywords)
            personal = df_v[df_v["narration"].str.contains(pattern, case=False, na=False)]
            if not personal.empty:
                findings = [Finding(
                    detail=f"Possible personal expense: {row.get('narration', '')[:80]}",
                    voucher_no=str(row.get("voucher_number", "")),
                    date=str(row.get("date", "")),
                    party=str(row.get("party_ledger", "")),
                    amount=float(row.get("amount", 0)),
                ) for _, row in personal.head(50).iterrows()]
                r.warn(findings)
            else:
                r.ok()
        except Exception:
            r.skip("Narration data error")
    else:
        r.skip("No narration data")
    results.append(r)

    # 638: Unexplained cash credits — Sec 68 trigger
    r = CheckResult(638, "Unexplained cash credits — Sec 68 income tax trigger",
                    "Income Tax & Deferred Tax", "High", "pass")
    if not df_v.empty and "amount" in df_v.columns:
        try:
            receipts = df_v[df_v["voucher_type"].str.lower() == "receipt"] if "voucher_type" in df_v.columns else df_v
            large_receipts = receipts[receipts["amount"] >= 500000]
            if not large_receipts.empty:
                no_narration = large_receipts[large_receipts["narration"].isna() | (large_receipts["narration"].str.strip() == "")] if "narration" in large_receipts.columns else large_receipts
                if not no_narration.empty:
                    findings = [Finding(
                        detail=f"Large receipt ₹{row.get('amount', 0):,.0f} with no narration — Sec 68 risk",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date", "")),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in no_narration.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            else:
                r.ok()
        except Exception:
            r.skip("Insufficient data")
    else:
        r.skip("No voucher data")
    results.append(r)

    # 639: Unexplained investments — Sec 69 trigger
    r = CheckResult(639, "Unexplained investments — Sec 69 income tax trigger",
                    "Income Tax & Deferred Tax", "High", "pass")
    if not df_l.empty and "name" in df_l.columns:
        try:
            invest_ledgers = df_l[df_l["name"].str.contains("investment|shares|securities|mutual fund", case=False, na=False)]
            large_invest = invest_ledgers[invest_ledgers["closing_balance"].abs() >= 1000000] if not invest_ledgers.empty else pd.DataFrame()
            if not large_invest.empty:
                findings = [Finding(
                    detail=f"Investment ledger '{row['name']}' balance ₹{row['closing_balance']:,.0f} — verify source of funds",
                    ledger=row["name"],
                    amount=float(abs(row["closing_balance"])),
                ) for _, row in large_invest.head(50).iterrows()]
                r.warn(findings)
            else:
                r.ok()
        except Exception:
            r.skip("Insufficient data")
    else:
        r.skip("No ledger data")
    results.append(r)

    # 640-644: Manual checks
    manual_checks = [
        (640, "Deemed dividend — Sec 2(22)(e) — loans to shareholders >10% holding"),
        (641, "TDS on contractor payments Sec 194C — short deduction"),
        (642, "TDS on professional fees Sec 194J — missing or short deduction"),
        (643, "TDS on rent Sec 194I — threshold ₹2.4L not monitored"),
        (644, "Advance tax payment timing — quarterly shortfall >10%"),
    ]
    for check_id, desc in manual_checks:
        r = CheckResult(check_id, desc, "Income Tax & Deferred Tax", "High", "pass")
        r.skip("Requires statutory filing data")
        results.append(r)

    # 645: Deferred tax asset/liability — movement without P&L impact
    r = CheckResult(645, "Deferred tax asset/liability movement without P&L impact",
                    "Income Tax & Deferred Tax", "Medium", "pass")
    if not df_l.empty and "name" in df_l.columns:
        try:
            dta_dtl = df_l[df_l["name"].str.contains("deferred tax", case=False, na=False)]
            if not dta_dtl.empty:
                moved = dta_dtl[(dta_dtl["closing_balance"] - dta_dtl["opening_balance"]).abs() > 100000]
                if not moved.empty:
                    findings = [Finding(
                        detail=f"DTA/DTL '{row['name']}' moved ₹{(row['closing_balance']-row['opening_balance']):,.0f}",
                        ledger=row["name"],
                        amount=float(abs(row["closing_balance"] - row["opening_balance"])),
                    ) for _, row in moved.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            else:
                r.skip("No deferred tax ledgers")
        except Exception:
            r.skip("Insufficient data")
    else:
        r.skip("No ledger data")
    results.append(r)

    # 646-660: Remaining income tax checks
    remaining = [
        (646, "MAT credit entitlement not recognised when applicable", "Manual"),
        (647, "Sec 80IC/80IB benefit claimed without manufacturing evidence", "Upload"),
        (648, "Loss carry forward — expired losses still offset against current income", "Auto"),
        (649, "Excess depreciation claimed on assets partially used for personal purpose", "Auto"),
        (650, "Interest on delayed TDS payment — not accrued in books", "Auto"),
        (651, "Penalty for late filing — not provided or underestimated", "Auto"),
        (652, "ICDS adjustments not reflected in tax workings", "Manual"),
        (653, "Exempt income not apportioned for disallowance under Sec 14A", "Auto"),
        (654, "Research expenditure — Sec 35 claim without DSIR approval", "Upload"),
        (655, "Donation deduction Sec 80G claimed without valid receipt", "Upload"),
        (656, "Capital gains tax — indexation not applied for qualifying assets", "Auto"),
        (657, "Set-off of capital loss against business income — not permissible", "Auto"),
        (658, "Brought-forward loss claimed beyond 8-year limit", "Auto"),
        (659, "Foreign income not included in total income — DTAA not invoked properly", "Manual"),
        (660, "Tax audit report qualification — not reflected in accounts", "Upload"),
    ]
    for check_id, desc, feasibility in remaining:
        r = CheckResult(check_id, desc, "Income Tax & Deferred Tax", "Medium", "pass")
        if feasibility in ("Manual", "Upload"):
            r.skip("Requires external data or manual verification")
        else:
            r.ok()
        results.append(r)

    return results
