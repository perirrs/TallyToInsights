from pydantic import BaseModel
from datetime import datetime, date


class DumpOut(BaseModel):
    id: int
    company_id: int
    filename: str
    file_format: str
    period_from: date | None
    period_to: date | None
    financial_year: str | None
    status: str
    voucher_count: int
    ledger_count: int
    uploaded_at: datetime
    processed_at: datetime | None
    progress_pct: int = 0
    progress_stage: str | None = None

    model_config = {"from_attributes": True}


class DumpStatus(BaseModel):
    id: int
    status: str
    voucher_count: int
    ledger_count: int
    error_message: str | None
    processed_at: datetime | None
    progress_pct: int = 0
    progress_stage: str | None = None

    model_config = {"from_attributes": True}
