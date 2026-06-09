import argparse
import asyncio
import sys
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.database import engine
from app.services.ai_service import AIService
from app.services.stock_data_service import StockDataService
from app.utils.logger import configure_logging


async def main(with_ai: bool) -> None:
    configure_logging()
    settings = get_settings()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise SystemExit("Database: FAILED") from None
    print("Database: OK")

    try:
        data = await StockDataService().get_stock_data("BBCA")
    except Exception:
        raise SystemExit("Yahoo Finance: FAILED") from None
    print(f"Yahoo Finance: OK ({len(data['history'])} candles)")

    if settings.telegram_bot_token:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
                )
                response.raise_for_status()
            print("Telegram: OK")
        except httpx.HTTPError:
            raise SystemExit("Telegram: FAILED") from None
    else:
        print("Telegram: SKIPPED")

    print("AI providers:", ", ".join(settings.configured_ai_providers) or "NONE")
    if with_ai:
        try:
            result = await AIService().analyze(data, quick=True)
        except Exception:
            raise SystemExit("AI: FAILED") from None
        print(f"AI: OK ({result['provider']}, {result['final_signal']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-ai", action="store_true", help="Lakukan satu request AI berbayar")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.with_ai))
