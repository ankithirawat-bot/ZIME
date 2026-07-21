"""Pipeline context for dependency injection.

Holds all injected dependencies without global state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from backend.pipeline.models import PipelineConfig

if TYPE_CHECKING:
    from backend.corporate_actions.adjustment_engine import AdjustmentEngine
    from backend.data.data_engine import DataEngine
    from backend.data_quality.anomaly_detector import AnomalyDetectorEngine
    from backend.data_quality.validator import DataValidator
    from backend.storage.repository import Repository


@dataclass
class PipelineContext:
    """Dependency injection container for the pipeline.

    Holds all required dependencies without global state.
    Each dependency is injected at construction time.

    Attributes:
        data_engine:         Data engine for fetching market data.
        repository:          Storage repository for persistence.
        validator:           Data quality validator.
        anomaly_detector:    Anomaly detection engine.
        adjustment_engine:   Corporate action adjustment engine.
        config:              Pipeline configuration.
        logger:              Logger instance.
    """

    data_engine: DataEngine
    repository: Repository
    validator: DataValidator
    anomaly_detector: AnomalyDetectorEngine
    adjustment_engine: AdjustmentEngine
    config: PipelineConfig = field(default_factory=PipelineConfig)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("pipeline"))

    def __post_init__(self) -> None:
        """Validate that all required dependencies are provided."""
        if self.data_engine is None:
            raise ValueError("data_engine is required")
        if self.repository is None:
            raise ValueError("repository is required")
        if self.validator is None:
            raise ValueError("validator is required")
        if self.anomaly_detector is None:
            raise ValueError("anomaly_detector is required")
        if self.adjustment_engine is None:
            raise ValueError("adjustment_engine is required")
