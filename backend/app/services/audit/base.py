"""Shared types and helpers for audit checks."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Finding:
    detail: str
    voucher_no: Optional[str] = None
    date: Optional[str] = None
    party: Optional[str] = None
    amount: Optional[float] = None
    ledger: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "detail": self.detail,
            "voucher_no": self.voucher_no,
            "date": str(self.date) if self.date else None,
            "party": self.party,
            "amount": self.amount,
            "ledger": self.ledger,
        }


@dataclass
class CheckResult:
    check_id: int
    description: str
    category: str
    risk_level: str
    status: str  # pass | fail | warning | skipped | error
    finding_count: int = 0
    findings: list[Finding] = field(default_factory=list)
    amount_at_risk: float = 0.0

    def fail(self, findings: list[Finding]):
        self.status = "fail"
        self.finding_count = len(findings)
        self.findings = findings[:200]  # cap at 200 findings per check
        self.amount_at_risk = sum(f.amount or 0 for f in findings)
        return self

    def warn(self, findings: list[Finding]):
        self.status = "warning"
        self.finding_count = len(findings)
        self.findings = findings[:200]
        self.amount_at_risk = sum(f.amount or 0 for f in findings)
        return self

    def skip(self, reason: str = ""):
        self.status = "skipped"
        return self

    def ok(self):
        self.status = "pass"
        return self
