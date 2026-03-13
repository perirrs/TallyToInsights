from sqlalchemy.orm import Session
from app.models.voucher import Voucher, VoucherLine
from app.schemas.report import GSTReport, GSTSummary


def get_gst_report(dump_id: int, db: Session) -> GSTReport:
    vouchers = db.query(Voucher).filter(Voucher.dump_id == dump_id).all()
    voucher_ids = [v.id for v in vouchers]

    vlines = db.query(VoucherLine).filter(
        VoucherLine.voucher_id.in_(voucher_ids)
    ).all() if voucher_ids else []

    # Map voucher_id -> voucher
    v_map = {v.id: v for v in vouchers}

    monthly: dict[str, dict] = {}

    for vl in vlines:
        gst_type = (vl.gst_type or "").upper()
        if gst_type not in ("CGST", "SGST", "IGST"):
            continue

        voucher = v_map.get(vl.voucher_id)
        if not voucher or not voucher.date:
            continue

        month_key = voucher.date.strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = {
                "month": month_key,
                "taxable_sales": 0.0, "cgst_collected": 0.0,
                "sgst_collected": 0.0, "igst_collected": 0.0,
                "taxable_purchases": 0.0, "itc_cgst": 0.0,
                "itc_sgst": 0.0, "itc_igst": 0.0,
            }

        amount = float(vl.amount or 0)
        vtype = (voucher.voucher_type or "").lower()

        if vtype == "sales":
            monthly[month_key]["taxable_sales"] += float(voucher.amount or 0)
            if gst_type == "CGST":
                monthly[month_key]["cgst_collected"] += amount
            elif gst_type == "SGST":
                monthly[month_key]["sgst_collected"] += amount
            elif gst_type == "IGST":
                monthly[month_key]["igst_collected"] += amount
        elif vtype == "purchase":
            monthly[month_key]["taxable_purchases"] += float(voucher.amount or 0)
            if gst_type == "CGST":
                monthly[month_key]["itc_cgst"] += amount
            elif gst_type == "SGST":
                monthly[month_key]["itc_sgst"] += amount
            elif gst_type == "IGST":
                monthly[month_key]["itc_igst"] += amount

    summaries = []
    total_output = 0.0
    total_itc = 0.0

    for month_key in sorted(monthly.keys()):
        m = monthly[month_key]
        output = m["cgst_collected"] + m["sgst_collected"] + m["igst_collected"]
        itc = m["itc_cgst"] + m["itc_sgst"] + m["itc_igst"]
        net = output - itc
        total_output += output
        total_itc += itc

        summaries.append(GSTSummary(
            month=month_key,
            taxable_sales=round(m["taxable_sales"], 2),
            cgst_collected=round(m["cgst_collected"], 2),
            sgst_collected=round(m["sgst_collected"], 2),
            igst_collected=round(m["igst_collected"], 2),
            total_tax=round(output, 2),
            taxable_purchases=round(m["taxable_purchases"], 2),
            itc_cgst=round(m["itc_cgst"], 2),
            itc_sgst=round(m["itc_sgst"], 2),
            itc_igst=round(m["itc_igst"], 2),
            total_itc=round(itc, 2),
            net_liability=round(net, 2),
        ))

    return GSTReport(
        dump_id=dump_id,
        monthly_summary=summaries,
        total_output_tax=round(total_output, 2),
        total_itc=round(total_itc, 2),
        net_payable=round(total_output - total_itc, 2),
    )
