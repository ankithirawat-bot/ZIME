"""
Volatility signal providers.

Each signal consumes an :class:`AnalyticsContext` and returns only a signed
score in [-1, 1] plus explainable :class:`Evidence`. Raw indicator values are
kept internal and never returned. Signals are registered in a
:class:`SignalRegistry` so new signals are added by registration, not by
editing engine code.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from backend.analytics.models import AnalyticsContext
from backend.analytics.volatility.evidence import Evidence
from backend.analytics.volatility.exceptions import SignalError, VolatilityError
from backend.analytics.volatility.models import SignalOutput

Signal = Callable[[AnalyticsContext], SignalOutput]


HV_BASELINE = 0.012
HV_SCALE = 0.012
RANGE_BASELINE = 0.020
RANGE_SCALE = 0.020


def _closes(context: AnalyticsContext) -> list[float]:
    closes = [bar.close for bar in context.prices]
    if any(c is None for c in closes):
        raise VolatilityError("Missing close prices in data")
    return closes


def _returns(closes: list[float]) -> list[float]:
    out = []
    for i in range(1, len(closes)):
        base = closes[i - 1]
        out.append((closes[i] - base) / base if base != 0 else 0.0)
    return out


def _stdev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def historical_volatility(context: AnalyticsContext) -> SignalOutput:
    """Score the level of recent historical (realized) volatility."""
    closes = _closes(context)
    cfg = context.config
    w = cfg.hv_window
    rets = _returns(closes)
    if len(rets) < w:
        return SignalOutput(
            "historical_volatility", 0.0,
            (Evidence("historical_volatility", "Insufficient history for historical volatility"),),
            available=False,
        )

    sd = _stdev(rets[-w:])
    score = max(-1.0, min(1.0, (sd - HV_BASELINE) / HV_SCALE))
    evidence = [Evidence("historical_volatility", f"Historical volatility {sd * 100:.1f}% (daily)")]
    return SignalOutput("historical_volatility", score, tuple(evidence))


def volatility_trend(context: AnalyticsContext) -> SignalOutput:
    """Score whether volatility is rising or falling."""
    closes = _closes(context)
    cfg = context.config
    w = cfg.vol_trend_window
    rets = _returns(closes)
    if len(rets) < 2 * w:
        return SignalOutput(
            "volatility_trend", 0.0,
            (Evidence("volatility_trend", "Insufficient data for volatility trend"),),
            available=False,
        )

    recent = _stdev(rets[-w:])
    earlier = _stdev(rets[-2 * w:-w])
    if earlier <= 1e-9:
        score = 1.0 if recent > 1e-9 else 0.0
    else:
        score = max(-1.0, min(1.0, (recent - earlier) / earlier))

    direction = "rising" if score >= 0 else "falling"
    evidence = [Evidence("volatility_trend", f"Volatility {direction}")]
    return SignalOutput("volatility_trend", score, tuple(evidence))


def range_expansion(context: AnalyticsContext) -> SignalOutput:
    """Score expansion or contraction of the daily price range."""
    bars = context.prices
    cfg = context.config
    w = cfg.range_window
    if len(bars) < w:
        return SignalOutput(
            "range_expansion", 0.0,
            (Evidence("range_expansion", "Insufficient data for range expansion"),),
            available=False,
        )

    ranges = [
        (b.high - b.low) / b.close for b in bars[-w:] if b.close != 0
    ]
    if not ranges:
        return SignalOutput(
            "range_expansion", 0.0,
            (Evidence("range_expansion", "Invalid zero price range"),), available=False,
        )

    avg = sum(ranges) / len(ranges)
    score = max(-1.0, min(1.0, (avg - RANGE_BASELINE) / RANGE_SCALE))
    evidence = [Evidence("range_expansion", f"Average daily range {avg * 100:.1f}%")]
    return SignalOutput("range_expansion", score, tuple(evidence))


def volatility_persistence(context: AnalyticsContext) -> SignalOutput:
    """Score how consistently volatility has stayed elevated or subdued."""
    closes = _closes(context)
    cfg = context.config
    w = cfg.hv_window
    rets = _returns(closes)
    if len(rets) < w:
        return SignalOutput(
            "persistence", 0.0,
            (Evidence("persistence", "Insufficient history for volatility persistence"),),
            available=False,
        )

    count = 0
    total = 0
    acc = 0.0
    for end in range(w, len(rets) + 1):
        seg = rets[end - w:end]
        local = max(-1.0, min(1.0, (_stdev(seg) - HV_BASELINE) / HV_SCALE))
        if local > 0:
            count += 1
        total += 1
        acc += local

    score = acc / total if total else 0.0
    evidence = [
        Evidence("persistence", f"Volatility persisted elevated {count} of {total} windows")
    ]
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
        "historical_volatility": ("historical_volatility", historical_volatility),
        "volatility_trend": ("volatility_trend", volatility_trend),
        "range_expansion": ("range_expansion", range_expansion),
        "persistence": ("persistence", volatility_persistence),
    }


def build_default_signal_registry() -> SignalRegistry:
    """Create a registry pre-populated with the standard volatility signals."""
    registry = SignalRegistry()
    for name, (_, signal) in _default_signal_config().items():
        registry.register(name, signal)
    return registry
