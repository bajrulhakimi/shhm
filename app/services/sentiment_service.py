import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.exceptions import RetryableExternalError


class SentimentService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def get_sentiment(
        self,
        stock_code: str,
        sector: str | None = None,
        corporate_actions: list[dict] | None = None,
    ) -> dict[str, str]:
        latest_news = "Data berita belum tersedia pada sistem."
        if self.settings.news_api_key:
            latest_news = await self._fetch_news(stock_code, sector)
        return {
            "latest_news": latest_news,
            "corporate_actions": self._format_corporate_actions(corporate_actions or []),
            "sector_sentiment": "Data sentimen sektor belum tersedia pada sistem.",
            "market_sentiment": "Data sentimen IHSG/market belum tersedia pada sistem.",
        }

    async def _fetch_news(self, stock_code: str, sector: str | None) -> str:
        retrying = AsyncRetrying(
            retry=retry_if_exception_type(RetryableExternalError),
            stop=stop_after_attempt(self.settings.external_request_max_attempts),
            wait=wait_exponential(
                multiplier=self.settings.external_request_backoff_seconds,
                max=30,
            ),
            reraise=True,
        )
        try:
            async for attempt in retrying:
                with attempt:
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.get(
                            self.settings.news_api_url,
                            params={
                                "q": f"{stock_code} Indonesia {sector or ''}".strip(),
                                "language": "id",
                                "sortBy": "publishedAt",
                                "pageSize": 5,
                            },
                            headers={"X-Api-Key": self.settings.news_api_key},
                        )
                    if response.status_code == 429 or response.status_code >= 500:
                        raise RetryableExternalError("News API sementara tidak tersedia.")
                    response.raise_for_status()
                    articles = response.json().get("articles", [])
                    if not articles:
                        return "Belum ada berita terbaru yang ditemukan."
                    return "\n".join(
                        self._format_article(article)
                        for article in articles
                    )
        except (httpx.HTTPError, ValueError, RetryableExternalError):
            return "Data berita belum berhasil diambil."
        return "Data berita belum tersedia pada sistem."

    @staticmethod
    def _format_article(article: dict) -> str:
        title = article.get("title", "Tanpa judul")
        source = article.get("source", {}).get("name", "N/A")
        return f"- {title} ({source})"

    @staticmethod
    def _format_corporate_actions(actions: list[dict]) -> str:
        if not actions:
            return "Data aksi korporasi belum tersedia pada sistem."
        return "\n".join(SentimentService._format_action(action) for action in actions[-5:])

    @staticmethod
    def _format_action(action: dict) -> str:
        return (
            f"- {action['date']}: dividen={action['dividends']}, "
            f"stock split={action['stock_splits']}"
        )
