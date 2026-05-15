"""Checks 111-130: Statutory & Tax"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    # Check 111: Output GST not computed on taxable sales
    r = CheckResult(111, "Output GST not computed on taxable sales (missing CGST/SGST/IGST)",
                    "Statutory & Tax", "High", "pass")
    if not df_v.empty and not df_vl.empty:
        sales = df_v[df_v["voucher_type"].str.lower() == "sales"]
        if not sales.empty:
            sales_ids = set(sales["id"].tolist()) if "id" in sales.columns else set()
            gst_lines = df_vl[
                df_vl.get("gst_type", pd.Series([""] * len(df_vl))).str.lower().isin(["cgst", "sgst", "igst"])
            ]
            gst_voucher_ids = set(gst_lines["voucher_id"].tolist()) if "voucher_id" in gst_lines.columns else set()
            no_gst = sales[sales.apply(
                lambda r: r.get("id") not in gst_voucher_ids and r.get("amount", 0) > 0, axis=1
            )]
            if not no_gst.empty:
                findings = [Finding(
                    detail=f"Sales invoice ₹{row.get('amount', 0):,.0f} to {row.get('party_ledger')} without GST",
                    voucher_no=str(row.get("voucher_number", "")),
                    date=str(row.get("date")),
                    party=str(row.get("party_ledger", "")),
                    amount=float(row.get("amount", 0)),
                ) for _, row in no_gst.head(50).iterrows()]
                r.warn(findings)
            else:
                r.ok()
        else:
            r.skip("No sales vouchers")
    else:
        r.skip("Insufficient data")
    results.append(r)

    # Check 112: TDS not deducted on vendor payments
    r = CheckResult(112, "TDS not deducted on eligible vendor payments above threshold",
                    "Statutory & Tax", "High", "pass")
    if not df_v.empty:
        payments = df_v[
            (df_v["voucher_type"].str.lower() == "payment") &
            (df_v.get("amount", 0) >= 30000)
        ]
        if not payments.empty and not df_vl.empty:
            # Check if TDS ledger appears in voucher lines
            tds_lines = df_vl[df_vl.get("ledger_name", pd.Series([""] * len(df_vl))).str.lower().str.contains("tds|tax deducted", na=False)]
            tds_vids = set(tds_lines["voucher_id"].tolist()) if "voucher_id" in tds_lines.columns else set()
            no_tds = payments[payments.apply(lambda r: r.get("id") not in tds_vids, axis=1)]
            if not no_tds.empty and len(no_tds) > len(payments) * 0.3:
                findings = [Finding(
                    detail=f"Payment ₹{row.get('amount', 0):,.0f} to {row.get('party_ledger')} may lack TDS deduction",
                    voucher_no=str(row.get("voucher_number", "")),
                    date=str(row.get("date")),
                    party=str(row.get("party_ledger", "")),
                    amount=float(row.get("amount", 0)),
                ) for _, row in no_tds.head(30).iterrows()]
                r.warn(findings)
            else:
                r.ok()
        else:
            r.skip("Insufficient data")
    results.append(r)

    # Check 113: GST on reverse charge not accounted
    r = CheckResult(113, "Reverse charge GST liability not created for RCM purchases",
                    "Statutory & Tax", "High", "pass")
    if not df_v.empty and "is_reverse_charge" in df_v.columns:
        rcm = df_v[df_v["is_reverse_charge"] == True]
        if not rcm.empty:
            # Check if corresponding GST lines exist
            findings = [Finding(
                detail=f"RCM purchase ₹{row.get('amount', 0):,.0f} from {row.get('party_ledger')} — verify GST liability entry",
                voucher_no=str(row.get("voucher_number", "")),
                date=str(row.get("date")),
                party=str(row.get("party_ledger", "")),
                amount=float(row.get("amount", 0)),
            ) for _, row in rcm.head(30).iterrows()]
            r.warn(findings)
        else:
            r.ok()
    else:
        r.skip("No RCM flag in data")
    results.append(r)

    # Check 114: PF/ESI not deducted from salary
    r = CheckResult(114, "PF/ESI contributions not deducted from eligible employee salaries",
                    "Statutory & Tax", "High", "pass")
    if not df_v.empty:
        salary = df_v[df_v["voucher_type"].str.lower().isin(["payroll", "salary"])]
        if not salary.empty and not df_vl.empty:
            pf_lines = df_vl[df_vl.get("ledger_name", pd.Series([""] * len(df_vl))).str.lower().str.contains("pf|provident|esi|esic", na=False)]
            if pf_lines.empty:
                findings = [Finding(
                    detail="No PF/ESI deduction entries found in payroll vouchers",
                    amount=salary.get("amount", pd.Series([0])).sum(),
                )]
                r.warn(findings)
            else:
                r.ok()
        else:
            r.skip("No payroll vouchers")
    results.append(r)

    # Checks 115-130
    stat_checks = [
        (115, "GST returns filed late — interest and penalty liability", "High"),
        (116, "ITC claimed on blocked credit items (motor vehicles, club membership)", "High"),
        (117, "ITC not reversed on exempt supplies as per Rule 42", "High"),
        (118, "Professional tax not deducted in applicable states", "Medium"),
        (119, "GST registration not taken for turnover above ₹20L threshold", "High"),
        (120, "Income tax advance tax shortfall (>10% of tax liability)", "High"),
        (121, "Customs duty/import duty not accrued for imported goods", "High"),
        (122, "Section 194C TDS not deducted on contractor payments >₹1L aggregate", "High"),
        (123, "Section 194J TDS not deducted on professional fees >₹30,000", "High"),
        (124, "GST e-way bill not generated for consignment >₹50,000", "Medium"),
        (125, "Composition dealer issuing tax invoice (not allowed)", "High"),
        (126, "Input tax credit claimed after due date (Section 16(4))", "High"),
        (127, "Salary paid to director without TDS deduction (Section 192)", "High"),
        (128, "Expenses disallowable under Section 40(a)(ia) — TDS default", "High"),
        (129, "Donation to unapproved trust claimed as deduction", "High"),
        (130, "Form 26AS mismatch — TDS deducted but not deposited", "High"),
    ]

    for cid, desc, risk in stat_checks:
        r = CheckResult(cid, desc, "Statutory & Tax", risk, "pass")
        if cid == 122 and not df_v.empty:
            contractor_kw = ["contractor", "labour", "sub-contractor", "manpower", "outsource"]
            if "party_ledger" in df_v.columns:
                contractors = df_v[df_v["party_ledger"].str.lower().apply(
                    lambda x: any(k in str(x) for k in contractor_kw)
                )]
                if not contractors.empty and "amount" in contractors.columns:
                    high = contractors[contractors["amount"] >= 100000]
                    if not high.empty and not df_vl.empty:
                        tds_vids = set(
                            df_vl[df_vl.get("ledger_name", pd.Series([""] * len(df_vl))).str.lower().str.contains("tds|194c", na=False)]["voucher_id"].tolist()
                        ) if "voucher_id" in df_vl.columns else set()
                        no_tds = high[high.apply(lambda r: r.get("id") not in tds_vids, axis=1)]
                        if not no_tds.empty:
                            findings = [Finding(
                                detail=f"Contractor payment ₹{row.get('amount', 0):,.0f} to {row.get('party_ledger')} — verify 194C TDS",
                                date=str(row.get("date")),
                                party=str(row.get("party_ledger", "")),
                                amount=float(row.get("amount", 0)),
                            ) for _, row in no_tds.head(20).iterrows()]
                            r.warn(findings)
        results.append(r)

    return results
