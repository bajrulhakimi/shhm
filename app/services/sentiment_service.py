class SentimentService:
    async def get_sentiment(self, stock_code: str, sector: str | None = None) -> dict[str, str]:
        return {
            "latest_news": "Data berita belum tersedia pada sistem.",
            "corporate_actions": "Data aksi korporasi belum tersedia pada sistem.",
            "sector_sentiment": "Data sentimen sektor belum tersedia pada sistem.",
            "market_sentiment": "Data sentimen IHSG/market belum tersedia pada sistem.",
        }

