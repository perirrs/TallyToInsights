"""
Normalized data structures returned by all parsers.
Parsers convert source-specific formats into these Python dicts,
which are then bulk-inserted into the DB.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class NLedger:
    name: str
    group_name: str = ""
    parent_group: str = ""
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    gstin: str = ""
    pan: str = ""
    address: str = ""
    is_bank: bool = False
    is_cash: bool = False
    tally_id: str = ""


@dataclass
class NVoucherLine:
    ledger_name: str
    amount: float
    is_debit: bool
    gst_type: str = ""       # CGST, SGST, IGST
    gst_rate: float = 0.0


@dataclass
class NStockLine:
    item_name: str
    qty: float
    rate: float
    amount: float
    godown: str = ""
    is_inward: bool = True


@dataclass
class NVoucher:
    voucher_type: str
    date: date
    amount: float = 0.0
    voucher_number: str = ""
    party_ledger: str = ""
    narration: str = ""
    is_cancelled: bool = False
    is_optional: bool = False
    posted_by: str = ""
    altered_by: str = ""
    altered_date: Optional[date] = None
    reference: str = ""
    gstin: str = ""
    place_of_supply: str = ""
    is_reverse_charge: bool = False
    employee_name: str = ""
    lines: list[NVoucherLine] = field(default_factory=list)
    stock_lines: list[NStockLine] = field(default_factory=list)


@dataclass
class NStockItem:
    name: str
    group_name: str = ""
    unit: str = ""
    hsn_code: str = ""
    gst_rate: float = 0.0
    opening_qty: float = 0.0
    opening_value: float = 0.0
    closing_qty: float = 0.0
    closing_value: float = 0.0


@dataclass
class ParseResult:
    ledgers: list[NLedger] = field(default_factory=list)
    vouchers: list[NVoucher] = field(default_factory=list)
    stock_items: list[NStockItem] = field(default_factory=list)
    period_from: Optional[date] = None
    period_to: Optional[date] = None
