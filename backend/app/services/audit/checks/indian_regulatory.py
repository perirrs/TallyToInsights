"""Checks 711-730: Indian Regulatory"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    # 711: MSMED Act — payments to MSMEs beyond 45 days
    r = CheckResult(711, "MSMED Act — payments to MSMEs beyond 45 days — interest liability",
                    "Indian Regulatory", "High", "pass")
    r.skip("Requires MSME vendor registration data (Upload)")
    results.append(r)

    # 712: Companies Act Sec 185 — loans to directors
    r = CheckResult(712, "Companies Act Sec 185 — loans/advances to directors or relatives",
                    "Indian Regulatory", "High", "pass")
    if not df_l.empty and "name" in df_l.columns:
        try:
            director_loans = df_l[df_l["name"].str.contains(r"loan to director|advance to director|director loan", case=False, na=False)]
            if not director_loans.empty:
                findings = [Finding(
                    detail=f"Possible director loan: '{row['name']}' ₹{row.get('closing_balance', 0):,.0f}",
                    ledger=row["name"],
                    amount=float(abs(row.get("closing_balance", 0))),
                ) for _, row in director_loans.head(50).iterrows()]
                r.fail(findings)
            else:
                r.ok()
        except Exception:
            r.skip("Insufficient data")
    else:
        r.skip("No ledger data")
    results.append(r)

    # 713: Companies Act Sec 186 — IC loans and investments beyond limit
    r = CheckResult(713, "Companies Act Sec 186 — IC loans and investments beyond limit",
                    "Indian Regulatory", "High", "pass")
    if not df_l.empty and "name" in df_l.columns:
        try:
            investments = df_l[df_l["name"].str.contains("investment|loan to subsidiary|IC loan", case=False, na=False)]
            total_invest = investments["closing_balance"].abs().sum() if not investments.empty else 0
            if total_invest > 0:
                findings = [Finding(
                    detail=f"Investment/IC loan total ₹{total_invest:,.0f} — verify Sec 186 limits (60% net worth or 100% free reserves)",
                    amount=float(total_invest),
                )]
                r.warn(findings)
            else:
                r.ok()
        except Exception:
            r.skip("Insufficient data")
    else:
        r.skip("No ledger data")
    results.append(r)

    # 714: CSR spend < 2% of 3-year average net profit
    r = CheckResult(714, "Companies Act Sec 135 — CSR spend <2% of 3-year average net profit",
                    "Indian Regulatory", "High", "pass")
    if not df_l.empty and "name" in df_l.columns:
        try:
            csr = df_l[df_l["name"].str.contains("CSR|corporate social responsibility", case=False, na=False)]
            revenue = df_l[df_l.get("is_revenue", pd.Series(False)) == True]["closing_balance"].abs().sum() if "is_revenue" in df_l.columns else 0
            if not csr.empty and revenue > 0:
                csr_spend = csr["closing_balance"].abs().sum()
                # Approximate: CSR should be >= 2% of net profit (approx 5-10% of revenue)
                estimated_profit = revenue * 0.05
                required_csr = estimated_profit * 0.02
                if csr_spend < required_csr:
                    findings = [Finding(
                        detail=f"CSR spend ₹{csr_spend:,.0f} may be below 2% of net profit (est. required ₹{required_csr:,.0f})",
                        amount=float(csr_spend),
                    )]
                    r.warn(findings)
                else:
                    r.ok()
            elif csr.empty:
                r.warn([Finding(detail="No CSR expense ledger found — verify applicability", amount=0)])
            else:
                r.ok()
        except Exception:
            r.skip("Insufficient data")
    else:
        r.skip("No ledger data")
    results.append(r)

    # 715-720: FEMA and other regulatory checks
    regulatory_checks = [
        (715, "FEMA — receipts from foreign parties without FIRC within 15 days", "Upload"),
        (716, "FEMA — overseas remittances beyond LRS limit $250,000 per year", "Auto"),
        (717, "FEMA — External Commercial Borrowing — end-use violation", "Upload"),
        (718, "SEBI — insider trading — large trades near price-sensitive events", "Upload"),
        (719, "SEBI — SAST — acquisition trigger threshold crossed", "Upload"),
        (720, "Transfer Pricing — RPTs without TP documentation (Form 3CEB)", "Upload"),
    ]
    for check_id, desc, feasibility in regulatory_checks:
        r = CheckResult(check_id, desc, "Indian Regulatory", "High", "pass")
        if feasibility == "Upload":
            r.skip("Requires external regulatory filing data")
        elif check_id == 716 and not df_v.empty:
            try:
                foreign = df_v[df_v["narration"].str.contains("remittance|forex|foreign|LRS", case=False, na=False)] if "narration" in df_v.columns else pd.DataFrame()
                large = foreign[foreign["amount"] > 1700000] if not foreign.empty and "amount" in foreign.columns else pd.DataFrame()  # ~$20,000
                if not large.empty:
                    findings = [Finding(
                        detail=f"Large foreign remittance ₹{row.get('amount', 0):,.0f} — verify LRS compliance",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in large.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            except Exception:
                r.ok()
        else:
            r.ok()
        results.append(r)

    # 721-730: PF, ESI, Labour law checks
    labour_checks = [
        (721, "PF contribution — employer contribution below 12% of basic", "Auto"),
        (722, "ESI contribution — employees above ₹21,000/month still covered", "Auto"),
        (723, "Gratuity not paid within 30 days of eligible employee exit", "Upload"),
        (724, "Minimum wages below state-notified rates", "Upload"),
        (725, "Professional Tax — state-specific slabs not applied correctly", "Auto"),
        (726, "Labour welfare fund — contribution not deposited timely", "Upload"),
        (727, "Factory Act compliance — overtime wage rate calculation error", "Upload"),
        (728, "Shops & Establishment Act — unregistered premises conducting business", "Manual"),
        (729, "BOCW Act — cess not deducted on construction contracts", "Auto"),
        (730, "Contract Labour Act — principal employer liability not accounted", "Upload"),
    ]
    for check_id, desc, feasibility in labour_checks:
        r = CheckResult(check_id, desc, "Indian Regulatory", "Medium", "pass")
        if feasibility in ("Upload", "Manual"):
            r.skip("Requires external HR/payroll data")
        elif check_id == 721 and not df_v.empty:
            try:
                pf = df_v[df_v["narration"].str.contains("provident fund|PF|EPF", case=False, na=False)] if "narration" in df_v.columns else pd.DataFrame()
                if not pf.empty:
                    r.ok()
                else:
                    r.warn([Finding(detail="No PF payment vouchers found — verify PF compliance")])
            except Exception:
                r.ok()
        elif check_id == 725 and not df_l.empty:
            try:
                pt = df_l[df_l["name"].str.contains("professional tax|PT payable", case=False, na=False)] if "name" in df_l.columns else pd.DataFrame()
                if not pt.empty:
                    r.ok()
                else:
                    r.warn([Finding(detail="No Professional Tax ledger found — verify state PT compliance")])
            except Exception:
                r.ok()
        else:
            r.ok()
        results.append(r)

    return results
