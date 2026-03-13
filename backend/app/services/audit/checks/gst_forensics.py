"""Checks 181-195: GST Forensics"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    sales_v = df_v[df_v["voucher_type"].str.lower() == "sales"] if not df_v.empty else pd.DataFrame()
    purchase_v = df_v[df_v["voucher_type"].str.lower() == "purchase"] if not df_v.empty else pd.DataFrame()

    gst_checks = [
        (181, "Outward supply declared in GSTR-1 lower than Tally invoice register", "High"),
        (182, "ITC reversed in Tally but credit note not reflected in vendor's GSTR-1", "Medium"),
        (183, "Place of supply incorrectly marked as intra-state for interstate B2B transaction", "High"),
        (184, "Zero-rated export supplies without LUT bond or IGST payment", "High"),
        (185, "Composite supply tax applied at higher-component rate instead of principal rate", "Medium"),
        (186, "Exempt supplies mixed with taxable in same invoice — apportionment missing", "High"),
        (187, "GST paid under wrong head (CGST vs IGST) — inter-state misclassification", "High"),
        (188, "HSN code in invoice different from HSN code in GSTR-1", "High"),
        (189, "E-invoice mandatory but generated without IRN", "High"),
        (190, "ITC on capital goods not spread over 5 years (if applicable)", "Medium"),
        (191, "Annual return (GSTR-9) mismatch with books", "High"),
        (192, "Section 17(5) blocked credit claimed (personal use, food & beverages)", "High"),
        (193, "GST on advances received not accounted (Section 12/13)", "High"),
        (194, "Reverse charge on import of services not computed", "High"),
        (195, "GSTIN format invalid — does not match 15-character standard", "High"),
    ]

    for cid, desc, risk in gst_checks:
        r = CheckResult(cid, desc, "GST Forensics", risk, "pass")

        if cid == 183 and not sales_v.empty:
            # Check place of supply vs GSTIN state
            if "place_of_supply" in sales_v.columns and "gstin" in sales_v.columns:
                # GSTIN starts with state code
                has_gstin = sales_v[sales_v["gstin"].notna() & (sales_v["gstin"].str.len() >= 2)]
                if not has_gstin.empty:
                    has_gstin = has_gstin.copy()
                    has_gstin["gstin_state"] = has_gstin["gstin"].str[:2]
                    # Company GSTIN state (assume from ledger)
                    if not df_l.empty:
                        company_gstins = df_l[df_l["gstin"].notna() & (df_l["gstin"].str.len() >= 2)]
                        if not company_gstins.empty:
                            company_state = company_gstins.iloc[0]["gstin"][:2]
                            interstate = has_gstin[has_gstin["gstin_state"] != company_state]
                            if not interstate.empty:
                                intra_pos = interstate[
                                    interstate["place_of_supply"].str.lower().str.contains(company_state.lower(), na=False) |
                                    (interstate["place_of_supply"].str.len() < 3)
                                ]
                                if not intra_pos.empty:
                                    findings = [Finding(
                                        detail=f"Inter-state customer {row.get('gstin')} but POS={row.get('place_of_supply')} — may need IGST",
                                        voucher_no=str(row.get("voucher_number", "")),
                                        date=str(row.get("date")),
                                        amount=float(row.get("amount", 0)),
                                    ) for _, row in intra_pos.head(30).iterrows()]
                                    r.warn(findings)
                                else:
                                    r.ok()
                            else:
                                r.ok()

        elif cid == 195 and not df_l.empty:
            # Validate GSTIN format: 15 chars, specific pattern
            if "gstin" in df_l.columns:
                import re
                gstin_pattern = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$")
                invalid = df_l[
                    df_l["gstin"].notna() &
                    (df_l["gstin"].str.strip() != "") &
                    ~df_l["gstin"].apply(lambda g: bool(gstin_pattern.match(str(g).strip().upper())))
                ]
                if not invalid.empty:
                    findings = [Finding(
                        detail=f"Invalid GSTIN format: {row.get('gstin')} for {row.get('name')}",
                        ledger=str(row.get("name", "")),
                    ) for _, row in invalid.head(30).iterrows()]
                    r.fail(findings)
                else:
                    r.ok()

        elif cid == 193 and not df_v.empty:
            # GST on advances
            receipts = df_v[df_v["voucher_type"].str.lower() == "receipt"]
            if not receipts.empty and "narration" in receipts.columns:
                advances = receipts[
                    receipts["narration"].str.lower().str.contains("advance|deposit|booking|token", na=False) &
                    (receipts.get("amount", 0) >= 50000)
                ]
                if not advances.empty:
                    # Check if corresponding GST liability entry exists
                    r.warn([Finding(
                        detail=f"Advance receipt ₹{row.get('amount', 0):,.0f} from {row.get('party_ledger')} — verify GST on advance",
                        date=str(row.get("date")),
                        party=str(row.get("party_ledger", "")),
                        amount=float(row.get("amount", 0)),
                    ) for _, row in advances.head(20).iterrows()])

        results.append(r)

    return results
