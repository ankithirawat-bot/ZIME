"""
Report Builder.

Converts raw factor results into a deterministic, human-readable
research report using predefined rules. No AI/LLM involved.
"""

from __future__ import annotations

from backend.core.enums import Signal
from backend.core.factor_result import FactorResult
from backend.engines.factor_engine import EngineError
from backend.reporting.models import DataSummary, ResearchReport, Section
from backend.services.research_service import ResearchResult


def build_report(result: ResearchResult) -> ResearchReport:
    """Build an explainable research report from a ResearchResult.

    Interprets factor outputs using deterministic rules and generates
    a human-readable report with trend, momentum, and volatility sections.

    Args:
        result: The ResearchResult to interpret.

    Returns:
        A ResearchReport with interpreted sections and summary.
    """
    # Build data summary
    data_summary = DataSummary(
        symbol=result.symbol,
        period=result.period,
        interval=result.interval,
        rows=result.rows,
        data_start=result.data_start.isoformat() if result.data_start else None,
        data_end=result.data_end.isoformat() if result.data_end else None,
    )

    # Collect factor values by label
    factors = result.factor_results
    errors = result.engine_errors

    # Build sections
    trend = _build_trend_section(factors)
    momentum = _build_momentum_section(factors)
    volatility = _build_volatility_section(factors)

    # Build warnings
    warnings = _build_warnings(factors, errors, result.rows)

    # Build overall summary
    overall = _build_overall_summary(trend, momentum, volatility, warnings)

    return ResearchReport(
        symbol=result.symbol,
        generated_at=result.generated_at,
        data_summary=data_summary,
        trend=trend,
        momentum=momentum,
        volatility=volatility,
        warnings=warnings,
        overall_summary=overall,
    )


def _build_trend_section(factors: dict[str, FactorResult]) -> Section:
    """Build the trend analysis section.

    Rules:
    - EMA/SMA: price > MA → bullish, price < MA → bearish
    - Multiple MAs aligned → stronger signal

    Args:
        factors: Mapping of factor labels to FactorResult.

    Returns:
        A Section with trend interpretation.
    """
    signals: list[str] = []
    interpretations: list[str] = []

    # Check moving averages
    ma_results = {}
    for label, fr in factors.items():
        lower = label.lower()
        if any(name in lower for name in ["sma", "ema", "wma", "vwma"]):
            if fr.value is not None:
                ma_results[label] = fr

    if ma_results:
        bullish_count = sum(1 for fr in ma_results.values() if fr.signal == Signal.BULLISH)
        bearish_count = sum(1 for fr in ma_results.values() if fr.signal == Signal.BEARISH)
        total = len(ma_results)

        for label, fr in ma_results.items():
            period = fr.metadata.get("period", "?") if fr.metadata else "?"
            if fr.signal == Signal.BULLISH:
                signals.append(f"{label}: Price above {period}-period moving average (bullish)")
            elif fr.signal == Signal.BEARISH:
                signals.append(f"{label}: Price below {period}-period moving average (bearish)")
            else:
                signals.append(f"{label}: Price near {period}-period moving average (neutral)")

        if bullish_count > bearish_count:
            interpretations.append(
                f"Price is trading above {bullish_count} of {total} key moving averages"
            )
        elif bearish_count > bullish_count:
            interpretations.append(
                f"Price is trading below {bearish_count} of {total} key moving averages"
            )
        else:
            interpretations.append("Price is mixed relative to key moving averages")
    else:
        interpretations.append("No moving average data available")

    return Section(
        name="Trend",
        interpretation=". ".join(interpretations),
        signals=signals,
    )


def _build_momentum_section(factors: dict[str, FactorResult]) -> Section:
    """Build the momentum analysis section.

    Rules:
    - RSI < 30 → oversold
    - RSI 30-70 → neutral
    - RSI > 70 → overbought
    - MACD > Signal → bullish crossover
    - MACD < Signal → bearish crossover
    - ROC > 0 → positive momentum
    - ROC < 0 → negative momentum

    Args:
        factors: Mapping of factor labels to FactorResult.

    Returns:
        A Section with momentum interpretation.
    """
    signals: list[str] = []
    interpretations: list[str] = []

    # RSI
    for label, fr in factors.items():
        if "rsi" in label.lower() and fr.value is not None:
            rsi_val = fr.value
            if rsi_val < 30:
                signals.append(f"{label}: RSI at {rsi_val:.1f} — oversold territory")
                interpretations.append(f"Momentum is oversold (RSI={rsi_val:.1f})")
            elif rsi_val > 70:
                signals.append(f"{label}: RSI at {rsi_val:.1f} — overbought territory")
                interpretations.append(f"Momentum is overbought (RSI={rsi_val:.1f})")
            else:
                signals.append(f"{label}: RSI at {rsi_val:.1f} — neutral range")
                interpretations.append(f"Momentum is neutral (RSI={rsi_val:.1f})")

    # MACD
    for label, fr in factors.items():
        if "macd" in label.lower() and fr.value is not None:
            if fr.signal == Signal.BULLISH:
                signals.append(f"{label}: MACD above signal line — bullish crossover")
                interpretations.append("MACD shows bullish momentum")
            elif fr.signal == Signal.BEARISH:
                signals.append(f"{label}: MACD below signal line — bearish crossover")
                interpretations.append("MACD shows bearish momentum")
            else:
                signals.append(f"{label}: MACD near signal line — neutral")
                interpretations.append("MACD is neutral")

    # ROC
    for label, fr in factors.items():
        if "roc" in label.lower() and fr.value is not None:
            roc_val = fr.value
            if roc_val > 0:
                signals.append(f"{label}: Rate of change at {roc_val:.2f}% — positive")
                interpretations.append(f"Price momentum is positive ({roc_val:.2f}%)")
            elif roc_val < 0:
                signals.append(f"{label}: Rate of change at {roc_val:.2f}% — negative")
                interpretations.append(f"Price momentum is negative ({roc_val:.2f}%)")
            else:
                signals.append(f"{label}: Rate of change at 0% — flat")
                interpretations.append("Price momentum is flat")

    # Williams %R
    for label, fr in factors.items():
        if "williams" in label.lower() and fr.value is not None:
            wr_val = fr.value
            if wr_val < -80:
                signals.append(f"{label}: Williams %R at {wr_val:.1f} — oversold")
            elif wr_val > -20:
                signals.append(f"{label}: Williams %R at {wr_val:.1f} — overbought")
            else:
                signals.append(f"{label}: Williams %R at {wr_val:.1f} — neutral")

    # Stochastic
    for label, fr in factors.items():
        if "stochastic" in label.lower() and fr.value is not None:
            stoch_val = fr.value
            if stoch_val < 20:
                signals.append(f"{label}: Stochastic at {stoch_val:.1f} — oversold")
            elif stoch_val > 80:
                signals.append(f"{label}: Stochastic at {stoch_val:.1f} — overbought")
            else:
                signals.append(f"{label}: Stochastic at {stoch_val:.1f} — neutral")

    if not interpretations:
        interpretations.append("No momentum data available")

    return Section(
        name="Momentum",
        interpretation=". ".join(interpretations),
        signals=signals,
    )


def _build_volatility_section(factors: dict[str, FactorResult]) -> Section:
    """Build the volatility analysis section.

    Rules:
    - ATR increasing → higher volatility
    - ATR stable → normal volatility
    - Bollinger: price above upper band → potential breakout
    - Bollinger: price below lower band → potential weakness
    - Bollinger bandwidth wide → high volatility

    Args:
        factors: Mapping of factor labels to FactorResult.

    Returns:
        A Section with volatility interpretation.
    """
    signals: list[str] = []
    interpretations: list[str] = []

    # ATR
    for label, fr in factors.items():
        if "atr" in label.lower() and fr.value is not None:
            atr_val = fr.value
            if fr.signal == Signal.BULLISH:
                signals.append(f"{label}: ATR at {atr_val:.4f} — increasing volatility")
                interpretations.append(f"Volatility is elevated (ATR={atr_val:.4f})")
            elif fr.signal == Signal.BEARISH:
                signals.append(f"{label}: ATR at {atr_val:.4f} — decreasing volatility")
                interpretations.append(f"Volatility is declining (ATR={atr_val:.4f})")
            else:
                signals.append(f"{label}: ATR at {atr_val:.4f} — stable volatility")
                interpretations.append(f"Volatility is normal (ATR={atr_val:.4f})")

    # Bollinger Bands
    for label, fr in factors.items():
        if "bollinger" in label.lower() and fr.value is not None:
            metadata = fr.metadata or {}
            bandwidth = metadata.get("bandwidth", 0)
            if fr.signal == Signal.BULLISH:
                signals.append(f"{label}: Price near upper band — potential breakout")
                interpretations.append("Bollinger Bands suggest upward pressure")
            elif fr.signal == Signal.BEARISH:
                signals.append(f"{label}: Price near lower band — potential weakness")
                interpretations.append("Bollinger Bands suggest downward pressure")
            else:
                signals.append(f"{label}: Price within bands — normal range")
                interpretations.append("Bollinger Bands show normal volatility")

            if bandwidth > 0.1:
                signals.append(f"{label}: Bandwidth at {bandwidth:.4f} — wide bands")
            elif bandwidth < 0.02:
                signals.append(f"{label}: Bandwidth at {bandwidth:.4f} — narrow bands (squeeze)")

    if not interpretations:
        interpretations.append("No volatility data available")

    return Section(
        name="Volatility",
        interpretation=". ".join(interpretations),
        signals=signals,
    )


def _build_warnings(
    factors: dict[str, FactorResult],
    errors: list[EngineError],
    rows: int,
) -> list[str]:
    """Build warnings about missing or failed data.

    Args:
        factors: Mapping of factor labels to FactorResult.
        errors:  List of engine errors.
        rows:    Number of data rows.

    Returns:
        List of warning messages.
    """
    warnings: list[str] = []

    # Check for failed factors
    if errors:
        for err in errors:
            warnings.append(f"Factor '{err.factor}' failed: {err.message}")

    # Check for factors with None values
    for label, fr in factors.items():
        if fr.value is None:
            warnings.append(f"Factor '{label}' returned no value (insufficient data?)")

    # Check for partial analysis
    expected_factors = {"sma", "ema", "rsi", "macd", "atr", "bollinger_bands"}
    present_factors = set()
    for label in factors:
        lower = label.lower()
        for name in expected_factors:
            if name in lower:
                present_factors.add(name)

    missing = expected_factors - present_factors
    if missing and factors:
        warnings.append(f"Missing indicators: {', '.join(sorted(missing))}")

    # Check for insufficient history
    if rows < 50:
        warnings.append(f"Limited history: only {rows} data points (50+ recommended)")

    return warnings


def _build_overall_summary(
    trend: Section,
    momentum: Section,
    volatility: Section,
    warnings: list[str],
) -> str:
    """Generate a concise overall summary from the sections.

    Rules:
    - Combine trend, momentum, and volatility interpretations
    - Add warning context if present
    - Keep it concise and actionable

    Args:
        trend:      Trend section.
        momentum:   Momentum section.
        volatility: Volatility section.
        warnings:   List of warnings.

    Returns:
        A concise summary string.
    """
    parts: list[str] = []

    # Trend
    trend_interp = trend.interpretation
    if "above" in trend_interp.lower():
        parts.append("Trend remains positive")
    elif "below" in trend_interp.lower():
        parts.append("Trend is negative")
    elif "mixed" in trend_interp.lower():
        parts.append("Trend is mixed")
    else:
        parts.append("Trend is unclear")

    # Momentum
    mom_interp = momentum.interpretation
    if "oversold" in mom_interp.lower():
        parts.append("momentum is oversold")
    elif "overbought" in mom_interp.lower():
        parts.append("momentum is overbought")
    elif "neutral" in mom_interp.lower():
        parts.append("momentum is neutral")
    elif "positive" in mom_interp.lower():
        parts.append("momentum is positive")
    elif "negative" in mom_interp.lower():
        parts.append("momentum is negative")
    else:
        parts.append("momentum is unclear")

    # Volatility
    vol_interp = volatility.interpretation
    if "elevated" in vol_interp.lower() or "higher" in vol_interp.lower():
        parts.append("while volatility is elevated")
    elif "declining" in vol_interp.lower():
        parts.append("while volatility is declining")
    elif "normal" in vol_interp.lower():
        parts.append("while volatility remains moderate")
    else:
        parts.append("with volatility unclear")

    summary = " ".join(parts) + "."

    # Add warning context
    if warnings:
        summary += f" Note: {len(warnings)} warning(s) present."

    return summary
