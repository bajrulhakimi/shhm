from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.stock import Stock
from app.services.ai_service import AIService
from app.services.group_service import GroupService
from app.services.sentiment_service import SentimentService
from app.services.stock_data_service import StockDataService
from app.services.usage_service import UsageService
from app.utils.validators import normalize_stock_code


class AnalysisService:
    def __init__(self) -> None:
        self.stock_data = StockDataService()
        self.sentiment = SentimentService()
        self.ai = AIService()
        self.groups = GroupService()
        self.usage = UsageService()

    async def analyze_stock(
        self,
        db: Session,
        code: str,
        user_id: int | None = None,
        enforce_limit: bool = True,
    ) -> dict[str, Any]:
        normalized = normalize_stock_code(code)
        self.ai.ensure_available()
        if enforce_limit:
            self.usage.check_and_record(db, user_id, "analysis")
        data = await self.stock_data.get_stock_data(
            normalized,
            self.groups.find_groups_for_stock(normalized),
        )
        data["sentiment"] = await self.sentiment.get_sentiment(
            normalized,
            data["stock"].get("sector"),
            data.get("corporate_actions"),
        )
        ai_result = await self.ai.analyze(data)
        self._upsert_stock(db, data["stock"])
        for provider, result in ai_result["individual_results"].items():
            provider_structured = self.ai.parse_result(result, normalized)
            db.add(
                Analysis(
                    user_id=user_id,
                    stock_code=normalized,
                    provider=provider,
                    raw_data=data,
                    structured_result=provider_structured["structured"],
                    ai_result=provider_structured["text"],
                    final_signal=provider_structured["final_signal"],
                    confidence_level=provider_structured["confidence_level"],
                )
            )
        if len(ai_result["individual_results"]) > 1:
            db.add(
                Analysis(
                    user_id=user_id,
                    stock_code=normalized,
                    provider=ai_result["provider"],
                    raw_data=data,
                    structured_result=ai_result["structured"],
                    ai_result=ai_result["text"],
                    final_signal=ai_result["final_signal"],
                    confidence_level=ai_result["confidence_level"],
                )
            )
        db.commit()
        return {"data": data, **ai_result}

    @staticmethod
    def _upsert_stock(db: Session, payload: dict[str, Any]) -> None:
        stock = db.scalar(select(Stock).where(Stock.code == payload["code"]))
        if not stock:
            stock = Stock(code=payload["code"])
            db.add(stock)
        stock.name = payload.get("name")
        stock.sector = payload.get("sector")
        stock.market_cap = payload.get("market_cap")
