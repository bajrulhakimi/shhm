from app.services.structured_result_service import StructuredResultService


def test_parses_and_renders_structured_json() -> None:
    raw = """{
      "stock_code": "BBCA",
      "trend": "Bullish moderat",
      "risks": "Risiko market",
      "signal": "buy on weakness",
      "confidence": "medium",
      "conclusion": "Menunggu area support"
    }"""
    result = StructuredResultService.parse(raw)

    assert result.signal == "BUY ON WEAKNESS"
    assert result.confidence == "Medium"
    assert result.risks == ["Risiko market"]
    assert "BUY ON WEAKNESS" in StructuredResultService.render(result)


def test_falls_back_safely_for_unstructured_text() -> None:
    result = StructuredResultService.parse("Kesimpulan AI: HOLD\nConfidence Level: High", "TLKM")

    assert result.stock_code == "TLKM"
    assert result.signal == "HOLD"
    assert result.confidence == "High"
