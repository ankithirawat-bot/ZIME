"""
Pattern Detector Base Class.

Abstract base for all pattern detectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.patterns.models import PatternResult, PatternSnapshot, PatternType


class PatternDetector(ABC):
    """Abstract base class for pattern detectors.

    Every detector must implement detect() and declare its pattern_type.
    """

    pattern_type: PatternType

    @abstractmethod
    def detect(self, snapshot: PatternSnapshot) -> PatternResult:
        """Detect and score a pattern from snapshot data.

        Args:
            snapshot: Market data for pattern evaluation.

        Returns:
            PatternResult with score, confidence, and explanations.
        """
