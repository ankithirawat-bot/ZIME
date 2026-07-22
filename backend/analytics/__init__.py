"""Analytics platform shared models, base engine, pipeline, and the trend/momentum/volume/RS/volatility engines."""

from backend.analytics.base_engine import AnalyticsEngineBase
from backend.analytics.models import (
    AnalyticsContext,
    AnalyticsFact,
    CorporateAction,
    MarketBar,
    TrendConfig,
)
from backend.analytics.momentum.exceptions import (
    InsufficientDataError,
    MomentumError,
    SignalError,
)
from backend.analytics.momentum.models import MomentumConfig, MomentumState
from backend.analytics.momentum.momentum_engine import MomentumEngine
from backend.analytics.pipeline import AnalyticsPipeline, PipelineResult
from backend.analytics.registry import AnalyticsRegistry
from backend.analytics.relative_strength.exceptions import RelativeStrengthError
from backend.analytics.relative_strength.models import (
    RelativeStrengthConfig,
    RelativeStrengthState,
)
from backend.analytics.relative_strength.relative_strength_engine import (
    RelativeStrengthEngine,
)
from backend.analytics.trend.exceptions import TrendError
from backend.analytics.trend.trend_engine import TrendEngine
from backend.analytics.volatility.exceptions import VolatilityError
from backend.analytics.volatility.models import VolatilityConfig, VolatilityState
from backend.analytics.volatility.volatility_engine import VolatilityEngine
from backend.analytics.volume.exceptions import VolumeError
from backend.analytics.volume.models import VolumeConfig, VolumeState
from backend.analytics.volume.volume_engine import VolumeEngine

__all__ = [
    "AnalyticsContext",
    "AnalyticsEngineBase",
    "AnalyticsFact",
    "AnalyticsPipeline",
    "AnalyticsRegistry",
    "CorporateAction",
    "InsufficientDataError",
    "MarketBar",
    "MomentumConfig",
    "MomentumEngine",
    "MomentumError",
    "MomentumState",
    "PipelineResult",
    "RelativeStrengthConfig",
    "RelativeStrengthEngine",
    "RelativeStrengthError",
    "RelativeStrengthState",
    "SignalError",
    "TrendConfig",
    "TrendEngine",
    "TrendError",
    "VolatilityConfig",
    "VolatilityEngine",
    "VolatilityError",
    "VolatilityState",
    "VolumeConfig",
    "VolumeEngine",
    "VolumeError",
    "VolumeState",
]
