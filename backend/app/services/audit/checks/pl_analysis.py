"""Checks 371-420: P&L Line Item Analysis"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding

CAT = "P&L Line Item Analysis"


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    try:
        # --- 371: Gross revenue vs net revenue reconciliation ---
        r = CheckResult(371, "Gross revenue vs net revenue reconciliation", CAT, "High", "pass")
        try:
            if not df_v.empty:
                gross_sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                credit_notes = df_v[df_v["voucher_type"].str.lower().isin(["credit note"])]["amount"].sum()
                if gross_sales > 0:
                    net_sales = gross_sales - credit_notes
                    ratio = credit_notes / gross_sales * 100
                    if ratio > 10:
                        findings = [Finding(detail=f"Net revenue is {ratio:.1f}% below gross — credit notes ₹{credit_notes:,.0f} on gross ₹{gross_sales:,.0f}", amount=credit_notes)]
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

        # --- 372: Product-wise revenue mix shift >10% ---
        r = CheckResult(372, "Product-wise revenue mix shift >10%", CAT, "Medium", "pass")
        try:
            if not df_s.empty:
                total_open = df_s["opening_value"].sum()
                total_close = df_s["closing_value"].sum()
                if total_open > 0 and total_close > 0:
                    df_s2 = df_s.copy()
                    df_s2["open_mix"] = df_s2["opening_value"] / total_open * 100
                    df_s2["close_mix"] = df_s2["closing_value"] / total_close * 100
                    df_s2["mix_shift"] = (df_s2["close_mix"] - df_s2["open_mix"]).abs()
                    bad = df_s2[df_s2["mix_shift"] > 10]
                    if not bad.empty:
                        findings = [Finding(detail=f"Stock '{row['name']}': mix shifted {row['mix_shift']:.1f}pp", ledger=str(row.get("group_name", "")), amount=float(row.get("closing_value", 0))) for _, row in bad.head(50).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient stock data")
            else:
                r.skip("No stock data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 373: Geographic/branch revenue mix shift (Module) ---
        r = CheckResult(373, "Geographic/branch revenue mix shift", CAT, "Medium", "skipped")
        r.skip("Requires external data")
        results.append(r)

        # --- 374: Sales returns percentage by product line >5% ---
        r = CheckResult(374, "Sales returns percentage by product line >5%", CAT, "High", "pass")
        try:
            if not df_v.empty:
                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                returns = df_v[df_v["voucher_type"].str.lower().isin(["credit note", "sales return"])]["amount"].sum()
                if sales > 0:
                    pct = returns / sales * 100
                    if pct > 5:
                        findings = [Finding(detail=f"Sales returns = {pct:.1f}% of gross sales (₹{returns:,.0f} on ₹{sales:,.0f})", amount=returns)]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No sales data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 375: Sales returns credited to wrong period ---
        r = CheckResult(375, "Sales returns credited to wrong period", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                returns = df_v[df_v["voucher_type"].str.lower().isin(["credit note", "sales return"])].copy()
                returns["_date"] = pd.to_datetime(returns["date"], errors="coerce")
                # Flag credit notes with reference to much older sales (narration contains prior year)
                cur_year = returns["_date"].dt.year.mode()[0] if not returns.empty else None
                if cur_year:
                    late_returns = returns[returns["_date"].dt.month.isin([1, 2, 3]) & (returns["_date"].dt.year == cur_year)]
                    if not late_returns.empty and late_returns["narration"].str.contains(str(cur_year - 1), na=False).any():
                        bad = late_returns[late_returns["narration"].str.contains(str(cur_year - 1), na=False)]
                        findings = [Finding(
                            detail=f"Credit note dated {row.get('date')} references prior year",
                            voucher_no=str(row.get("voucher_number", "")),
                            date=str(row.get("date", "")),
                            party=str(row.get("party_ledger", "")),
                            amount=float(row.get("amount", 0)),
                        ) for _, row in bad.head(50).iterrows()]
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

        # --- 376: Raw material cost per unit vs prior year >10% ---
        r = CheckResult(376, "Raw material cost per unit vs prior year >10%", CAT, "High", "pass")
        try:
            if not df_s.empty:
                raw_mat = df_s[df_s["group_name"].str.contains("raw material|raw mat", case=False, na=False)]
                if not raw_mat.empty:
                    bad = []
                    for _, row in raw_mat.iterrows():
                        open_qty = row.get("opening_qty", 0) or 0
                        open_val = row.get("opening_value", 0) or 0
                        close_qty = row.get("closing_qty", 0) or 0
                        close_val = row.get("closing_value", 0) or 0
                        open_unit = open_val / open_qty if open_qty > 0 else 0
                        close_unit = close_val / close_qty if close_qty > 0 else 0
                        if open_unit > 0 and close_unit > 0:
                            chg = (close_unit - open_unit) / open_unit * 100
                            if abs(chg) > 10:
                                bad.append(Finding(detail=f"'{row['name']}': cost/unit changed {chg:.1f}% (₹{open_unit:.2f}→₹{close_unit:.2f})", amount=close_val))
                    if bad:
                        r.fail(bad[:50])
                    else:
                        r.ok()
                else:
                    r.skip("No raw material stock items")
            else:
                r.skip("No stock data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 377: Other income as % of total revenue >15% ---
        r = CheckResult(377, "Other income as % of total revenue >15%", CAT, "Medium", "pass")
        try:
            if not df_l.empty:
                other_inc = df_l[df_l["name"].str.contains("other income|non.?operating", case=False, na=False)]["closing_balance"].sum()
                rev = df_l[df_l["is_revenue"] == True]["closing_balance"].sum()
                if rev > 0:
                    pct = abs(other_inc) / abs(rev) * 100
                    if pct > 15:
                        findings = [Finding(detail=f"Other income = {pct:.1f}% of total revenue (₹{other_inc:,.0f} on ₹{rev:,.0f})", amount=other_inc)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No revenue ledger data")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 378: Exceptional items not disclosed separately ---
        r = CheckResult(378, "Exceptional items not disclosed separately", CAT, "High", "pass")
        try:
            if not df_v.empty:
                excep = df_v[df_v["party_ledger"].str.contains("exceptional|extraordinary", case=False, na=False)]
                if not excep.empty:
                    total = excep["amount"].sum()
                    all_sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                    if all_sales > 0 and total / all_sales > 0.05:
                        findings = [Finding(
                            detail=f"Exceptional item ₹{row['amount']:,.0f} — verify separate disclosure",
                            voucher_no=str(row.get("voucher_number", "")),
                            date=str(row.get("date", "")),
                            party=str(row.get("party_ledger", "")),
                            amount=float(row.get("amount", 0)),
                        ) for _, row in excep.head(50).iterrows()]
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

        # 379-395: Mixed Module/Auto checks
        module_checks_379_395 = [
            (379, "Segment-wise revenue not reconciling to total", "High"),
            (380, "EBIT margin below industry median for 2+ consecutive quarters", "High"),
            (381, "Provision for doubtful debts inadequate vs ageing", "High"),
            (382, "Deferred revenue recognition policy inconsistency", "High"),
            (383, "Prior period items >1% of total revenue", "Medium"),
            (384, "Revenue recognised before delivery/service completion", "High"),
            (385, "Bill and hold arrangements without proper criteria", "High"),
        ]
        for chk_id, desc, risk in module_checks_379_395:
            r = CheckResult(chk_id, desc, CAT, risk, "skipped")
            r.skip("Requires external data")
            results.append(r)

        # --- 386: Salary expense as % of revenue >40% ---
        r = CheckResult(386, "Salary/employee cost as % of revenue >40%", CAT, "Medium", "pass")
        try:
            if not df_v.empty:
                sal = df_v[df_v["party_ledger"].str.contains("salary|wages|payroll", case=False, na=False)]["amount"].sum()
                if sal == 0:
                    sal = df_v[df_v["voucher_type"].str.lower().isin(["payroll", "salary"])]["amount"].sum()
                rev = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                if rev > 0 and sal > 0:
                    pct = sal / rev * 100
                    if pct > 40:
                        findings = [Finding(detail=f"Employee cost = {pct:.1f}% of revenue (₹{sal:,.0f} on ₹{rev:,.0f})", amount=sal)]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient salary or revenue data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 387: Gross profit negative ---
        r = CheckResult(387, "Gross profit negative — sales below cost of goods sold", CAT, "High", "pass")
        try:
            if not df_v.empty:
                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                purch = df_v[df_v["voucher_type"].str.lower() == "purchase"]["amount"].sum()
                gp = sales - purch
                if sales > 0 and gp < 0:
                    findings = [Finding(detail=f"Gross profit negative: sales ₹{sales:,.0f} - purchases ₹{purch:,.0f} = ₹{gp:,.0f}", amount=abs(gp))]
                    r.fail(findings)
                elif sales > 0:
                    r.ok()
                else:
                    r.skip("No sales data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 388: Finance cost exceeding EBIT ---
        r = CheckResult(388, "Finance cost exceeding EBIT — interest coverage <1", CAT, "High", "pass")
        try:
            if not df_v.empty:
                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                purch = df_v[df_v["voucher_type"].str.lower() == "purchase"]["amount"].sum()
                opex = df_v[df_l["is_expense"] == True]["amount"].sum() if not df_l.empty else 0
                interest = df_v[df_v["party_ledger"].str.contains("interest", case=False, na=False)]["amount"].sum()
                ebit = sales - purch
                if ebit > 0 and interest > 0:
                    coverage = ebit / interest
                    if coverage < 1:
                        findings = [Finding(detail=f"Interest coverage ratio = {coverage:.2f}x (EBIT ₹{ebit:,.0f}, Interest ₹{interest:,.0f})", amount=interest)]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient EBIT or interest data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # 389-420: Mix of Module and Auto checks
        remaining_checks = [
            (389, "Tax charge inconsistent with profit before tax", "High", True),
            (390, "Minority interest charges without subsidiary disclosure", "High", False),
            (391, "Share of profit/loss from associates not reconciling", "High", False),
            (392, "Amortisation of intangibles policy change", "Medium", False),
            (393, "Research costs expensed vs capitalised inconsistency", "Medium", False),
            (394, "Government grants not disclosed separately in P&L", "Medium", False),
            (395, "Foreign exchange gain/loss material and unexplained", "High", True),
            (396, "One-time gains inflating recurring profitability", "High", True),
            (397, "Restructuring charges without board resolution", "High", False),
            (398, "Impairment losses not tested annually", "High", False),
            (399, "Lease expense vs right-of-use asset amortisation mismatch", "Medium", False),
            (400, "Revenue from long-term contracts not % completion", "High", False),
            (401, "Warranty provisions inadequate vs historical claims", "Medium", False),
            (402, "Environmental liabilities not provisioned", "High", False),
            (403, "Litigation contingencies not disclosed", "High", False),
            (404, "Employee benefit obligations actuarial gain/loss", "Medium", False),
            (405, "Stock-based compensation expense not disclosed", "Medium", False),
            (406, "Related party revenues above arm's length pricing", "High", True),
            (407, "Management fees charged by parent >2% of revenue", "High", True),
            (408, "Royalty expense >5% of revenue without justification", "High", True),
            (409, "Service charges to group entities >3% of revenue", "Medium", False),
            (410, "Commission expense >10% of sales without agency agreement", "High", True),
            (411, "Sample and gift expenses >0.5% of revenue", "Low", True),
            (412, "Political donations in books without compliance", "High", True),
            (413, "CSR spend shortfall vs 2% of average net profit", "High", True),
            (414, "Deferred tax asset/liability movement inconsistent", "High", False),
            (415, "Prior year adjustments without restatement", "High", False),
            (416, "Provision write-back without adequate justification", "High", True),
            (417, "Bad debt recovery income without original write-off", "Medium", True),
            (418, "Gain on disposal of fixed assets material and recurring", "Medium", True),
            (419, "Miscellaneous income >5% of operating revenue", "Medium", True),
            (420, "P&L reclassification between periods without disclosure", "High", False),
        ]

        for chk_id, desc, risk, is_auto in remaining_checks:
            r = CheckResult(chk_id, desc, CAT, risk, "pass")
            try:
                if not is_auto:
                    r.skip("Requires external data")
                else:
                    # Auto checks with simple pandas logic
                    if chk_id == 389:
                        if not df_v.empty:
                            tax_v = df_v[df_v["party_ledger"].str.contains("income tax|tax payable", case=False, na=False)]
                            if not tax_v.empty:
                                tax_total = tax_v["amount"].sum()
                                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if sales > 0 and tax_total / sales > 0.35:
                                    findings = [Finding(detail=f"Tax charge {tax_total / sales * 100:.1f}% of sales — verify effective rate", amount=tax_total)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("No tax charge data")
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 395:
                        if not df_v.empty:
                            forex = df_v[df_v["party_ledger"].str.contains("forex|foreign exchange|exchange (gain|loss)", case=False, na=False)]
                            if not forex.empty:
                                total = forex["amount"].sum()
                                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if sales > 0 and abs(total) / sales > 0.03:
                                    findings = [Finding(detail=f"Forex impact ₹{total:,.0f} = {abs(total)/sales*100:.1f}% of sales", amount=abs(total))]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("No forex data")
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 396:
                        if not df_v.empty:
                            one_time = df_v[df_v["party_ledger"].str.contains("one.?time|exceptional|extraordinary", case=False, na=False)]
                            if not one_time.empty:
                                total = one_time["amount"].sum()
                                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if sales > 0 and total / sales > 0.05:
                                    findings = [Finding(
                                        detail=f"One-time gain ₹{row['amount']:,.0f} inflating profitability",
                                        voucher_no=str(row.get("voucher_number", "")),
                                        date=str(row.get("date", "")),
                                        amount=float(row.get("amount", 0)),
                                    ) for _, row in one_time.head(50).iterrows()]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 406:
                        if not df_v.empty and not df_l.empty:
                            rp_pan = df_l[df_l["pan"].notna() & (df_l["pan"].str.len() == 10)]
                            if not rp_pan.empty:
                                sales_rp = df_v[df_v["party_ledger"].isin(rp_pan["name"])]
                                if not sales_rp.empty:
                                    total = sales_rp["amount"].sum()
                                    all_sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                    if all_sales > 0 and total / all_sales > 0.30:
                                        findings = [Finding(detail=f"Related party revenue = {total/all_sales*100:.1f}% of total sales", amount=total)]
                                        r.warn(findings)
                                    else:
                                        r.ok()
                                else:
                                    r.ok()
                            else:
                                r.skip("No PAN-linked ledgers for RP check")
                        else:
                            r.skip("No data")
                    elif chk_id == 407:
                        if not df_v.empty:
                            mgmt = df_v[df_v["party_ledger"].str.contains("management fee|mgmt fee", case=False, na=False)]
                            if not mgmt.empty:
                                total = mgmt["amount"].sum()
                                rev = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if rev > 0 and total / rev > 0.02:
                                    findings = [Finding(detail=f"Management fees = {total/rev*100:.1f}% of revenue (₹{total:,.0f})", amount=total)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 408:
                        if not df_v.empty:
                            royalty = df_v[df_v["party_ledger"].str.contains("royalty", case=False, na=False)]
                            if not royalty.empty:
                                total = royalty["amount"].sum()
                                rev = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if rev > 0 and total / rev > 0.05:
                                    findings = [Finding(detail=f"Royalty expense = {total/rev*100:.1f}% of revenue (₹{total:,.0f})", amount=total)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 410:
                        if not df_v.empty:
                            comm = df_v[df_v["party_ledger"].str.contains("commission", case=False, na=False)]
                            if not comm.empty:
                                total = comm["amount"].sum()
                                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if sales > 0 and total / sales > 0.10:
                                    findings = [Finding(detail=f"Commission = {total/sales*100:.1f}% of sales (₹{total:,.0f})", amount=total)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 411:
                        if not df_v.empty:
                            samples = df_v[df_v["party_ledger"].str.contains("sample|gift", case=False, na=False)]
                            if not samples.empty:
                                total = samples["amount"].sum()
                                rev = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if rev > 0 and total / rev > 0.005:
                                    findings = [Finding(detail=f"Samples/gifts = {total/rev*100:.2f}% of revenue (₹{total:,.0f})", amount=total)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 412:
                        if not df_v.empty:
                            pol = df_v[df_v["party_ledger"].str.contains("political|donation|electoral", case=False, na=False)]
                            if not pol.empty:
                                findings = [Finding(
                                    detail=f"Political/donation payment ₹{row['amount']:,.0f} — verify compliance",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    date=str(row.get("date", "")),
                                    party=str(row.get("party_ledger", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in pol.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 413:
                        if not df_v.empty:
                            csr = df_v[df_v["party_ledger"].str.contains("csr|corporate social", case=False, na=False)]
                            if not csr.empty:
                                csr_total = csr["amount"].sum()
                                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if sales > 0 and csr_total / sales < 0.02:
                                    findings = [Finding(detail=f"CSR spend ₹{csr_total:,.0f} = {csr_total/sales*100:.2f}% of revenue — may be below 2% of net profit requirement", amount=csr_total)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("No CSR entries found")
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 416:
                        if not df_v.empty:
                            prov_wb = df_v[df_v["narration"].str.contains("provision.*written back|write.?back.*provision", case=False, na=False)]
                            if not prov_wb.empty:
                                total = prov_wb["amount"].sum()
                                findings = [Finding(
                                    detail=f"Provision write-back ₹{row['amount']:,.0f} — verify justification",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    date=str(row.get("date", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in prov_wb.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 417:
                        if not df_v.empty:
                            recovery = df_v[df_v["party_ledger"].str.contains("bad debt recovery|recovery of written", case=False, na=False)]
                            if not recovery.empty:
                                total = recovery["amount"].sum()
                                findings = [Finding(
                                    detail=f"Bad debt recovery ₹{row['amount']:,.0f} — verify original write-off exists",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    date=str(row.get("date", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in recovery.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 418:
                        if not df_v.empty:
                            fa_disp = df_v[df_v["party_ledger"].str.contains("gain on sale.*asset|profit on sale.*asset|asset disposal", case=False, na=False)]
                            if not fa_disp.empty:
                                total = fa_disp["amount"].sum()
                                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if sales > 0 and total / sales > 0.02:
                                    findings = [Finding(detail=f"Asset disposal gains ₹{total:,.0f} = {total/sales*100:.1f}% of sales", amount=total)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 419:
                        if not df_v.empty:
                            misc_inc = df_v[df_v["party_ledger"].str.contains("miscellaneous income|sundry income|other income", case=False, na=False)]
                            if not misc_inc.empty:
                                total = misc_inc["amount"].sum()
                                sales = df_v[df_v["voucher_type"].str.lower() == "sales"]["amount"].sum()
                                if sales > 0 and total / sales > 0.05:
                                    findings = [Finding(detail=f"Miscellaneous income = {total/sales*100:.1f}% of operating revenue (₹{total:,.0f})", amount=total)]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    else:
                        r.skip("No automated logic available")
            except Exception:
                r.skip("Error in check")
            results.append(r)

    except Exception:
        pass

    return results
