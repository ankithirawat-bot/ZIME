"""Strategy signal types and scoring."""

from __future__ import annotations

from enum import StrEnum


class SignalType(StrEnum):
    """Investment signal types."""

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    WATCH = "WATCH"
    IGNORE = "IGNORE"


SIGNAL_SCORES: dict[SignalType, float] = {
    SignalType.STRONG_BUY: 1.0,
    SignalType.BUY: 0.75,
    SignalType.HOLD: 0.5,
    SignalType.REDUCE: 0.25,
    SignalType.SELL: 0.0,
    SignalType.STRONG_SELL: -0.25,
    SignalType.WATCH: 0.5,
    SignalType.IGNORE: 0.5,
}


def signal_from_score(score: float) -> SignalType:
    """Convert a numeric score to a signal type.

    Args:
        score: Score between -0.25 and 1.0.

    Returns:
        Corresponding signal type.
    """
    if score >= 0.9:
        return SignalType.STRONG_BUY
    if score >= 0.65:
        return SignalType.BUY
    if score >= 0.45:
        return SignalType.HOLD
    if score >= 0.2:
        return SignalType.REDUCE
    if score >= -0.1:
        return SignalType.SELL
    return SignalType.STRONG_SELL


def signal_confidence(
    matched: int,
    total: int,
    signal: SignalType,
) -> float:
    """Calculate confidence for a signal.

    Args:
        matched: Number of matched rules.
        total:   Total number of rules.
        signal:  The signal type.

    Returns:
        Confidence score between 0 and 100.
    """
    if total == 0:
        return 0.0

    base = (matched / total) * 100

    if signal in (SignalType.WATCH, SignalType.IGNORE):
        return min(base, 50.0)

    return min(base, 100.0)
