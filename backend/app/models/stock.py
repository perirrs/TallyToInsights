from sqlalchemy import String, Numeric, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    dump_id: Mapped[int] = mapped_column(ForeignKey("data_dumps.id"), index=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    group_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hsn_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gst_rate: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    opening_qty: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    opening_value: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    closing_qty: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    closing_value: Mapped[float] = mapped_column(Numeric(20, 4), default=0)

    dump: Mapped["DataDump"] = relationship("DataDump", back_populates="stock_items")
    voucher_lines: Mapped[list["StockVoucherLine"]] = relationship("StockVoucherLine", back_populates="stock_item")


class StockVoucherLine(Base):
    __tablename__ = "stock_voucher_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    voucher_id: Mapped[int] = mapped_column(ForeignKey("vouchers.id"), index=True)
    stock_item_id: Mapped[int | None] = mapped_column(ForeignKey("stock_items.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(500))
    godown: Mapped[str | None] = mapped_column(String(500), nullable=True)
    qty: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    rate: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    amount: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    is_inward: Mapped[bool] = mapped_column(default=True)

    voucher: Mapped["Voucher"] = relationship("Voucher", back_populates="stock_lines")
    stock_item: Mapped["StockItem | None"] = relationship("StockItem", back_populates="voucher_lines")
