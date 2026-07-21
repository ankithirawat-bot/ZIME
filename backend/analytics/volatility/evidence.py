"""Evidence model for volatility analysis.

An :class:`Evidence` item records one explainable observation together with
its source signal and an optional weight. Evidence is the only narrative the
volatility engine exposes; raw indicator values are never surfaced.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    """Immutable single piece of explainable evidence.

    Attributes:
        source:  Originating signal/component name.
        text:    Human-readable observation.
        weight:  Optional relative strength of the observation.
    """

    source: str
    text: str
    weight: float = 0.0


def evidence_texts(items: Iterable[Evidence]) -> tuple[str, ...]:
    """Return the text of each evidence item, in order."""
    return tuple(item.text for item in items)
