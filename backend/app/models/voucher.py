from datetime import date, datetime
from sqlalchemy import String, Numeric, Integer, ForeignKey, Boolean, Text, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(primary_key=True)
    dump_id: Mapped[int] = mapped_column(ForeignKey("data_dumps.id"), index=True)
    voucher_number: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    voucher_type: Mapped[str] = mapped_column(String(100), index=True)
    # Sales, Purchase, Receipt, Payment, Journal, Contra, Debit Note, Credit Note, etc.
    date: Mapped[date] = mapped_column(Date, index=True)
    party_ledger: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    narration: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    altered_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    altered_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # GST fields
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    place_of_supply: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_reverse_charge: Mapped[bool] = mapped_column(Boolean, default=False)
    # Payroll
    employee_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    dump: Mapped["DataDump"] = relationship("DataDump", back_populates="vouchers")
    lines: Mapped[list["VoucherLine"]] = relationship("VoucherLine", back_populates="voucher", cascade="all, delete-orphan")
    stock_lines: Mapped[list["StockVoucherLine"]] = relationship("StockVoucherLine", back_populates="voucher", cascade="all, delete-orphan")


class VoucherLine(Base):
    __tablename__ = "voucher_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    voucher_id: Mapped[int] = mapped_column(ForeignKey("vouchers.id"), index=True)
    ledger_id: Mapped[int | None] = mapped_column(ForeignKey("ledgers.id"), nullable=True)
    ledger_name: Mapped[str] = mapped_column(String(500))
    amount: Mapped[float] = mapped_column(Numeric(20, 4))
    is_debit: Mapped[bool] = mapped_column(Boolean, default=True)
    # GST type: CGST, SGST, IGST, None
    gst_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gst_rate: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    voucher: Mapped["Voucher"] = relationship("Voucher", back_populates="lines")
    ledger: Mapped["Ledger | None"] = relationship("Ledger", foreign_keys=[ledger_id], back_populates="debit_lines")
