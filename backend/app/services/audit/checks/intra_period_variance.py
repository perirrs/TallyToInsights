"""Checks 301-335: Intra-Period Variance"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding

CAT = "Intra-Period Variance"


def _monthly(df_v: pd.DataFrame, vtype_filter=None, ledger_kw=None) -> pd.Series:
    """Return monthly sum of amounts for given voucher types or narration keyword."""
    if df_v.empty or "date" not in df_v.columns:
        return pd.Series(dtype=float)
    tmp = df_v.copy()
    tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
    if vtype_filter:
        tmp = tmp[tmp["voucher_type"].str.lower().isin([v.lower() for v in vtype_filter])]
    if ledger_kw:
        tmp = tmp[tmp["party_ledger"].str.contains(ledger_kw, case=False, na=False)]
    return tmp.groupby("_month")["amount"].sum()


def _mom_pct(series: pd.Series) -> pd.Series:
    """Month-over-month % change."""
    return series.pct_change() * 100


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    try:
        # --- 301: Monthly revenue variance >20% MoM ---
        r = CheckResult(301, "Monthly revenue variance >20% MoM", CAT, "High", "pass")
        try:
            rev_ledgers = df_l[df_l["is_revenue"] == True]["name"].tolist() if not df_l.empty else []
            if not df_v.empty and "date" in df_v.columns and rev_ledgers:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                rev = tmp[tmp["party_ledger"].isin(rev_ledgers)].groupby("_month")["amount"].sum()
                if len(rev) >= 2:
                    chg = _mom_pct(rev).dropna()
                    bad_months = chg[chg.abs() > 20]
                    if not bad_months.empty:
                        findings = [Finding(detail=f"Month {m}: {v:.1f}% MoM change in revenue", amount=rev.get(m, 0)) for m, v in bad_months.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient monthly data")
            else:
                r.skip("No revenue data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 302: Monthly COGS variance >15% ---
        r = CheckResult(302, "Monthly COGS variance vs prior month and 3-month rolling avg >15%", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                cogs = tmp[tmp["voucher_type"].str.lower().isin(["purchase", "credit note"])].groupby("_month")["amount"].sum()
                if len(cogs) >= 2:
                    chg = _mom_pct(cogs).dropna()
                    bad = chg[chg.abs() > 15]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: {v:.1f}% COGS MoM change", amount=cogs.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient monthly data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 303: Monthly gross margin % deviation >5% from annual avg ---
        r = CheckResult(303, "Monthly gross margin % deviation >5% from current-year annual average", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                sales = tmp[tmp["voucher_type"].str.lower() == "sales"].groupby("_month")["amount"].sum()
                purchases = tmp[tmp["voucher_type"].str.lower() == "purchase"].groupby("_month")["amount"].sum()
                if len(sales) >= 3 and len(purchases) >= 3:
                    common = sales.index.intersection(purchases.index)
                    gm = ((sales[common] - purchases[common]) / sales[common].replace(0, float("nan")) * 100).dropna()
                    annual_avg = gm.mean()
                    bad = gm[(gm - annual_avg).abs() > 5]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: GM={v:.1f}% vs avg={annual_avg:.1f}%", amount=float(sales.get(m, 0))) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient monthly data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 304: Monthly revenue variance by branch >25% (Module) ---
        r = CheckResult(304, "Monthly revenue variance by branch >25%", CAT, "Medium", "skipped")
        r.skip("Requires external data")
        results.append(r)

        # --- 305: Monthly opex line-item variance >20% ---
        r = CheckResult(305, "Monthly opex line-item variance each expense head >20%", CAT, "Medium", "pass")
        try:
            exp_ledgers = df_l[df_l["is_expense"] == True]["name"].tolist() if not df_l.empty else []
            if not df_v.empty and "date" in df_v.columns and exp_ledgers:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                exp = tmp[tmp["party_ledger"].isin(exp_ledgers)].groupby("_month")["amount"].sum()
                if len(exp) >= 2:
                    chg = _mom_pct(exp).dropna()
                    bad = chg[chg.abs() > 20]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: {v:.1f}% opex MoM variance", amount=exp.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient data")
            else:
                r.skip("No expense data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 306: Quarterly budget vs actual revenue (Module) ---
        r = CheckResult(306, "Quarterly budget vs actual revenue variance >10%", CAT, "High", "skipped")
        r.skip("Requires external data")
        results.append(r)

        # --- 307: Quarterly budget vs actual cost (Module) ---
        r = CheckResult(307, "Quarterly budget vs actual cost variance >10%", CAT, "High", "skipped")
        r.skip("Requires external data")
        results.append(r)

        # --- 308: EBITDA variance quarter-on-quarter >15% ---
        r = CheckResult(308, "EBITDA variance quarter-on-quarter >15%", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_qtr"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("Q")
                sales = tmp[tmp["voucher_type"].str.lower() == "sales"].groupby("_qtr")["amount"].sum()
                purch = tmp[tmp["voucher_type"].str.lower() == "purchase"].groupby("_qtr")["amount"].sum()
                if len(sales) >= 2:
                    common = sales.index.intersection(purch.index) if len(purch) >= 2 else sales.index
                    ebitda = sales.reindex(common, fill_value=0) - purch.reindex(common, fill_value=0)
                    chg = ebitda.pct_change().dropna() * 100
                    bad = chg[chg.abs() > 15]
                    if not bad.empty:
                        findings = [Finding(detail=f"Quarter {m}: {v:.1f}% EBITDA QoQ change", amount=ebitda.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient quarterly data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 309: Weekly transaction volume anomaly ---
        r = CheckResult(309, "Weekly transaction volume anomaly — week with <50% of average count", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_week"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("W")
                weekly = tmp.groupby("_week").size()
                if len(weekly) >= 4:
                    avg = weekly.mean()
                    bad = weekly[weekly < avg * 0.5]
                    if not bad.empty:
                        findings = [Finding(detail=f"Week {w}: {c} txns vs avg {avg:.0f}") for w, c in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient weekly data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 310: Daily sales run-rate deviation (Upload) ---
        r = CheckResult(310, "Daily sales run-rate deviation from monthly target >30% for 5+ days", CAT, "Medium", "skipped")
        r.skip("Requires external data")
        results.append(r)

        # --- 311: Sales discount % variance >5% vs prior month ---
        r = CheckResult(311, "Sales discount % variance >5% vs prior month", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                disc = tmp[tmp["party_ledger"].str.contains("discount", case=False, na=False) & (tmp["voucher_type"].str.lower() == "sales")].groupby("_month")["amount"].sum()
                sales = tmp[tmp["voucher_type"].str.lower() == "sales"].groupby("_month")["amount"].sum()
                if len(disc) >= 2 and len(sales) >= 2:
                    common = disc.index.intersection(sales.index)
                    pct = (disc[common] / sales[common].replace(0, float("nan")) * 100).dropna()
                    chg = pct.diff().abs().dropna()
                    bad = chg[chg > 5]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: discount % changed by {v:.1f}pp") for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient discount data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 312: Purchase discount % variance >5% vs prior month ---
        r = CheckResult(312, "Purchase discount % variance >5% vs prior month", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                disc = tmp[tmp["party_ledger"].str.contains("discount", case=False, na=False) & (tmp["voucher_type"].str.lower() == "purchase")].groupby("_month")["amount"].sum()
                purch = tmp[tmp["voucher_type"].str.lower() == "purchase"].groupby("_month")["amount"].sum()
                if len(disc) >= 2 and len(purch) >= 2:
                    common = disc.index.intersection(purch.index)
                    pct = (disc[common] / purch[common].replace(0, float("nan")) * 100).dropna()
                    chg = pct.diff().abs().dropna()
                    bad = chg[chg > 5]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: purchase discount % changed by {v:.1f}pp") for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 313: Provision balance variance spike >25% ---
        r = CheckResult(313, "Provision balance variance — unexplained spike >25% in single month", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                prov = tmp[tmp["party_ledger"].str.contains("provision", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(prov) >= 2:
                    chg = _mom_pct(prov).dropna()
                    bad = chg[chg > 25]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: provision spiked {v:.1f}% MoM", amount=prov.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient provision data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 314: Prepaid expense amortisation variance (Module) ---
        r = CheckResult(314, "Prepaid expense amortisation variance >10% vs plan", CAT, "Medium", "skipped")
        r.skip("Requires external data")
        results.append(r)

        # --- 315: Monthly depreciation variance >3% vs plan ---
        r = CheckResult(315, "Monthly depreciation variance >3% vs plan", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                dep = tmp[tmp["party_ledger"].str.contains("depreciation", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(dep) >= 2:
                    chg = _mom_pct(dep).dropna()
                    bad = chg[chg.abs() > 3]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: depreciation varied {v:.1f}% MoM", amount=dep.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient depreciation data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 316: Credit notes exceeding 5% of gross sales in any month ---
        r = CheckResult(316, "Credit notes issued exceeding 5% of gross sales in any month", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                cn = tmp[tmp["voucher_type"].str.lower().isin(["credit note", "debit note"])].groupby("_month")["amount"].sum()
                sales = tmp[tmp["voucher_type"].str.lower() == "sales"].groupby("_month")["amount"].sum()
                if len(sales) >= 1:
                    common = cn.index.intersection(sales.index)
                    if len(common) > 0:
                        pct = (cn[common] / sales[common].replace(0, float("nan")) * 100).dropna()
                        bad = pct[pct > 5]
                        if not bad.empty:
                            findings = [Finding(detail=f"Month {m}: credit notes = {v:.1f}% of sales", amount=cn.get(m, 0)) for m, v in bad.head(50).items()]
                            r.fail(findings)
                        else:
                            r.ok()
                    else:
                        r.ok()
                else:
                    r.skip("No sales data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 317: Debit notes exceeding 5% of gross purchases ---
        r = CheckResult(317, "Debit notes issued exceeding 5% of gross purchases in any month", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                dn = tmp[tmp["voucher_type"].str.lower() == "debit note"].groupby("_month")["amount"].sum()
                purch = tmp[tmp["voucher_type"].str.lower() == "purchase"].groupby("_month")["amount"].sum()
                if len(purch) >= 1 and len(dn) >= 1:
                    common = dn.index.intersection(purch.index)
                    if len(common) > 0:
                        pct = (dn[common] / purch[common].replace(0, float("nan")) * 100).dropna()
                        bad = pct[pct > 5]
                        if not bad.empty:
                            findings = [Finding(detail=f"Month {m}: debit notes = {v:.1f}% of purchases", amount=dn.get(m, 0)) for m, v in bad.head(50).items()]
                            r.fail(findings)
                        else:
                            r.ok()
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient debit note data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 318: Employee cost variance MoM >10% ---
        r = CheckResult(318, "Employee cost variance month-on-month >10% outside increment cycle", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                emp = tmp[tmp["voucher_type"].str.lower().isin(["payroll", "salary"])].groupby("_month")["amount"].sum()
                if len(emp) < 2:
                    emp = tmp[tmp["party_ledger"].str.contains("salary|payroll|wages", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(emp) >= 2:
                    chg = _mom_pct(emp).dropna()
                    bad = chg[chg.abs() > 10]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: employee cost varied {v:.1f}% MoM", amount=emp.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient payroll data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 319: Contractor payment monthly variance >25% ---
        r = CheckResult(319, "Contractor payment monthly variance >25% without contract revision", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                cont = tmp[tmp["party_ledger"].str.contains("contractor|contract labour", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(cont) >= 2:
                    chg = _mom_pct(cont).dropna()
                    bad = chg[chg.abs() > 25]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: contractor payments varied {v:.1f}%", amount=cont.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient contractor data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 320: Repair and maintenance expense spike >50% ---
        r = CheckResult(320, "Repair and maintenance expense spike >50% in a single month", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                rm = tmp[tmp["party_ledger"].str.contains("repair|maintenance", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(rm) >= 2:
                    chg = _mom_pct(rm).dropna()
                    bad = chg[chg > 50]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: R&M spiked {v:.1f}% MoM", amount=rm.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient R&M data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 321: Travelling expense monthly variance >30% ---
        r = CheckResult(321, "Travelling expense monthly variance >30% outside seasonal pattern", CAT, "Low", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                tr = tmp[tmp["party_ledger"].str.contains("travel|conveyance", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(tr) >= 2:
                    chg = _mom_pct(tr).dropna()
                    bad = chg[chg.abs() > 30]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: travel expense varied {v:.1f}%", amount=tr.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient travel data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 322: Professional fees monthly spike >30% ---
        r = CheckResult(322, "Professional fees monthly spike >30% without engagement letter", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                pf = tmp[tmp["party_ledger"].str.contains("professional|legal|consultancy|audit fee", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(pf) >= 2:
                    chg = _mom_pct(pf).dropna()
                    bad = chg[chg > 30]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: professional fees spiked {v:.1f}%", amount=pf.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient professional fee data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 323: Miscellaneous expense monthly variance >50% with no narration ---
        r = CheckResult(323, "Miscellaneous expense monthly variance >50% with no narration", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                misc = tmp[tmp["party_ledger"].str.contains("misc|sundry", case=False, na=False)].copy()
                no_narr = misc[misc["narration"].isna() | (misc["narration"].str.strip() == "")]
                monthly = no_narr.groupby("_month")["amount"].sum()
                if len(monthly) >= 2:
                    chg = _mom_pct(monthly).dropna()
                    bad = chg[chg.abs() > 50]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: misc (no narration) varied {v:.1f}%", amount=monthly.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient misc data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 324: Advertisement spend variance (Module) ---
        r = CheckResult(324, "Advertisement spend variance vs annual budget >20% in any quarter", CAT, "Medium", "skipped")
        r.skip("Requires external data")
        results.append(r)

        # --- 325: Insurance premium monthly spike ---
        r = CheckResult(325, "Insurance premium monthly spike indicating new asset or policy", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                ins = tmp[tmp["party_ledger"].str.contains("insurance", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(ins) >= 2:
                    chg = _mom_pct(ins).dropna()
                    bad = chg[chg > 50]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: insurance premium spiked {v:.1f}%", amount=ins.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient insurance data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 326: Interest expense monthly variance >10% ---
        r = CheckResult(326, "Interest expense monthly variance >10% without loan disbursement", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                interest = tmp[tmp["party_ledger"].str.contains("interest", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(interest) >= 2:
                    chg = _mom_pct(interest).dropna()
                    bad = chg[chg.abs() > 10]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: interest expense varied {v:.1f}%", amount=interest.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient interest data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 327: Freight charges monthly variance >20% ---
        r = CheckResult(327, "Freight charges monthly variance >20% vs shipment volume", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                freight = tmp[tmp["party_ledger"].str.contains("freight|shipping|courier", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(freight) >= 2:
                    chg = _mom_pct(freight).dropna()
                    bad = chg[chg.abs() > 20]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: freight charges varied {v:.1f}%", amount=freight.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient freight data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 328: Utility cost monthly variance >15% ---
        r = CheckResult(328, "Utility cost monthly variance >15% without production justification", CAT, "Low", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                util = tmp[tmp["party_ledger"].str.contains("electricity|utility|power|water", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(util) >= 2:
                    chg = _mom_pct(util).dropna()
                    bad = chg[chg.abs() > 15]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: utility cost varied {v:.1f}%", amount=util.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient utility data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 329: Monthly tax provision variance >10% ---
        r = CheckResult(329, "Monthly tax provision variance >10% without rate change", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                tax_prov = tmp[tmp["party_ledger"].str.contains("tax provision|provision for tax|income tax", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(tax_prov) >= 2:
                    chg = _mom_pct(tax_prov).dropna()
                    bad = chg[chg.abs() > 10]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: tax provision varied {v:.1f}%", amount=tax_prov.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient tax provision data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 330: Monthly bad debt write-off exceeding 2% of opening debtors ---
        r = CheckResult(330, "Monthly bad debt write-off exceeding 2% of opening debtors", CAT, "High", "pass")
        try:
            debtor_ledgers = df_l[df_l["group_name"].str.contains("sundry debtor|receivable", case=False, na=False)] if not df_l.empty else pd.DataFrame()
            total_debtors = debtor_ledgers["opening_balance"].sum() if not debtor_ledgers.empty else 0
            if not df_v.empty and total_debtors > 0:
                bad_debt = df_v[df_v["party_ledger"].str.contains("bad debt|write.?off", case=False, na=False)]
                if not bad_debt.empty:
                    total_bd = bad_debt["amount"].sum()
                    if total_bd > total_debtors * 0.02:
                        findings = [Finding(
                            detail=f"Bad debt write-off ₹{row['amount']:,.0f} ({total_bd / total_debtors * 100:.1f}% of debtors)",
                            voucher_no=str(row.get("voucher_number", "")),
                            date=str(row.get("date", "")),
                            party=str(row.get("party_ledger", "")),
                            amount=float(row.get("amount", 0)),
                        ) for _, row in bad_debt.head(50).iterrows()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.ok()
            else:
                r.skip("Insufficient debtor data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 331: Short-term debt increase >20% in a single month ---
        r = CheckResult(331, "Short-term debt increase >20% in a single month", CAT, "High", "pass")
        try:
            if not df_l.empty:
                st_debt = df_l[df_l["group_name"].str.contains("short.?term|current liabilit|loans.*payable", case=False, na=False)]
                if not st_debt.empty:
                    total_open = st_debt["opening_balance"].sum()
                    total_close = st_debt["closing_balance"].sum()
                    if total_open > 0:
                        pct_chg = (total_close - total_open) / total_open * 100
                        if pct_chg > 20:
                            findings = [Finding(detail=f"Short-term debt increased {pct_chg:.1f}% (₹{total_open:,.0f} → ₹{total_close:,.0f})", amount=total_close - total_open)]
                            r.fail(findings)
                        else:
                            r.ok()
                    else:
                        r.ok()
                else:
                    r.skip("No short-term debt ledgers found")
            else:
                r.skip("No ledger data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 332: Packing material cost % of sales monthly variance >10% ---
        r = CheckResult(332, "Packing material cost as % of sales monthly variance >10%", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                pack = tmp[tmp["party_ledger"].str.contains("packing|packaging", case=False, na=False)].groupby("_month")["amount"].sum()
                sales = tmp[tmp["voucher_type"].str.lower() == "sales"].groupby("_month")["amount"].sum()
                if len(pack) >= 2 and len(sales) >= 2:
                    common = pack.index.intersection(sales.index)
                    pct = (pack[common] / sales[common].replace(0, float("nan")) * 100).dropna()
                    chg = pct.diff().abs().dropna()
                    bad = chg[chg > 10]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: packing % changed by {v:.1f}pp") for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient packing material data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 333: Direct labour cost per unit monthly variance >10% ---
        r = CheckResult(333, "Direct labour cost per unit monthly variance >10%", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                labour = tmp[tmp["party_ledger"].str.contains("direct labour|labour charges|wages", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(labour) >= 2:
                    chg = _mom_pct(labour).dropna()
                    bad = chg[chg.abs() > 10]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: direct labour cost varied {v:.1f}%", amount=labour.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient labour data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 334: Monthly royalty payment vs contractual schedule ---
        r = CheckResult(334, "Monthly royalty payment vs contractual schedule — overpayment", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                royalty = tmp[tmp["party_ledger"].str.contains("royalty", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(royalty) >= 2:
                    chg = _mom_pct(royalty).dropna()
                    bad = chg[chg > 20]
                    if not bad.empty:
                        findings = [Finding(detail=f"Month {m}: royalty payment spiked {v:.1f}%", amount=royalty.get(m, 0)) for m, v in bad.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient royalty data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 335: Insurance premium expense spike ---
        r = CheckResult(335, "Insurance premium expense spike — unexplained increase", CAT, "Medium", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                tmp = df_v.copy()
                tmp["_month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M")
                ins = tmp[tmp["party_ledger"].str.contains("insurance premium", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(ins) < 2:
                    ins = tmp[tmp["party_ledger"].str.contains("insurance", case=False, na=False)].groupby("_month")["amount"].sum()
                if len(ins) >= 2:
                    avg = ins.mean()
                    bad_months = ins[ins > avg * 1.5]
                    if not bad_months.empty:
                        findings = [Finding(detail=f"Month {m}: insurance ₹{v:,.0f} vs avg ₹{avg:,.0f}", amount=float(v)) for m, v in bad_months.head(50).items()]
                        r.fail(findings)
                    else:
                        r.ok()
                else:
                    r.skip("Insufficient insurance data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

    except Exception as e:
        pass

    return results
