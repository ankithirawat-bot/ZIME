"""Screener engine.

Core evaluation engine for screening symbols against filter definitions.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from backend.screener.exceptions import EvaluationError
from backend.screener.models import (
    EvaluationContext,
    FilterCondition,
    FilterGroup,
    FilterStatistics,
    ScreenDefinition,
    ScreenResult,
)
from backend.screener.operators import OperatorRegistry, evaluate_comparison, evaluate_logical
from backend.screener.registry import FilterRegistry


class ScreenerEngine:
    """Core screening engine.

    Evaluates symbols against screen definitions using composable filters
    and logical operators.
    """

    def __init__(
        self,
        filter_registry: FilterRegistry | None = None,
        operator_registry: OperatorRegistry | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            filter_registry:   Registry of available filters.
            operator_registry: Registry of available operators.
        """
        self._filter_registry = filter_registry or FilterRegistry()
        self._operator_registry = operator_registry or OperatorRegistry()

    @property
    def filter_registry(self) -> FilterRegistry:
        """Access the filter registry."""
        return self._filter_registry

    @property
    def operator_registry(self) -> OperatorRegistry:
        """Access the operator registry."""
        return self._operator_registry

    def evaluate(
        self,
        screen: ScreenDefinition,
        context: EvaluationContext,
    ) -> bool:
        """Evaluate a single symbol against a screen definition.

        Args:
            screen:  Screen definition.
            context: Evaluation context with symbol data.

        Returns:
            True if the symbol passes all filters.

        Raises:
            EvaluationError: If evaluation fails.
        """
        try:
            return self._evaluate_group(screen.filters, context)
        except Exception as e:
            if isinstance(e, EvaluationError):
                raise
            raise EvaluationError(context.symbol, str(e))

    def evaluate_many(
        self,
        screen: ScreenDefinition,
        contexts: Sequence[EvaluationContext],
    ) -> ScreenResult:
        """Evaluate multiple symbols against a screen definition.

        Args:
            screen:   Screen definition.
            contexts: Evaluation contexts for each symbol.

        Returns:
            ScreenResult with passed/failed symbols and statistics.
        """
        start = time.monotonic()
        passed: list[str] = []
        failed: list[str] = []

        for ctx in contexts:
            result = self._evaluate_with_stats(screen, ctx)
            if result:
                passed.append(ctx.symbol)
            else:
                failed.append(ctx.symbol)

        elapsed = time.monotonic() - start

        filter_stats = self._compute_filter_stats(screen, contexts)

        return ScreenResult(
            screen_name=screen.metadata.name,
            passed=tuple(passed),
            failed=tuple(failed),
            elapsed_seconds=elapsed,
            filter_stats=filter_stats,
            total_evaluated=len(contexts),
        )

    def evaluate_universe(
        self,
        screen: ScreenDefinition,
        universe_provider: Callable[[], Sequence[EvaluationContext]],
    ) -> ScreenResult:
        """Evaluate all symbols from a universe provider.

        Args:
            screen:            Screen definition.
            universe_provider: Callable returning all symbol contexts.

        Returns:
            ScreenResult with passed/failed symbols.
        """
        contexts = universe_provider()
        return self.evaluate_many(screen, contexts)

    def _evaluate_group(
        self,
        group: FilterGroup,
        context: EvaluationContext,
    ) -> bool:
        """Evaluate a filter group recursively.

        Args:
            group:   Filter group to evaluate.
            context: Evaluation context.

        Returns:
            True if the group conditions are satisfied.
        """
        results: list[bool] = []

        for condition in group.conditions:
            result = self._evaluate_condition(condition, context)
            results.append(result)

        for subgroup in group.groups:
            result = self._evaluate_group(subgroup, context)
            results.append(result)

        return evaluate_logical(tuple(results), group.operator)

    def _evaluate_condition(
        self,
        condition: FilterCondition,
        context: EvaluationContext,
    ) -> bool:
        """Evaluate a single filter condition.

        Args:
            condition: Filter condition to evaluate.
            context:   Evaluation context.

        Returns:
            True if the condition is satisfied.
        """
        filter_func = self._filter_registry.get(condition.name)
        actual_value = filter_func(context)

        result = evaluate_comparison(
            actual_value,
            condition.operator,
            condition.value,
            self._operator_registry,
        )

        if condition.negate:
            result = not result

        return result

    def _evaluate_with_stats(
        self,
        screen: ScreenDefinition,
        context: EvaluationContext,
    ) -> bool:
        """Evaluate a symbol and track per-filter statistics.

        Args:
            screen:  Screen definition.
            context: Evaluation context.

        Returns:
            True if the symbol passes all filters.
        """
        return self._evaluate_group(screen.filters, context)

    def _compute_filter_stats(
        self,
        screen: ScreenDefinition,
        contexts: Sequence[EvaluationContext],
    ) -> tuple[FilterStatistics, ...]:
        """Compute per-filter statistics.

        Args:
            screen:   Screen definition.
            contexts: All evaluation contexts.

        Returns:
            Tuple of FilterStatistics for each filter.
        """
        stats: dict[str, dict[str, int]] = {}
        self._collect_filter_names(screen.filters, stats)

        for ctx in contexts:
            self._evaluate_and_count(screen.filters, ctx, stats)

        return tuple(
            FilterStatistics(
                filter_name=name,
                passed_count=counts.get("passed", 0),
                failed_count=counts.get("failed", 0),
            )
            for name, counts in stats.items()
        )

    def _collect_filter_names(
        self,
        group: FilterGroup,
        stats: dict[str, dict[str, int]],
    ) -> None:
        """Collect all filter names from a group."""
        for condition in group.conditions:
            if condition.name not in stats:
                stats[condition.name] = {"passed": 0, "failed": 0}
        for subgroup in group.groups:
            self._collect_filter_names(subgroup, stats)

    def _evaluate_and_count(
        self,
        group: FilterGroup,
        context: EvaluationContext,
        stats: dict[str, dict[str, int]],
    ) -> None:
        """Evaluate and count per-filter pass/fail."""
        for condition in group.conditions:
            try:
                result = self._evaluate_condition(condition, context)
                key = "passed" if result else "failed"
                stats[condition.name][key] += 1
            except Exception:
                stats[condition.name]["failed"] += 1

        for subgroup in group.groups:
            self._evaluate_and_count(subgroup, context, stats)
