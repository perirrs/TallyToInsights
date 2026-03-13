from pydantic import BaseModel
from datetime import date


class LedgerBalance(BaseModel):
    name: str
    group: str
    amount: float
    percentage: float = 0.0


class FinancialSummary(BaseModel):
    dump_id: int
    period_from: date | None
    period_to: date | None
    revenue: float
    expenses: float
    gross_profit: float
    net_profit: float
    gross_margin_pct: float
    net_margin_pct: float
    total_assets: float
    total_liabilities: float
    equity: float
    revenue_ledgers: list[LedgerBalance]
    expense_ledgers: list[LedgerBalance]
    asset_ledgers: list[LedgerBalance]
    liability_ledgers: list[LedgerBalance]


class CashFlowItem(BaseModel):
    date: date
    description: str
    inflow: float
    outflow: float
    balance: float


class CashFlowReport(BaseModel):
    dump_id: int
    opening_balance: float
    closing_balance: float
    total_inflow: float
    total_outflow: float
    net_flow: float
    monthly_summary: list[dict]
    daily_items: list[CashFlowItem]


class AgingBucket(BaseModel):
    party: str
    current: float
    days_1_30: float
    days_31_60: float
    days_61_90: float
    days_90_plus: float
    total: float
    oldest_date: date | None


class AgingReport(BaseModel):
    dump_id: int
    report_type: str  # receivable | payable
    total_outstanding: float
    overdue_amount: float
    buckets: list[AgingBucket]


class GSTSummary(BaseModel):
    month: str
    taxable_sales: float
    cgst_collected: float
    sgst_collected: float
    igst_collected: float
    total_tax: float
    taxable_purchases: float
    itc_cgst: float
    itc_sgst: float
    itc_igst: float
    total_itc: float
    net_liability: float


class GSTReport(BaseModel):
    dump_id: int
    monthly_summary: list[GSTSummary]
    total_output_tax: float
    total_itc: float
    net_payable: float


class AuditFinding(BaseModel):
    voucher_no: str | None
    date: str | None
    party: str | None
    amount: float | None
    detail: str
    ledger: str | None = None


class AuditCheckResult(BaseModel):
    check_id: int
    description: str
    category: str
    risk_level: str
    status: str
    finding_count: int
    amount_at_risk: float
    findings: list[AuditFinding]


class AuditSummary(BaseModel):
    dump_id: int
    total_checks: int
    passed: int
    failed: int
    warnings: int
    skipped: int
    high_risk_failures: int
    medium_risk_failures: int
    low_risk_failures: int
    audit_health_score: float
    total_amount_at_risk: float
    category_summary: list[dict]
    results: list[AuditCheckResult]


class ComparisonReport(BaseModel):
    company_id: int
    dump_ids: list[int]
    periods: list[str]
    revenue: list[float]
    expenses: list[float]
    net_profit: list[float]
    gross_margin: list[float]
    total_assets: list[float]
    total_liabilities: list[float]
    key_ratios: dict[str, list[float]]
