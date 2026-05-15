"""CSV parser — delegates to the Excel parser after reading CSV into a temp xlsx."""
import pandas as pd
from .normalize import ParseResult
from .excel_parser import _parse_voucher_sheet, _parse_trial_balance, _parse_stock_sheet


def parse_csv(file_path: str) -> ParseResult:
    result = ParseResult()
    try:
        df = pd.read_csv(file_path, dtype=str, encoding="utf-8", on_bad_lines="skip")
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, dtype=str, encoding="latin-1", on_bad_lines="skip")

    cols = " ".join(str(c).lower() for c in df.columns)

    if any(k in cols for k in ["date", "voucher", "transaction"]):
        _parse_voucher_sheet(df, result)
    elif any(k in cols for k in ["trial", "closing", "opening", "ledger"]):
        _parse_trial_balance(df, result)
    elif any(k in cols for k in ["stock", "item", "inventory"]):
        _parse_stock_sheet(df, result)
    else:
        _parse_voucher_sheet(df, result)

    return result
