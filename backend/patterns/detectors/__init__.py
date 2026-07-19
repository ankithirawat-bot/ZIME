"""Pattern detectors package."""

from backend.patterns.detectors.vcp import VCPDetector
from backend.patterns.detectors.flat_base import FlatBaseDetector
from backend.patterns.detectors.ascending_triangle import AscendingTriangleDetector
from backend.patterns.detectors.cup_handle import CupHandleDetector
from backend.patterns.detectors.high_tight_flag import HighTightFlagDetector

__all__ = [
    "VCPDetector",
    "FlatBaseDetector",
    "AscendingTriangleDetector",
    "CupHandleDetector",
    "HighTightFlagDetector",
]
