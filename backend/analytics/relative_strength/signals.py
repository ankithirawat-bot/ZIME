"""
Relative Strength signal providers.

Each signal consumes an :class:`AnalyticsContext` and returns only a signed
score in [-1, 1] plus explainable :class:`Evidence`. Raw indicator values are
kept internal and never returned. Signals are registered in a
:class:`SignalRegistry` so new signals are added by registration, not by
editing engine code.
"""

from __future__ import annotations

from collections.abc import Callable

from backend.analytics.models import AnalyticsContext, MarketBar
from backend.analytics.relative_strength.evidence import Evidence
from backend.analytics.relative_strength.exceptions import SignalError
from backend.analytics.relative_strength.models import SignalOutput

Signal = Callable[[AnalyticsContext], SignalOutput]


def _closes(bars: tuple[MarketBar, ...]) -> list[float]:
    return [bar.close for bar in bars]


def _window_return(closes: list[float], window: int) -> float | None:
    if len(closes) < window + 1:
        return None
    base = closes[-(window + 1)]
    if base == 0:
        return None
    return (closes[-1] - base) / abs(base)


def _outperformance(
    name: str,
    instr: list[float],
    peer: list[float],
    window: int,
) -> SignalOutput:
    if len(instr) < window + 1 or len(peer) < window + 1:
        return SignalOutput(
            name, 0.0,
            (Evidence(name, f"Insufficient history for {name} comparison"),),
            available=False,
        )

    ir = _window_return(instr, window)
    br = _window_return(peer, window)
    if ir is None or br is None:
        return SignalOutput(
            name, 0.0,
            (Evidence(name, f"Insufficient history for {name} comparison"),),
            available=False,
        )

    diff = ir - br
    score = max(-1.0, min(1.0, diff / 0.15))
    direction = "outperforming" if diff >= 0 else "underperforming"
    evidence = [
        Evidence(
            name,
            f"{direction.capitalize()} {abs(diff) * 100:.1f}% vs peer over {window} sessions",
        )
    ]
    return SignalOutput(name, score, tuple(evidence))


def benchmark_outperformance(context: AnalyticsContext) -> SignalOutput:
    """Score outperformance of the instrument versus its benchmark index."""
    cfg = context.config
    return _outperformance(
        "benchmark",
        _closes(context.prices),
        _closes(context.benchmark_prices),
        cfg.rs_window,
    )


def sector_leadership(context: AnalyticsContext) -> SignalOutput:
    """Score leadership of the instrument versus its sector."""
    cfg = context.config
    return _outperformance(
        "sector",
        _closes(context.prices),
        _closes(context.sector_prices),
        cfg.rs_window,
    )


def industry_leadership(context: AnalyticsContext) -> SignalOutput:
    """Score leadership of the instrument versus its industry."""
    cfg = context.config
    return _outperformance(
        "industry",
        _closes(context.prices),
        _closes(context.industry_prices),
        cfg.rs_window,
    )


def relative_momentum_persistence(context: AnalyticsContext) -> SignalOutput:
    """Score how consistently the instrument has outperformed its benchmark."""
    cfg = context.config
    instr = _closes(context.prices)
    peer = _closes(context.benchmark_prices)
    pw = cfg.rs_persistence_window

    if len(instr) < pw + 1 or len(peer) < pw + 1:
        return SignalOutput(
            "persistence", 0.0,
            (Evidence("persistence", "Insufficient history for RS persistence"),),
            available=False,
        )

    n = min(len(instr), len(peer))
    count = 0
    total = 0
    for end in range(pw, n):
        iw = instr[end - pw:end + 1]
        bw = peer[end - pw:end + 1]
        ir = (iw[-1] - iw[0]) / abs(iw[0]) if iw[0] != 0 else 0.0
        br = (bw[-1] - bw[0]) / abs(bw[0]) if bw[0] != 0 else 0.0
        if ir > br:
            count += 1
        total += 1

    score = (count / total) * 2.0 - 1.0
    evidence = [
        Evidence("persistence", f"Relative momentum persisted {count} of {total} windows")
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
        "benchmark": ("benchmark", benchmark_outperformance),
        "sector": ("sector", sector_leadership),
        "industry": ("industry", industry_leadership),
        "persistence": ("persistence", relative_momentum_persistence),
    }


def build_default_signal_registry() -> SignalRegistry:
    """Create a registry pre-populated with the standard RS signals."""
    registry = SignalRegistry()
    for name, (_, signal) in _default_signal_config().items():
        registry.register(name, signal)
    return registry
