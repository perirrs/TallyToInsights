"""Checks 576-600: Treasury & Working Capital"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding

CAT = "Treasury & Working Capital"


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    try:
        def _current_assets(df_l):
            return df_l[df_l["group_name"].str.contains(
                "current asset|sundry debtor|stock|inventory|cash|bank|prepaid|advance.*supplier",
                case=False, na=False
            )]["closing_balance"].sum()

        def _current_liabs(df_l):
            return abs(df_l[df_l["group_name"].str.contains(
                "current liabilit|sundry creditor|trade payable|advance.*customer|short.?term loan|bank od|overdraft",
                case=False, na=False
            )]["closing_balance"].sum())

        # --- 576: Current ratio below 1.0 ---
        r = CheckResult(576, "Current ratio below 1.0 — liquidity stress", CAT, "High", "pass")
        try:
            if not df_l.empty:
                ca = _current_assets(df_l)
                cl = _current_liabs(df_l)
                if ca > 0 and cl > 0:
                    ratio = ca / cl
                    if ratio < 1.0:
                        findings = [Finding(detail=f"Current ratio = {ratio:.2f}x (CA ₹{ca:,.0f} vs CL ₹{cl:,.0f})", amount=cl - ca)]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient balance sheet data")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 577: Quick ratio below 0.5 ---
        r = CheckResult(577, "Quick ratio below 0.5", CAT, "High", "pass")
        try:
            if not df_l.empty:
                ca = _current_assets(df_l)
                inv = df_l[df_l["group_name"].str.contains("stock|inventory", case=False, na=False)]["closing_balance"].sum()
                cl = _current_liabs(df_l)
                if ca > 0 and cl > 0:
                    quick = (ca - inv) / cl
                    if quick < 0.5:
                        findings = [Finding(detail=f"Quick ratio = {quick:.2f}x — below 0.5 threshold", amount=cl)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient balance sheet data")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 578: Days Sales Outstanding >90 days ---
        r = CheckResult(578, "Days Sales Outstanding >90 days", CAT, "High", "pass")
        try:
            if not df_l.empty and not df_v.empty:
                debtors = df_l[df_l["group_name"].str.contains("sundry debtor|trade receivable", case=False, na=False)]["closing_balance"].sum()
                annual_sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                if annual_sales > 0 and debtors > 0:
                    dso = debtors / annual_sales * 365
                    if dso > 90:
                        findings = [Finding(detail=f"DSO = {dso:.0f} days (debtors ₹{debtors:,.0f}, annual sales ₹{annual_sales:,.0f})", amount=debtors)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient debtor or sales data")
            else:
                r.skip("No data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 579: Days Payable Outstanding <15 days (too fast payment) ---
        r = CheckResult(579, "Days Payable Outstanding <15 days — premature vendor payment", CAT, "High", "pass")
        try:
            if not df_l.empty and not df_v.empty:
                creditors = abs(df_l[df_l["group_name"].str.contains("sundry creditor|trade payable", case=False, na=False)]["closing_balance"].sum())
                annual_purch = df_v[df_v["voucher_type"].str.lower() == "purchase"]["amount"].sum()
                if annual_purch > 0 and creditors > 0:
                    dpo = creditors / annual_purch * 365
                    if dpo < 15:
                        findings = [Finding(detail=f"DPO = {dpo:.0f} days — payments too rapid, verify terms (payables ₹{creditors:,.0f})", amount=creditors)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient creditor or purchase data")
            else:
                r.skip("No data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 580: Inventory Days >180 days ---
        r = CheckResult(580, "Inventory Days >180 — slow-moving stock risk", CAT, "High", "pass")
        try:
            if not df_s.empty and not df_v.empty:
                inv_value = df_s["closing_value"].sum()
                annual_cogs = df_v[df_v["voucher_type"].str.lower() == "purchase"]["amount"].sum()
                if annual_cogs > 0 and inv_value > 0:
                    inv_days = inv_value / annual_cogs * 365
                    if inv_days > 180:
                        findings = [Finding(detail=f"Inventory days = {inv_days:.0f} days (stock ₹{inv_value:,.0f})", amount=inv_value)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient inventory or purchase data")
            else:
                r.skip("No data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 581: Cash conversion cycle >120 days ---
        r = CheckResult(581, "Cash conversion cycle >120 days — working capital stress", CAT, "High", "pass")
        try:
            if not df_l.empty and not df_v.empty:
                debtors = df_l[df_l["group_name"].str.contains("sundry debtor|trade receivable", case=False, na=False)]["closing_balance"].sum()
                creditors = abs(df_l[df_l["group_name"].str.contains("sundry creditor|trade payable", case=False, na=False)]["closing_balance"].sum())
                inv_value = df_s["closing_value"].sum() if not df_s.empty else 0
                annual_sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                annual_purch = df_v[df_v["voucher_type"].str.lower() == "purchase"]["amount"].sum()
                if annual_sales > 0 and annual_purch > 0:
                    dso = debtors / annual_sales * 365 if debtors > 0 else 0
                    dpo = creditors / annual_purch * 365 if creditors > 0 else 0
                    inv_days = inv_value / annual_purch * 365 if inv_value > 0 else 0
                    ccc = dso + inv_days - dpo
                    if ccc > 120:
                        findings = [Finding(detail=f"CCC = {ccc:.0f} days (DSO={dso:.0f}, Inv={inv_days:.0f}, DPO={dpo:.0f})", amount=debtors + inv_value)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient data")
            else:
                r.skip("No data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 582: Cash balance below 7 days of operating expenses ---
        r = CheckResult(582, "Cash balance below 7 days of operating expenses", CAT, "High", "pass")
        try:
            if not df_l.empty and not df_v.empty:
                cash = df_l[(df_l["is_cash"] == True) | (df_l["is_bank"] == True)]["closing_balance"].sum()
                annual_opex = df_v[df_l["is_expense"] == True]["amount"].sum() if not df_l.empty else 0
                if annual_opex == 0:
                    annual_opex = df_v[df_v["voucher_type"].str.lower() == "purchase"]["amount"].sum()
                daily_opex = annual_opex / 365 if annual_opex > 0 else 0
                if daily_opex > 0 and cash > 0:
                    days_cover = cash / daily_opex
                    if days_cover < 7:
                        findings = [Finding(detail=f"Cash covers only {days_cover:.0f} days of opex (cash ₹{cash:,.0f}, daily opex ₹{daily_opex:,.0f})", amount=cash)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient cash or opex data")
            else:
                r.skip("No data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 583: Working capital negative ---
        r = CheckResult(583, "Net working capital negative — operational funding gap", CAT, "High", "pass")
        try:
            if not df_l.empty:
                ca = _current_assets(df_l)
                cl = _current_liabs(df_l)
                if ca > 0 or cl > 0:
                    nwc = ca - cl
                    if nwc < 0:
                        findings = [Finding(detail=f"Net working capital = ₹{nwc:,.0f} (CA ₹{ca:,.0f} - CL ₹{cl:,.0f})", amount=abs(nwc))]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient balance sheet data")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 584: Bank overdraft exceeding 30 days continuously ---
        r = CheckResult(584, "Bank overdraft balance — prolonged OD indicates stress", CAT, "High", "pass")
        try:
            if not df_l.empty:
                bank_od = df_l[(df_l["is_bank"] == True) & (df_l["closing_balance"] < 0)]
                if not bank_od.empty:
                    total_od = abs(bank_od["closing_balance"].sum())
                    findings = [Finding(
                        detail=f"Bank account '{row['name']}' in overdraft: ₹{abs(row['closing_balance']):,.0f}",
                        ledger=str(row.get("name", "")),
                        amount=abs(float(row.get("closing_balance", 0))),
                    ) for _, row in bank_od.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 585: Fixed deposits pledged against borrowings not disclosed ---
        r = CheckResult(585, "Fixed deposits pledged against borrowings not disclosed", CAT, "Medium", "pass")
        try:
            if not df_l.empty:
                fds = df_l[df_l["name"].str.contains("fixed deposit|FD|term deposit", case=False, na=False)]
                if not fds.empty:
                    total_fd = fds["closing_balance"].sum()
                    loans = abs(df_l[df_l["group_name"].str.contains("secured loan|term loan", case=False, na=False)]["closing_balance"].sum())
                    if loans > 0 and total_fd > 0 and total_fd / loans < 0.5:
                        findings = [Finding(detail=f"FDs ₹{total_fd:,.0f} vs secured loans ₹{loans:,.0f} — verify pledge status", amount=total_fd)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No FD ledgers found")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # 586-600: Treasury checks mix
        treasury_checks = [
            (586, "Inter-bank fund transfers not reconciled", "High", True),
            (587, "Treasury investments in high-risk instruments", "High", False),
            (588, "Short-term investments at cost not marked to market", "Medium", False),
            (589, "Cash pooling arrangements not documented", "Medium", False),
            (590, "Foreign currency cash held without approved policy", "High", False),
            (591, "Bank reconciliation outstanding items >30 days", "High", True),
            (592, "Cheques issued but not presented for >90 days", "Medium", True),
            (593, "Cash in hand exceeding ₹2L without justification", "High", True),
            (594, "Working capital loan utilisation <40% — excess borrowing", "Medium", True),
            (595, "Interest on CC/OD account not reconciled with bank statement", "High", False),
            (596, "Letter of credit expired without utilisation — bank charges", "Medium", False),
            (597, "Bank guarantee issued without board approval", "High", False),
            (598, "ECB drawdown not utilised for stated purpose", "High", False),
            (599, "FEMA compliance for remittances not documented", "High", False),
            (600, "Treasury policy limit breach — maximum single investment", "High", False),
        ]

        for chk_id, desc, risk, is_auto in treasury_checks:
            r = CheckResult(chk_id, desc, CAT, risk, "pass")
            try:
                if not is_auto:
                    r.skip("Requires external data")
                else:
                    if chk_id == 586:
                        if not df_v.empty:
                            transfers = df_v[df_v["voucher_type"].str.lower() == "contra"]
                            no_ref = transfers[transfers["reference"].isna() | (transfers["reference"].str.strip() == "")]
                            if not no_ref.empty and len(no_ref) / max(len(transfers), 1) > 0.10:
                                findings = [Finding(
                                    detail=f"Contra/bank transfer without reference ₹{row['amount']:,.0f}",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    date=str(row.get("date", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in no_ref.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 591:
                        if not df_v.empty and "date" in df_v.columns:
                            contra = df_v[df_v["voucher_type"].str.lower() == "contra"].copy()
                            contra["_date"] = pd.to_datetime(contra["date"], errors="coerce")
                            max_date = contra["_date"].max()
                            old = contra[contra["_date"] < max_date - pd.Timedelta(days=30)]
                            if not old.empty and len(old) / max(len(contra), 1) > 0.10:
                                findings = [Finding(
                                    detail=f"Bank transaction from {row.get('date')} may be unreconciled (>30 days old)",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    date=str(row.get("date", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in old.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 592:
                        if not df_v.empty and "date" in df_v.columns:
                            payments = df_v[df_v["voucher_type"].str.lower() == "payment"].copy()
                            payments["_date"] = pd.to_datetime(payments["date"], errors="coerce")
                            max_date = payments["_date"].max()
                            old_cheques = payments[
                                (payments["narration"].str.contains("cheque|chq|check", case=False, na=False)) &
                                (payments["_date"] < max_date - pd.Timedelta(days=90))
                            ]
                            if not old_cheques.empty:
                                findings = [Finding(
                                    detail=f"Cheque payment from {row.get('date')} may be stale (>90 days)",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    date=str(row.get("date", "")),
                                    party=str(row.get("party_ledger", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in old_cheques.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 593:
                        if not df_l.empty:
                            cash = df_l[df_l["is_cash"] == True]
                            high_cash = cash[cash["closing_balance"] > 200000]
                            if not high_cash.empty:
                                findings = [Finding(
                                    detail=f"Cash balance '{row['name']}' = ₹{row['closing_balance']:,.0f} — exceeds ₹2L",
                                    ledger=str(row.get("name", "")),
                                    amount=float(row.get("closing_balance", 0)),
                                ) for _, row in high_cash.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 594:
                        if not df_l.empty and not df_v.empty:
                            wc_loan = abs(df_l[df_l["group_name"].str.contains("cash credit|working capital|cc limit", case=False, na=False)]["closing_balance"].sum())
                            if wc_loan > 0:
                                monthly_purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"]["amount"].sum() / 12
                                if monthly_purchases > 0 and wc_loan / monthly_purchases < 0.4:
                                    findings = [Finding(detail=f"WC loan ₹{wc_loan:,.0f} appears underutilised vs monthly purchases ₹{monthly_purchases:,.0f}", amount=wc_loan)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("No working capital loan found")
                        else:
                            r.skip("No data")
                    else:
                        r.skip("Requires external data")
            except Exception:
                r.skip("Error in check")
            results.append(r)

    except Exception:
        pass

    return results
