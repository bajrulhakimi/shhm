import json


def build_scan_prompt(data: dict) -> str:
    return f"""Kamu adalah AI analis saham. Analisa singkat, objektif, dan berbasis data.
Jangan memberikan prediksi pasti. Gunakan probabilitas berdasarkan data.

Data (JSON):
{json.dumps(data, ensure_ascii=False, indent=2, default=str)}

Kembalikan HANYA objek JSON valid tanpa markdown dengan struktur:
{{
  "stock_code": "{data["stock"]["code"]}",
  "trend": "ringkasan trend",
  "volume": "ringkasan volume",
  "technical": "ringkasan teknikal termasuk support/resistance",
  "fundamental": "ringkasan fundamental",
  "sentiment": "ringkasan sentimen",
  "risks": ["risiko utama"],
  "signal": "BUY|BUY ON WEAKNESS|BUY ON BREAKOUT|HOLD|WATCHLIST|AVOID",
  "confidence": "Low|Medium|High",
  "conclusion": "alasan singkat"
}}"""
