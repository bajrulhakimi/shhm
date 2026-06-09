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

Berikan hasil dengan format:

📊 Analisa Saham {data["stock"]["code"]}

💰 Harga:
📈 Trend:
📊 Volume:
🧭 Analisa Teknikal:
🏢 Analisa Fundamental:
📰 Sentimen:
🟢 Area Entry Potensial:
🎯 Target / Resistance:
🔴 Cut Loss:
⚠️ Risiko:
✅ Kesimpulan AI:
Pilih tepat satu: BUY, BUY ON WEAKNESS, BUY ON BREAKOUT, HOLD, WATCHLIST, AVOID.

📌 Confidence Level:
Pilih tepat satu: Low, Medium, High.

Disclaimer:
Analisa ini bukan ajakan membeli atau menjual saham.
Keputusan investasi tetap menjadi tanggung jawab pengguna."""
