from typing import Any

from app.utils.formatter import finite_or_none


class ConclusionSummaryService:
    @classmethod
    def build(cls, data: dict[str, Any]) -> dict[str, Any]:
        stock = data["stock"]
        technical = data["technical"]
        price = cls._number(stock.get("last_price"))
        support = cls._number(technical.get("support"))
        resistance = cls._number(technical.get("resistance"))
        ma20 = cls._number(technical.get("ma20"))
        ma50 = cls._number(technical.get("ma50"))
        ma200 = cls._number(technical.get("ma200"))
        macd = cls._number(technical.get("macd"))
        macd_signal = cls._number(technical.get("macd_signal"))
        rsi = cls._number(technical.get("rsi14"))
        volume_ratio = cls._number(technical.get("volume_ratio"))
        daily_change = cls._number(stock.get("daily_change_percent"))

        score = cls._score(
            price,
            ma20,
            ma50,
            ma200,
            macd,
            macd_signal,
            rsi,
            volume_ratio,
            daily_change,
        )
        trend_signal = cls._trend_signal(price, ma20, ma50, ma200, macd, macd_signal)
        macd_label = cls._macd_label(macd, macd_signal)

        entry_low = (
            support
            if support and support < price
            else ma20
            if ma20 and ma20 < price
            else price
        )
        entry_high = price
        stop_loss = cls._round_idx_price((entry_low or price) * 0.95)
        risk = max(price - stop_loss, cls._idx_tick(price))
        one_r_target = price + risk
        target_1 = cls._round_idx_price(
            min(resistance, one_r_target) if resistance and resistance > price else one_r_target
        )
        target_2 = cls._round_idx_price(price + (2 * risk))
        risk_reward = (target_2 - price) / risk if risk else 0

        return {
            "stock_code": stock["code"],
            "score": score,
            "attractiveness": cls._attractiveness(score),
            "trend_signal": trend_signal,
            "macd_label": macd_label,
            "rsi": rsi,
            "price": price,
            "daily_change_percent": daily_change,
            "volume_ratio": volume_ratio,
            "entry_low": round(entry_low),
            "entry_high": round(entry_high),
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_reward": round(risk_reward, 2),
        }

    @classmethod
    def render(cls, summary: dict[str, Any]) -> str:
        return "\n".join(
            [
                (
                    f"{summary['stock_code']} | {summary['score']}/100 | "
                    f"{summary['attractiveness']}"
                ),
                (
                    f"Sinyal: {summary['trend_signal']} | {summary['macd_label']} | "
                    f"RSI {cls._format_decimal(summary['rsi'])}"
                ),
                (
                    f"Harga: {cls._format_price(summary['price'])} | "
                    f"Harian {cls._format_percent(summary['daily_change_percent'])} | "
                    f"Volume {cls._format_ratio(summary['volume_ratio'])}"
                ),
                (
                    f"Entry: {cls._format_price(summary['entry_low'])} - "
                    f"{cls._format_price(summary['entry_high'])}"
                ),
                (
                    f"SL: {cls._format_price(summary['stop_loss'])} | "
                    f"T1: {cls._format_price(summary['target_1'])} | "
                    f"T2: {cls._format_price(summary['target_2'])} | "
                    f"RR 1:{summary['risk_reward']:.2f}"
                ),
            ]
        )

    @staticmethod
    def _score(
        price: float,
        ma20: float,
        ma50: float,
        ma200: float,
        macd: float,
        macd_signal: float,
        rsi: float,
        volume_ratio: float,
        daily_change: float,
    ) -> int:
        score = 0
        score += 10 if price and ma20 and price > ma20 else 0
        score += 10 if price and ma50 and price > ma50 else 0
        score += 15 if price and ma200 and price > ma200 else 0
        score += 10 if ma20 and ma50 and ma20 > ma50 else 0
        score += 10 if ma50 and ma200 and ma50 > ma200 else 0
        score += (
            15 if macd is not None and macd_signal is not None and macd > macd_signal else 0
        )
        score += 15 if 50 <= rsi <= 70 else 8 if 40 <= rsi < 50 else 4 if 30 <= rsi < 40 else 0
        score += (
            10
            if volume_ratio >= 1.5
            else 7
            if volume_ratio >= 1
            else 3
            if volume_ratio >= 0.7
            else 0
        )
        score += 5 if daily_change > 0 else 0

        if rsi > 80:
            score -= 15
        elif rsi > 70:
            score -= 7
        if price and ma20 and price > ma20 * 1.15:
            score -= 15
        if daily_change > 10:
            score -= 5
        return max(0, min(100, round(score)))

    @staticmethod
    def _trend_signal(
        price: float,
        ma20: float,
        ma50: float,
        ma200: float,
        macd: float,
        macd_signal: float,
    ) -> str:
        bullish = sum(
            [
                bool(price and ma20 and price > ma20),
                bool(price and ma50 and price > ma50),
                bool(price and ma200 and price > ma200),
                bool(ma20 and ma50 and ma20 > ma50),
                bool(macd is not None and macd_signal is not None and macd > macd_signal),
            ]
        )
        if bullish >= 4:
            return "Bullish Kuat"
        if bullish >= 3:
            return "Bullish"
        if bullish == 2:
            return "Netral"
        if bullish == 1:
            return "Bearish"
        return "Bearish Kuat"

    @staticmethod
    def _macd_label(macd: float, signal: float) -> str:
        if macd is None or signal is None:
            return "MACD N/A"
        if macd > signal:
            return "MACD Positif"
        if macd < signal:
            return "MACD Negatif"
        return "MACD Netral"

    @staticmethod
    def _attractiveness(score: int) -> str:
        if score >= 75:
            return "Menarik"
        if score >= 60:
            return "Cukup Menarik"
        if score >= 45:
            return "Netral"
        return "Belum Menarik"

    @staticmethod
    def _number(value: Any) -> float:
        normalized = finite_or_none(value)
        return float(normalized) if normalized is not None else 0.0

    @staticmethod
    def _idx_tick(price: float) -> int:
        if price < 200:
            return 1
        if price < 500:
            return 2
        if price < 2000:
            return 5
        if price < 5000:
            return 10
        return 25

    @classmethod
    def _round_idx_price(cls, price: float) -> int:
        tick = cls._idx_tick(price)
        return max(tick, round(price / tick) * tick)

    @staticmethod
    def _format_price(value: Any) -> str:
        return f"{round(float(value)):,.0f}".replace(",", ".") if value else "N/A"

    @staticmethod
    def _format_decimal(value: Any) -> str:
        return f"{float(value):.2f}" if value is not None else "N/A"

    @staticmethod
    def _format_percent(value: Any) -> str:
        return f"{float(value):+.2f}%" if value is not None else "N/A"

    @staticmethod
    def _format_ratio(value: Any) -> str:
        return f"{float(value):.2f}x" if value is not None else "N/A"
