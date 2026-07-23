from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Recommendation:
    symbol: str
    recommendation: str
    confidence: float
    score: float
    trend: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "score": self.score,
            "trend": self.trend,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class Signal:
    symbol: str
    signal_type: str
    trend: str
    strength: float
    confidence: float
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "trend": self.trend,
            "strength": self.strength,
            "confidence": self.confidence,
            "score": self.score,
        }


@dataclass(frozen=True)
class Insight:
    title: str
    description: str
    category: str
    timestamp: str
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "timestamp": self.timestamp,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class MarketHealth:
    trend: str
    trend_score: float
    breadth: str
    breadth_score: float
    momentum: str
    momentum_score: float
    volatility: str
    volatility_score: float
    liquidity: str
    liquidity_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "trend": self.trend,
            "trend_score": self.trend_score,
            "breadth": self.breadth,
            "breadth_score": self.breadth_score,
            "momentum": self.momentum,
            "momentum_score": self.momentum_score,
            "volatility": self.volatility,
            "volatility_score": self.volatility_score,
            "liquidity": self.liquidity,
            "liquidity_score": self.liquidity_score,
        }


@dataclass(frozen=True)
class IntelligenceSummary:
    market_regime: str
    risk_level: str
    overall_score: float
    last_refresh: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "market_regime": self.market_regime,
            "risk_level": self.risk_level,
            "overall_score": self.overall_score,
            "last_refresh": self.last_refresh,
        }


@dataclass(frozen=True)
class IntelligenceViewModel:
    screen_name: str
    screen_description: str
    summary: IntelligenceSummary
    recommendations: tuple[Recommendation, ...]
    signals: tuple[Signal, ...]
    market_health: MarketHealth
    insights: tuple[Insight, ...]
    controller_status: str
    event_bus_status: str
    worker_status: str
    connection_status: str
    last_refresh: str
    recommendation_count: int
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "screen_name": self.screen_name,
            "screen_description": self.screen_description,
            "summary": self.summary.to_dict(),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "signals": [s.to_dict() for s in self.signals],
            "market_health": self.market_health.to_dict(),
            "insights": [i.to_dict() for i in self.insights],
            "controller_status": self.controller_status,
            "event_bus_status": self.event_bus_status,
            "worker_status": self.worker_status,
            "connection_status": self.connection_status,
            "last_refresh": self.last_refresh,
            "recommendation_count": self.recommendation_count,
            "generated_at": self.generated_at.isoformat(timespec="seconds"),
        }
