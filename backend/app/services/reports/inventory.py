from sqlalchemy.orm import Session
from app.models.stock import StockItem, StockVoucherLine


def get_inventory_report(dump_id: int, db: Session) -> dict:
    items = db.query(StockItem).filter(StockItem.dump_id == dump_id).all()

    summary = []
    total_opening = 0.0
    total_closing = 0.0

    for item in items:
        opening_val = float(item.opening_value or 0)
        closing_val = float(item.closing_value or 0)
        opening_qty = float(item.opening_qty or 0)
        closing_qty = float(item.closing_qty or 0)

        total_opening += opening_val
        total_closing += closing_val

        avg_rate = closing_val / closing_qty if closing_qty > 0 else 0

        summary.append({
            "id": item.id,
            "name": item.name,
            "group": item.group_name,
            "unit": item.unit,
            "hsn_code": item.hsn_code,
            "gst_rate": float(item.gst_rate or 0),
            "opening_qty": opening_qty,
            "opening_value": opening_val,
            "closing_qty": closing_qty,
            "closing_value": closing_val,
            "avg_rate": round(avg_rate, 4),
            "is_negative": closing_qty < 0,
            "is_slow_moving": closing_val > 500000 and closing_qty > 0,
        })

    # Group summary
    groups: dict[str, dict] = {}
    for item in summary:
        g = item["group"] or "Ungrouped"
        if g not in groups:
            groups[g] = {"group": g, "items": 0, "closing_value": 0}
        groups[g]["items"] += 1
        groups[g]["closing_value"] += item["closing_value"]

    return {
        "dump_id": dump_id,
        "total_items": len(items),
        "total_opening_value": round(total_opening, 2),
        "total_closing_value": round(total_closing, 2),
        "negative_stock_items": [i for i in summary if i["is_negative"]],
        "slow_moving_items": [i for i in summary if i["is_slow_moving"]],
        "group_summary": sorted(list(groups.values()), key=lambda x: -x["closing_value"]),
        "items": sorted(summary, key=lambda x: -x["closing_value"])[:200],
    }
