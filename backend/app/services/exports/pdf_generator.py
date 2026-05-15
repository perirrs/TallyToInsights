"""Generate a professional PDF report using ReportLab."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from sqlalchemy.orm import Session
from app.models.dump import DataDump
from app.models.company import Company
from app.models.audit_result import AuditResult
from app.services.reports.financial import get_financial_summary
from app.services.reports.dashboard import get_dashboard_kpis

NAVY = colors.HexColor("#003366")
LIGHT_BLUE = colors.HexColor("#E8F0FE")
RED = colors.HexColor("#CC0000")
GREEN = colors.HexColor("#006600")
ORANGE = colors.HexColor("#CC6600")
GREY = colors.HexColor("#F5F5F5")


def _risk_color(level: str) -> colors.Color:
    return {"High": RED, "Medium": ORANGE, "Low": GREEN}.get(level, colors.black)


def _status_color(status: str) -> colors.Color:
    return {"fail": RED, "warning": ORANGE, "pass": GREEN}.get(status, colors.grey)


def generate_full_report_pdf(dump_id: int, db: Session) -> bytes:
    dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
    company = db.query(Company).filter(Company.id == dump.company_id).first()
    company_name = company.name if company else f"Company #{dump.company_id}"
    period = f"{dump.period_from} to {dump.period_to}" if dump.period_from else "All Periods"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"TallyToInsights — {company_name}",
        author="TallyToInsights",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=20, textColor=NAVY, spaceAfter=6)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, textColor=NAVY, spaceBefore=12)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, textColor=NAVY, spaceBefore=8)
    body = styles["Normal"]
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8)

    story = []

    # ---- Cover Page ----
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("TallyToInsights", title_style))
    story.append(Paragraph("Comprehensive Audit & Financial Intelligence Report", h2))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY))
    story.append(Spacer(1, 0.5 * cm))

    cover_data = [
        ["Company", company_name],
        ["GSTIN", company.gstin or "N/A" if company else "N/A"],
        ["Period", period],
        ["Financial Year", dump.financial_year or "N/A"],
        ["Total Vouchers", str(dump.voucher_count)],
        ["Total Ledgers", str(dump.ledger_count)],
        ["Report Generated", datetime.now().strftime("%d %b %Y %H:%M")],
    ]
    cover_table = Table(cover_data, colWidths=[5 * cm, 11 * cm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, GREY]),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # ---- Executive Summary ----
    try:
        kpis = get_dashboard_kpis(dump_id, db)
        story.append(Paragraph("Executive Summary", h1))
        story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
        story.append(Spacer(1, 0.3 * cm))

        kpi_data = [
            ["Metric", "Value", "Metric", "Value"],
            ["Revenue", f"₹{kpis['revenue']:,.2f}", "Cash Position", f"₹{kpis['cash_position']:,.2f}"],
            ["Expenses", f"₹{kpis['expenses']:,.2f}", "Receivables", f"₹{kpis['receivables']:,.2f}"],
            ["Net Profit", f"₹{kpis['net_profit']:,.2f}", "Payables", f"₹{kpis['payables']:,.2f}"],
            ["Net Margin", f"{kpis['net_margin_pct']:.2f}%", "Amount at Risk", f"₹{kpis['amount_at_risk']:,.2f}"],
            ["Audit Score", f"{kpis['audit_health_score']:.1f}%", "High-Risk Issues", str(kpis['audit_high_risk'])],
        ]
        kt = Table(kpi_data, colWidths=[5 * cm, 6 * cm, 5 * cm, 6 * cm])
        kt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("FONTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (0, -1), LIGHT_BLUE),
            ("BACKGROUND", (2, 1), (2, -1), LIGHT_BLUE),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY]),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(kt)
        story.append(Spacer(1, 0.5 * cm))

        # Top issues
        if kpis["top_issues"]:
            story.append(Paragraph("Top Audit Concerns", h2))
            for issue in kpis["top_issues"]:
                clr = _risk_color(issue["risk_level"])
                story.append(Paragraph(
                    f"<font color='#{clr.hexval()[1:]}'>●</font> <b>[{issue['risk_level']}]</b> "
                    f"{issue['description']} — {issue['finding_count']} findings "
                    f"(₹{issue['amount_at_risk']:,.2f} at risk)",
                    body,
                ))
            story.append(Spacer(1, 0.3 * cm))
    except Exception as e:
        story.append(Paragraph(f"KPI summary unavailable: {e}", body))

    story.append(PageBreak())

    # ---- Financial Summary ----
    try:
        fs = get_financial_summary(dump_id, db)
        story.append(Paragraph("Financial Summary — P&L", h1))
        story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
        story.append(Spacer(1, 0.3 * cm))

        pl_data = [["Item", "Amount (₹)", "% Revenue"]]
        pl_data.append(["Revenue", f"{fs.revenue:,.2f}", "100.00%"])
        pl_data.append(["Expenses", f"{fs.expenses:,.2f}", f"{fs.expenses/fs.revenue*100:.2f}%" if fs.revenue else "N/A"])
        pl_data.append(["Gross Profit", f"{fs.gross_profit:,.2f}", f"{fs.gross_margin_pct:.2f}%"])
        pl_data.append(["Net Profit", f"{fs.net_profit:,.2f}", f"{fs.net_margin_pct:.2f}%"])
        pl_data.append(["Total Assets", f"{fs.total_assets:,.2f}", ""])
        pl_data.append(["Total Liabilities", f"{fs.total_liabilities:,.2f}", ""])
        pl_data.append(["Equity", f"{fs.equity:,.2f}", ""])

        plt = Table(pl_data, colWidths=[9 * cm, 5 * cm, 4 * cm])
        plt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("FONTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY]),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(plt)
    except Exception as e:
        story.append(Paragraph(f"Financial summary unavailable: {e}", body))

    story.append(PageBreak())

    # ---- Audit Report ----
    audit_results = db.query(AuditResult).filter(AuditResult.dump_id == dump_id).order_by(
        AuditResult.risk_level, AuditResult.check_id
    ).all()

    story.append(Paragraph("Audit Checks Summary — 300 Checks", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.3 * cm))

    # Category summary
    cat_map: dict[str, dict] = {}
    for r in audit_results:
        if r.category not in cat_map:
            cat_map[r.category] = {"total": 0, "fail": 0, "warn": 0, "pass": 0}
        cat_map[r.category]["total"] += 1
        if r.status == "fail":
            cat_map[r.category]["fail"] += 1
        elif r.status == "warning":
            cat_map[r.category]["warn"] += 1
        else:
            cat_map[r.category]["pass"] += 1

    cat_data = [["Category", "Total", "Pass", "Warnings", "Failures"]]
    for cat, d in sorted(cat_map.items()):
        cat_data.append([cat, d["total"], d["pass"], d["warn"], d["fail"]])

    ct = Table(cat_data, colWidths=[7 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("FONTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(ct)
    story.append(Spacer(1, 0.5 * cm))

    # Failed checks detail
    failed = [r for r in audit_results if r.status in ("fail", "warning")]
    if failed:
        story.append(Paragraph("Failed & Warning Checks — Detail", h2))
        story.append(Spacer(1, 0.2 * cm))

        for r in failed[:100]:  # first 100 failed checks in PDF
            risk_clr = _risk_color(r.risk_level)
            status_clr = _status_color(r.status)
            story.append(Paragraph(
                f"<b>#{r.check_id}</b> [{r.risk_level}] {r.check_description} — "
                f"<font color='#{status_clr.hexval()[1:]}'><b>{r.status.upper()}</b></font> "
                f"({r.finding_count} findings, ₹{r.amount_at_risk:,.2f} at risk)",
                small,
            ))
            # Show first 3 findings
            for f in (r.findings or [])[:3]:
                story.append(Paragraph(
                    f"   → {f.get('detail', '')} {f.get('voucher_no', '')} "
                    f"{str(f.get('date', ''))} ₹{f.get('amount', 0) or 0:,.2f}",
                    small,
                ))
            story.append(Spacer(1, 0.1 * cm))

    doc.build(story)
    buf.seek(0)
    return buf.read()
