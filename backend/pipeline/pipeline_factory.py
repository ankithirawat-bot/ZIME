"""Pipeline factory for dependency injection.

Constructs a fully configured MarketPipeline using dependency injection.
The factory performs assembly only; dependency creation is handled by
:mod:`backend.bootstrap.pipeline_bootstrap`.
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
        config: PipelineConfig,
        normalizer: DataNormalizer,
        validator: DataValidator,
        anomaly_detector: AnomalyDetectorEngine,
        adjustment_engine: AdjustmentEngine,
        logger: logging.Logger,
    ) -> MarketPipeline:
        """Create a fully configured MarketPipeline.

        All dependencies must be provided; no fallback defaults are created.
        Use :func:`backend.bootstrap.create_default_pipeline` for a
        convenience helper that supplies defaults.

        Args:
            registry:          Provider registry for data fetching.
            conn_manager:      Database connection manager.
            config:            Pipeline configuration.
            normalizer:        Data normalizer.
            validator:         Data quality validator.
            anomaly_detector:  Anomaly detection engine.
            adjustment_engine: Corporate action adjustment engine.
            logger:            Logger instance.

        Returns:
            Configured MarketPipeline instance.
        """
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
