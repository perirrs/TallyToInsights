from pydantic import BaseModel
from datetime import datetime


class CompanyCreate(BaseModel):
    name: str
    gstin: str | None = None
    pan: str | None = None
    address: str | None = None
    financial_year_start_month: int = 4
    currency: str = "INR"


class CompanyOut(BaseModel):
    id: int
    name: str
    gstin: str | None
    pan: str | None
    address: str | None
    financial_year_start_month: int
    currency: str
    created_at: datetime

    model_config = {"from_attributes": True}
