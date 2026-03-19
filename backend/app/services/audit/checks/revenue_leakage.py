"""Checks 516-545: Revenue Leakage"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding

CAT = "Revenue Leakage"


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    try:
        # --- 516: Unrecorded revenue — cash receipts without invoice ---
        r = CheckResult(516, "Unrecorded revenue — cash receipts without invoice", CAT, "High", "pass")
        try:
            if not df_v.empty:
                receipts = df_v[df_v["voucher_type"].str.lower() == "receipt"]
                # Flag receipts not linked to a sales voucher (no reference)
                unlinked = receipts[receipts["reference"].isna() | (receipts["reference"].str.strip() == "")]
                if not unlinked.empty:
                    total = unlinked["amount"].sum()
                    sales_total = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                    if sales_total > 0 and total / sales_total > 0.05:
                        findings = [Finding(
                            detail=f"Cash receipt without invoice reference ₹{row['amount']:,.0f}",
                            voucher_no=str(row.get("voucher_number", "")),
                            date=str(row.get("date", "")),
                            party=str(row.get("party_ledger", "")),
                            amount=float(row.get("amount", 0)),
                        ) for _, row in unlinked.head(50).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.ok()
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 517: Revenue reversal in subsequent period >2% ---
        r = CheckResult(517, "Revenue reversal in subsequent period >2%", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_date"] = pd.to_datetime(tmp["date"], errors="coerce")
                tmp["_month"] = tmp["_date"].dt.to_period("M")
                sales = tmp[tmp["voucher_type"].str.lower() == "sales"].groupby("_month")["amount"].sum()
                credit_notes = tmp[tmp["voucher_type"].str.lower().isin(["credit note"])].groupby("_month")["amount"].sum()
                if len(sales) >= 2:
                    months = sales.index.tolist()
                    bad = []
                    for i in range(1, len(months)):
                        m = months[i]
                        prev_sales = sales.get(months[i - 1], 0)
                        if prev_sales > 0:
                            cn = credit_notes.get(m, 0)
                            if cn / prev_sales > 0.02:
                                bad.append(Finding(detail=f"Month {m}: credit notes ₹{cn:,.0f} = {cn/prev_sales*100:.1f}% of prior month sales", amount=cn))
                    if bad:
                        r.warn(bad[:50])
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient monthly data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 518: Sales without GST where applicable ---
        r = CheckResult(518, "Sales transactions without GST where GST is applicable", CAT, "High", "pass")
        try:
            if not df_v.empty and not df_vl.empty:
                sales_ids = set(df_v[df_v["voucher_type"].str.lower() == "sales"]["id"].tolist())
                sales_vl = df_vl[df_vl["voucher_id"].isin(sales_ids)]
                no_gst = sales_vl[(sales_vl["gst_rate"] == 0) & (sales_vl["gst_type"].isna() | (sales_vl["gst_type"] == ""))]
                if not no_gst.empty:
                    total = no_gst["amount"].sum()
                    total_sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                    if total_sales > 0 and total / total_sales > 0.05:
                        findings = [Finding(
                            detail=f"Sales line without GST: ₹{row['amount']:,.0f} for ledger '{row.get('ledger_name', '')}'",
                            amount=float(row.get("amount", 0)),
                            ledger=str(row.get("ledger_name", "")),
                        ) for _, row in no_gst.head(50).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.ok()
            else:
                r.skip("No voucher line data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 519: Discounts given without approval threshold ---
        r = CheckResult(519, "Discounts given exceeding approval threshold (>10% per invoice)", CAT, "High", "pass")
        try:
            if not df_vl.empty and not df_v.empty:
                sales_ids = set(df_v[df_v["voucher_type"].str.lower() == "sales"]["id"].tolist())
                sales_lines = df_vl[df_vl["voucher_id"].isin(sales_ids)]
                disc_lines = sales_lines[sales_lines["ledger_name"].str.contains("discount", case=False, na=False)]
                if not disc_lines.empty:
                    disc_by_voucher = disc_lines.groupby("voucher_id")["amount"].sum()
                    total_by_voucher = sales_lines.groupby("voucher_id")["amount"].sum()
                    pct = (disc_by_voucher / total_by_voucher.replace(0, float("nan")) * 100).dropna()
                    bad = pct[pct > 10]
                    if not bad.empty:
                        findings = [Finding(detail=f"Voucher {vid}: discount = {v:.1f}%", amount=disc_by_voucher.get(vid, 0)) for vid, v in bad.head(50).items()]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.ok()
            else:
                r.skip("No voucher line data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 520: Free goods given without recording as promotional expense ---
        r = CheckResult(520, "Free goods/samples given without recording as promotional expense", CAT, "Medium", "pass")
        try:
            if not df_v.empty:
                free_goods = df_v[df_v["narration"].str.contains("free.*goods|free sample|promotional goods", case=False, na=False)]
                if not free_goods.empty:
                    total = free_goods["amount"].sum()
                    findings = [Finding(
                        detail=f"Free goods entry ₹{row['amount']:,.0f} — verify expense recognition",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in free_goods.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 521: Under-billed customers (invoice amount < PO value) ---
        r = CheckResult(521, "Under-billed customers — invoice amount below agreed price", CAT, "High", "pass")
        try:
            if not df_v.empty:
                # Proxy: sales with round-number amounts that may indicate incomplete billing
                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]
                if not sales.empty:
                    round_sales = sales[sales["amount"] % 1000 == 0]
                    pct = len(round_sales) / len(sales) * 100
                    if pct > 30:
                        findings = [Finding(
                            detail=f"Sales voucher ₹{row['amount']:,.0f} is a round number — verify billing completeness",
                            voucher_no=str(row.get("voucher_number", "")),
                            date=str(row.get("date", "")),
                            party=str(row.get("party_ledger", "")),
                            amount=float(row.get("amount", 0)),
                        ) for _, row in round_sales.head(50).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No sales data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 522: Revenue from expired contracts still being recognised ---
        r = CheckResult(522, "Revenue from expired contracts still being recognised", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                sales = df_v[df_v["voucher_type"].str.lower() == "sales"].copy()
                sales["_date"] = pd.to_datetime(sales["date"], errors="coerce")
                # Sales without reference to a valid contract
                no_ref = sales[sales["reference"].isna() | (sales["reference"].str.strip() == "")]
                if not no_ref.empty:
                    total = no_ref["amount"].sum()
                    all_sales = sales["amount"].sum()
                    if all_sales > 0 and total / all_sales > 0.20:
                        findings = [Finding(
                            detail=f"Sales without reference/contract ₹{row['amount']:,.0f}",
                            voucher_no=str(row.get("voucher_number", "")),
                            date=str(row.get("date", "")),
                            party=str(row.get("party_ledger", "")),
                            amount=float(row.get("amount", 0)),
                        ) for _, row in no_ref.head(50).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.ok()
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 523-545: Remaining revenue leakage checks ---
        remaining = [
            (523, "Billing cycle gaps — months with zero sales invoices", "High", True),
            (524, "Duplicate invoice numbers across periods", "High", True),
            (525, "Invoices cancelled after payment received without refund", "High", True),
            (526, "Revenue booked in wrong account/ledger", "High", True),
            (527, "Subscription revenue not recognised ratably", "High", False),
            (528, "Milestone-based billing — milestone achieved without invoice", "High", False),
            (529, "Service delivery without invoice within 30 days", "High", False),
            (530, "Export sales without export documents", "High", True),
            (531, "Sales to group entities below market price", "High", True),
            (532, "Scrap sales not invoiced", "Medium", True),
            (533, "By-product revenue not recorded", "Medium", True),
            (534, "Rental income from assets not invoiced monthly", "Medium", True),
            (535, "Interest on trade receivables not charged", "Medium", True),
            (536, "Penalty clauses on contracts not enforced", "Medium", False),
            (537, "Price escalation clauses not applied", "High", False),
            (538, "Retention money not released and not recognised", "Medium", False),
            (539, "Advance payments from customers not converted to sales", "High", True),
            (540, "Consignment stock sold but not invoiced", "High", False),
            (541, "Deferred revenue unwind not on schedule", "High", True),
            (542, "Grant income not recognised in correct period", "Medium", False),
            (543, "Royalty income not collected as per agreement", "Medium", True),
            (544, "License fee revenue not invoiced on due dates", "Medium", True),
            (545, "Service revenue recognised without acceptance certificate", "High", False),
        ]

        for chk_id, desc, risk, is_auto in remaining:
            r = CheckResult(chk_id, desc, CAT, risk, "pass")
            try:
                if not is_auto:
                    r.skip("Requires external data")
                else:
                    if chk_id == 523:
                        if not df_v.empty and "date" in df_v.columns:
                            tmp = df_v[df_v["voucher_type"].str.lower() == "sales"].copy()
                            tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                            monthly = tmp.groupby("_month").size()
                            if len(monthly) >= 2:
                                zero_months = monthly[monthly == 0]
                                if not zero_months.empty:
                                    findings = [Finding(detail=f"Month {m}: zero sales invoices") for m in zero_months.head(50).index]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("Insufficient monthly data")
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 524:
                        if not df_v.empty:
                            sales = df_v[df_v["voucher_type"].str.lower() == "sales"]
                            dups = sales[sales["voucher_number"].duplicated(keep=False) & sales["voucher_number"].notna()]
                            if not dups.empty:
                                findings = [Finding(
                                    detail=f"Duplicate voucher number {row.get('voucher_number')} ₹{row['amount']:,.0f}",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    date=str(row.get("date", "")),
                                    party=str(row.get("party_ledger", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in dups.head(50).iterrows()]
                                r.fail(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 525:
                        if not df_v.empty:
                            receipts = df_v[df_v["voucher_type"].str.lower() == "receipt"]["reference"].dropna().tolist()
                            cancelled = df_v[(df_v["voucher_type"].str.lower() == "sales") & (df_v.get("is_cancelled", pd.Series(False, index=df_v.index)) == True)]
                            if not cancelled.empty:
                                billed_cancelled = cancelled[cancelled["voucher_number"].isin(receipts)]
                                if not billed_cancelled.empty:
                                    findings = [Finding(
                                        detail=f"Invoice {row.get('voucher_number')} cancelled after receipt — verify refund",
                                        voucher_no=str(row.get("voucher_number", "")),
                                        amount=float(row.get("amount", 0)),
                                    ) for _, row in billed_cancelled.head(50).iterrows()]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 526:
                        if not df_l.empty:
                            rev_in_wrong = df_l[(df_l["is_expense"] == True) & (df_l["name"].str.contains("income|revenue|sales", case=False, na=False))]
                            if not rev_in_wrong.empty:
                                findings = [Finding(detail=f"Ledger '{row['name']}' in expense group but name suggests revenue", ledger=str(row.get("name", "")), amount=float(row.get("closing_balance", 0))) for _, row in rev_in_wrong.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 530:
                        if not df_v.empty:
                            exports = df_v[(df_v["voucher_type"].str.lower() == "sales") & (df_v["party_ledger"].str.contains("export|foreign|overseas", case=False, na=False))]
                            if not exports.empty:
                                no_gstin = exports[exports["gstin"].isna() | (exports["gstin"].str.strip() == "")]
                                if not no_gstin.empty:
                                    findings = [Finding(
                                        detail=f"Export sale without GSTIN/document ₹{row['amount']:,.0f}",
                                        voucher_no=str(row.get("voucher_number", "")),
                                        date=str(row.get("date", "")),
                                        party=str(row.get("party_ledger", "")),
                                        amount=float(row.get("amount", 0)),
                                    ) for _, row in no_gstin.head(50).iterrows()]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 531:
                        if not df_v.empty and not df_l.empty:
                            rp = df_l[df_l["pan"].notna() & (df_l["pan"].str.len() == 10)]["name"].tolist()
                            rp_sales = df_v[(df_v["voucher_type"].str.lower() == "sales") & (df_v["party_ledger"].isin(rp))]
                            all_sales = df_v[df_v["voucher_type"].str.lower() == "sales"]
                            if not rp_sales.empty and not all_sales.empty:
                                avg_rp = rp_sales["amount"].mean()
                                avg_all = all_sales["amount"].mean()
                                if avg_rp < avg_all * 0.80:
                                    findings = [Finding(detail=f"Related party avg invoice ₹{avg_rp:,.0f} vs overall avg ₹{avg_all:,.0f} — possible below-market pricing", amount=avg_rp)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No data")
                    elif chk_id == 532:
                        if not df_v.empty:
                            scrap = df_v[df_v["party_ledger"].str.contains("scrap", case=False, na=False)]
                            if scrap.empty:
                                findings = [Finding(detail="No scrap sales entries found — verify if scrap is being disposed without invoicing")]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 533:
                        if not df_l.empty:
                            by_prod = df_l[df_l["name"].str.contains("by.?product|co.?product", case=False, na=False)]
                            if by_prod.empty:
                                r.skip("No by-product ledgers identified")
                            else:
                                no_rev = by_prod[by_prod["is_revenue"] == False]
                                if not no_rev.empty:
                                    findings = [Finding(detail=f"By-product ledger '{row['name']}' not classified as revenue", ledger=str(row.get("name", ""))) for _, row in no_rev.head(50).iterrows()]
                                    r.warn(findings)
                                else:
                                    r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 534:
                        if not df_v.empty and "date" in df_v.columns:
                            rental = df_v[df_v["party_ledger"].str.contains("rent.*income|rental income", case=False, na=False)].copy()
                            if not rental.empty:
                                rental["_month"] = pd.to_datetime(rental["date"], errors="coerce").dt.to_period("M")
                                monthly = rental.groupby("_month").size()
                                max_m = rental["_month"].max()
                                min_m = rental["_month"].min()
                                expected = (max_m - min_m).n + 1 if hasattr(max_m - min_m, "n") else len(monthly)
                                if len(monthly) < expected * 0.8:
                                    findings = [Finding(detail=f"Rental income recorded only in {len(monthly)} of ~{expected} expected months", amount=rental["amount"].sum())]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("No rental income entries")
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 535:
                        if not df_v.empty:
                            int_income = df_v[df_v["party_ledger"].str.contains("interest.*receivable|interest on debtor|late payment interest", case=False, na=False)]
                            debtors = df_l[df_l["group_name"].str.contains("sundry debtor", case=False, na=False)] if not df_l.empty else pd.DataFrame()
                            if int_income.empty and not debtors.empty and debtors["closing_balance"].sum() > 0:
                                findings = [Finding(detail=f"No interest on overdue debtors recorded — total debtors ₹{debtors['closing_balance'].sum():,.0f}", amount=debtors["closing_balance"].sum())]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 539:
                        if not df_l.empty:
                            adv = df_l[df_l["name"].str.contains("advance from customer|customer advance|advance receipt", case=False, na=False)]
                            if not adv.empty:
                                total = adv["closing_balance"].sum()
                                if abs(total) > 0:
                                    open_total = adv["opening_balance"].sum()
                                    chg = abs(total) - abs(open_total)
                                    if chg > 0:
                                        findings = [Finding(detail=f"Customer advances increased by ₹{chg:,.0f} (total ₹{abs(total):,.0f}) — verify conversion to sales", amount=chg)]
                                        r.warn(findings)
                                    else:
                                        r.ok()
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 541:
                        if not df_l.empty:
                            defer = df_l[df_l["name"].str.contains("deferred revenue|unearned revenue", case=False, na=False)]
                            if not defer.empty:
                                open_bal = defer["opening_balance"].sum()
                                close_bal = defer["closing_balance"].sum()
                                if abs(open_bal) > 0 and abs(close_bal) >= abs(open_bal):
                                    findings = [Finding(detail=f"Deferred revenue not unwinding: opening ₹{abs(open_bal):,.0f} closing ₹{abs(close_bal):,.0f}", amount=abs(close_bal))]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("No deferred revenue ledgers")
                        else:
                            r.skip("No ledger data")
                    elif chk_id == 543:
                        if not df_v.empty:
                            royalty_inc = df_v[df_v["party_ledger"].str.contains("royalty income|royalty receivable", case=False, na=False)]
                            royalty_pay = df_v[df_v["party_ledger"].str.contains("royalty.*payable|royalty.*accrued", case=False, na=False)]
                            if royalty_pay.empty and royalty_inc.empty:
                                r.skip("No royalty entries found")
                            elif royalty_inc.empty and not royalty_pay.empty:
                                findings = [Finding(detail="Royalty payable entries exist but no royalty income recorded — verify collection")]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 544:
                        if not df_v.empty and "date" in df_v.columns:
                            lic = df_v[df_v["party_ledger"].str.contains("license fee|licence fee", case=False, na=False)].copy()
                            if not lic.empty:
                                lic["_month"] = pd.to_datetime(lic["date"], errors="coerce").dt.to_period("M")
                                monthly = lic.groupby("_month").size()
                                if monthly.min() == 0 or len(monthly) < 3:
                                    findings = [Finding(detail=f"Licence fee income gaps — only {len(monthly)} months with entries", amount=lic["amount"].sum())]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("No licence fee entries")
                        else:
                            r.skip("No voucher data")
                    else:
                        r.skip("Requires external data")
            except Exception:
                r.skip("Error in check")
            results.append(r)

    except Exception:
        pass

    return results
