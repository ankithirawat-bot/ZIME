"""
Pattern Recognition Engine.

Orchestrates multiple pattern detectors, compares scores,
and returns the best candidate.
"""

from __future__ import annotations

from backend.patterns.base import PatternDetector
from backend.patterns.models import PatternResult, PatternSnapshot, PatternType
from backend.patterns.detectors import (
    AscendingTriangleDetector,
    CupHandleDetector,
    FlatBaseDetector,
    HighTightFlagDetector,
    VCPDetector,
)


class PatternEngine:
    """Pattern Recognition Engine.

    Registers all detectors, executes them, and selects
    the highest-scoring pattern.
    """

    def __init__(self, detectors: list[PatternDetector] | None = None) -> None:
        """Initialize engine with detectors.

        Args:
            detectors: Optional custom detector list. Uses defaults if None.
        """
        self._detectors = detectors or [
            VCPDetector(),
            FlatBaseDetector(),
            AscendingTriangleDetector(),
            CupHandleDetector(),
            HighTightFlagDetector(),
        ]

    def evaluate(self, snapshot: PatternSnapshot) -> PatternResult:
        """Evaluate all patterns and return the best candidate.

        Args:
            snapshot: Market data for pattern evaluation.

        Returns:
            Highest-scoring PatternResult, or UNKNOWN if none detected.
        """
        results: list[PatternResult] = []

        for detector in self._detectors:
            try:
                result = detector.detect(snapshot)
                if result.score > 0:
                    results.append(result)
            except Exception:
                continue

        if not results:
            return PatternResult(
                pattern_name=PatternType.UNKNOWN,
                score=0,
                confidence=0,
                reasons=["No patterns detected"],
                warnings=["Unable to identify any pattern"],
            )

        best = max(results, key=lambda r: r.score)
        return best
