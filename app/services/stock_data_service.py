import asyncio
import time
from typing import Any

import pandas as pd
import yfinance as yf

from app.config import get_settings
from app.exceptions import StockDataError
from app.services.fundamental_service import FundamentalService
from app.services.technical_indicator_service import TechnicalIndicatorService
from app.utils.formatter import finite_or_none
from app.utils.validators import normalize_stock_code, yahoo_symbol


class StockDataService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    async def get_stock_data(self, code: str, groups: list[str] | None = None) -> dict[str, Any]:
        normalized = normalize_stock_code(code)
        cached = self._cache.get(normalized)
        if cached and time.monotonic() - cached[0] < self.settings.stock_data_cache_seconds:
            data = dict(cached[1])
            data["groups"] = groups or data.get("groups", [])
            return data
        data = await asyncio.to_thread(self._fetch_sync, normalized, groups or [])
        self._cache[normalized] = (time.monotonic(), data)
        return data

    @staticmethod
    def _fetch_sync(code: str, groups: list[str]) -> dict[str, Any]:
        ticker = yf.Ticker(yahoo_symbol(code))
        try:
            history = ticker.history(period="18mo", interval="1d", auto_adjust=False)
            if history.empty or len(history) < 20:
                raise StockDataError(f"Data saham {code} tidak ditemukan atau belum memadai.")
            history = history.dropna(subset=["Close"])
            info = ticker.info or {}
        except StockDataError:
            raise
        except Exception as exc:
            raise StockDataError(f"Data saham {code} belum berhasil diambil.") from exc

        technical = TechnicalIndicatorService.calculate(history)
        last = history.iloc[-1]
        previous_close = (
            float(history["Close"].iloc[-2]) if len(history) > 1 else float(last["Close"])
        )
        last_close = float(last["Close"])
        daily_change = (
            (last_close - previous_close) / previous_close * 100 if previous_close else None
        )
        market_cap = finite_or_none(info.get("marketCap"))
        name = info.get("longName") or info.get("shortName") or code
        sector = info.get("sector")

        stock = {
            "code": code,
            "yahoo_symbol": yahoo_symbol(code),
            "name": name,
            "last_price": finite_or_none(last_close),
            "daily_change_percent": finite_or_none(daily_change),
            "volume": finite_or_none(last["Volume"]),
            "market_cap": market_cap,
            "sector": sector,
            "open": finite_or_none(last["Open"]),
            "high": finite_or_none(last["High"]),
            "low": finite_or_none(last["Low"]),
            "close": finite_or_none(last["Close"]),
            "currency": info.get("currency", "IDR"),
        }
        return {
            "stock": stock,
            "groups": groups,
            "technical": technical,
            "fundamental": FundamentalService.from_yahoo_info(info),
            "history": StockDataService._history_records(history.tail(250)),
        }

    @staticmethod
    def _history_records(history: pd.DataFrame) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for index, row in history.iterrows():
            records.append(
                {
                    "date": index.strftime("%Y-%m-%d"),
                    "open": finite_or_none(row.get("Open")),
                    "high": finite_or_none(row.get("High")),
                    "low": finite_or_none(row.get("Low")),
                    "close": finite_or_none(row.get("Close")),
                    "volume": finite_or_none(row.get("Volume")),
                }
            )
        return records
