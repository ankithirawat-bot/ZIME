"""
Analytics shared models.

Common inputs and outputs for the analytics platform. An :class:`AnalyticsContext`
carries normalized market data, corporate actions and configuration; an
:class:`AnalyticsFact` is the explainable, indicator-free result emitted by
analytics engines (such as the trend engine).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class MarketBar:
    """Immutable normalized OHLCV bar.

    Attributes:
        trade_date:      Session date.
        open:            Open price.
        high:            High price.
        low:             Low price.
        close:           Close price.
        volume:          Traded volume.
        adjusted_close:  Split/dividend adjusted close, if available.
    """

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None = None


@dataclass(frozen=True)
class CorporateAction:
    """Immutable corporate action reference.

    Attributes:
        date:        Ex-date of the action.
        action_type: Type label (e.g. "SPLIT", "BONUS", "DIVIDEND").
        ratio:       Effective ratio (e.g. 2.0 for a 2:1 split).
    """

    date: date
    action_type: str
    ratio: float


@dataclass(frozen=True)
class TrendConfig:
    """Immutable configuration for trend analysis.

    Attributes:
        ema_short_period:    Short EMA period (e.g. 20).
        ema_mid_period:      Medium EMA period (e.g. 50).
        sma_long_period:     Long SMA period (e.g. 200).
        slope_window:        Bars used for slope estimation.
        structure_window:    Bars used for high/low structure analysis.
        persistence_threshold: Run length for full persistence credit.
        weight_ma:           Weight of the MA-alignment signal.
        weight_structure:    Weight of the structure signal.
        weight_slope:        Weight of the slope signal.
        weight_persistence:  Weight of the persistence signal.
        conflict_threshold:  Agreement below this flags conflicting signals.
    """

    ema_short_period: int = 20
    ema_mid_period: int = 50
    sma_long_period: int = 200
    slope_window: int = 50
    structure_window: int = 50
    persistence_threshold: int = 60
    weight_ma: float = 0.35
    weight_structure: float = 0.25
    weight_slope: float = 0.25
    weight_persistence: float = 0.15
    conflict_threshold: float = 0.5


@dataclass(frozen=True)
class AnalyticsContext:
    """Immutable input to an analytics engine.

    Attributes:
        symbol:           Instrument symbol.
        exchange:         Exchange identifier.
        prices:           Tuple of normalized market bars.
        corporate_actions: Corporate actions relevant to the window.
        config:           Engine configuration.
    """

    symbol: str
    exchange: str
    prices: tuple[MarketBar, ...]
    corporate_actions: tuple[CorporateAction, ...] = ()
    config: TrendConfig = field(default_factory=TrendConfig)


@dataclass(frozen=True)
class AnalyticsFact:
    """Immutable explainable analytics result.

    Attributes:
        name:      Fact name (e.g. "Trend").
        state:     Categorical state (engine-specific value string).
        confidence: Confidence score in [0, 100].
        evidence:  Human-readable evidence strings.
        metadata:  Auxiliary structured data (no raw indicator values).
    """

    name: str
    state: str
    confidence: float
    evidence: tuple[str, ...]
    metadata: dict[str, Any]
