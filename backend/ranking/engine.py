"""Ranking engine.

Core evaluation engine for ranking securities using configurable
weighted factors.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Any

from backend.ranking.exceptions import EmptyUniverseError
from backend.ranking.models import (
    FactorScore,
    RankingDefinition,
    RankingEntry,
    RankingResult,
    RankingStatistics,
)
from backend.ranking.normalization import normalize_factor_scores
from backend.ranking.registry import FactorRegistry
from backend.ranking.weights import apply_weights


class RankingEngine:
    """Core ranking engine.

    Ranks securities using configurable weighted factors.
    """

    def __init__(
        self,
        factor_registry: FactorRegistry | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            factor_registry: Registry of available factors.
        """
        self._factor_registry = factor_registry or FactorRegistry()

    @property
    def factor_registry(self) -> FactorRegistry:
        """Access the factor registry."""
        return self._factor_registry

    def rank(
        self,
        definition: RankingDefinition,
        symbols_data: dict[str, dict[str, Any]],
    ) -> RankingResult:
        """Rank symbols using the ranking definition.

        Args:
            definition:   Ranking definition with factors.
            symbols_data: Dictionary mapping symbols to their data.

        Returns:
            RankingResult with ranked entries.

        Raises:
            EmptyUniverseError: If no symbols are provided.
        """
        if not symbols_data:
            raise EmptyUniverseError()

        start = time.monotonic()

        factor_scores_by_symbol = self._compute_all_factor_scores(
            definition, symbols_data
        )

        entries = self._compute_rankings(
            definition, symbols_data, factor_scores_by_symbol
        )

        statistics = self._compute_statistics(entries, len(definition.factors), start)

        return RankingResult(
            ranking_name=definition.metadata.name,
            entries=entries,
            statistics=statistics,
        )

    def rank_screen(
        self,
        definition: RankingDefinition,
        screen_result: Any,
    ) -> RankingResult:
        """Rank symbols from a screen result.

        Args:
            definition:   Ranking definition with factors.
            screen_result: ScreenResult with symbol data.

        Returns:
            RankingResult with ranked entries.
        """
        symbols_data = {}
        if hasattr(screen_result, "passed"):
            for symbol in screen_result.passed:
                if hasattr(screen_result, "contexts"):
                    ctx = next(
                        (c for c in screen_result.contexts if c.symbol == symbol), None
                    )
                    if ctx:
                        symbols_data[symbol] = {
                            "fundamentals": ctx.fundamentals,
                            "technicals": ctx.technicals,
                            "quality": getattr(ctx, "quality_data", {}),
                        }

        return self.rank(definition, symbols_data)

    def rank_universe(
        self,
        definition: RankingDefinition,
        universe_provider: Callable[[], dict[str, dict[str, Any]]],
    ) -> RankingResult:
        """Rank all symbols from a universe provider.

        Args:
            definition:       Ranking definition with factors.
            universe_provider: Callable returning symbol data.

        Returns:
            RankingResult with ranked entries.
        """
        symbols_data = universe_provider()
        return self.rank(definition, symbols_data)

    def _compute_all_factor_scores(
        self,
        definition: RankingDefinition,
        symbols_data: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, float | None]]:
        """Compute raw factor scores for all symbols.

        Args:
            definition:   Ranking definition.
            symbols_data: Symbol data dictionary.

        Returns:
            Dictionary mapping factor names to symbol scores.
        """
        result: dict[str, dict[str, float | None]] = {}
        for factor in definition.factors:
            factor_func = self._factor_registry.get(factor.name)
            scores: dict[str, float | None] = {}
            for symbol, data in symbols_data.items():
                scores[symbol] = factor_func(data)
            result[factor.name] = scores
        return result

    def _compute_rankings(
        self,
        definition: RankingDefinition,
        symbols_data: dict[str, dict[str, Any]],
        factor_scores_by_symbol: dict[str, dict[str, float | None]],
    ) -> tuple[RankingEntry, ...]:
        """Compute final rankings.

        Args:
            definition:          Ranking definition.
            symbols_data:        Symbol data.
            factor_scores_by_symbol: Raw factor scores.

        Returns:
            Tuple of RankingEntry objects sorted by score.
        """
        entries: list[RankingEntry] = []

        for symbol in symbols_data:
            entry = self._compute_symbol_ranking(
                symbol, definition, factor_scores_by_symbol
            )
            entries.append(entry)

        entries.sort(key=lambda e: e.total_score, reverse=True)

        ranked_entries = []
        for i, entry in enumerate(entries):
            ranked_entries.append(
                RankingEntry(
                    symbol=entry.symbol,
                    rank=i + 1,
                    total_score=entry.total_score,
                    factor_scores=entry.factor_scores,
                )
            )

        return tuple(ranked_entries)

    def _compute_symbol_ranking(
        self,
        symbol: str,
        definition: RankingDefinition,
        factor_scores_by_symbol: dict[str, dict[str, float | None]],
    ) -> RankingEntry:
        """Compute ranking for a single symbol.

        Args:
            symbol:               Ticker symbol.
            definition:           Ranking definition.
            factor_scores_by_symbol: Raw factor scores.

        Returns:
            RankingEntry for the symbol.
        """
        factor_scores: list[FactorScore] = []
        normalized_scores: dict[str, float] = {}
        weights: dict[str, float] = {}

        for factor in definition.factors:
            raw_values = list(factor_scores_by_symbol[factor.name].values())
            raw_value = factor_scores_by_symbol[factor.name].get(symbol)
            valid_values = [v for v in raw_values if v is not None]

            if raw_value is None or not valid_values:
                normalized = 0.0
            else:
                normalized_values = normalize_factor_scores(
                    tuple(valid_values),
                    factor.normalization,
                    factor.direction,
                )
                valid_idx = [
                    i for i, v in enumerate(raw_values) if v is not None
                ]
                symbol_idx = raw_values.index(raw_value)
                if symbol_idx in valid_idx:
                    pos = valid_idx.index(symbol_idx)
                    normalized = normalized_values[pos]
                else:
                    normalized = 0.0

            weighted = normalized * factor.weight
            normalized_scores[factor.name] = normalized
            weights[factor.name] = factor.weight

            factor_scores.append(
                FactorScore(
                    factor_name=factor.name,
                    symbol=symbol,
                    raw_value=raw_value if raw_value is not None else 0.0,
                    normalized=normalized,
                    weight=factor.weight,
                    weighted=weighted,
                )
            )

        total_score = apply_weights(normalized_scores, weights)

        return RankingEntry(
            symbol=symbol,
            rank=0,
            total_score=total_score,
            factor_scores=tuple(factor_scores),
        )

    def _compute_statistics(
        self,
        entries: tuple[RankingEntry, ...],
        num_factors: int,
        start_time: float,
    ) -> RankingStatistics:
        """Compute ranking statistics.

        Args:
            entries:     Ranking entries.
            num_factors: Number of factors used.
            start_time:  Start time.

        Returns:
            RankingStatistics.
        """
        elapsed = time.monotonic() - start_time
        scores = [e.total_score for e in entries]
        n = len(scores)

        if n == 0:
            return RankingStatistics(
                total_symbols=0,
                total_factors=num_factors,
                elapsed_seconds=elapsed,
            )

        mean_score = sum(scores) / n
        sorted_scores = sorted(scores)
        if n % 2 == 0:
            median_score = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
        else:
            median_score = sorted_scores[n // 2]

        variance = sum((s - mean_score) ** 2 for s in scores) / max(n - 1, 1)
        std_score = math.sqrt(variance)

        return RankingStatistics(
            total_symbols=n,
            total_factors=num_factors,
            elapsed_seconds=elapsed,
            mean_score=mean_score,
            median_score=median_score,
            std_score=std_score,
        )
