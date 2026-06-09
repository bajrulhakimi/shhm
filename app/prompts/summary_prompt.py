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

Berikan output:
📊 Ringkasan Gabungan AI

🤖 Pendapat setiap AI:
✅ Kesamaan Analisa:
⚠️ Perbedaan Analisa:
📉 Risiko Utama:
📈 Peluang Utama:
🎯 Sinyal Akhir:
Pilih tepat satu: STRONG BUY, BUY, BUY ON WEAKNESS, BUY ON BREAKOUT, HOLD, WATCHLIST, AVOID.
📌 Confidence Level:
Low, Medium, atau High.

Disclaimer:
Ini bukan nasihat keuangan resmi. Gunakan sebagai referensi tambahan."""
