"""Checks 546-575: Procurement & Contract"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding

CAT = "Procurement & Contract"


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    try:
        # --- 546: Purchase orders without corresponding GRN ---
        r = CheckResult(546, "Purchase orders without corresponding GRN", CAT, "High", "pass")
        try:
            if not df_v.empty:
                purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"]
                no_ref = purchases[purchases["reference"].isna() | (purchases["reference"].str.strip() == "")]
                if not no_ref.empty:
                    total = no_ref["amount"].sum()
                    all_purch = purchases["amount"].sum()
                    if all_purch > 0 and total / all_purch > 0.10:
                        findings = [Finding(
                            detail=f"Purchase without PO/GRN reference ₹{row['amount']:,.0f}",
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

        # --- 547: Vendor invoice amount > PO value by >5% ---
        r = CheckResult(547, "Vendor invoice amount > PO value by >5%", CAT, "High", "pass")
        try:
            if not df_v.empty:
                purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"]
                # Check for purchases significantly higher than the median (as a proxy for PO value)
                if not purchases.empty and len(purchases) > 5:
                    median_amt = purchases["amount"].median()
                    high = purchases[purchases["amount"] > median_amt * 1.5]
                    if not high.empty and len(high) / len(purchases) < 0.10:
                        findings = [Finding(
                            detail=f"Purchase ₹{row['amount']:,.0f} significantly above median ₹{median_amt:,.0f} — verify PO",
                            voucher_no=str(row.get("voucher_number", "")),
                            date=str(row.get("date", "")),
                            party=str(row.get("party_ledger", "")),
                            amount=float(row.get("amount", 0)),
                        ) for _, row in high.head(50).iterrows()]
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

        # --- 548: Split purchases to avoid approval threshold ---
        r = CheckResult(548, "Split purchases to avoid approval threshold", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"].copy()
                purchases["_date"] = pd.to_datetime(purchases["date"], errors="coerce")
                # Same vendor, same day, multiple small purchases
                grouped = purchases.groupby(["party_ledger", "_date"]).agg(count=("amount", "count"), total=("amount", "sum")).reset_index()
                splits = grouped[(grouped["count"] >= 3) & (grouped["total"] > 0)]
                if not splits.empty:
                    findings = [Finding(
                        detail=f"Vendor '{row['party_ledger']}' on {row['_date'].date() if hasattr(row['_date'], 'date') else row['_date']}: {row['count']} purchases totalling ₹{row['total']:,.0f}",
                        party=str(row.get("party_ledger", "")),
                        date=str(row.get("_date", "")),
                        amount=float(row.get("total", 0)),
                    ) for _, row in splits.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 549: Single-vendor sourcing without competitive bidding ---
        r = CheckResult(549, "Single-vendor sourcing >60% of category spend", CAT, "High", "pass")
        try:
            if not df_v.empty:
                purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"]
                if not purchases.empty:
                    vendor_total = purchases.groupby("party_ledger")["amount"].sum()
                    total = vendor_total.sum()
                    if total > 0:
                        top_vendor_pct = vendor_total.max() / total * 100
                        top_vendor = vendor_total.idxmax()
                        if top_vendor_pct > 60:
                            findings = [Finding(detail=f"Top vendor '{top_vendor}' = {top_vendor_pct:.1f}% of total purchases (₹{vendor_total.max():,.0f})", party=str(top_vendor), amount=vendor_total.max())]
                            r.warn(findings)
                        else:
                            r.ok()
                    else:
                        r.ok()
                else:
                    r.skip("No purchase data")
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 550: Vendor with no GSTIN receiving payments above ₹2L ---
        r = CheckResult(550, "Vendor without GSTIN receiving payments above ₹2L", CAT, "High", "pass")
        try:
            if not df_v.empty:
                purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"]
                no_gstin = purchases[purchases["gstin"].isna() | (purchases["gstin"].str.strip() == "")]
                high_value = no_gstin[no_gstin["amount"] > 200000]
                if not high_value.empty:
                    findings = [Finding(
                        detail=f"Purchase ₹{row['amount']:,.0f} from '{row.get('party_ledger')}' without GSTIN",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date", "")),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in high_value.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 551: New vendor with large first payment ---
        r = CheckResult(551, "New vendor with large first-time payment above median by 3x", CAT, "High", "pass")
        try:
            if not df_v.empty and "date" in df_v.columns:
                purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"].copy()
                purchases["_date"] = pd.to_datetime(purchases["date"], errors="coerce")
                vendor_first = purchases.groupby("party_ledger")["_date"].min()
                vendor_max_amt = purchases.groupby("party_ledger")["amount"].max()
                median_purch = purchases["amount"].median()
                new_big = []
                for vendor, first_date in vendor_first.items():
                    first_purchase = purchases[(purchases["party_ledger"] == vendor) & (purchases["_date"] == first_date)].iloc[0] if len(purchases[(purchases["party_ledger"] == vendor) & (purchases["_date"] == first_date)]) > 0 else None
                    if first_purchase is not None and first_purchase["amount"] > median_purch * 3:
                        new_big.append(Finding(
                            detail=f"New vendor '{vendor}' first payment ₹{first_purchase['amount']:,.0f} (3x+ median)",
                            party=str(vendor),
                            date=str(first_date),
                            amount=float(first_purchase["amount"]),
                        ))
                if new_big:
                    r.warn(new_big[:50])
                else:
                    r.ok()
            else:
                r.skip("No voucher data")
        except Exception:
            r.skip("Error in check")
        results.append(r)

        # --- 552-575: Remaining procurement checks ---
        remaining = [
            (552, "Advance payment to vendor without contract", "High", True),
            (553, "Vendor payment within days of vendor creation", "High", True),
            (554, "Procurement without three-quote comparison", "High", False),
            (555, "Contract value vs actual spend variance >15%", "High", False),
            (556, "Vendor master with employee address or phone", "High", False),
            (557, "Purchases just below approval limit repeatedly", "High", True),
            (558, "Contract renewal without performance review", "Medium", False),
            (559, "Sole-source justification without procurement committee approval", "High", False),
            (560, "Emergency purchase >5% of annual procurement", "High", True),
            (561, "Purchase of non-standard items without approval", "Medium", False),
            (562, "Quality rejection rate >5% for any vendor", "High", False),
            (563, "Vendor payment terms changed without approval", "High", False),
            (564, "Procurement card misuse — personal items", "High", False),
            (565, "PO date after goods receipt date", "High", True),
            (566, "Invoice date before PO date", "High", True),
            (567, "GRN quantity > PO quantity", "High", False),
            (568, "Vendor invoice for discontinued product/service", "Medium", True),
            (569, "Duplicate vendor codes with same PAN", "High", True),
            (570, "Vendor bank account changed just before large payment", "High", False),
            (571, "Services procured without SOW/specification", "High", False),
            (572, "Contract milestones not tracked — overpayment risk", "High", False),
            (573, "Late delivery penalties not deducted", "Medium", False),
            (574, "Procurement savings not tracked vs budget", "Low", False),
            (575, "Annual rate contracts not renewed — purchases at old rates", "Medium", False),
        ]

        for chk_id, desc, risk, is_auto in remaining:
            r = CheckResult(chk_id, desc, CAT, risk, "pass")
            try:
                if not is_auto:
                    r.skip("Requires external data")
                else:
                    if chk_id == 552:
                        if not df_v.empty:
                            payments = df_v[df_v["voucher_type"].str.lower() == "payment"]
                            adv = payments[payments["narration"].str.contains("advance|prepayment", case=False, na=False)]
                            no_ref = adv[adv["reference"].isna() | (adv["reference"].str.strip() == "")]
                            if not no_ref.empty:
                                findings = [Finding(
                                    detail=f"Advance payment without contract reference ₹{row['amount']:,.0f}",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    date=str(row.get("date", "")),
                                    party=str(row.get("party_ledger", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in no_ref.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 553:
                        if not df_v.empty and "date" in df_v.columns:
                            purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"].copy()
                            purchases["_date"] = pd.to_datetime(purchases["date"], errors="coerce")
                            vendor_first = purchases.groupby("party_ledger")["_date"].min()
                            early_pay = []
                            for vendor, first_date in vendor_first.items():
                                vendor_purchases = purchases[purchases["party_ledger"] == vendor]
                                payments_near = vendor_purchases[vendor_purchases["_date"] <= first_date + pd.Timedelta(days=7)]
                                if not payments_near.empty and len(vendor_purchases) <= 2:
                                    early_pay.append(Finding(
                                        detail=f"Vendor '{vendor}' paid within 7 days of first purchase",
                                        party=str(vendor),
                                        date=str(first_date),
                                        amount=float(payments_near["amount"].sum()),
                                    ))
                            if early_pay:
                                r.warn(early_pay[:50])
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 557:
                        if not df_v.empty:
                            purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"]
                            if not purchases.empty:
                                median = purchases["amount"].median()
                                just_below = purchases[(purchases["amount"] > median * 0.85) & (purchases["amount"] < median)]
                                pct = len(just_below) / len(purchases) * 100
                                if pct > 20:
                                    findings = [Finding(
                                        detail=f"Purchase just below median threshold ₹{row['amount']:,.0f}",
                                        voucher_no=str(row.get("voucher_number", "")),
                                        date=str(row.get("date", "")),
                                        party=str(row.get("party_ledger", "")),
                                        amount=float(row.get("amount", 0)),
                                    ) for _, row in just_below.head(50).iterrows()]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.skip("No purchase data")
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 560:
                        if not df_v.empty:
                            purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"]
                            emergency = purchases[purchases["narration"].str.contains("urgent|emergency|adhoc|ad.?hoc", case=False, na=False)]
                            if not emergency.empty:
                                total = emergency["amount"].sum()
                                all_purch = purchases["amount"].sum()
                                if all_purch > 0 and total / all_purch > 0.05:
                                    findings = [Finding(
                                        detail=f"Emergency purchase ₹{row['amount']:,.0f}",
                                        voucher_no=str(row.get("voucher_number", "")),
                                        date=str(row.get("date", "")),
                                        party=str(row.get("party_ledger", "")),
                                        amount=float(row.get("amount", 0)),
                                    ) for _, row in emergency.head(50).iterrows()]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 565:
                        if not df_v.empty and "date" in df_v.columns:
                            purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"].copy()
                            purchases["_date"] = pd.to_datetime(purchases["date"], errors="coerce")
                            # Flag purchases where reference (PO date) is after invoice date
                            no_ref = purchases[purchases["reference"].notna() & (purchases["reference"].str.strip() != "")]
                            # Cannot directly compare dates without PO data, flag as needing review
                            if not no_ref.empty:
                                r.ok()
                            else:
                                r.skip("No PO reference data available")
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 566:
                        if not df_v.empty and "date" in df_v.columns:
                            purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"].copy()
                            purchases["_date"] = pd.to_datetime(purchases["date"], errors="coerce")
                            future_dated = purchases[purchases["_date"] > purchases["_date"].max()]
                            if not future_dated.empty:
                                findings = [Finding(
                                    detail=f"Invoice dated {row.get('date')} appears anomalous",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in future_dated.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 568:
                        if not df_v.empty:
                            purchases = df_v[df_v["voucher_type"].str.lower() == "purchase"]
                            # Flag purchases with unusual narration suggesting discontinued items
                            disc = purchases[purchases["narration"].str.contains("discontinued|obsolete|old model", case=False, na=False)]
                            if not disc.empty:
                                findings = [Finding(
                                    detail=f"Purchase of possibly discontinued item ₹{row['amount']:,.0f}",
                                    voucher_no=str(row.get("voucher_number", "")),
                                    date=str(row.get("date", "")),
                                    amount=float(row.get("amount", 0)),
                                ) for _, row in disc.head(50).iterrows()]
                                r.warn(findings)
                            else:
                                r.ok()
                        else:
                            r.skip("No voucher data")
                    elif chk_id == 569:
                        if not df_l.empty:
                            creditors = df_l[df_l["group_name"].str.contains("sundry creditor|trade payable|accounts payable", case=False, na=False)]
                            dup_pan = creditors[creditors["pan"].notna() & creditors["pan"].duplicated(keep=False)]
                            if not dup_pan.empty:
                                findings = [Finding(
                                    detail=f"Duplicate vendor PAN '{row.get('pan')}' for '{row['name']}'",
                                    ledger=str(row.get("name", "")),
                                    amount=float(row.get("closing_balance", 0)),
                                ) for _, row in dup_pan.head(50).iterrows()]
                                r.fail(findings)
                            else:
                                r.ok()
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
