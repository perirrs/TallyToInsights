from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DataDump(Base):
    __tablename__ = "data_dumps"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    file_format: Mapped[str] = mapped_column(String(20))  # xml, excel, csv, json
    period_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    financial_year: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. "2023-24"
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    # uploaded | processing | processed | failed | auditing
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    progress_stage: Mapped[str | None] = mapped_column(String(200), nullable=True)
    voucher_count: Mapped[int] = mapped_column(Integer, default=0)
    ledger_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="dumps")
    uploaded_by: Mapped["User"] = relationship("User", back_populates="dumps")
    ledgers: Mapped[list["Ledger"]] = relationship("Ledger", back_populates="dump", cascade="all, delete-orphan")
    vouchers: Mapped[list["Voucher"]] = relationship("Voucher", back_populates="dump", cascade="all, delete-orphan")
    stock_items: Mapped[list["StockItem"]] = relationship("StockItem", back_populates="dump", cascade="all, delete-orphan")
    audit_results: Mapped[list["AuditResult"]] = relationship("AuditResult", back_populates="dump", cascade="all, delete-orphan")
