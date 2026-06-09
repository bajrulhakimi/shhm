import numpy as np
import pandas as pd

from app.services.technical_indicator_service import TechnicalIndicatorService


def test_calculates_technical_indicators() -> None:
    close = np.linspace(100, 200, 260)
    history = pd.DataFrame(
        {
            "Open": close - 1,
            "High": close + 2,
            "Low": close - 2,
            "Close": close,
            "Volume": np.full(260, 1_000_000),
        }
    )
    result = TechnicalIndicatorService.calculate(history)

    assert result["ma200"] is not None
    assert result["ma5"] > result["ma200"]
    assert result["high_52w"] == 202
    assert result["low_52w"] > 98
    assert result["volume_ratio"] == 1

