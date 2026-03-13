import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.company import Company
from app.models.dump import DataDump
from app.schemas.dump import DumpOut, DumpStatus
from app.utils.auth import get_current_user
from app.config import settings
from app.tasks.process_dump import process_dump_background

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {".xml", ".xlsx", ".xls", ".csv", ".json"}


@router.post("/{company_id}", response_model=DumpOut, status_code=201)
async def upload_dump(
    company_id: int,
    file: UploadFile = File(...),
    period_from: str | None = Form(None),
    period_to: str | None = Form(None),
    financial_year: str | None = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")
    if not user.is_admin and company not in user.companies:
        raise HTTPException(403, "Access denied")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_MB:
        raise HTTPException(400, f"File too large: {size_mb:.1f}MB (max {settings.MAX_UPLOAD_MB}MB)")

    filename = f"{uuid.uuid4().hex}{ext}"
    company_dir = os.path.join(settings.UPLOAD_DIR, str(company_id))
    os.makedirs(company_dir, exist_ok=True)
    file_path = os.path.join(company_dir, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    fmt_map = {".xml": "xml", ".xlsx": "excel", ".xls": "excel", ".csv": "csv", ".json": "json"}

    dump = DataDump(
        company_id=company_id,
        user_id=user.id,
        filename=file.filename,
        file_path=file_path,
        file_format=fmt_map[ext],
        period_from=datetime.strptime(period_from, "%Y-%m-%d").date() if period_from else None,
        period_to=datetime.strptime(period_to, "%Y-%m-%d").date() if period_to else None,
        financial_year=financial_year,
        status="uploaded",
    )
    db.add(dump)
    db.commit()
    db.refresh(dump)

    background_tasks.add_task(process_dump_background, dump.id)
    return dump


@router.get("/{company_id}", response_model=list[DumpOut])
def list_dumps(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")
    if not user.is_admin and company not in user.companies:
        raise HTTPException(403, "Access denied")
    return db.query(DataDump).filter(DataDump.company_id == company_id).order_by(DataDump.uploaded_at.desc()).all()


@router.get("/status/{dump_id}", response_model=DumpStatus)
def get_dump_status(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
    if not dump:
        raise HTTPException(404, "Dump not found")
    return dump


@router.delete("/{dump_id}", status_code=204)
def delete_dump(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
    if not dump:
        raise HTTPException(404, "Dump not found")
    company = db.query(Company).filter(Company.id == dump.company_id).first()
    if not user.is_admin and company not in user.companies:
        raise HTTPException(403, "Access denied")
    if os.path.exists(dump.file_path):
        os.remove(dump.file_path)
    db.delete(dump)
    db.commit()
