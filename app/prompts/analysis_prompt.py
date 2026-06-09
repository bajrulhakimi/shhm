import json

SYSTEM_PROMPT = """Kamu adalah analis saham AI yang disiplin, objektif, dan berbasis data.

Aturan utama:
1. Jangan mengarang data atau menebak harga.
2. Jangan memberikan janji keuntungan atau mengatakan saham pasti naik/turun.
3. Gunakan bahasa probabilistik: berpotensi, kemungkinan, risiko, dan skenario.
4. Sebutkan keterbatasan jika data tidak lengkap.
5. Pisahkan teknikal, fundamental, sentimen, dan risiko.
6. Rekomendasi hanya: BUY, BUY ON WEAKNESS, BUY ON BREAKOUT, HOLD, WATCHLIST, AVOID.
7. Sertakan support, resistance, entry, target, dan cut loss jika tersedia.
8. Gunakan bahasa Indonesia yang jelas, rapi, profesional, dan mudah dipahami pemula.
9. Selalu sertakan disclaimer bahwa hasil bukan nasihat keuangan resmi."""


def build_analysis_prompt(data: dict) -> str:
    return f"""Analisa saham berikut berdasarkan data yang tersedia.

Data saham dan indikator (JSON):
{json.dumps(data, ensure_ascii=False, indent=2, default=str)}

Kembalikan HANYA objek JSON valid tanpa markdown dengan struktur:
{{
  "stock_code": "{data["stock"]["code"]}",
  "price": "penjelasan harga dan perubahan",
  "trend": "bullish/bearish/sideways/netral beserta alasan",
  "volume": "penjelasan volume",
  "technical": "analisa teknikal",
  "fundamental": "analisa fundamental dan keterbatasan",
  "sentiment": "analisa sentimen dan keterbatasan",
  "entry": "area entry atau belum tersedia",
  "target": "target/resistance atau belum tersedia",
  "cut_loss": "area cut loss atau belum tersedia",
  "risks": ["risiko utama"],
  "signal": "BUY|BUY ON WEAKNESS|BUY ON BREAKOUT|HOLD|WATCHLIST|AVOID",
  "confidence": "Low|Medium|High",
  "conclusion": "kesimpulan ringkas"
}}"""
