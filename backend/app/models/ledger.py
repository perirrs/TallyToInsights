from sqlalchemy import String, Numeric, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Ledger(Base):
    __tablename__ = "ledgers"

    id: Mapped[int] = mapped_column(primary_key=True)
    dump_id: Mapped[int] = mapped_column(ForeignKey("data_dumps.id"), index=True)
    tally_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    group_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_group: Mapped[str | None] = mapped_column(String(500), nullable=True)
    opening_balance: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    closing_balance: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    is_revenue: Mapped[bool] = mapped_column(Boolean, default=False)
    is_expense: Mapped[bool] = mapped_column(Boolean, default=False)
    is_asset: Mapped[bool] = mapped_column(Boolean, default=False)
    is_liability: Mapped[bool] = mapped_column(Boolean, default=False)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    is_bank: Mapped[bool] = mapped_column(Boolean, default=False)
    is_cash: Mapped[bool] = mapped_column(Boolean, default=False)

    dump: Mapped["DataDump"] = relationship("DataDump", back_populates="ledgers")
    debit_lines: Mapped[list["VoucherLine"]] = relationship(
        "VoucherLine", foreign_keys="VoucherLine.ledger_id", back_populates="ledger"
    )
