"""
Recommendation models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RecommendationResult:
    """Immutable result from the Recommendation Engine.

    Attributes:
        recommendation:  Final recommended action (e.g. "Strong Buy", "Avoid").
        confidence:      Aggregated confidence score in [0, 100].
        facts:           All AnalyticsFacts produced by the pipeline.
        metadata:        Auxiliary structured data.
    """

    recommendation: str
    confidence: float
    facts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
