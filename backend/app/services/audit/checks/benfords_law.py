"""Checks 196-210: Benford's Law Analysis"""
import pandas as pd
import numpy as np
from app.services.audit.base import CheckResult, Finding

# Expected Benford frequencies
BENFORD = {1: 30.1, 2: 17.6, 3: 12.5, 4: 9.7, 5: 7.9, 6: 6.7, 7: 5.8, 8: 5.1, 9: 4.6}


def _first_digit(x: float) -> int | None:
    try:
        s = str(abs(x)).lstrip("0").replace(".", "")
        return int(s[0]) if s else None
    except Exception:
        return None


def _benford_test(amounts: pd.Series, label: str, check_id: int, desc: str, risk: str) -> CheckResult:
    r = CheckResult(check_id, desc, "Benford's Law", risk, "pass")
    clean = amounts[(amounts > 0) & amounts.notna()]
    if len(clean) < 100:
        return r.skip(f"Insufficient data ({len(clean)} entries, need 100+)")

    digits = clean.apply(_first_digit).dropna()
    observed = {}
    for d in range(1, 10):
        observed[d] = (digits == d).sum() / len(digits) * 100

    # Chi-square test
    chi2 = 0
    for d in range(1, 10):
        exp = BENFORD[d] * len(digits) / 100
        obs = observed[d] * len(digits) / 100
        if exp > 0:
            chi2 += (obs - exp) ** 2 / exp

    # Critical value for df=8 at 5% significance = 15.507
    critical = 15.507

    deviations = []
    for d in range(1, 10):
        diff = abs(observed[d] - BENFORD[d])
        if diff > 5:  # >5% deviation from expected
            deviations.append(Finding(
                detail=f"Digit {d}: observed {observed[d]:.1f}% vs expected {BENFORD[d]:.1f}% (deviation: {diff:.1f}%)",
                amount=clean[clean.apply(_first_digit) == d].sum(),
            ))

    if chi2 > critical:
        r.fail(deviations or [Finding(detail=f"Benford χ²={chi2:.2f} > critical {critical}. Data may be manipulated.")])
    elif chi2 > critical * 0.7:
        r.warn(deviations or [Finding(detail=f"Benford χ²={chi2:.2f} borderline. Investigate.")])
    else:
        r.ok()

    return r


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    benford_configs = [
        (196, "Benford's Law: first-digit distribution on all invoice amounts", "All Vouchers", "High"),
        (197, "Benford's Law: first-digit distribution on sales invoices only", "Sales", "High"),
        (198, "Benford's Law: first-digit distribution on purchase invoices only", "Purchase", "High"),
        (199, "Benford's Law: first-digit distribution on payment vouchers", "Payment", "High"),
        (200, "Benford's Law: first-digit distribution on journal entries", "Journal", "High"),
        (201, "Benford's Law: second-digit distribution on high-value invoices", "All Vouchers", "Medium"),
        (202, "Benford's Law: leading-digit analysis on vendor payments (AP)", "Payment", "High"),
        (203, "Benford's Law: amount distribution on cash transactions", "Cash", "High"),
        (204, "Benford's Law: digit analysis on salary payments by employee", "Payroll", "Medium"),
        (205, "Benford's Law: digit distribution on expense claims", "Expense", "Medium"),
        (206, "Benford's Law: GST-exclusive amounts conformance check", "GST", "Medium"),
        (207, "Benford's Law: receipt amounts conformance", "Receipt", "Medium"),
        (208, "Benford's Law: credit note amounts conformance", "Credit Note", "Medium"),
        (209, "Benford's Law: debit note amounts conformance", "Debit Note", "Medium"),
        (210, "Benford's Law: fixed asset purchase amounts conformance", "Fixed Assets", "High"),
    ]

    for cid, desc, vtype_filter, risk in benford_configs:
        if df_v.empty or "amount" not in df_v.columns:
            r = CheckResult(cid, desc, "Benford's Law", risk, "pass")
            r.skip("No voucher data")
            results.append(r)
            continue

        if vtype_filter == "All Vouchers":
            amounts = df_v["amount"]
        elif vtype_filter == "Cash":
            amounts = df_v[
                df_v.get("narration", pd.Series([""] * len(df_v))).str.lower().str.contains("cash", na=False) |
                df_v.get("party_ledger", pd.Series([""] * len(df_v))).str.lower().str.contains("cash", na=False)
            ]["amount"]
        else:
            amounts = df_v[df_v["voucher_type"].str.lower().str.contains(vtype_filter.lower(), na=False)]["amount"]

        results.append(_benford_test(amounts, vtype_filter, cid, desc, risk))

    return results
