"""Checks 421-465: Balance Sheet Analysis"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding

CAT = "Balance Sheet Analysis"


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    try:
        # --- 421: Fixed assets net block growth >20% without capex approval ---
        r = CheckResult(421, "Fixed assets net block growth >20% without capex approval", CAT, "High", "pass")
        try:
            if not df_l.empty:
                fa = df_l[df_l["group_name"].str.contains("fixed asset|plant.*machinery|furniture|vehicle|computer", case=False, na=False)]
                if not fa.empty:
                    open_bal = fa["opening_balance"].sum()
                    close_bal = fa["closing_balance"].sum()
                    if open_bal > 0:
                        growth = (close_bal - open_bal) / open_bal * 100
                        if growth > 20:
                            findings = [Finding(detail=f"Fixed assets grew {growth:.1f}% (₹{open_bal:,.0f} → ₹{close_bal:,.0f}) — verify capex approval", amount=close_bal - open_bal)]
                            r.warn(findings)
                        else:
                            r.ok()
                    else:
                        r.ok()
                else:
                    r.skip("No fixed asset ledgers found")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 422: Intangible assets proportion of total assets >40% ---
        r = CheckResult(422, "Intangible assets proportion of total assets >40%", CAT, "Medium", "pass")
        try:
            if not df_l.empty:
                intang = df_l[df_l["group_name"].str.contains("intangible|goodwill|patent|trademark|brand", case=False, na=False)]["closing_balance"].sum()
                total_assets = df_l[df_l["is_asset"] == True]["closing_balance"].sum()
                if total_assets > 0:
                    pct = abs(intang) / abs(total_assets) * 100
                    if pct > 40:
                        findings = [Finding(detail=f"Intangibles = {pct:.1f}% of total assets (₹{intang:,.0f} on ₹{total_assets:,.0f})", amount=intang)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No asset ledger data")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 423: Trade receivables >90 days >30% of total receivables ---
        r = CheckResult(423, "Trade receivables >90 days >30% of total receivables", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                sales_v = df_v[df_v["voucher_type"].str.lower() == "sales"].copy()
                sales_v["_date"] = pd.to_datetime(sales_v["date"], errors="coerce")
                if not sales_v.empty:
                    max_date = sales_v["_date"].max()
                    old = sales_v[sales_v["_date"] < max_date - pd.Timedelta(days=90)]
                    total_recv = sales_v["amount"].sum()
                    old_recv = old["amount"].sum()
                    if total_recv > 0:
                        pct = old_recv / total_recv * 100
                        if pct > 30:
                            findings = [Finding(detail=f"Sales >90 days = {pct:.1f}% of total (₹{old_recv:,.0f} on ₹{total_recv:,.0f})", amount=old_recv)]
                            r.warn(findings)
                        else:
                            r.ok()
                    else:
                        r.ok()
                else:
                    r.skip("No sales vouchers")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 424: Inventory holding exceeds 6 months of COGS ---
        r = CheckResult(424, "Inventory holding exceeds 6 months of COGS", CAT, "High", "pass")
        try:
            if not df_s.empty and not df_v.empty:
                inv_value = df_s["closing_value"].sum()
                annual_purch = df_v[df_v["voucher_type"].str.lower() == "purchase"]["amount"].sum()
                monthly_cogs = annual_purch / 12 if annual_purch > 0 else 0
                if monthly_cogs > 0:
                    months = inv_value / monthly_cogs
                    if months > 6:
                        findings = [Finding(detail=f"Inventory holding = {months:.1f} months of COGS (₹{inv_value:,.0f})", amount=inv_value)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No purchase data to compute COGS")
            else:
                r.skip("Insufficient stock or voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 425: Cash and bank balances >30% of total assets (idle cash) ---
        r = CheckResult(425, "Cash and bank balances >30% of total assets — idle cash concern", CAT, "Medium", "pass")
        try:
            if not df_l.empty:
                cash_bank = df_l[(df_l["is_cash"] == True) | (df_l["is_bank"] == True)]["closing_balance"].sum()
                total_assets = df_l[df_l["is_asset"] == True]["closing_balance"].sum()
                if total_assets > 0:
                    pct = abs(cash_bank) / abs(total_assets) * 100
                    if pct > 30:
                        findings = [Finding(detail=f"Cash/bank = {pct:.1f}% of total assets (₹{cash_bank:,.0f})", amount=cash_bank)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No asset data")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 426: Loans and advances >20% of total assets ---
        r = CheckResult(426, "Loans and advances >20% of total assets", CAT, "High", "pass")
        try:
            if not df_l.empty:
                la = df_l[df_l["group_name"].str.contains("loans.*advance|advance.*loans|loan to", case=False, na=False)]["closing_balance"].sum()
                total_assets = df_l[df_l["is_asset"] == True]["closing_balance"].sum()
                if total_assets > 0:
                    pct = abs(la) / abs(total_assets) * 100
                    if pct > 20:
                        findings = [Finding(detail=f"Loans & advances = {pct:.1f}% of total assets (₹{la:,.0f})", amount=la)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No asset data")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 427: Deferred tax asset not justified by future taxable profits ---
        r = CheckResult(427, "Deferred tax asset not justified by future taxable profits", CAT, "High", "pass")
        try:
            if not df_l.empty:
                dta = df_l[df_l["name"].str.contains("deferred tax asset", case=False, na=False)]["closing_balance"].sum()
                if abs(dta) > 0:
                    sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum() if not df_v.empty else 0
                    if sales > 0 and abs(dta) / sales > 0.10:
                        findings = [Finding(detail=f"Deferred tax asset ₹{dta:,.0f} = {abs(dta)/sales*100:.1f}% of revenue — verify recoverability", amount=dta)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.ok()
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 428: Capital WIP stagnant for more than 12 months ---
        r = CheckResult(428, "Capital WIP stagnant for more than 12 months", CAT, "Medium", "pass")
        try:
            if not df_l.empty:
                cwip = df_l[df_l["group_name"].str.contains("capital work.?in.?progress|cwip", case=False, na=False)]
                if not cwip.empty:
                    stagnant = cwip[cwip["opening_balance"] == cwip["closing_balance"]]
                    if not stagnant.empty:
                        findings = [Finding(detail=f"CWIP '{row['name']}' unchanged at ₹{row['closing_balance']:,.0f}", ledger=str(row.get("name", "")), amount=float(row.get("closing_balance", 0))) for _, row in stagnant.head(50).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No CWIP ledgers found")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 429: Investments in subsidiaries without valuation ---
        r = CheckResult(429, "Investments in subsidiaries without valuation", CAT, "High", "pass")
        try:
            if not df_l.empty:
                inv = df_l[df_l["group_name"].str.contains("investment|subsidiary|associate", case=False, na=False)]
                if not inv.empty:
                    total = inv["closing_balance"].sum()
                    total_assets = df_l[df_l["is_asset"] == True]["closing_balance"].sum()
                    if total_assets > 0 and abs(total) / abs(total_assets) > 0.20:
                        findings = [Finding(detail=f"Investments = {abs(total)/abs(total_assets)*100:.1f}% of total assets (₹{total:,.0f}) — verify valuation", amount=total)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.ok()
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 430: Negative net worth / shareholders' equity ---
        r = CheckResult(430, "Negative net worth — shareholders equity eroded", CAT, "High", "pass")
        try:
            if not df_l.empty:
                eq = df_l[df_l["group_name"].str.contains("share capital|reserve|equity|retained earning", case=False, na=False)]["closing_balance"].sum()
                if eq < 0:
                    findings = [Finding(detail=f"Shareholders equity is negative: ₹{eq:,.0f}", amount=abs(eq))]
                    r.fail(findings)
                else:
                    r.ok()
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 431: Accumulated losses eroding paid-up capital by >50% ---
        r = CheckResult(431, "Accumulated losses eroding paid-up capital by >50%", CAT, "High", "pass")
        try:
            if not df_l.empty:
                cap = abs(df_l[df_l["group_name"].str.contains("share capital|paid.?up", case=False, na=False)]["closing_balance"].sum())
                acc_loss = df_l[df_l["name"].str.contains("accumulated loss|deficit|p&l.*loss", case=False, na=False)]["closing_balance"].sum()
                if cap > 0 and abs(acc_loss) / cap > 0.50:
                    findings = [Finding(detail=f"Accumulated losses ₹{abs(acc_loss):,.0f} = {abs(acc_loss)/cap*100:.1f}% of paid-up capital", amount=abs(acc_loss))]
                    r.fail(findings)
                else:
                    r.ok()
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 432-465: Additional balance sheet checks ---
        bs_checks = [
            (432, "Contingent liabilities exceeding 20% of net worth", "High", True),
            (433, "Off-balance-sheet financing arrangements", "High", False),
            (434, "Revaluation reserve without independent valuation", "Medium", False),
            (435, "Capital reduction without court approval", "High", False),
            (436, "Preference shares redeemable overdue", "High", False),
            (437, "Debentures overdue for redemption", "High", False),
            (438, "Public deposits accepted without RBI compliance", "High", False),
            (439, "Overdraft balances in savings accounts", "High", True),
            (440, "Fixed deposit pledged exceeding 50% of total FDs", "Medium", False),
            (441, "Trade payables to related parties >30% of total payables", "High", True),
            (442, "Security deposits outstanding >2 years without resolution", "Medium", True),
            (443, "Unclaimed dividends not transferred to IEPF", "High", True),
            (444, "Capital contribution by directors not properly documented", "High", False),
            (445, "Forfeited shares proceeds not transferred to capital reserve", "Medium", False),
            (446, "Employee provident fund trust investment non-compliance", "High", False),
            (447, "Gratuity fund shortfall >10% of actuarial liability", "High", False),
            (448, "Warranty provisions not actuarially determined", "Medium", False),
            (449, "Decommissioning liability not provisioned", "High", False),
            (450, "Operating lease commitments >3x annual rent expense", "Medium", False),
            (451, "Capital commitments not disclosed in notes", "Medium", False),
            (452, "Secured loans without charge registration", "High", False),
            (453, "Unsecured loans from directors without board approval", "High", True),
            (454, "Loans from shareholders above prescribed limit", "High", True),
            (455, "Inter-company loans without interest — deemed dividend risk", "High", True),
            (456, "Bank borrowings exceeding sanctioned limit", "High", True),
            (457, "Term loan repayment schedule non-compliance", "High", False),
            (458, "Asset coverage ratio for secured loans <1.25x", "High", True),
            (459, "Mortgage of assets without lender consent for additional charge", "High", False),
            (460, "Foreign currency loans not hedged — mark-to-market loss", "High", False),
            (461, "FCCB redemption premium not provided for", "High", False),
            (462, "Derivatives at fair value — unrealised loss not provisioned", "High", False),
            (463, "Goodwill not tested for impairment annually", "High", False),
            (464, "Investment property not at fair value/cost model consistently", "Medium", False),
            (465, "Biological assets not measured at fair value", "Medium", False),
        ]

        for chk_id, desc, risk, is_auto in bs_checks:
            r = CheckResult(chk_id, desc, CAT, risk, "pass")
            try:
                if not is_auto:
                    r.skip("Requires external data")
                else:
                    if chk_id == 432:
                        if not df_l.empty:
                            networth = df_l[df_l["group_name"].str.contains("share capital|reserve|equity", case=False, na=False)]["closing_balance"].sum()
                            cont_liab = df_l[df_l["name"].str.contains("contingent|guarantee|letter of credit", case=False, na=False)]["closing_balance"].sum()
                            if networth > 0 and abs(cont_liab) / networth > 0.20:
                                findings = [Finding(detail=f"Contingent liabilities ₹{cont_liab:,.0f} = {abs(cont_liab)/networth*100:.1f}% of net worth", amount=abs(cont_liab))]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 439:
                        if not df_l.empty:
                            savings_od = df_l[(df_l["is_bank"] == True) & (df_l["closing_balance"] < 0)]
                            if not savings_od.empty:
                                findings = [Finding(detail=f"Bank account '{row['name']}' shows negative balance ₹{row['closing_balance']:,.0f}", ledger=str(row.get("name", "")), amount=abs(float(row.get("closing_balance", 0)))) for _, row in savings_od.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 441:
                        if not df_l.empty:
                            total_payables = df_l[df_l["group_name"].str.contains("sundry creditor|trade payable|accounts payable", case=False, na=False)]["closing_balance"].sum()
                            rp_payables = df_l[(df_l["group_name"].str.contains("sundry creditor|trade payable", case=False, na=False)) & (df_l["pan"].notna())]["closing_balance"].sum()
                            if total_payables > 0 and abs(rp_payables) / abs(total_payables) > 0.30:
                                findings = [Finding(detail=f"Related party payables = {abs(rp_payables)/abs(total_payables)*100:.1f}% of total payables", amount=abs(rp_payables))]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 442:
                        if not df_l.empty:
                            sec_dep = df_l[df_l["name"].str.contains("security deposit", case=False, na=False)]
                            if not sec_dep.empty:
                                stagnant = sec_dep[sec_dep["opening_balance"] == sec_dep["closing_balance"]]
                                if not stagnant.empty:
                                    findings = [Finding(detail=f"Security deposit '{row['name']}' stagnant at ₹{row['closing_balance']:,.0f}", ledger=str(row.get("name", "")), amount=float(row.get("closing_balance", 0))) for _, row in stagnant.head(50).iterrows()]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("No security deposit ledgers")
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 443:
                        if not df_l.empty:
                            unclaimed = df_l[df_l["name"].str.contains("unclaimed dividend|IEPF", case=False, na=False)]
                            if not unclaimed.empty:
                                total = unclaimed["closing_balance"].sum()
                                if abs(total) > 0:
                                    findings = [Finding(detail=f"Unclaimed dividends ₹{abs(total):,.0f} — verify IEPF transfer", amount=abs(total))]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 453:
                        if not df_l.empty:
                            dir_loans = df_l[df_l["group_name"].str.contains("loan.*director|director.*loan|unsecured loan", case=False, na=False)]
                            if not dir_loans.empty:
                                total = dir_loans["closing_balance"].sum()
                                if abs(total) > 0:
                                    findings = [Finding(detail=f"Unsecured loans from directors ₹{abs(total):,.0f} — verify board approval", ledger=str(row.get("name", "")), amount=abs(float(row.get("closing_balance", 0)))) for _, row in dir_loans.head(50).iterrows()]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 454:
                        if not df_l.empty:
                            sh_loans = df_l[df_l["group_name"].str.contains("loan.*shareholder|shareholder.*loan", case=False, na=False)]
                            if not sh_loans.empty:
                                total = sh_loans["closing_balance"].sum()
                                if abs(total) > 0:
                                    findings = [Finding(detail=f"Shareholder loans ₹{abs(total):,.0f} — verify prescribed limit compliance", amount=abs(total))]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 455:
                        if not df_l.empty:
                            ic_loans = df_l[df_l["name"].str.contains("loan to group|inter.?company loan|loan to subsidiary", case=False, na=False)]
                            if not ic_loans.empty:
                                no_int = ic_loans[ic_loans["name"].str.contains("interest.?free|zero interest|no interest", case=False, na=False)]
                                if not no_int.empty:
                                    total = no_int["closing_balance"].sum()
                                    findings = [Finding(detail=f"Interest-free intercompany loan ₹{abs(total):,.0f} — deemed dividend risk", amount=abs(total))]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 456:
                        if not df_l.empty:
                            bank_od = df_l[(df_l["is_bank"] == True) & (df_l["closing_balance"] < 0)]
                            if not bank_od.empty:
                                total_od = abs(bank_od["closing_balance"].sum())
                                findings = [Finding(detail=f"Bank OD/CC ₹{total_od:,.0f} — verify against sanctioned limits", amount=total_od)]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 458:
                        if not df_l.empty:
                            secured = df_l[df_l["group_name"].str.contains("secured loan|term loan", case=False, na=False)]["closing_balance"].sum()
                            fixed_assets = df_l[df_l["group_name"].str.contains("fixed asset", case=False, na=False)]["closing_balance"].sum()
                            if secured > 0 and fixed_assets > 0:
                                ratio = fixed_assets / secured
                                if ratio < 1.25:
                                    findings = [Finding(detail=f"Asset coverage ratio = {ratio:.2f}x (FA ₹{fixed_assets:,.0f} vs secured loans ₹{secured:,.0f})", amount=secured)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("Insufficient secured loan / asset data")
                        else:
                            r.skip("No ledger data")
                    else:
                        r.skip("Requires external data")
            except Exception:
                r.skip("Error in check")
            results.append(r)

    except Exception:
        pass

    return results
