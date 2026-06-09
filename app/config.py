from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Stock Analyzer Bot"
    app_env: str = "local"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_access_key: str | None = None

    database_url: str = "mysql+pymysql://root:password@localhost:3306/stockbot?charset=utf8mb4"
    telegram_bot_token: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    claude_api_key: str | None = None
    claude_model: str = "claude-haiku-4-5"
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-v4-flash"

    default_ai_provider: Literal["openai", "gemini", "claude", "deepseek"] = "openai"
    summary_ai_provider: Literal["openai", "gemini", "claude", "deepseek"] = "openai"
    enable_multi_ai: bool = False

    max_analysis_per_day: int = Field(default=20, ge=1)
    max_scan_per_day: int = Field(default=5, ge=1)
    max_scan_stocks: int = Field(default=20, ge=1, le=500)
    scan_delay_seconds: float = Field(default=2, ge=0)
    ai_request_timeout_seconds: float = Field(default=90, ge=10)
    stock_data_cache_seconds: int = Field(default=300, ge=0)
    log_level: str = "INFO"

    stock_groups_file: Path = BASE_DIR / "app" / "data" / "stock_groups.json"

    @field_validator(
        "api_access_key",
        "telegram_bot_token",
        "openai_api_key",
        "gemini_api_key",
        "claude_api_key",
        "deepseek_api_key",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        return value or None

    @property
    def configured_ai_providers(self) -> list[str]:
        return [
            name
            for name, key in {
                "openai": self.openai_api_key,
                "gemini": self.gemini_api_key,
                "claude": self.claude_api_key,
                "deepseek": self.deepseek_api_key,
            }.items()
            if key
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
