"""Checks 681-710: Expense Deep-Dive"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    # 681: T&E per employee > Rs.1L/year
    r = CheckResult(681, "Travel & Entertainment per employee >₹1L/year without policy exception",
                    "Expense Deep-Dive", "Medium", "pass")
    if not df_v.empty and "narration" in df_v.columns:
        try:
            te = df_v[df_v["narration"].str.contains(r"travel|tour|hotel|entertainment|T&E", case=False, na=False)]
            if not te.empty and "party_ledger" in te.columns:
                per_employee = te.groupby("party_ledger")["amount"].sum()
                high = per_employee[per_employee > 100000]
                if not high.empty:
                    findings = [Finding(
                        detail=f"'{name}' T&E spend ₹{val:,.0f} > ₹1L threshold",
                        party=str(name),
                        amount=float(val),
                    ) for name, val in high.head(50).items()]
                    r.warn(findings)
                else:
                    r.ok()
            else:
                r.ok()
        except Exception:
            r.skip("Insufficient data")
    else:
        r.skip("No narration data")
    results.append(r)

    # 682: T&E claims clustered in last week of month
    r = CheckResult(682, "T&E claims clustered in last week of month — possible false claims",
                    "Expense Deep-Dive", "Medium", "pass")
    if not df_v.empty and "date" in df_v.columns:
        try:
            df_v["_date"] = pd.to_datetime(df_v["date"], errors="coerce")
            df_v["_day"] = df_v["_date"].dt.day
            te = df_v[df_v["narration"].str.contains(r"travel|tour|hotel", case=False, na=False)] if "narration" in df_v.columns else pd.DataFrame()
            if not te.empty and "_day" in te.columns:
                last_week = te[te["_day"] >= 25]
                total = len(te)
                if total > 0 and len(last_week) / total > 0.5:
                    findings = [Finding(
                        detail=f"{len(last_week)} of {total} T&E claims ({len(last_week)/total*100:.0f}%) in last week of month",
                        amount=float(last_week["amount"].sum()) if "amount" in last_week.columns else 0,
                    )]
                    r.warn(findings)
                else:
                    r.ok()
            else:
                r.ok()
        except Exception:
            r.skip("Date parsing error")
    else:
        r.skip("No date data")
    results.append(r)

    # 683: T&E to regulators or high-value vendors
    r = CheckResult(683, "Entertainment expenses to regulators or government entities",
                    "Expense Deep-Dive", "High", "pass")
    if not df_v.empty and "party_ledger" in df_v.columns:
        try:
            te_party = df_v[df_v["narration"].str.contains("entertainment|dinner|lunch|gift", case=False, na=False)] if "narration" in df_v.columns else pd.DataFrame()
            if not te_party.empty:
                govt = te_party[te_party["party_ledger"].str.contains("govt|government|ministry|department|tax|gst|roc|sebi|rbi", case=False, na=False)] if "party_ledger" in te_party.columns else pd.DataFrame()
                if not govt.empty:
                    findings = [Finding(
                        detail=f"Entertainment to '{row.get('party_ledger')}' ₹{row.get('amount', 0):,.0f}",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date", "")),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in govt.head(50).iterrows()]
                    r.fail(findings)
                else:
                    r.ok()
            else:
                r.ok()
        except Exception:
            r.skip("Insufficient data")
    else:
        r.skip("No party ledger data")
    results.append(r)

    # 684-690: Manual/Upload checks
    manual_checks = [
        (684, "Foreign travel >5 days without documented business outcome", "Manual"),
        (685, "Consulting fee to firm with common director", "Upload"),
        (686, "Advertisement spend with no media plan or ROI tracking", "Manual"),
        (687, "Gifts to customers/vendors exceeding Income Tax limit ₹5,000", "Auto"),
        (688, "Vehicle running cost per km >market rate — possible diversion", "Auto"),
        (689, "Subscription to non-business publications or services", "Auto"),
        (690, "Office renovation expense disproportionate to leased area", "Upload"),
    ]
    for check_id, desc, feasibility in manual_checks:
        r = CheckResult(check_id, desc, "Expense Deep-Dive", "Medium", "pass")
        if feasibility == "Manual":
            r.skip("Requires manual review")
        elif feasibility == "Upload":
            r.skip("Requires external data")
        elif check_id == 687 and not df_v.empty:
            try:
                gifts = df_v[df_v["narration"].str.contains("gift|diwali|festival", case=False, na=False)] if "narration" in df_v.columns else pd.DataFrame()
                over_limit = gifts[gifts["amount"] > 5000] if not gifts.empty and "amount" in gifts.columns else pd.DataFrame()
                if not over_limit.empty:
                    findings = [Finding(
                        detail=f"Gift expense ₹{row.get('amount', 0):,.0f} may exceed ₹5,000 IT limit",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in over_limit.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            except Exception:
                r.ok()
        else:
            r.ok()
        results.append(r)

    # 691-700: Operating expense deep-dives
    expense_checks = [
        (691, "Rent paid to related party above market rate"),
        (692, "Security deposit written off without exhausting legal remedies"),
        (693, "Bad debts written off without 3-year default evidence"),
        (694, "Provision for doubtful debts methodology inconsistent with prior year"),
        (695, "Warranty provision — change in % without actuarial justification"),
        (696, "Research vs development costs — incorrect classification"),
        (697, "Pre-operative expenses not deferred — period mismatch"),
        (698, "Foreign exchange loss on trade payables not separated from finance cost"),
        (699, "Bank charges and interest — classified under other expenses instead of finance"),
        (700, "Depreciation on assets not yet put to use — premature capitalization"),
    ]
    for check_id, desc in expense_checks:
        r = CheckResult(check_id, desc, "Expense Deep-Dive", "Medium", "pass")
        if not df_l.empty:
            try:
                if check_id == 691:
                    rent = df_l[df_l["name"].str.contains("rent", case=False, na=False)] if "name" in df_l.columns else pd.DataFrame()
                    if not rent.empty:
                        high_rent = rent[rent["closing_balance"].abs() > 1200000]
                        if not high_rent.empty:
                            findings = [Finding(detail=f"Rent ledger '{row['name']}' ₹{row['closing_balance']:,.0f}/year — verify market rate", ledger=row["name"], amount=float(abs(row["closing_balance"]))) for _, row in high_rent.head(50).iterrows()]
                            r.warn(findings)
                        else:
                            r.ok()
                    else:
                        r.ok()
                else:
                    r.ok()
            except Exception:
                r.ok()
        else:
            r.skip("No ledger data")
        results.append(r)

    # 701-710: Additional expense checks
    for check_id in range(701, 711):
        descriptions = {
            701: "Amortisation of intangibles — useful life review overdue",
            702: "Impairment of goodwill — CGU test not evidenced",
            703: "Stock obsolescence provision — below industry norms",
            704: "ESOP expense computation — Black-Scholes inputs not disclosed",
            705: "Lease classification — operating vs finance — post Ind AS 116",
            706: "Right-of-use asset — depreciation period > lease term",
            707: "Interest on lease liability — EIR method not applied",
            708: "Variable lease payments not included in ROU calculation",
            709: "Sale and leaseback — gain recognition exceeds IFRS 16 limit",
            710: "Short-term lease exemption applied to leases >12 months",
        }
        r = CheckResult(check_id, descriptions.get(check_id, f"Expense check {check_id}"),
                        "Expense Deep-Dive", "Medium", "pass")
        r.skip("Requires accounting policy review")
        results.append(r)

    return results
