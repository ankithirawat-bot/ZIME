"""
Evaluation Pipeline.

Executes engines in fixed order. No strategy-specific logic.
Returns an immutable EvaluationContext.
"""

from __future__ import annotations

from backend.composite.composite_engine import CompositeEngine
from backend.patterns.engine import PatternEngine
from backend.regime.regime_engine import analyze_regime
from backend.relative_strength.rs_engine import analyze_relative_strength
from backend.risk.risk_engine import RiskEngine
from backend.strategy.models import EvaluationContext, StrategyInput
from backend.trade.trade_engine import TradeEngine
from backend.trend.trend_engine import TrendQualityEngine
from backend.volume.volume_engine import VolumeEngine


class EvaluationPipeline:
    """Executes engines in fixed order and returns EvaluationContext.

    Order:
        1. Market Regime
        2. Relative Strength
        3. Trend
        4. Pattern
        5. Volume
        6. Composite
        7. Trade
        8. Risk
    """

    def __init__(self) -> None:
        self._trend_engine = TrendQualityEngine()
        self._pattern_engine = PatternEngine()
        self._volume_engine = VolumeEngine()
        self._composite_engine = CompositeEngine()
        self._trade_engine = TradeEngine()
        self._risk_engine = RiskEngine()

    def run(self, strategy_input: StrategyInput) -> EvaluationContext:
        """Execute all engines and return immutable context.

        Args:
            strategy_input: Full strategy input with snapshots.

        Returns:
            Immutable EvaluationContext with all engine outputs.
        """
        market_result = analyze_regime(strategy_input.market_snapshot)
        rs_result = analyze_relative_strength(strategy_input.relative_strength_snapshot)
        trend_result = self._trend_engine.evaluate(strategy_input.trend_snapshot)
        pattern_result = self._pattern_engine.evaluate(strategy_input.pattern_snapshot)
        volume_result = self._volume_engine.evaluate(strategy_input.volume_snapshot)

        composite_result = self._composite_engine.evaluate(
            market_regime=market_result,
            relative_strength=rs_result,
            trend=trend_result,
            pattern=pattern_result,
            volume=volume_result,
        )

        trade_result = self._trade_engine.evaluate(
            composite=composite_result,
            pattern=pattern_result,
        )

        risk_result = self._risk_engine.evaluate(
            trade_plan=trade_result,
            composite=composite_result,
        )

        return EvaluationContext(
            market_result=market_result,
            relative_strength_result=rs_result,
            trend_result=trend_result,
            pattern_result=pattern_result,
            volume_result=volume_result,
            composite_result=composite_result,
            trade_result=trade_result,
            risk_result=risk_result,
        )
