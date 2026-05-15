from sqlalchemy.orm import Session
from app.models.voucher import Voucher


def get_payroll_report(dump_id: int, db: Session) -> dict:
    payroll_types = ["payroll", "salary", "wage"]
    vouchers = db.query(Voucher).filter(
        Voucher.dump_id == dump_id,
        Voucher.voucher_type.in_(payroll_types),
    ).order_by(Voucher.date).all()

    if not vouchers:
        return {
            "dump_id": dump_id,
            "total_vouchers": 0,
            "total_salary": 0,
            "monthly_salary": [],
            "employee_summary": [],
        }

    monthly: dict[str, dict] = {}
    employees: dict[str, dict] = {}

    for v in vouchers:
        if not v.date:
            continue
        month_key = v.date.strftime("%Y-%m")
        amount = float(v.amount or 0)
        emp = v.employee_name or v.party_ledger or "Unknown"

        if month_key not in monthly:
            monthly[month_key] = {"month": month_key, "total": 0.0, "count": 0}
        monthly[month_key]["total"] += amount
        monthly[month_key]["count"] += 1

        if emp not in employees:
            employees[emp] = {"employee": emp, "total": 0.0, "months": 0}
        employees[emp]["total"] += amount
        employees[emp]["months"] += 1

    total_salary = sum(v.get("total", 0) for v in monthly.values())

    return {
        "dump_id": dump_id,
        "total_vouchers": len(vouchers),
        "total_salary": round(total_salary, 2),
        "monthly_salary": sorted(list(monthly.values()), key=lambda x: x["month"]),
        "employee_summary": sorted(list(employees.values()), key=lambda x: -x["total"])[:100],
    }
