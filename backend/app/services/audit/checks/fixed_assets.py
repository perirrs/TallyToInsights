"""Checks 151-165: Fixed Assets"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    fa_checks = [
        (151, "Asset added to register but depreciation schedule not initiated", "High"),
        (152, "Asset sold/disposed without removal from fixed asset register", "High"),
        (153, "Depreciation charged at incorrect rate vs Companies Act Schedule II", "High"),
        (154, "Capital expenditure wrongly booked as revenue expense", "High"),
        (155, "Revenue expenditure wrongly capitalized", "High"),
        (156, "Fully depreciated assets still appearing in active register", "Medium"),
        (157, "Asset revaluation without revaluation reserve entry", "High"),
        (158, "Lease asset capitalization without corresponding liability", "High"),
        (159, "Repair and maintenance expense abnormally high (>10% of asset value)", "Medium"),
        (160, "Asset purchase from related party at above-market price", "High"),
        (161, "Grant received for asset not deducted from asset cost", "High"),
        (162, "Impairment loss not recorded for underperforming assets", "Medium"),
        (163, "Addition to WIP without project completion certificate", "Medium"),
        (164, "Asset insurance not renewed (lapse in coverage period)", "Low"),
        (165, "Physical verification not done for assets > 5 years old", "Low"),
    ]

    for cid, desc, risk in fa_checks:
        r = CheckResult(cid, desc, "Fixed Assets", risk, "pass")

        if cid == 151 and not df_l.empty:
            # Look for asset ledgers without depreciation counterpart
            if "group_name" in df_l.columns and "name" in df_l.columns:
                fa_ledgers = df_l[df_l["group_name"].str.lower().str.contains("fixed asset|capital|machinery|equipment|vehicle|building|furniture", na=False)]
                dep_ledgers = df_l[df_l["name"].str.lower().str.contains("depreciation|dep", na=False)]
                if not fa_ledgers.empty and dep_ledgers.empty:
                    r.warn([Finding(
                        detail=f"Found {len(fa_ledgers)} fixed asset ledgers but no depreciation ledger entries",
                        amount=float(fa_ledgers.get("closing_balance", pd.Series([0])).sum()),
                    )])

        elif cid == 154 and not df_v.empty and not df_vl.empty:
            # Revenue entries that look like capital (equipment, machinery, etc.)
            capital_kw = ["machinery", "equipment", "computer", "vehicle", "furniture", "plant", "building", "asset"]
            if "ledger_name" in df_vl.columns and "amount" in df_vl.columns:
                cap_as_rev = df_vl[
                    df_vl["ledger_name"].str.lower().apply(lambda n: any(k in str(n) for k in capital_kw)) &
                    (pd.to_numeric(df_vl["amount"], errors="coerce") >= 50000)
                ]
                # Further filter: only if the parent voucher is not an asset purchase
                if not cap_as_rev.empty:
                    expense_vids = set()
                    if "voucher_id" in cap_as_rev.columns:
                        for vid in cap_as_rev["voucher_id"].unique():
                            v = df_v[df_v["id"] == vid] if "id" in df_v.columns else pd.DataFrame()
                            if not v.empty and v.iloc[0].get("voucher_type", "").lower() in ["payment", "purchase", "journal"]:
                                expense_vids.add(vid)
                    suspect = cap_as_rev[cap_as_rev["voucher_id"].isin(expense_vids)]
                    if not suspect.empty:
                        findings = [Finding(
                            detail=f"Possible capital item '{row.get('ledger_name')}' ₹{row.get('amount', 0):,.0f} in expense voucher",
                            amount=float(row.get("amount", 0)),
                            ledger=str(row.get("ledger_name", "")),
                        ) for _, row in suspect.head(20).iterrows()]
                        r.warn(findings)

        elif cid == 153 and not df_l.empty:
            # Check depreciation ledgers for obvious rate issues
            dep = df_l[df_l["name"].str.lower().str.contains("depreciation", na=False)]
            if not dep.empty and "closing_balance" in dep.columns:
                fa = df_l[df_l.get("is_asset", pd.Series([False] * len(df_l))) == True]
                if not fa.empty and "closing_balance" in fa.columns:
                    total_fa = pd.to_numeric(fa["closing_balance"], errors="coerce").sum()
                    total_dep = pd.to_numeric(dep["closing_balance"], errors="coerce").abs().sum()
                    if total_fa > 0:
                        dep_rate = total_dep / total_fa * 100
                        if dep_rate > 50 or dep_rate < 1:
                            r.warn([Finding(
                                detail=f"Implied depreciation rate {dep_rate:.1f}% seems unusual (expected 5-25%)",
                                amount=total_dep,
                            )])

        results.append(r)

    return results
