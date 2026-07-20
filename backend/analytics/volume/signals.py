"""
Volume signal providers.

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
from backend.analytics.volume.evidence import Evidence
from backend.analytics.volume.exceptions import SignalError
from backend.analytics.volume.models import SignalOutput

Signal = Callable[[AnalyticsContext], SignalOutput]


def _volumes(context: AnalyticsContext) -> list[float]:
    return [bar.volume for bar in context.prices]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def relative_volume(context: AnalyticsContext) -> SignalOutput:
    """Score current volume against its recent average."""
    vols = _volumes(context)
    cfg = context.config
    w = cfg.relative_volume_window
    if len(vols) < 2:
        return SignalOutput(
            "relative_volume", 0.0,
            (Evidence("relative_volume", "Insufficient history for relative volume"),),
            available=False,
        )

    window = vols[-w:] if len(vols) >= w else vols
    avg = _mean(window)
    last = vols[-1]
    if avg == 0:
        return SignalOutput(
            "relative_volume", 0.0,
            (Evidence("relative_volume", "Invalid zero average volume"),), available=False,
        )

    ratio = last / avg
    score = max(-1.0, min(1.0, ratio - 1.0))
    evidence = [Evidence("relative_volume", f"Relative volume {ratio:.2f}x average")]
    return SignalOutput("relative_volume", score, tuple(evidence))


def volume_trend(context: AnalyticsContext) -> SignalOutput:
    """Score the trend of volume (rising vs falling participation)."""
    vols = _volumes(context)
    cfg = context.config
    w = cfg.volume_trend_window
    if len(vols) < 2 * w:
        return SignalOutput(
            "volume_trend", 0.0,
            (Evidence("volume_trend", "Insufficient data for volume trend"),),
            available=False,
        )

    recent = _mean(vols[-w:])
    earlier = _mean(vols[-2 * w:-w])
    if earlier == 0:
        return SignalOutput(
            "volume_trend", 0.0,
            (Evidence("volume_trend", "Invalid zero baseline volume"),), available=False,
        )

    ratio = recent / earlier
    score = max(-1.0, min(1.0, ratio - 1.0))
    direction = "rising" if ratio >= 1 else "falling"
    evidence = [Evidence("volume_trend", f"Volume trend {direction} ({ratio:.2f}x)")]
    return SignalOutput("volume_trend", score, tuple(evidence))


def accumulation_distribution(context: AnalyticsContext) -> SignalOutput:
    """Score accumulation vs distribution via up/down volume split."""
    prices = context.prices
    cfg = context.config
    w = cfg.accumulation_window
    if len(prices) < 2:
        return SignalOutput(
            "accumulation", 0.0,
            (Evidence("accumulation", "Insufficient data for accumulation"),),
            available=False,
        )

    window = prices[-w:] if len(prices) >= w else prices
    up_vol = 0.0
    down_vol = 0.0
    total = 0.0
    for i in range(1, len(window)):
        vol = window[i].volume
        total += vol
        if window[i].close > window[i - 1].close:
            up_vol += vol
        elif window[i].close < window[i - 1].close:
            down_vol += vol

    if total == 0:
        return SignalOutput(
            "accumulation", 0.0,
            (Evidence("accumulation", "Invalid zero total volume"),), available=False,
        )

    up_ratio = up_vol / total
    score = up_ratio * 2.0 - 1.0
    label = "Accumulation" if up_ratio >= 0.5 else "Distribution"
    evidence = [
        Evidence("accumulation", f"{label}: {up_ratio * 100:.0f}% of volume on up days")
    ]
    return SignalOutput("accumulation", score, tuple(evidence))


def volume_consistency(context: AnalyticsContext) -> SignalOutput:
    """Score how steady (consistent) the volume profile is."""
    vols = _volumes(context)
    cfg = context.config
    w = cfg.consistency_window
    if len(vols) < 2:
        return SignalOutput(
            "consistency", 0.0,
            (Evidence("consistency", "Insufficient data for consistency"),),
            available=False,
        )

    window = vols[-w:] if len(vols) >= w else vols
    mean = _mean(window)
    if mean == 0:
        return SignalOutput(
            "consistency", 0.0,
            (Evidence("consistency", "Invalid zero average volume"),), available=False,
        )

    variance = sum((v - mean) ** 2 for v in window) / len(window)
    cv = math.sqrt(variance) / mean
    score = max(-1.0, min(1.0, 1.0 - 2.0 * cv))
    if score > 0.3:
        text = "Volume consistency high"
    elif score < -0.3:
        text = "Volume erratic"
    else:
        text = "Volume consistency moderate"
    evidence = [Evidence("consistency", f"{text} (CV {cv:.2f})")]
    return SignalOutput("consistency", score, tuple(evidence))


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
        "relative_volume": ("relative_volume", relative_volume),
        "volume_trend": ("volume_trend", volume_trend),
        "accumulation": ("accumulation", accumulation_distribution),
        "consistency": ("consistency", volume_consistency),
    }


def build_default_signal_registry() -> SignalRegistry:
    """Create a registry pre-populated with the standard volume signals."""
    registry = SignalRegistry()
    for name, (_, signal) in _default_signal_config().items():
        registry.register(name, signal)
    return registry
