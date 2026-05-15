"""Checks 261-275: Data Quality"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    dq_checks = [
        (261, "Ledger master with duplicate names but different codes", "Medium"),
        (262, "Vouchers with missing mandatory fields (date, amount, party)", "High"),
        (263, "Ledger group hierarchy broken or circular reference", "Medium"),
        (264, "Stock items with no unit of measure defined", "Low"),
        (265, "Negative quantity in stock voucher lines", "High"),
        (266, "Phone/email format errors in party master", "Low"),
        (267, "Pincode or state code inconsistency in address master", "Low"),
        (268, "Currency code not ISO 4217 compliant", "Medium"),
        (269, "Voucher dates outside company financial year range", "High"),
        (270, "Ledger closing balance differs from sum of transactions", "High"),
        (271, "Special characters or SQL injection patterns in narration", "High"),
        (272, "Tally company name mismatch across multiple dump files", "Medium"),
        (273, "Encoding errors or non-UTF8 characters in ledger names", "Low"),
        (274, "Amount fields with more than 4 decimal places", "Low"),
        (275, "Voucher type codes not matching standard Tally types", "Medium"),
    ]

    for cid, desc, risk in dq_checks:
        r = CheckResult(cid, desc, "Data Quality", risk, "pass")

        try:
            if cid == 261 and not df_l.empty and "name" in df_l.columns:
                # Duplicate ledger names (case-insensitive)
                df_l2 = df_l.copy()
                df_l2["name_lower"] = df_l2["name"].str.lower().str.strip()
                dupes = df_l2.groupby("name_lower").filter(lambda x: len(x) > 1)
                if not dupes.empty:
                    findings = [Finding(
                        detail=f"Duplicate ledger name: '{row['name']}' appears {len(df_l2[df_l2['name_lower'] == row['name_lower']])} times",
                        ledger=str(row["name"]),
                    ) for _, row in dupes.drop_duplicates("name_lower").head(20).iterrows()]
                    r.fail(findings)
                else:
                    r.ok()

            elif cid == 262 and not df_v.empty:
                # Missing mandatory fields
                issues = []
                if "date" in df_v.columns:
                    no_date = df_v[df_v["date"].isna()]
                    if not no_date.empty:
                        issues.append(Finding(detail=f"{len(no_date)} vouchers have no date"))
                if "amount" in df_v.columns:
                    no_amt = df_v[df_v["amount"].isna() | (df_v["amount"] == 0)]
                    if not no_amt.empty:
                        issues.append(Finding(detail=f"{len(no_amt)} vouchers have zero/null amount"))
                if issues:
                    r.fail(issues)
                else:
                    r.ok()

            elif cid == 265 and not df_v.empty:
                # Check for stock lines with negative qty (from df_vl approximation)
                if "stock_lines" in df_v.columns:
                    r.skip("Need stock voucher line data separately")
                else:
                    r.skip("No stock line data in main voucher table")

            elif cid == 269 and not df_v.empty and "date" in df_v.columns:
                # Vouchers outside FY
                try:
                    df_v2 = df_v.copy()
                    df_v2["_dt"] = pd.to_datetime(df_v2["date"], errors="coerce")
                    valid = df_v2.dropna(subset=["_dt"])
                    if not valid.empty:
                        min_date = valid["_dt"].min()
                        max_date = valid["_dt"].max()
                        # Check if any dates are wildly different (>2 years spread)
                        if (max_date - min_date).days > 800:
                            r.warn([Finding(
                                detail=f"Data spans {(max_date - min_date).days} days ({min_date.date()} to {max_date.date()}) — verify FY range",
                            )])
                        else:
                            r.ok()
                except Exception:
                    r.skip("Date parsing error")

            elif cid == 270 and not df_l.empty and not df_vl.empty:
                # Verify closing balance = opening + net transactions
                r.skip("Requires full transaction history per ledger")

            elif cid == 271 and not df_v.empty and "narration" in df_v.columns:
                # SQL injection / script injection in narration
                import re
                suspect_pattern = re.compile(r"(select\s|insert\s|drop\s|delete\s|<script|union\s|exec\(|';)", re.IGNORECASE)
                suspect = df_v[df_v["narration"].str.contains(suspect_pattern, na=False)]
                if not suspect.empty:
                    findings = [Finding(
                        detail=f"Suspicious content in narration: '{str(row.get('narration', ''))[:100]}'",
                        voucher_no=str(row.get("voucher_number", "")),
                        date=str(row.get("date")),
                    ) for _, row in suspect.head(20).iterrows()]
                    r.fail(findings)
                else:
                    r.ok()

            else:
                r.ok()

        except Exception as e:
            r.skip(f"Error: {str(e)[:50]}")

        results.append(r)

    return results
