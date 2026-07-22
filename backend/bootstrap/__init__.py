"""Application bootstrap and dependency composition."""

from backend.bootstrap.pipeline_bootstrap import (
    create_default_pipeline,
    create_development_wiring,
    create_production_wiring,
    create_testing_wiring,
)

__all__ = [
    "create_default_pipeline",
    "create_development_wiring",
    "create_production_wiring",
    "create_testing_wiring",
]
