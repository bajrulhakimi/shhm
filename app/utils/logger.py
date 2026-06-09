import logging

from sqlalchemy.engine import make_url

from app.config import get_settings


class SecretRedactionFilter(logging.Filter):
    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self.secrets = [secret for secret in secrets if secret]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self.secrets:
            message = message.replace(secret, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


def configure_logging() -> None:
    settings = get_settings()
    try:
        database_password = make_url(settings.database_url).password or ""
    except ValueError:
        database_password = ""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    redaction_filter = SecretRedactionFilter(
        [
            settings.telegram_bot_token or "",
            settings.telegram_webhook_secret or "",
            settings.openai_api_key or "",
            settings.gemini_api_key or "",
            settings.claude_api_key or "",
            settings.deepseek_api_key or "",
            settings.news_api_key or "",
            settings.api_access_key or "",
            settings.metrics_access_key or "",
            database_password,
        ]
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(redaction_filter)
