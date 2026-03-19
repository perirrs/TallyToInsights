from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth import get_current_user
from app.models.user import User
import json
import os

router = APIRouter(prefix="/api/audit-checks", tags=["audit-checks"])

CHECKS_FILE = os.path.join(os.path.dirname(__file__), "../../../data/checks_735.json")
OVERRIDES_FILE = os.path.join(os.path.dirname(__file__), "../../../data/check_overrides.json")


def load_checks():
    if os.path.exists(CHECKS_FILE):
        with open(CHECKS_FILE) as f:
            return json.load(f)
    return []


def load_overrides():
    if os.path.exists(OVERRIDES_FILE):
        with open(OVERRIDES_FILE) as f:
            return json.load(f)
    return {"created": [], "updated": {}, "deleted": []}


def save_overrides(overrides):
    os.makedirs(os.path.dirname(OVERRIDES_FILE), exist_ok=True)
    with open(OVERRIDES_FILE, "w") as f:
        json.dump(overrides, f, indent=2)


def merge_checks():
    base = load_checks()
    overrides = load_overrides()
    deleted_ids = set(overrides.get("deleted", []))
    updated = overrides.get("updated", {})
    created = overrides.get("created", [])

    result = []
    for check in base:
        if check["id"] in deleted_ids:
            continue
        key = str(check["id"])
        if key in updated:
            result.append({**check, **updated[key]})
        else:
            result.append(check)

    result.extend(created)
    return result


@router.get("/")
def list_checks(
    search: str = "",
    category: str = "",
    risk: str = "",
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    checks = merge_checks()

    if search:
        s = search.lower()
        checks = [c for c in checks if s in c.get("desc", "").lower()]
    if category:
        checks = [c for c in checks if c.get("category", "") == category]
    if risk:
        checks = [c for c in checks if c.get("risk", "") == risk]

    total = len(checks)
    start = (page - 1) * page_size
    items = checks[start: start + page_size]

    categories = sorted(set(c.get("category", "") for c in merge_checks() if c.get("category")))

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "categories": categories,
    }


@router.post("/", status_code=201)
def create_check(data: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    overrides = load_overrides()
    # Generate a new ID
    all_checks = merge_checks()
    max_id = max((c["id"] for c in all_checks), default=0)
    new_check = {
        "id": max_id + 1,
        "desc": data.get("desc", ""),
        "category": data.get("category", ""),
        "risk": data.get("risk", "Medium"),
        "feasibility": data.get("feasibility", "Auto"),
        "analysis": data.get("analysis", ""),
        "module": data.get("module", ""),
        "source": data.get("source", ""),
        "active": data.get("active", True),
    }
    overrides.setdefault("created", []).append(new_check)
    save_overrides(overrides)
    return new_check


@router.put("/{check_id}")
def update_check(check_id: int, data: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    overrides = load_overrides()
    # Check if it's a created check
    created = overrides.get("created", [])
    for i, c in enumerate(created):
        if c["id"] == check_id:
            overrides["created"][i] = {**c, **data, "id": check_id}
            save_overrides(overrides)
            return overrides["created"][i]

    # Otherwise update base check
    base = load_checks()
    base_check = next((c for c in base if c["id"] == check_id), None)
    if not base_check:
        raise HTTPException(404, "Check not found")

    overrides.setdefault("updated", {})[str(check_id)] = data
    save_overrides(overrides)
    return {**base_check, **data}


@router.delete("/{check_id}", status_code=204)
def delete_check(check_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    overrides = load_overrides()
    # Remove from created if present
    created = overrides.get("created", [])
    new_created = [c for c in created if c["id"] != check_id]
    if len(new_created) < len(created):
        overrides["created"] = new_created
        save_overrides(overrides)
        return

    # Mark as deleted for base checks
    deleted = overrides.get("deleted", [])
    if check_id not in deleted:
        deleted.append(check_id)
        overrides["deleted"] = deleted
        save_overrides(overrides)


@router.post("/upload-excel")
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        import openpyxl
        import io

        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content))
        ws = wb.active

        overrides = load_overrides()
        all_checks = merge_checks()
        max_id = max((c["id"] for c in all_checks), default=0)

        headers = [str(cell.value).strip().lower() if cell.value else "" for cell in ws[1]]
        added = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            row_dict = dict(zip(headers, row))
            max_id += 1
            new_check = {
                "id": max_id,
                "desc": str(row_dict.get("desc", row_dict.get("description", "")) or ""),
                "category": str(row_dict.get("category", "") or ""),
                "risk": str(row_dict.get("risk", "Medium") or "Medium"),
                "feasibility": str(row_dict.get("feasibility", "Auto") or "Auto"),
                "analysis": str(row_dict.get("analysis", "") or ""),
                "module": str(row_dict.get("module", "") or ""),
                "source": str(row_dict.get("source", "") or ""),
                "active": True,
            }
            overrides.setdefault("created", []).append(new_check)
            added += 1

        save_overrides(overrides)
        return {"message": f"Imported {added} checks successfully"}
    except ImportError:
        raise HTTPException(500, "openpyxl not installed")
    except Exception as e:
        raise HTTPException(400, f"Failed to parse Excel file: {str(e)}")
