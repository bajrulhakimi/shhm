from app.services.conclusion_summary_service import ConclusionSummaryService


def test_builds_compact_quantitative_conclusion() -> None:
    data = {
        "stock": {
            "code": "SMMA",
            "last_price": 22450,
            "daily_change_percent": 7.03,
        },
        "technical": {
            "ma20": 20080,
            "ma50": 19000,
            "ma200": 17000,
            "macd": 150,
            "macd_signal": 100,
            "rsi14": 89.25,
            "volume_ratio": 0.82,
            "support": 20080,
            "resistance": 35550,
        },
    }

    summary = ConclusionSummaryService.build(data)
    rendered = ConclusionSummaryService.render(summary)

    assert summary["trend_signal"] == "Bullish Kuat"
    assert summary["macd_label"] == "MACD Positif"
    assert summary["target_2"] > summary["price"]
    assert "SMMA |" in rendered
    assert "Harga: 22.450 | Harian +7.03% | Volume 0.82x" in rendered
    assert "Entry: 20.080 - 22.450" in rendered
    assert "RR 1:2.00" in rendered


def test_score_penalizes_overbought_extension() -> None:
    score = ConclusionSummaryService._score(
        price=120,
        ma20=100,
        ma50=90,
        ma200=80,
        macd=5,
        macd_signal=3,
        rsi=90,
        volume_ratio=0.5,
        daily_change=11,
    )

    assert score < 75
