from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import normalize_stock_code


class AnalyzeRequest(BaseModel):
    code: str
    telegram_id: int | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return normalize_stock_code(value)


class ScanRequest(BaseModel):
    group_name: str = "IHSG"
    telegram_id: int | None = None
    limit: int | None = Field(default=None, ge=1, le=500)


class AnalysisResponse(BaseModel):
    stock_code: str
    provider: str
    final_signal: str
    confidence_level: str
    result: str
    provider_errors: dict[str, str] = Field(default_factory=dict)


class StockResponse(BaseModel):
    data: dict[str, Any]
