"""
Factor Execution Engine.

Executes multiple registered factors in a single request, collecting
successes and failures without stopping on errors.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from backend.core.factor_result import FactorResult
from backend.factors.registry import FactorRegistry


@dataclass
class FactorRequest:
    """A single factor execution request.

    Attributes:
        factor: Registry name of the factor (e.g. "sma", "rsi").
        params: Keyword arguments to pass to the factor constructor.
    """

    factor: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineError:
    """An error that occurred during factor execution.

    Attributes:
        factor:  The factor name that failed.
        message: Human-readable error description.
        detail:  Optional traceback or exception string.
    """

    factor: str
    message: str
    detail: str = ""


@dataclass
class EngineResult:
    """Result of a batch factor execution.

    Attributes:
        success: Whether the engine completed without crashing.
                 Individual factor failures do not affect this.
        results: Mapping of result labels to FactorResult instances.
        errors:  List of EngineError for any factors that failed.
    """

    success: bool
    results: dict[str, FactorResult]
    errors: list[EngineError]


class FactorEngine:
    """Executes multiple factors against price data in a single call.

    The engine resolves factors from the FactorRegistry, instantiates
    them with the provided parameters, and executes each one independently.
    If a factor fails, the error is recorded and execution continues.

    Usage::

        engine = FactorEngine()
        result = engine.calculate(
            data=price_df,
            requests=[
                {"factor": "sma", "params": {"period": 20}},
                {"factor": "rsi", "params": {"period": 14}},
            ],
        )
        for label, factor_result in result.results.items():
            print(f"{label}: {factor_result.value}")

    The engine never raises exceptions. All errors are captured in
    ``EngineResult.errors``.
    """

    def calculate(
        self,
        data: pd.DataFrame,
        requests: list[dict[str, Any]],
        symbol: str = "UNKNOWN",
    ) -> EngineResult:
        """Execute multiple factors and collect results.

        Args:
            data:     Price DataFrame passed to each factor's compute().
            requests: List of dicts, each with ``factor`` (str) and
                      optionally ``params`` (dict).
            symbol:   Ticker symbol passed to each factor's compute().

        Returns:
            An EngineResult with successes in ``results`` and failures
            in ``errors``.
        """
        results: dict[str, FactorResult] = {}
        errors: list[EngineError] = []

        if not requests:
            return EngineResult(success=True, results=results, errors=errors)

        # Validate and deduplicate
        seen_labels: set[str] = set()
        validated: list[tuple[str, dict[str, Any], str]] = []

        for req in requests:
            factor_name = req.get("factor")
            params = req.get("params", {})

            if factor_name is None:
                errors.append(EngineError(
                    factor="(unknown)",
                    message="Request missing 'factor' field",
                ))
                continue

            if not isinstance(factor_name, str):
                errors.append(EngineError(
                    factor=str(factor_name),
                    message=f"Factor name must be a string, got {type(factor_name).__name__}",
                ))
                continue

            if not isinstance(params, dict):
                errors.append(EngineError(
                    factor=factor_name,
                    message=f"Params must be a dict, got {type(params).__name__}",
                ))
                continue

            label = self._make_label(factor_name, params)

            if label in seen_labels:
                errors.append(EngineError(
                    factor=factor_name,
                    message=f"Duplicate request for '{label}' (factor='{factor_name}', params={params})",
                ))
                continue

            # Validate factor exists in registry
            try:
                FactorRegistry.get(factor_name)
            except KeyError as e:
                errors.append(EngineError(
                    factor=factor_name,
                    message=str(e),
                ))
                continue

            seen_labels.add(label)
            validated.append((factor_name, params, label))

        # Execute each factor
        for factor_name, params, label in validated:
            try:
                factor_cls = FactorRegistry.get(factor_name)
                factor_instance = factor_cls(**params)
                result = factor_instance.compute(symbol=symbol, prices=data)
                results[label] = result
            except Exception as exc:
                errors.append(EngineError(
                    factor=factor_name,
                    message=f"Execution failed: {exc}",
                    detail=traceback.format_exc(),
                ))

        return EngineResult(
            success=True,
            results=results,
            errors=errors,
        )

    @staticmethod
    def _make_label(factor_name: str, params: dict[str, Any]) -> str:
        """Generate a result label from factor name and params.

        Convention: factor name uppercased, then primary param value appended
        if present. For example:

        - ("sma", {"period": 20}) -> "SMA20"
        - ("rsi", {"period": 14}) -> "RSI14"
        - ("macd", {}) -> "MACD"
        - ("macd", {"fast_period": 8}) -> "MACD8"

        Args:
            factor_name: The factor's registry name.
            params:      The constructor parameters.

        Returns:
            A string label suitable for use as a dict key.
        """
        base = factor_name.upper().replace(" ", "_")

        # Try common period parameter names
        for key in ("period", "k_period", "fast_period"):
            if key in params:
                return f"{base}{params[key]}"

        return base
