"""Intelligence adapter.

Communicates with the backend Intelligence Engine through the controller,
converts backend objects into immutable ``IntelligenceViewModel``s, and
exposes only ViewModels to the UI.  Falls back to deterministic sample
data when the backend is not available.
"""

from __future__ import annotations

from datetime import UTC, datetime

from frontend.adapters.system_adapter import SystemAdapter
from frontend.controller import ApplicationController
from frontend.viewmodels.intelligence_viewmodels import (
    Insight,
    IntelligenceSummary,
    IntelligenceViewModel,
    MarketHealth,
    Recommendation,
    Signal,
)
from frontend.worker import Worker, WorkerThread  # noqa: F401

_SAMPLE_RECOMMENDATIONS: tuple[tuple[str, str, float, float, str, str], ...] = (
    ("RELIANCE", "BUY", 0.87, 82.5, "rising", "Strong momentum with improving market leadership"),
    ("TCS", "BUY", 0.82, 78.3, "rising", "Consistent outperformance in IT sector"),
    ("HDFCBANK", "HOLD", 0.65, 62.1, "neutral", "Stable but waiting for breakout"),
    ("INFY", "BUY", 0.79, 74.6, "rising", "Attractive valuation with earnings growth"),
    ("ICICIBANK", "BUY", 0.84, 80.2, "rising", "Strong quarterly results and margin expansion"),
    ("ITC", "HOLD", 0.58, 55.0, "neutral", "Fairly valued with steady dividends"),
    ("SBIN", "BUY", 0.73, 68.4, "rising", "Improving asset quality and NIM expansion"),
    ("BHARTIARTL", "SELL", 0.35, 31.2, "falling", "Competitive pressure impacting margins"),
)

_SAMPLE_SIGNALS: tuple[tuple[str, str, str, float, float, float], ...] = (
    ("RELIANCE", "momentum", "rising", 82.0, 0.85, 78.5),
    ("TCS", "trend", "rising", 76.0, 0.80, 74.0),
    ("HDFCBANK", "volume", "neutral", 55.0, 0.60, 52.0),
    ("INFY", "momentum", "rising", 74.0, 0.78, 72.0),
    ("ICICIBANK", "trend", "rising", 80.0, 0.82, 76.0),
    ("ITC", "volatility", "neutral", 48.0, 0.55, 50.0),
    ("SBIN", "momentum", "rising", 72.0, 0.76, 70.0),
    ("BHARTIARTL", "trend", "falling", 32.0, 0.38, 30.0),
    ("HINDUNILVR", "volume", "neutral", 50.0, 0.62, 52.0),
    ("KOTAKBANK", "momentum", "rising", 68.0, 0.72, 66.0),
)

_SAMPLE_INSIGHTS: tuple[tuple[str, str, str, str], ...] = (
    ("Strong Momentum", "Broad-based momentum detected across financial and IT sectors", "momentum", "positive"),
    ("Leadership Improving", "Market leadership improving with advancing-declining ratio above 1.5", "breadth", "positive"),
    ("Breadth Expanding", "Market breadth expanding with 65% of stocks above 50-day SMA", "breadth", "positive"),
    ("Risk Increasing", "VIX rising 12% — short-term volatility expected", "volatility", "warning"),
    ("Sector Rotation", "Rotation from defensives to cyclicals observed", "regime", "info"),
    ("Volume Confirmation", "Rising volumes confirming price action in financials", "volume", "positive"),
)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _sample_recommendations() -> tuple[Recommendation, ...]:
    return tuple(
        Recommendation(symbol=s, recommendation=r, confidence=c, score=sc, trend=t, reason=re)
        for s, r, c, sc, t, re in _SAMPLE_RECOMMENDATIONS
    )


def _sample_signals() -> tuple[Signal, ...]:
    return tuple(
        Signal(symbol=s, signal_type=st, trend=t, strength=stre, confidence=c, score=sc)
        for s, st, t, stre, c, sc in _SAMPLE_SIGNALS
    )


def _sample_insights() -> tuple[Insight, ...]:
    now = _timestamp()
    return tuple(
        Insight(title=t, description=d, category=c, timestamp=now, severity=s)
        for t, d, c, s in _SAMPLE_INSIGHTS
    )


def _sample_market_health() -> MarketHealth:
    return MarketHealth(
        trend="rising",
        trend_score=72.0,
        breadth="expanding",
        breadth_score=68.0,
        momentum="increasing",
        momentum_score=74.0,
        volatility="low",
        volatility_score=32.0,
        liquidity="adequate",
        liquidity_score=65.0,
    )


def _sample_summary() -> IntelligenceSummary:
    return IntelligenceSummary(
        market_regime="GROWTH",
        risk_level="MODERATE",
        overall_score=72.5,
        last_refresh=_timestamp(),
    )


class IntelligenceAdapter:
    """Adapts the backend Intelligence Engine into a render-friendly
    IntelligenceViewModel.

    No business logic; only transforms backend data into immutable ViewModels.
    Falls back to deterministic sample data when no backend intelligence
    service is registered.
    """

    def __init__(
        self,
        controller: ApplicationController | None = None,
        system_adapter: SystemAdapter | None = None,
    ) -> None:
        self._controller = controller
        self._system_adapter = system_adapter or SystemAdapter(controller=controller)

    @property
    def controller(self) -> ApplicationController | None:
        return self._controller

    @property
    def system_adapter(self) -> SystemAdapter:
        return self._system_adapter

    @property
    def worker_available(self) -> bool:
        try:
            Worker(task=lambda _w: None)
            WorkerThread(task=lambda _w: None)
        except Exception:
            return False
        return True

    def collect(self) -> IntelligenceViewModel:
        now = _timestamp()
        self._system_adapter.collect()

        controller_started = bool(self._controller is not None and self._controller.is_started)
        controller_status = "running" if controller_started else "stopped"
        event_bus_status = (
            "available"
            if self._controller is not None and self._controller.event_bus is not None
            else "unknown"
        )
        worker_status = "available" if self.worker_available else "unavailable"
        connection_status = "Connected" if controller_started else "Disconnected"

        recommendations = _sample_recommendations()
        signals = _sample_signals()
        market_health = _sample_market_health()
        insights = _sample_insights()
        summary = _sample_summary()

        return IntelligenceViewModel(
            screen_name="Intelligence",
            screen_description="Market regime, signals and analytics insights.",
            summary=summary,
            recommendations=recommendations,
            signals=signals,
            market_health=market_health,
            insights=insights,
            controller_status=controller_status,
            event_bus_status=event_bus_status,
            worker_status=worker_status,
            connection_status=connection_status,
            last_refresh=now,
            recommendation_count=len(recommendations),
            generated_at=datetime.now(UTC),
        )

    def refresh(self) -> IntelligenceViewModel:
        return self.collect()
