"""Strategy engine.

Core evaluation engine for generating investment signals.
"""

from __future__ import annotations

from typing import Any

from backend.strategy.models import (
    MatchedRule,
    StrategyDefinition,
    StrategySignal,
)
from backend.strategy.registry import RuleRegistry
from backend.strategy.rules import evaluate_rule
from backend.strategy.signals import SIGNAL_SCORES, SignalType, signal_confidence, signal_from_score


class StrategyEngine:
    """Core strategy evaluation engine.

    Evaluates symbols against strategy rules and generates signals.
    """

    def __init__(self, rule_registry: RuleRegistry | None = None) -> None:
        """Initialize the engine.

        Args:
            rule_registry: Registry of available rules.
        """
        self._rule_registry = rule_registry or RuleRegistry()

    @property
    def rule_registry(self) -> RuleRegistry:
        """Access the rule registry."""
        return self._rule_registry

    def evaluate(
        self,
        definition: StrategyDefinition,
        symbol: str,
        data: dict[str, Any],
    ) -> StrategySignal:
        """Evaluate a single symbol against a strategy.

        Args:
            definition: Strategy definition.
            symbol:     Ticker symbol.
            data:       Symbol data dictionary.

        Returns:
            StrategySignal with the evaluation result.
        """
        return self._evaluate_symbol(definition, symbol, data)

    def evaluate_many(
        self,
        definition: StrategyDefinition,
        symbols_data: dict[str, dict[str, Any]],
    ) -> tuple[StrategySignal, ...]:
        """Evaluate multiple symbols against a strategy.

        Args:
            definition:   Strategy definition.
            symbols_data: Dictionary mapping symbols to their data.

        Returns:
            Tuple of StrategySignal for each symbol.
        """
        return tuple(
            self._evaluate_symbol(definition, symbol, data)
            for symbol, data in symbols_data.items()
        )

    def evaluate_screen(
        self,
        definition: StrategyDefinition,
        screen_result: Any,
    ) -> tuple[StrategySignal, ...]:
        """Evaluate symbols from a screen result.

        Args:
            definition:   Strategy definition.
            screen_result: ScreenResult with symbol data.

        Returns:
            Tuple of StrategySignal for each symbol.
        """
        symbols_data: dict[str, dict[str, Any]] = {}
        if hasattr(screen_result, "passed"):
            for symbol in screen_result.passed:
                symbols_data[symbol] = {"screen": {"passed": True}}
        if hasattr(screen_result, "failed"):
            for symbol in screen_result.failed:
                symbols_data[symbol] = {"screen": {"passed": False}}

        return self.evaluate_many(definition, symbols_data)

    def evaluate_rankings(
        self,
        definition: StrategyDefinition,
        ranking_result: Any,
    ) -> tuple[StrategySignal, ...]:
        """Evaluate symbols from a ranking result.

        Args:
            definition:     Strategy definition.
            ranking_result: RankingResult with ranked entries.

        Returns:
            Tuple of StrategySignal for each symbol.
        """
        symbols_data: dict[str, dict[str, Any]] = {}
        if hasattr(ranking_result, "entries"):
            for entry in ranking_result.entries:
                symbols_data[entry.symbol] = {
                    "ranking": {
                        "total_score": entry.total_score,
                        "rank": entry.rank,
                    }
                }

        return self.evaluate_many(definition, symbols_data)

    def evaluate_and_rank(
        self,
        definition: StrategyDefinition,
        symbols_data: dict[str, dict[str, Any]],
    ) -> tuple[StrategySignal, ...]:
        """Evaluate and return symbols sorted by signal strength.

        Args:
            definition:   Strategy definition.
            symbols_data: Dictionary mapping symbols to their data.

        Returns:
            Tuple of StrategySignal sorted by confidence (descending).
        """
        signals = self.evaluate_many(definition, symbols_data)
        return tuple(sorted(signals, key=lambda s: s.confidence, reverse=True))

    def _evaluate_symbol(
        self,
        definition: StrategyDefinition,
        symbol: str,
        data: dict[str, Any],
    ) -> StrategySignal:
        """Evaluate a single symbol.

        Args:
            definition: Strategy definition.
            symbol:     Ticker symbol.
            data:       Symbol data.

        Returns:
            StrategySignal with evaluation result.
        """
        matched_rules: list[MatchedRule] = []
        failed_rules: list[MatchedRule] = []

        for rule in definition.rules:
            result = evaluate_rule(rule, data)
            if result.matched:
                matched_rules.append(result)
            else:
                failed_rules.append(result)

        signal, confidence = self._compute_signal(
            matched_rules, failed_rules, definition
        )

        return StrategySignal(
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            matched_rules=tuple(matched_rules),
            failed_rules=tuple(failed_rules),
            total_rules=len(definition.rules),
        )

    def _compute_signal(
        self,
        matched: list[MatchedRule],
        failed: list[MatchedRule],
        definition: StrategyDefinition,
    ) -> tuple[SignalType, float]:
        """Compute the final signal and confidence.

        Args:
            matched:    Matched rules.
            failed:     Failed rules.
            definition: Strategy definition.

        Returns:
            Tuple of (SignalType, confidence).
        """
        total = len(definition.rules)
        if total == 0:
            return SignalType.HOLD, 0.0

        weighted_score = 0.0
        total_weight = 0.0

        for rule in definition.rules:
            rule_weight = rule.weight
            total_weight += rule_weight

            for m in matched:
                if m.rule_name == rule.name:
                    weighted_score += SIGNAL_SCORES.get(rule.signal, 0.5) * rule_weight
                    break

        if total_weight > 0:
            avg_score = weighted_score / total_weight
        else:
            avg_score = 0.5

        signal = signal_from_score(avg_score)
        confidence = signal_confidence(len(matched), total, signal)

        return signal, confidence
