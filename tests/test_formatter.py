from app.utils.formatter import (
    ensure_disclaimer,
    extract_confidence,
    extract_signal,
    split_telegram_message,
)


def test_extracts_longest_signal_first() -> None:
    text = "Sinyal: BUY ON BREAKOUT\nConfidence Level: Medium"
    assert extract_signal(text) == "BUY ON BREAKOUT"
    assert extract_confidence(text) == "Medium"


def test_extracts_explicit_final_signal_before_incidental_words() -> None:
    text = "Risiko: sebaiknya AVOID bila support jebol.\nKesimpulan AI: BUY"
    assert extract_signal(text) == "BUY"


def test_disclaimer_and_message_split() -> None:
    text = ensure_disclaimer("Analisa singkat")
    assert "bukan nasihat keuangan" in text.lower()
    assert all(len(chunk) <= 100 for chunk in split_telegram_message("a" * 250, 100))
