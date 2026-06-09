from typing import Any

import pandas as pd

from app.exceptions import StockDataError
from app.utils.formatter import finite_or_none


class TechnicalIndicatorService:
    @staticmethod
    def calculate(history: pd.DataFrame) -> dict[str, Any]:
        if history.empty or "Close" not in history:
            raise StockDataError("Data historis harga tidak tersedia.")

        close = history["Close"].astype(float)
        volume = history["Volume"].astype(float)
        result: dict[str, Any] = {}
        for period in (5, 20, 50, 100, 200):
            result[f"ma{period}"] = finite_or_none(close.rolling(period).mean().iloc[-1])

        delta = close.diff()
        gains = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        losses = -delta.clip(upper=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        rs = gains / losses.replace(0, float("nan"))
        result["rsi14"] = finite_or_none((100 - (100 / (1 + rs))).iloc[-1])

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        result["macd"] = finite_or_none(macd.iloc[-1])
        result["macd_signal"] = finite_or_none(macd.ewm(span=9, adjust=False).mean().iloc[-1])

        recent = history.tail(min(60, len(history)))
        rolling_low = recent["Low"].rolling(5, center=True).min()
        rolling_high = recent["High"].rolling(5, center=True).max()
        last_price = float(close.iloc[-1])
        supports = recent.loc[recent["Low"].eq(rolling_low), "Low"].astype(float)
        resistances = recent.loc[recent["High"].eq(rolling_high), "High"].astype(float)
        support_candidates = supports[supports < last_price]
        resistance_candidates = resistances[resistances > last_price]
        result["support"] = finite_or_none(
            support_candidates.max() if not support_candidates.empty else recent["Low"].min()
        )
        result["resistance"] = finite_or_none(
            resistance_candidates.min() if not resistance_candidates.empty else recent["High"].max()
        )
        result["high_52w"] = finite_or_none(history.tail(252)["High"].max())
        result["low_52w"] = finite_or_none(history.tail(252)["Low"].min())
        avg_volume = volume.tail(20).mean()
        result["avg_volume_20"] = finite_or_none(avg_volume)
        result["volume_ratio"] = finite_or_none(
            volume.iloc[-1] / avg_volume if avg_volume else None
        )
        return result
