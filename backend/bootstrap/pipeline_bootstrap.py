"""
Pipeline bootstrap — dependency composition.

Responsible for creating default dependencies and configuring
production / testing / development wiring.  The :class:`PipelineFactory`
itself performs assembly only; it never creates defaults.
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
from backend.pipeline.pipeline_factory import PipelineFactory
from backend.storage.postgresql.connection import ConnectionManager
from backend.storage.postgresql.postgres_repository import PostgreSQLRepository


def _build_context(
    registry: ProviderRegistry,
    conn_manager: ConnectionManager,
    config: PipelineConfig,
    logger: logging.Logger,
) -> PipelineContext:
    """Shared wiring logic — creates all dependencies and assembles context."""
    normalizer = DataNormalizer()
    validator = DataValidator()
    anomaly_detector = AnomalyDetectorEngine()
    adjustment_engine = AdjustmentEngine()
    data_engine = DataEngine(registry=registry, normalizer=normalizer)
    repository = PostgreSQLRepository(conn_manager)

    return PipelineContext(
        data_engine=data_engine,
        repository=repository,
        validator=validator,
        anomaly_detector=anomaly_detector,
        adjustment_engine=adjustment_engine,
        config=config,
        logger=logger,
    )


def create_production_wiring(
    registry: ProviderRegistry,
    conn_manager: ConnectionManager,
    config: PipelineConfig | None = None,
    logger: logging.Logger | None = None,
) -> PipelineContext:
    """Create a production-ready wiring context.

    Args:
        registry:     Provider registry for data fetching.
        conn_manager: Database connection manager.
        config:       Optional pipeline config (defaults created).
        logger:       Optional logger (defaults created).

    Returns:
        Fully populated PipelineContext.
    """
    return _build_context(
        registry=registry,
        conn_manager=conn_manager,
        config=config if config is not None else PipelineConfig(),
        logger=logger if logger is not None else logging.getLogger("pipeline"),
    )


def create_testing_wiring(
    registry: ProviderRegistry,
    conn_manager: ConnectionManager,
    config: PipelineConfig | None = None,
    logger: logging.Logger | None = None,
) -> PipelineContext:
    """Create a testing wiring context.

    Currently identical to production wiring.  Tests that need custom
    wiring can construct :class:`PipelineContext` directly.

    Args:
        registry:     Provider registry (mock/stub in tests).
        conn_manager: Connection manager (mock/stub in tests).
        config:       Optional pipeline config.
        logger:       Optional logger.

    Returns:
        PipelineContext.
    """
    return _build_context(
        registry=registry,
        conn_manager=conn_manager,
        config=config if config is not None else PipelineConfig(),
        logger=logger if logger is not None else logging.getLogger("pipeline"),
    )


def create_development_wiring(
    registry: ProviderRegistry,
    conn_manager: ConnectionManager,
    config: PipelineConfig | None = None,
    logger: logging.Logger | None = None,
) -> PipelineContext:
    """Create a development wiring context.

    Args:
        registry:     Provider registry.
        conn_manager: Database connection manager.
        config:       Optional pipeline config.
        logger:       Optional logger.

    Returns:
        PipelineContext.
    """
    return _build_context(
        registry=registry,
        conn_manager=conn_manager,
        config=config if config is not None else PipelineConfig(),
        logger=logger if logger is not None else logging.getLogger("pipeline"),
    )


def create_default_pipeline(
    registry: ProviderRegistry,
    conn_manager: ConnectionManager,
    config: PipelineConfig | None = None,
    logger: logging.Logger | None = None,
) -> MarketPipeline:
    """Create a fully configured MarketPipeline with default dependencies.

    This is the recommended public API for constructing a pipeline.
    Internally delegates to the production wiring and the factory.

    Args:
        registry:     Provider registry for data fetching.
        conn_manager: Database connection manager.
        config:       Optional pipeline config.
        logger:       Optional logger.

    Returns:
        Configured MarketPipeline instance.
    """
    context = create_production_wiring(registry, conn_manager, config, logger)
    return PipelineFactory.create_with_context(context)
