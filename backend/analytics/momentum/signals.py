"""
Momentum signal providers.

Each signal consumes an :class:`AnalyticsContext` and returns only a signed
score in [-1, 1] plus explainable :class:`Evidence`. Raw indicator values are
kept internal and never returned. Signals are registered in a
:class:`SignalRegistry` so new signals are added by registration, not by
editing engine code.
"""

from __future__ import annotations

from collections.abc import Callable

from backend.analytics.models import AnalyticsContext
from backend.analytics.momentum.evidence import Evidence
from backend.analytics.momentum.exceptions import SignalError
from backend.analytics.momentum.models import SignalOutput

Signal = Callable[[AnalyticsContext], SignalOutput]


def _closes(context: AnalyticsContext) -> list[float]:
    return [bar.close for bar in context.prices]


def _pct(change: float, base: float) -> float:
    if base == 0:
        return 0.0
    return change / abs(base)


def rate_of_change(context: AnalyticsContext) -> SignalOutput:
    """Score momentum via short and long rate of change."""
    closes = _closes(context)
    cfg = context.config
    short = cfg.roc_short_period
    long_ = cfg.roc_long_period
    if len(closes) < long_ + 1:
        return SignalOutput(
            "roc", 0.0,
            (Evidence("roc", "Insufficient history for rate of change"),),
            available=False,
        )

    base_short = closes[-(short + 1)]
    base_long = closes[-(long_ + 1)]
    if base_short == 0 or base_long == 0:
        return SignalOutput(
            "roc", 0.0, (Evidence("roc", "Invalid base price"),), available=False,
        )

    roc_short = _pct(closes[-1] - base_short, base_short)
    roc_long = _pct(closes[-1] - base_long, base_long)
    combo = roc_short * 0.6 + roc_long * 0.4
    score = max(-1.0, min(1.0, combo / 0.2))
    direction = "rising" if combo > 0 else "falling"
    evidence = [
        Evidence(
            "roc",
            f"Rate of change {direction}: short {roc_short * 100:.1f}% "
            f"(over {short}) / long {roc_long * 100:.1f}% (over {long_})",
        )
    ]
    return SignalOutput("roc", score, tuple(evidence))


def price_acceleration(context: AnalyticsContext) -> SignalOutput:
    """Score the acceleration (second derivative) of the price move."""
    closes = _closes(context)
    cfg = context.config
    w = cfg.acceleration_window
    if len(closes) < 2 * w + 1:
        return SignalOutput(
            "acceleration", 0.0,
            (Evidence("acceleration", "Insufficient data for acceleration"),),
            available=False,
        )

    slope_recent = _pct(closes[-1] - closes[-(w + 1)], closes[-(w + 1)])
    slope_earlier = _pct(closes[-(w + 1)] - closes[-(2 * w + 1)], closes[-(2 * w + 1)])
    accel = slope_recent - slope_earlier
    score = max(-1.0, min(1.0, accel / 0.05))

    if accel > 0.02:
        text = "Strong positive acceleration"
    elif accel < -0.02:
        text = "Momentum decelerating"
    else:
        text = "Momentum steady"
    evidence = [Evidence("acceleration", f"{text} ({accel * 100:.1f}% change in slope)")]
    return SignalOutput("acceleration", score, tuple(evidence))


def momentum_persistence(context: AnalyticsContext) -> SignalOutput:
    """Score how many consecutive sessions momentum has held its direction."""
    closes = _closes(context)
    cfg = context.config
    if len(closes) < 2:
        return SignalOutput(
            "persistence", 0.0,
            (Evidence("persistence", "Insufficient data for momentum persistence"),),
            available=False,
        )

    returns = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    direction = 1 if sum(returns) >= 0 else -1
    run = 0
    for r in reversed(returns):
        sign = 1 if r > 0 else (-1 if r < 0 else 0)
        if sign == 0 or sign != direction:
            break
        run += 1

    score = direction * min(1.0, run / max(1, cfg.momentum_persistence_threshold))
    evidence = [
        Evidence(
            "persistence",
            f"Momentum persisted {run} sessions in {'up' if direction > 0 else 'down'} direction",
        )
    ]
    if context.prices:
        start = context.prices[0].trade_date
        end = context.prices[-1].trade_date
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


def breakout_continuation(context: AnalyticsContext) -> SignalOutput:
    """Score confirmation or failure of a recent breakout/breakdown."""
    bars = context.prices
    cfg = context.config
    w = cfg.breakout_window
    if len(bars) < w + 2:
        return SignalOutput(
            "breakout", 0.0,
            (Evidence("breakout", "Insufficient data for breakout analysis"),),
            available=False,
        )

    window = bars[-(w + 1):-1]
    prev_high = max(b.high for b in window)
    prev_low = min(b.low for b in window)
    last = bars[-1].close

    if last > prev_high:
        score, text = 0.7, "Breakout continuation confirmed"
    elif last < prev_low:
        score, text = -0.7, "Breakdown continuation confirmed"
    else:
        score, text = 0.0, "No breakout detected"
    evidence = [Evidence("breakout", text)]
    return SignalOutput("breakout", score, tuple(evidence))


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
        "roc": ("roc", rate_of_change),
        "acceleration": ("acceleration", price_acceleration),
        "persistence": ("persistence", momentum_persistence),
        "breakout": ("breakout", breakout_continuation),
    }


def build_default_signal_registry() -> SignalRegistry:
    """Create a registry pre-populated with the standard momentum signals."""
    registry = SignalRegistry()
    for name, (_, signal) in _default_signal_config().items():
        registry.register(name, signal)
    return registry
