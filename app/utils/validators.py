import re

from app.exceptions import AppError

STOCK_CODE_PATTERN = re.compile(r"^[A-Z0-9]{2,12}$")


def normalize_stock_code(code: str) -> str:
    normalized = code.strip().upper().removesuffix(".JK")
    if not STOCK_CODE_PATTERN.fullmatch(normalized):
        raise AppError("Format kode saham tidak valid.")
    return normalized


def yahoo_symbol(code: str) -> str:
    return f"{normalize_stock_code(code)}.JK"

