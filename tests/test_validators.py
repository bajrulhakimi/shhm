import pytest

from app.exceptions import AppError
from app.utils.validators import normalize_stock_code, yahoo_symbol


def test_normalize_stock_code() -> None:
    assert normalize_stock_code(" bbca.jk ") == "BBCA"
    assert yahoo_symbol("bbri") == "BBRI.JK"


def test_rejects_invalid_stock_code() -> None:
    with pytest.raises(AppError):
        normalize_stock_code("BBCA; DROP TABLE")

