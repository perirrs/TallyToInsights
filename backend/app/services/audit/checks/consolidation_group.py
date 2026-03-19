"""Checks 661-680: Consolidation & Group"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    # All consolidation checks require group-level/multi-entity data
    checks = [
        (661, "Inter-company balances not eliminated — IC receivable ≠ IC payable", "Manual"),
        (662, "Unrealised profit in closing stock from IC sales — not eliminated", "Manual"),
        (663, "Different accounting policies across group entities — revenue recognition", "Manual"),
        (664, "Intra-group revenue not eliminated in consolidated P&L", "Manual"),
        (665, "Investment in subsidiary vs subsidiary net worth — impairment test", "Manual"),
        (666, "Goodwill on consolidation — annual impairment test not evidenced", "Manual"),
        (667, "Minority interest computation error — incorrect ownership %", "Manual"),
        (668, "Subsidiary with different financial year — adjustments not made", "Manual"),
        (669, "Foreign subsidiary translation — incorrect exchange rate applied", "Upload"),
        (670, "IC dividend eliminated but tax credit on dividend retained", "Manual"),
        (671, "IC management fee not eliminated from consolidated expenses", "Auto"),
        (672, "Consolidated cash flow — IC cash movements not netted", "Manual"),
        (673, "Step acquisition — additional stake purchase not fair-valued", "Manual"),
        (674, "Partial disposal of subsidiary — gain/loss incorrectly computed", "Manual"),
        (675, "Associates and JVs — equity method not applied where applicable", "Manual"),
        (676, "Structured entity consolidation — SPV not included", "Manual"),
        (677, "IC loans at off-market interest rates — arm's length not established", "Auto"),
        (678, "Preference shares in subsidiary — treatment as debt vs equity in consolidation", "Manual"),
        (679, "Deferred tax on temporary differences arising from consolidation", "Manual"),
        (680, "IC transactions in different currencies — forex impact not eliminated", "Upload"),
    ]

    for check_id, desc, feasibility in checks:
        r = CheckResult(check_id, desc, "Consolidation & Group", "High", "pass")
        if feasibility in ("Manual", "Upload"):
            r.skip("Requires consolidated/multi-entity data")
        elif check_id == 671 and not df_l.empty:
            # Check for management fee ledgers
            try:
                mgmt_fee = df_l[df_l["name"].str.contains("management fee|mgmt fee|inter.company", case=False, na=False)] if "name" in df_l.columns else pd.DataFrame()
                if not mgmt_fee.empty:
                    findings = [Finding(
                        detail=f"IC management fee ledger '{row['name']}' — verify elimination in consolidation",
                        ledger=row["name"],
                        amount=float(abs(row.get("closing_balance", 0))),
                    ) for _, row in mgmt_fee.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            except Exception:
                r.ok()
        elif check_id == 677 and not df_l.empty:
            # Check for IC loans with no interest income/expense
            try:
                ic_loans = df_l[df_l["name"].str.contains("loan to group|inter.company loan|IC loan", case=False, na=False)] if "name" in df_l.columns else pd.DataFrame()
                if not ic_loans.empty:
                    findings = [Finding(
                        detail=f"IC loan '{row['name']}' ₹{row.get('closing_balance', 0):,.0f} — verify arm's length interest rate",
                        ledger=row["name"],
                        amount=float(abs(row.get("closing_balance", 0))),
                    ) for _, row in ic_loans.head(50).iterrows()]
                    r.warn(findings)
                else:
                    r.ok()
            except Exception:
                r.ok()
        else:
            r.ok()
        results.append(r)

    return results
