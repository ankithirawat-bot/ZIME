"""Pipeline factory for dependency injection.

Constructs a fully configured MarketPipeline using dependency injection.
"""

from __future__ import annotations

import logging

from backend.corporate_actions.adjustment_engine import AdjustmentEngine
from backend.data.data_engine import DataEngine
from backend.data.normalizer import DataNormalizer
from backend.data.provider_registry import ProviderRegistry
from backend.data_quality.anomaly_detector import AnomalyDetectorEngine
from backend.data_quality.validator import DataValidator
from backend.pipeline.market_pipeline import MarketPipeline
from backend.pipeline.models import PipelineConfig
from backend.pipeline.pipeline_context import PipelineContext
from backend.storage.postgresql.connection import ConnectionManager
from backend.storage.postgresql.postgres_repository import PostgreSQLRepository


class PipelineFactory:
    """Factory for constructing fully configured MarketPipeline instances.

    Uses dependency injection to construct all required components.
    No global state is maintained.
    """

    @staticmethod
    def create(
        registry: ProviderRegistry,
        conn_manager: ConnectionManager,
        config: PipelineConfig | None = None,
        normalizer: DataNormalizer | None = None,
        validator: DataValidator | None = None,
        anomaly_detector: AnomalyDetectorEngine | None = None,
        adjustment_engine: AdjustmentEngine | None = None,
        logger: logging.Logger | None = None,
    ) -> MarketPipeline:
        """Create a fully configured MarketPipeline.

        Args:
            registry:        Provider registry for data fetching.
            conn_manager:    Database connection manager.
            config:          Pipeline configuration (defaults created).
            normalizer:      Data normalizer (defaults created).
            validator:       Data quality validator (defaults created).
            anomaly_detector: Anomaly detection engine (defaults created).
            adjustment_engine: Corporate action adjustment engine (defaults created).
            logger:          Logger instance (defaults created).

        Returns:
            Configured MarketPipeline instance.
        """
        config = config or PipelineConfig()
        normalizer = normalizer or DataNormalizer()
        validator = validator or DataValidator()
        anomaly_detector = anomaly_detector or AnomalyDetectorEngine()
        adjustment_engine = adjustment_engine or AdjustmentEngine()
        logger = logger or logging.getLogger("pipeline")

        data_engine = DataEngine(registry=registry, normalizer=normalizer)
        repository = PostgreSQLRepository(conn_manager)

        context = PipelineContext(
            data_engine=data_engine,
            repository=repository,
            validator=validator,
            anomaly_detector=anomaly_detector,
            adjustment_engine=adjustment_engine,
            config=config,
            logger=logger,
        )

        return MarketPipeline(context)

    @staticmethod
    def create_with_context(context: PipelineContext) -> MarketPipeline:
        """Create a MarketPipeline from an existing context.

        Args:
            context: Pre-configured pipeline context.

        Returns:
            MarketPipeline using the provided context.
        """
        return MarketPipeline(context)
