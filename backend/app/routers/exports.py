from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
from app.database import get_db
from app.models.user import User
from app.models.dump import DataDump
from app.models.company import Company
from app.utils.auth import get_current_user
from app.services.exports.pdf_generator import generate_full_report_pdf
from app.services.exports.excel_generator import generate_excel_report

router = APIRouter(prefix="/api/exports", tags=["exports"])


def _check_access(dump_id: int, db: Session, user: User) -> DataDump:
    dump = db.query(DataDump).filter(DataDump.id == dump_id).first()
    if not dump:
        raise HTTPException(404, "Dump not found")
    if dump.status != "processed":
        raise HTTPException(400, "Dump not fully processed")
    company = db.query(Company).filter(Company.id == dump.company_id).first()
    if not user.is_admin and company not in user.companies:
        raise HTTPException(403, "Access denied")
    return dump


@router.get("/{dump_id}/pdf")
def export_pdf(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _check_access(dump_id, db, user)
    pdf_bytes = generate_full_report_pdf(dump_id, db)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=TallyInsights_{dump_id}.pdf"},
    )


@router.get("/{dump_id}/excel")
def export_excel(dump_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dump = _check_access(dump_id, db, user)
    excel_bytes = generate_excel_report(dump_id, db)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=TallyInsights_{dump_id}.xlsx"},
    )
