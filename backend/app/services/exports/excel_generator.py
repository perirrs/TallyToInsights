"""Generate comprehensive Excel report for a processed dump."""
import io
from datetime import datetime
import xlsxwriter
from sqlalchemy.orm import Session
from app.models.dump import DataDump
from app.models.company import Company
from app.models.audit_result import AuditResult
from app.services.reports.financial import get_financial_summary
from app.services.reports.cashflow import get_cash_flow_report
from app.services.reports.receivables import get_aging_report
from app.services.reports.gst import get_gst_report
from app.services.reports.dashboard import get_dashboard_kpis


def generate_excel_report(dump_id: int, db: Session) -> bytes:
    dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
    company = db.query(Company).filter(Company.id == dump.company_id).first()

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "default_date_format": "dd/mm/yyyy"})

    # Formats
    hdr = wb.add_format({"bold": True, "bg_color": "#003366", "font_color": "white", "border": 1, "align": "center"})
    title_fmt = wb.add_format({"bold": True, "font_size": 14, "bg_color": "#E8F0FE", "border": 1})
    num_fmt = wb.add_format({"num_format": "#,##0.00", "border": 1})
    pct_fmt = wb.add_format({"num_format": "0.00%", "border": 1})
    cell = wb.add_format({"border": 1})
    red_fmt = wb.add_format({"border": 1, "font_color": "#CC0000", "bold": True})
    green_fmt = wb.add_format({"border": 1, "font_color": "#006600", "bold": True})
    orange_fmt = wb.add_format({"border": 1, "font_color": "#CC6600", "bold": True})

    company_name = company.name if company else f"Company #{dump.company_id}"
    period = f"{dump.period_from} to {dump.period_to}" if dump.period_from else f"Dump #{dump_id}"

    # ---- Sheet 1: Dashboard ----
    try:
        kpis = get_dashboard_kpis(dump_id, db)
        ws = wb.add_worksheet("Dashboard")
        ws.set_column("A:A", 35)
        ws.set_column("B:B", 20)
        ws.merge_range("A1:B1", f"TallyToInsights — {company_name}", title_fmt)
        ws.merge_range("A2:B2", f"Period: {period}", cell)
        ws.write("A4", "Metric", hdr)
        ws.write("B4", "Value", hdr)
        kpi_rows = [
            ("Revenue", kpis["revenue"]),
            ("Expenses", kpis["expenses"]),
            ("Net Profit", kpis["net_profit"]),
            ("Cash Position", kpis["cash_position"]),
            ("Receivables", kpis["receivables"]),
            ("Payables", kpis["payables"]),
            ("Total Vouchers", kpis["total_vouchers"]),
            ("Audit Health Score (%)", kpis["audit_health_score"]),
            ("Audit Failures", kpis["audit_failures"]),
            ("High Risk Issues", kpis["audit_high_risk"]),
            ("Amount at Risk", kpis["amount_at_risk"]),
        ]
        for i, (label, val) in enumerate(kpi_rows, start=4):
            ws.write(i, 0, label, cell)
            ws.write(i, 1, val, num_fmt)
    except Exception:
        pass

    # ---- Sheet 2: Financial Summary ----
    try:
        fs = get_financial_summary(dump_id, db)
        ws = wb.add_worksheet("P&L Summary")
        ws.set_column("A:A", 40)
        ws.set_column("B:D", 18)
        ws.merge_range("A1:C1", "Profit & Loss Summary", title_fmt)
        headers = ["Ledger / Metric", "Amount (₹)", "% of Revenue"]
        for j, h in enumerate(headers):
            ws.write(1, j, h, hdr)
        row = 2
        ws.write(row, 0, "REVENUE", hdr)
        for lb in fs.revenue_ledgers:
            row += 1
            ws.write(row, 0, lb.name, cell)
            ws.write(row, 1, lb.amount, num_fmt)
            ws.write(row, 2, lb.percentage / 100, pct_fmt)
        row += 1
        ws.write(row, 0, "Total Revenue", hdr)
        ws.write(row, 1, fs.revenue, num_fmt)
        row += 2
        ws.write(row, 0, "EXPENSES", hdr)
        for lb in fs.expense_ledgers:
            row += 1
            ws.write(row, 0, lb.name, cell)
            ws.write(row, 1, lb.amount, num_fmt)
            ws.write(row, 2, lb.percentage / 100, pct_fmt)
        row += 1
        ws.write(row, 0, "Total Expenses", hdr)
        ws.write(row, 1, fs.expenses, num_fmt)
        row += 2
        ws.write(row, 0, "Gross Profit", hdr)
        ws.write(row, 1, fs.gross_profit, num_fmt)
        ws.write(row, 2, fs.gross_margin_pct / 100, pct_fmt)
        row += 1
        ws.write(row, 0, "Net Profit", hdr)
        ws.write(row, 1, fs.net_profit, num_fmt if fs.net_profit >= 0 else red_fmt)
        ws.write(row, 2, fs.net_margin_pct / 100, pct_fmt)
    except Exception:
        pass

    # ---- Sheet 3: Audit Results ----
    audit_results = db.query(AuditResult).filter(AuditResult.dump_id == dump_id).order_by(
        AuditResult.risk_level, AuditResult.check_id
    ).all()
    ws = wb.add_worksheet("Audit Results")
    ws.set_column("A:A", 8)
    ws.set_column("B:B", 50)
    ws.set_column("C:C", 25)
    ws.set_column("D:D", 10)
    ws.set_column("E:E", 12)
    ws.set_column("F:F", 12)
    ws.set_column("G:G", 18)
    ws.merge_range("A1:G1", f"Audit Report — {company_name} ({period})", title_fmt)
    headers = ["Check #", "Description", "Category", "Risk", "Status", "Findings", "Amount at Risk"]
    for j, h in enumerate(headers):
        ws.write(1, j, h, hdr)

    risk_color = {"High": red_fmt, "Medium": orange_fmt, "Low": green_fmt}
    status_color = {"fail": red_fmt, "warning": orange_fmt, "pass": green_fmt, "skipped": cell}

    for i, r in enumerate(audit_results, start=2):
        rfmt = risk_color.get(r.risk_level, cell)
        sfmt = status_color.get(r.status, cell)
        ws.write(i, 0, r.check_id, cell)
        ws.write(i, 1, r.check_description, cell)
        ws.write(i, 2, r.category, cell)
        ws.write(i, 3, r.risk_level, rfmt)
        ws.write(i, 4, r.status.upper(), sfmt)
        ws.write(i, 5, r.finding_count, cell)
        ws.write(i, 6, r.amount_at_risk or 0, num_fmt)

    # ---- Sheet 4: Audit Findings Detail ----
    ws2 = wb.add_worksheet("Audit Findings")
    ws2.set_column("A:A", 8)
    ws2.set_column("B:B", 35)
    ws2.set_column("C:C", 20)
    ws2.set_column("D:D", 12)
    ws2.set_column("E:E", 15)
    ws2.set_column("F:F", 18)
    ws2.set_column("G:G", 50)
    headers2 = ["Check #", "Category", "Voucher No", "Date", "Party", "Amount", "Detail"]
    ws2.merge_range("A1:G1", "Detailed Audit Findings", title_fmt)
    for j, h in enumerate(headers2):
        ws2.write(1, j, h, hdr)
    row = 2
    for r in audit_results:
        if r.status not in ("fail", "warning"):
            continue
        for f in (r.findings or []):
            ws2.write(row, 0, r.check_id, cell)
            ws2.write(row, 1, r.category, cell)
            ws2.write(row, 2, f.get("voucher_no", ""), cell)
            ws2.write(row, 3, str(f.get("date", "")), cell)
            ws2.write(row, 4, f.get("party", ""), cell)
            ws2.write(row, 5, f.get("amount", 0) or 0, num_fmt)
            ws2.write(row, 6, f.get("detail", ""), cell)
            row += 1
            if row > 10000:
                break

    # ---- Sheet 5: GST Summary ----
    try:
        gst = get_gst_report(dump_id, db)
        ws = wb.add_worksheet("GST Summary")
        ws.set_column("A:L", 15)
        ws.merge_range("A1:L1", "GST Monthly Summary", title_fmt)
        gst_headers = ["Month", "Taxable Sales", "CGST Out", "SGST Out", "IGST Out", "Total Output",
                       "Taxable Purchases", "ITC CGST", "ITC SGST", "ITC IGST", "Total ITC", "Net Liability"]
        for j, h in enumerate(gst_headers):
            ws.write(1, j, h, hdr)
        for i, m in enumerate(gst.monthly_summary, start=2):
            data_row = [
                m.month, m.taxable_sales, m.cgst_collected, m.sgst_collected,
                m.igst_collected, m.total_tax, m.taxable_purchases,
                m.itc_cgst, m.itc_sgst, m.itc_igst, m.total_itc, m.net_liability,
            ]
            for j, val in enumerate(data_row):
                ws.write(i, j, val, num_fmt if j > 0 else cell)
    except Exception:
        pass

    # ---- Sheet 6: Receivables Aging ----
    try:
        ar = get_aging_report(dump_id, "receivable", db)
        ws = wb.add_worksheet("Receivables Aging")
        ws.set_column("A:A", 40)
        ws.set_column("B:H", 18)
        ws.merge_range("A1:H1", f"Receivables Aging — Total Outstanding: ₹{ar.total_outstanding:,.2f}", title_fmt)
        headers = ["Party", "Current (0d)", "1-30 Days", "31-60 Days", "61-90 Days", "90+ Days", "Total", "Last Date"]
        for j, h in enumerate(headers):
            ws.write(1, j, h, hdr)
        for i, b in enumerate(ar.buckets, start=2):
            ws.write(i, 0, b.party, cell)
            ws.write(i, 1, b.current, num_fmt)
            ws.write(i, 2, b.days_1_30, num_fmt)
            ws.write(i, 3, b.days_31_60, num_fmt)
            ws.write(i, 4, b.days_61_90, num_fmt)
            ws.write(i, 5, b.days_90_plus, red_fmt if b.days_90_plus > 0 else num_fmt)
            ws.write(i, 6, b.total, num_fmt)
            ws.write(i, 7, str(b.oldest_date) if b.oldest_date else "", cell)
    except Exception:
        pass

    wb.close()
    buf.seek(0)
    return buf.read()
