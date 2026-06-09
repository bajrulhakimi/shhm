import math
import re
from collections import defaultdict
from typing import Any

DISCLAIMER = (
    "Disclaimer: Analisa ini bukan ajakan membeli atau menjual saham dan bukan nasihat "
    "keuangan resmi. Keputusan investasi tetap menjadi tanggung jawab pengguna."
)

SIGNALS = ["BUY ON BREAKOUT", "BUY ON WEAKNESS", "STRONG BUY", "WATCHLIST", "AVOID", "HOLD", "BUY"]
SIGNAL_PATTERN = "|".join(re.escape(signal) for signal in SIGNALS)


def finite_or_none(value: Any) -> Any:
    if value is None:
        return None
    try:
        if math.isnan(value) or math.isinf(value):
            return None
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


def format_number(value: Any, decimals: int = 2) -> str:
    value = finite_or_none(value)
    if value is None:
        return "N/A"
    if isinstance(value, int | float):
        return f"{value:,.{decimals}f}"
    return str(value)


def extract_signal(text: str) -> str | None:
    upper = text.upper()
    for label in ("SINYAL AKHIR", "KESIMPULAN AI", "SINYAL", "KESIMPULAN"):
        match = re.search(rf"{label}\s*[:\-]?\s*({SIGNAL_PATTERN})\b", upper)
        if match:
            return match.group(1)
    for signal in SIGNALS:
        if re.search(rf"\b{re.escape(signal)}\b", upper):
            return signal
    return None


def extract_confidence(text: str) -> str | None:
    match = re.search(r"confidence(?: level)?\s*[:\-]?\s*(low|medium|high)", text, re.IGNORECASE)
    return match.group(1).title() if match else None


def ensure_disclaimer(text: str) -> str:
    return text if "bukan nasihat keuangan" in text.lower() else f"{text.rstrip()}\n\n{DISCLAIMER}"


def split_telegram_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for paragraph in text.splitlines(keepends=True):
        if len(current) + len(paragraph) <= limit:
            current += paragraph
            continue
        if current:
            chunks.append(current.rstrip())
        while len(paragraph) > limit:
            chunks.append(paragraph[:limit])
            paragraph = paragraph[limit:]
        current = paragraph
    if current:
        chunks.append(current.rstrip())
    return chunks


def format_scan_ranking(group_name: str, results: list[dict[str, Any]]) -> str:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        buckets[result.get("final_signal") or "WATCHLIST"].append(result)

    sections = [
        ("🟢 Top BUY", ["STRONG BUY", "BUY"]),
        ("🚀 Buy on Breakout", ["BUY ON BREAKOUT"]),
        ("📉 Buy on Weakness", ["BUY ON WEAKNESS"]),
        ("👀 Watchlist", ["WATCHLIST", "HOLD"]),
        ("🔴 Avoid", ["AVOID"]),
    ]
    lines = [f"📊 Hasil Scan {group_name}"]
    for title, signals in sections:
        items = [item for signal in signals for item in buckets.get(signal, [])]
        lines.append(f"\n{title}:")
        if not items:
            lines.append("- Tidak ada")
        for index, item in enumerate(items[:10], 1):
            reason = item.get("short_reason") or item.get("summary", "").replace("\n", " ")[:140]
            lines.append(f"{index}. {item['stock_code']} - {reason}")
    lines.append(f"\n{DISCLAIMER}")
    return "\n".join(lines)
