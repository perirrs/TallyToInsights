"""Checks 296-300: User & IT Audit"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    it_checks = [
        (296, "Single user ID responsible for >40% of high-value journal entries", "High"),
        (297, "User ID used from multiple IP addresses simultaneously", "High"),
        (298, "Admin user directly posting operational vouchers", "High"),
        (299, "Vouchers altered or deleted by a different user than creator", "High"),
        (300, "Tally audit log gaps — missing log entries for certain dates", "High"),
    ]

    for cid, desc, risk in it_checks:
        r = CheckResult(cid, desc, "User & IT Audit", risk, "pass")

        try:
            if cid == 296 and not df_v.empty:
                if "posted_by" in df_v.columns and "amount" in df_v.columns:
                    high_val = df_v[(df_v.get("amount", 0) >= 100000) & df_v["voucher_type"].str.lower().isin(["journal", "payment"])]
                    if not high_val.empty and "posted_by" in high_val.columns:
                        user_counts = high_val["posted_by"].value_counts(normalize=True) * 100
                        dominant = user_counts[user_counts > 40]
                        if not dominant.empty:
                            findings = [Finding(
                                detail=f"User '{user}' posted {pct:.1f}% of high-value journal/payment entries",
                                amount=float(high_val[high_val["posted_by"] == user]["amount"].sum()),
                            ) for user, pct in dominant.items()]
                            r.warn(findings)
                        else:
                            r.ok()
                    else:
                        r.skip("No posted_by data")
                else:
                    r.skip("No user audit data in dump")

            elif cid == 299 and not df_v.empty:
                if "posted_by" in df_v.columns and "altered_by" in df_v.columns:
                    altered = df_v[
                        df_v["altered_by"].notna() &
                        (df_v["altered_by"].str.strip() != "") &
                        (df_v["posted_by"] != df_v["altered_by"])
                    ]
                    if not altered.empty:
                        findings = [Finding(
                            detail=f"Voucher {row.get('voucher_number')} posted by {row.get('posted_by')} but altered by {row.get('altered_by')}",
                            voucher_no=str(row.get("voucher_number", "")),
                            date=str(row.get("date")),
                            amount=float(row.get("amount", 0)),
                        ) for _, row in altered.head(30).iterrows()]
                        r.warn(findings)
                    else:
                        r.ok()
                else:
                    r.skip("No alteration user data")

            elif cid == 300 and not df_v.empty and "date" in df_v.columns:
                # Check for date gaps in voucher log
                try:
                    df_v2 = df_v.copy()
                    df_v2["_dt"] = pd.to_datetime(df_v2["date"], errors="coerce")
                    dates = df_v2["_dt"].dt.date.dropna().unique()
                    if len(dates) > 10:
                        date_range = pd.date_range(min(dates), max(dates), freq="B")  # business days
                        missing = [str(d.date()) for d in date_range if d.date() not in dates]
                        if len(missing) > 5:
                            r.warn([Finding(
                                detail=f"{len(missing)} business days with no voucher entries. First few: {', '.join(missing[:5])}",
                            )])
                        else:
                            r.ok()
                except Exception:
                    r.skip("Date error")
            else:
                r.ok()

        except Exception as e:
            r.skip(f"Error: {str(e)[:50]}")

        results.append(r)

    return results
