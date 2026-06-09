from typing import Any

from app.utils.formatter import finite_or_none


class FundamentalService:
    @staticmethod
    def from_yahoo_info(info: dict[str, Any]) -> dict[str, Any]:
        return {
            "eps": finite_or_none(info.get("trailingEps")),
            "per": finite_or_none(info.get("trailingPE")),
            "pbv": finite_or_none(info.get("priceToBook")),
            "roe": finite_or_none(info.get("returnOnEquity")),
            "der": finite_or_none(info.get("debtToEquity")),
            "revenue_growth": finite_or_none(info.get("revenueGrowth")),
            "net_profit_growth": finite_or_none(info.get("earningsGrowth")),
            "dividend_yield": finite_or_none(info.get("dividendYield")),
            "data_note": (
                "Data fundamental bersumber dari Yahoo Finance dan dapat terbatas atau tertunda."
            ),
        }

