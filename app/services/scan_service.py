import asyncio
import re
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.scan_result import ScanResult
from app.services.ai_service import AIService
from app.services.group_service import GroupService
from app.services.sentiment_service import SentimentService
from app.services.stock_data_service import StockDataService
from app.services.usage_service import UsageService
from app.utils.formatter import format_scan_ranking


class ScanService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.groups = GroupService()
        self.stock_data = StockDataService()
        self.sentiment = SentimentService()
        self.ai = AIService()
        self.usage = UsageService()

    async def scan_group(
        self,
        db: Session,
        group_name: str,
        user_id: int | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        self.ai.ensure_available()
        self.usage.check_and_record(db, user_id, "scan")
        codes = self.groups.get_codes(group_name)
        effective_limit = min(limit or self.settings.max_scan_stocks, self.settings.max_scan_stocks)
        codes = codes[:effective_limit]
        results: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for index, code in enumerate(codes):
            try:
                data = await self.stock_data.get_stock_data(
                    code,
                    self.groups.find_groups_for_stock(code),
                )
                data["sentiment"] = await self.sentiment.get_sentiment(
                    code,
                    data["stock"].get("sector"),
                )
                ai_result = await self.ai.analyze(data, quick=True)
                row = {
                    "stock_code": code,
                    "final_signal": ai_result["final_signal"],
                    "confidence_level": ai_result["confidence_level"],
                    "summary": ai_result["text"],
                    "short_reason": self._short_reason(ai_result["text"]),
                }
                results.append(row)
                db.add(
                    ScanResult(
                        user_id=user_id,
                        group_name=group_name.upper(),
                        stock_code=code,
                        final_signal=row["final_signal"],
                        confidence_level=row["confidence_level"],
                        summary=row["summary"],
                    )
                )
                db.commit()
            except Exception as exc:
                db.rollback()
                errors.append({"stock_code": code, "error": str(exc)})
            if index < len(codes) - 1 and self.settings.scan_delay_seconds:
                await asyncio.sleep(self.settings.scan_delay_seconds)
        return {
            "group_name": group_name.upper(),
            "results": results,
            "errors": errors,
            "formatted": format_scan_ranking(group_name.upper(), results),
        }

    @staticmethod
    def _short_reason(text: str) -> str:
        for label in ("Kesimpulan", "Teknikal", "Trend"):
            match = re.search(rf"{label}\s*:\s*(.+)", text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:160]
        return text.replace("\n", " ").strip()[:160]
