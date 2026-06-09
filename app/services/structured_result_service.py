import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.utils.formatter import DISCLAIMER, extract_confidence, extract_signal

Signal = Literal[
    "STRONG BUY",
    "BUY",
    "BUY ON WEAKNESS",
    "BUY ON BREAKOUT",
    "HOLD",
    "WATCHLIST",
    "AVOID",
]
Confidence = Literal["Low", "Medium", "High"]


class StructuredAnalysis(BaseModel):
    stock_code: str = ""
    price: str = ""
    trend: str = ""
    volume: str = ""
    technical: str = ""
    fundamental: str = ""
    sentiment: str = ""
    entry: str = ""
    target: str = ""
    cut_loss: str = ""
    risks: list[str] = Field(default_factory=list)
    signal: Signal = "WATCHLIST"
    confidence: Confidence = "Low"
    conclusion: str = ""

    @field_validator("signal", mode="before")
    @classmethod
    def normalize_signal(cls, value: Any) -> str:
        normalized = str(value or "WATCHLIST").strip().upper()
        return normalized if normalized in Signal.__args__ else "WATCHLIST"

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> str:
        normalized = str(value or "Low").strip().title()
        return normalized if normalized in Confidence.__args__ else "Low"

    @field_validator("risks", mode="before")
    @classmethod
    def normalize_risks(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        return value or []


class StructuredResultService:
    @staticmethod
    def parse(text: str, stock_code: str = "") -> StructuredAnalysis:
        candidate = StructuredResultService._extract_json(text)
        if candidate:
            try:
                data = json.loads(candidate)
                if "stock_code" not in data:
                    data["stock_code"] = stock_code
                return StructuredAnalysis.model_validate(data)
            except (json.JSONDecodeError, ValidationError, TypeError):
                pass
        return StructuredAnalysis(
            stock_code=stock_code,
            conclusion=text.strip(),
            signal=extract_signal(text) or "WATCHLIST",
            confidence=extract_confidence(text) or "Low",
        )

    @staticmethod
    def _extract_json(text: str) -> str | None:
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            return fenced.group(1)
        start, end = text.find("{"), text.rfind("}")
        return text[start : end + 1] if start >= 0 and end > start else None

    @staticmethod
    def render(result: StructuredAnalysis) -> str:
        risk_text = "\n".join(f"- {risk}" for risk in result.risks) or "Data risiko terbatas."
        return f"""📊 Analisa Saham {result.stock_code}

💰 Harga:
{result.price or "Data harga tersedia pada payload analisa."}

📈 Trend:
{result.trend or "Belum dapat disimpulkan."}

📊 Volume:
{result.volume or "Belum dapat disimpulkan."}

🧭 Analisa Teknikal:
{result.technical or "Data teknikal terbatas."}

🏢 Analisa Fundamental:
{result.fundamental or "Data fundamental terbatas."}

📰 Sentimen:
{result.sentiment or "Data berita belum tersedia pada sistem."}

🟢 Area Entry Potensial:
{result.entry or "Belum tersedia."}

🎯 Target / Resistance:
{result.target or "Belum tersedia."}

🔴 Cut Loss:
{result.cut_loss or "Belum tersedia."}

⚠️ Risiko:
{risk_text}

✅ Kesimpulan AI:
{result.signal} - {result.conclusion or "Berdasarkan data yang tersedia."}

📌 Confidence Level:
{result.confidence}

{DISCLAIMER}"""

    @staticmethod
    def as_dict(result: StructuredAnalysis) -> dict[str, Any]:
        return result.model_dump(mode="json")
