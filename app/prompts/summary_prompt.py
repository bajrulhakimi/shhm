import json

SUMMARY_SYSTEM_PROMPT = """Kamu adalah AI peringkas analisa saham yang objektif dan berbasis data.
Jangan mengarang data, menjanjikan keuntungan, atau membuat prediksi pasti.
Sebutkan keterbatasan dan risiko. Gunakan bahasa Indonesia yang profesional.
Sinyal akhir hanya: STRONG BUY, BUY, BUY ON WEAKNESS, BUY ON BREAKOUT, HOLD, WATCHLIST, AVOID.
Selalu sertakan disclaimer bahwa hasil bukan nasihat keuangan resmi."""


def build_summary_prompt(stock_data: dict, results: dict[str, str]) -> str:
    return f"""Kamu adalah AI peringkas hasil analisa saham dari beberapa model AI.
Bandingkan hasil mereka dan buat kesimpulan akhir yang paling rasional. Jangan mengarang data.

Data saham:
{json.dumps(stock_data, ensure_ascii=False, indent=2, default=str)}

Hasil model:
{json.dumps(results, ensure_ascii=False, indent=2)}

Kembalikan HANYA objek JSON valid tanpa markdown dengan struktur:
{{
  "stock_code": "{stock_data["stock"]["code"]}",
  "trend": "kesamaan dan perbedaan trend",
  "volume": "kesimpulan volume",
  "technical": "kesimpulan teknikal gabungan",
  "fundamental": "kesimpulan fundamental gabungan",
  "sentiment": "kesimpulan sentimen gabungan",
  "entry": "area entry",
  "target": "target/resistance",
  "cut_loss": "area cut loss",
  "risks": ["risiko utama"],
  "signal": "STRONG BUY|BUY|BUY ON WEAKNESS|BUY ON BREAKOUT|HOLD|WATCHLIST|AVOID",
  "confidence": "Low|Medium|High",
  "conclusion": "kesimpulan akhir dan perbedaan pendapat model"
}}"""
