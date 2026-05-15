from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AuditResult(Base):
    __tablename__ = "audit_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    dump_id: Mapped[int] = mapped_column(ForeignKey("data_dumps.id"), index=True)
    check_id: Mapped[int] = mapped_column(Integer, index=True)
    check_description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(200), index=True)
    risk_level: Mapped[str] = mapped_column(String(10))  # High, Medium, Low
    status: Mapped[str] = mapped_column(String(20))  # pass, fail, warning, skipped, error
    finding_count: Mapped[int] = mapped_column(Integer, default=0)
    findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Each finding: {voucher_no, date, party, amount, detail, ledger}
    amount_at_risk: Mapped[float] = mapped_column(default=0.0)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dump: Mapped["DataDump"] = relationship("DataDump", back_populates="audit_results")
