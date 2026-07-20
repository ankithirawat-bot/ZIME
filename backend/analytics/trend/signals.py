"""
Trend signal providers.

Each signal consumes an :class:`AnalyticsContext` and returns only a signed
score in [-1, 1] plus explainable :class:`Evidence`. Raw indicator values are
kept internal and never returned. Signals are registered in a
:class:`SignalRegistry` so new signals are added by registration, not by
editing engine code.
"""

from __future__ import annotations

from collections.abc import Callable

from backend.analytics.models import AnalyticsContext
from backend.analytics.trend.evidence import Evidence
from backend.analytics.trend.exceptions import SignalError
from backend.analytics.trend.models import SignalOutput

Signal = Callable[[AnalyticsContext], SignalOutput]


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period or period < 1:
        return None
    k = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    ema = seed
    for value in values[period:]:
        ema = value * k + ema * (1.0 - k)
    return ema


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period or period < 1:
        return None
    return sum(values[-period:]) / period


def _closes(context: AnalyticsContext) -> list[float]:
    return [bar.close for bar in context.prices]


def moving_average_alignment(context: AnalyticsContext) -> SignalOutput:
    """Score moving-average stack alignment and price position."""
    closes = _closes(context)
    cfg = context.config
    ema_s = _ema(closes, cfg.ema_short_period)
    ema_m = _ema(closes, cfg.ema_mid_period)
    sma_l = _sma(closes, cfg.sma_long_period)

    if ema_s is None or ema_m is None or sma_l is None:
        return SignalOutput(
            "ma_alignment", 0.0,
            (Evidence("ma_alignment", "Insufficient history for moving-average alignment"),),
            available=False,
        )

    price = closes[-1]
    checks = [
        ("EMA20 above EMA50", ema_s > ema_m),
        ("EMA50 above SMA200", ema_m > sma_l),
        ("Price above EMA20", price > ema_s),
        ("Price above long-term trend", price > sma_l),
    ]
    bullish = sum(1 for _, cond in checks if cond)
    total = len(checks)
    evidence: list[Evidence] = []
    for label, cond in checks:
        evidence.append(
            Evidence("ma_alignment", f"{label}: {'aligned' if cond else 'not aligned'}")
        )
    if bullish == total:
        evidence.insert(0, Evidence("ma_alignment", "EMA stack aligned (bullish)"))
    elif bullish == 0:
        evidence.insert(0, Evidence("ma_alignment", "EMA stack inverted (bearish)"))

    score = (bullish / total) * 2.0 - 1.0
    return SignalOutput("ma_alignment", score, tuple(evidence))


def higher_highs_lows(context: AnalyticsContext) -> SignalOutput:
    """Score trend structure via higher highs and higher lows."""
    cfg = context.config
    bars = context.prices
    window = min(cfg.structure_window, len(bars))
    if window < 3:
        return SignalOutput(
            "structure", 0.0,
            (Evidence("structure", "Insufficient data for structure analysis"),),
            available=False,
        )

    highs = [bar.high for bar in bars[-window:]]
    lows = [bar.low for bar in bars[-window:]]
    hh = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i - 1])
    lh = sum(1 for i in range(1, len(highs)) if highs[i] < highs[i - 1])
    hl = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i - 1])
    ll = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i - 1])

    bullish = hh + hl
    bearish = lh + ll
    total = hh + lh + hl + ll
    score = (bullish - bearish) / total if total else 0.0

    evidence: list[Evidence] = []
    evidence.append(
        Evidence("structure", f"Higher highs detected ({hh})" if hh > lh
                 else f"Lower highs detected ({lh})")
    )
    evidence.append(
        Evidence("structure", f"Higher lows detected ({hl})" if hl > ll
                 else f"Lower lows detected ({ll})")
    )
    return SignalOutput("structure", score, tuple(evidence))


def slope_direction(context: AnalyticsContext) -> SignalOutput:
    """Score the direction of the recent price slope."""
    closes = _closes(context)
    cfg = context.config
    window = min(cfg.slope_window, len(closes) - 1)
    if window < 2:
        return SignalOutput(
            "slope", 0.0,
            (Evidence("slope", "Insufficient data for slope estimation"),),
            available=False,
        )
    first = closes[-(window + 1)]
    last = closes[-1]
    if first == 0:
        return SignalOutput(
            "slope", 0.0, (Evidence("slope", "Invalid base price"),), available=False,
        )
    slope_pct = (last - first) / abs(first)
    score = max(-1.0, min(1.0, slope_pct / 0.2))
    direction = "rising" if slope_pct > 0 else "falling"
    evidence = [Evidence("slope", f"Long-term slope {direction} ({slope_pct * 100:.1f}%)")]
    return SignalOutput("slope", score, tuple(evidence))


def trend_persistence(context: AnalyticsContext) -> SignalOutput:
    """Score how long the current trend direction has persisted."""
    cfg = context.config
    bars = context.prices
    closes = [bar.close for bar in bars]
    if len(closes) < 2:
        return SignalOutput(
            "persistence", 0.0,
            (Evidence("persistence", "Insufficient data for persistence analysis"),),
            available=False,
        )

    sma_l = _sma(closes, cfg.sma_long_period)
    baseline = sma_l if sma_l is not None else (_ema(closes, cfg.ema_mid_period) or closes[-1])
    above = closes[-1] >= baseline

    run = 0
    for value in reversed(closes):
        if (value >= baseline) == above:
            run += 1
        else:
            break

    score = (1.0 if above else -1.0) * min(1.0, run / max(1, cfg.persistence_threshold))
    evidence: list[Evidence] = [
        Evidence(
            "persistence",
            f"Trend persisted {run} sessions {'above' if above else 'below'} long-term average",
        )
    ]
    if bars:
        start = bars[0].trade_date
        end = bars[-1].trade_date
        start = bars[0].trade_date
        end = bars[-1].trade_date
        for ca in context.corporate_actions:
            if start <= ca.date <= end:
                evidence.append(
                    Evidence(
                        "persistence",
                        f"Corporate action '{ca.action_type}' on {ca.date.isoformat()} "
                        f"(ratio {ca.ratio}) within window",
                    )
                )
    return SignalOutput("persistence", score, tuple(evidence))


class SignalRegistry:
    """Registry mapping signal names to callables (no switch statements)."""

    def __init__(self) -> None:
        self._signals: dict[str, Signal] = {}

    def register(self, name: str, signal: Signal) -> None:
        """Register a signal under a name."""
        self._signals[name] = signal

    def get(self, name: str) -> Signal:
        """Return a registered signal.

        Raises:
            SignalError: When the signal name is not registered.
        """
        signal = self._signals.get(name)
        if signal is None:
            raise SignalError(f"Signal not registered: {name}")
        return signal

    def all(self) -> dict[str, Signal]:
        """Return a copy of all registered signals."""
        return dict(self._signals)

    def names(self) -> tuple[str, ...]:
        """Return all registered signal names."""
        return tuple(sorted(self._signals))


def _default_signal_config() -> dict[str, tuple[str, Signal]]:
    return {
        "ma_alignment": ("ma_alignment", moving_average_alignment),
        "structure": ("structure", higher_highs_lows),
        "slope": ("slope", slope_direction),
        "persistence": ("persistence", trend_persistence),
    }


def build_default_signal_registry() -> SignalRegistry:
    """Create a registry pre-populated with the standard trend signals."""
    registry = SignalRegistry()
    for name, (_, signal) in _default_signal_config().items():
        registry.register(name, signal)
    return registry
