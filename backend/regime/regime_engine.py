"""
Market Regime Engine.

Deterministic engine that evaluates market conditions and classifies
the environment using predefined rules. No AI/LLM involved.
"""

from __future__ import annotations

from backend.regime.models import (
    MarketRegime,
    MarketSnapshot,
    Regime,
)


def analyze_regime(snapshot: MarketSnapshot) -> MarketRegime:
    """Analyze market snapshot and classify the regime.

    Evaluates trend, momentum, breadth, and volatility conditions
    using a scoring system to classify the overall market regime.

    Args:
        snapshot: Complete market snapshot.

    Returns:
        A MarketRegime with classification, score, and explanations.
    """
    score = 0.0
    max_score = 100.0
    reasons: list[str] = []
    warnings: list[str] = []

    # Trend scoring
    trend_score, trend_reasons, trend_warnings = _score_trend(snapshot)
    score += trend_score
    reasons.extend(trend_reasons)
    warnings.extend(trend_warnings)

    # Momentum scoring
    momentum_score, momentum_reasons, momentum_warnings = _score_momentum(snapshot)
    score += momentum_score
    reasons.extend(momentum_reasons)
    warnings.extend(momentum_warnings)

    # Breadth scoring
    breadth_score, breadth_reasons, breadth_warnings = _score_breadth(snapshot)
    score += breadth_score
    reasons.extend(breadth_reasons)
    warnings.extend(breadth_warnings)

    # VIX scoring
    vix_score, vix_reasons, vix_warnings = _score_vix(snapshot)
    score += vix_score
    reasons.extend(vix_reasons)
    warnings.extend(vix_warnings)

    # Clamp score
    score = max(0.0, min(max_score, score))

    # Classify regime
    regime = _classify_regime(score)

    # Calculate confidence (based on data completeness)
    confidence = _calculate_confidence(snapshot, warnings)

    return MarketRegime(
        regime=regime,
        confidence=confidence,
        score=score,
        reasons=reasons,
        warnings=warnings,
    )


def _score_trend(snapshot: MarketSnapshot) -> tuple[float, list[str], list[str]]:
    """Score trend conditions.

    Rules:
    - Nifty above 200 SMA: +15
    - Midcap above 200 SMA: +10
    - Smallcap above 200 SMA: +10
    - Price above EMA20: +5
    - Price above EMA50: +5

    Args:
        snapshot: Market snapshot.

    Returns:
        Tuple of (score, reasons, warnings).
    """
    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    # Nifty 50 trend
    nifty = snapshot.nifty50
    if nifty.sma200 is not None:
        if nifty.current_price > nifty.sma200:
            score += 15
            reasons.append("Nifty trading above long-term trend (200 SMA)")
        else:
            reasons.append("Nifty trading below long-term trend (200 SMA)")
    else:
        warnings.append("Missing Nifty 50 SMA200 data")

    # Midcap trend
    midcap = snapshot.nifty_midcap
    if midcap.sma200 is not None:
        if midcap.current_price > midcap.sma200:
            score += 10
            reasons.append("Midcap trading above long-term trend (200 SMA)")
        else:
            reasons.append("Midcap trading below long-term trend (200 SMA)")
    else:
        warnings.append("Missing Midcap SMA200 data")

    # Smallcap trend
    smallcap = snapshot.nifty_smallcap
    if smallcap.sma200 is not None:
        if smallcap.current_price > smallcap.sma200:
            score += 10
            reasons.append("Smallcap trading above long-term trend (200 SMA)")
        else:
            reasons.append("Smallcap trading below long-term trend (200 SMA)")
    else:
        warnings.append("Missing Smallcap SMA200 data")

    # EMA20 (use Nifty as reference)
    if nifty.ema20 is not None:
        if nifty.current_price > nifty.ema20:
            score += 5
            reasons.append("Price above short-term trend (EMA20)")
        else:
            reasons.append("Price below short-term trend (EMA20)")
    else:
        warnings.append("Missing Nifty 50 EMA20 data")

    # EMA50 (use Nifty as reference)
    if nifty.ema50 is not None:
        if nifty.current_price > nifty.ema50:
            score += 5
            reasons.append("Price above medium-term trend (EMA50)")
        else:
            reasons.append("Price below medium-term trend (EMA50)")
    else:
        warnings.append("Missing Nifty 50 EMA50 data")

    return score, reasons, warnings


def _score_momentum(snapshot: MarketSnapshot) -> tuple[float, list[str], list[str]]:
    """Score momentum conditions.

    Rules:
    - RSI > 55: +5
    - MACD bullish: +5

    Args:
        snapshot: Market snapshot.

    Returns:
        Tuple of (score, reasons, warnings).
    """
    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    nifty = snapshot.nifty50

    # RSI
    if nifty.rsi14 is not None:
        if nifty.rsi14 > 55:
            score += 5
            reasons.append(f"Momentum positive (RSI={nifty.rsi14:.1f})")
        elif nifty.rsi14 < 45:
            reasons.append(f"Momentum negative (RSI={nifty.rsi14:.1f})")
        else:
            reasons.append(f"Momentum neutral (RSI={nifty.rsi14:.1f})")
    else:
        warnings.append("Missing Nifty 50 RSI14 data")

    # MACD
    if nifty.macd_bullish is not None:
        if nifty.macd_bullish:
            score += 5
            reasons.append("MACD showing bullish momentum")
        else:
            reasons.append("MACD showing bearish momentum")
    else:
        warnings.append("Missing Nifty 50 MACD data")

    return score, reasons, warnings


def _score_breadth(snapshot: MarketSnapshot) -> tuple[float, list[str], list[str]]:
    """Score market breadth conditions.

    Rules:
    - Above 50 DMA > 60%: +15
    - Above 200 DMA > 50%: +20

    Args:
        snapshot: Market snapshot.

    Returns:
        Tuple of (score, reasons, warnings).
    """
    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    breadth = snapshot.breadth

    # 50 DMA breadth
    if breadth.percent_above_50dma is not None:
        if breadth.percent_above_50dma > 60:
            score += 15
            reasons.append(
                f"Market breadth expanding ({breadth.percent_above_50dma:.1f}% above 50 DMA)"
            )
        elif breadth.percent_above_50dma < 40:
            reasons.append(
                f"Market breadth contracting ({breadth.percent_above_50dma:.1f}% above 50 DMA)"
            )
        else:
            reasons.append(
                f"Market breadth neutral ({breadth.percent_above_50dma:.1f}% above 50 DMA)"
            )
    else:
        warnings.append("Missing breadth data (percent above 50 DMA)")

    # 200 DMA breadth
    if breadth.percent_above_200dma is not None:
        if breadth.percent_above_200dma > 50:
            score += 20
            reasons.append(
                f"Long-term breadth healthy ({breadth.percent_above_200dma:.1f}% above 200 DMA)"
            )
        elif breadth.percent_above_200dma < 30:
            reasons.append(
                f"Long-term breadth weak ({breadth.percent_above_200dma:.1f}% above 200 DMA)"
            )
        else:
            reasons.append(
                f"Long-term breadth neutral ({breadth.percent_above_200dma:.1f}% above 200 DMA)"
            )
    else:
        warnings.append("Missing breadth data (percent above 200 DMA)")

    return score, reasons, warnings


def _score_vix(snapshot: MarketSnapshot) -> tuple[float, list[str], list[str]]:
    """Score volatility (VIX) conditions.

    Rules:
    - Low VIX (<15): +5
    - High VIX (>25): -5

    Args:
        snapshot: Market snapshot.

    Returns:
        Tuple of (score, reasons, warnings).
    """
    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    if snapshot.india_vix is not None:
        vix = snapshot.india_vix
        if vix < 15:
            score += 5
            reasons.append(f"Volatility low (VIX={vix:.1f}) — favorable for equities")
        elif vix > 25:
            score -= 5
            reasons.append(f"Volatility high (VIX={vix:.1f}) — caution advised")
        else:
            reasons.append(f"Volatility moderate (VIX={vix:.1f})")
    else:
        warnings.append("Missing India VIX data")

    return score, reasons, warnings


def _classify_regime(score: float) -> Regime:
    """Classify regime based on score.

    Rules:
    - 90+: Strong Bull
    - 75-89: Bull
    - 55-74: Neutral
    - 35-54: Weak
    - Below 35: Bear

    Args:
        score: Raw score (0-100).

    Returns:
        Classified regime.
    """
    if score >= 90:
        return Regime.STRONG_BULL
    elif score >= 75:
        return Regime.BULL
    elif score >= 55:
        return Regime.NEUTRAL
    elif score >= 35:
        return Regime.WEAK
    else:
        return Regime.BEAR


def _calculate_confidence(
    snapshot: MarketSnapshot,
    warnings: list[str],
) -> float:
    """Calculate confidence based on data completeness.

    More missing data = lower confidence.

    Args:
        snapshot: Market snapshot.
        warnings: List of warnings.

    Returns:
        Confidence score (0-100).
    """
    # Start with 100, deduct for missing data
    confidence = 100.0

    # Deduct for each warning (roughly 5% per missing piece)
    confidence -= len(warnings) * 5.0

    # Ensure within bounds
    return max(0.0, min(100.0, confidence))
