from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyOut
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.post("/", response_model=CompanyOut, status_code=201)
def create_company(data: CompanyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = Company(**data.model_dump(), created_by_id=user.id)
    company.users.append(user)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.is_admin:
        return db.query(Company).all()
    return user.companies


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")
    if not user.is_admin and company not in user.companies:
        raise HTTPException(403, "Access denied")
    return company


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, data: CompanyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")
    if not user.is_admin and company not in user.companies:
        raise HTTPException(403, "Access denied")
    for k, v in data.model_dump().items():
        setattr(company, k, v)
    db.commit()
    db.refresh(company)
    return company


@router.post("/{company_id}/users/{user_id}")
def add_user_to_company(company_id: int, user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(403, "Admin only")
    company = db.query(Company).filter(Company.id == company_id).first()
    target_user = db.query(User).filter(User.id == user_id).first()
    if not company or not target_user:
        raise HTTPException(404, "Not found")
    if target_user not in company.users:
        company.users.append(target_user)
        db.commit()
    return {"message": "User added"}
