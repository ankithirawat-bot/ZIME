"""Performance evaluation metrics.

Computes regression, classification, risk-adjusted, and rolling
performance metrics for model evaluation.
"""

from __future__ import annotations

import math

from backend.intelligence.exceptions import EvaluationError
from backend.intelligence.models import EvaluationRequest, EvaluationResult

EPSILON = 1e-10


def _mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stdev(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def compute_rmse(actuals: tuple[float, ...], predictions: tuple[float, ...]) -> float:
    """Compute root mean squared error."""
    n = len(actuals)
    if n == 0:
        return 0.0
    return math.sqrt(sum((a - p) ** 2 for a, p in zip(actuals, predictions)) / n)


def compute_mae(actuals: tuple[float, ...], predictions: tuple[float, ...]) -> float:
    """Compute mean absolute error."""
    n = len(actuals)
    if n == 0:
        return 0.0
    return sum(abs(a - p) for a, p in zip(actuals, predictions)) / n


def compute_mape(actuals: tuple[float, ...], predictions: tuple[float, ...]) -> float:
    """Compute mean absolute percentage error."""
    n = len(actuals)
    if n == 0:
        return 0.0
    pct_errors: list[float] = []
    for a, p in zip(actuals, predictions):
        if abs(a) > EPSILON:
            pct_errors.append(abs((a - p) / a))
    return _mean(tuple(pct_errors)) * 100.0 if pct_errors else 0.0


def compute_sharpe(
    returns: tuple[float, ...],
    risk_free_rate: float = 0.0,
    annual_factor: float = 252.0,
) -> float:
    """Compute Sharpe ratio."""
    if len(returns) < 2:
        return 0.0
    excess = tuple(r - risk_free_rate / annual_factor for r in returns)
    mean_excess = _mean(excess)
    std_excess = _stdev(excess)
    if std_excess <= EPSILON:
        return 0.0
    return (mean_excess / std_excess) * math.sqrt(annual_factor)


def compute_sortino(
    returns: tuple[float, ...],
    risk_free_rate: float = 0.0,
    annual_factor: float = 252.0,
) -> float:
    """Compute Sortino ratio (downside deviation only)."""
    if len(returns) < 2:
        return 0.0
    excess = tuple(r - risk_free_rate / annual_factor for r in returns)
    mean_excess = _mean(excess)
    downside: list[float] = [min(0, r) for r in excess]
    downside_std = _stdev(tuple(downside))
    if downside_std <= EPSILON:
        return 0.0
    return (mean_excess / downside_std) * math.sqrt(annual_factor)


def compute_hit_ratio(
    actuals: tuple[float, ...],
    predictions: tuple[float, ...],
) -> float:
    """Compute hit ratio (directional accuracy)."""
    n = len(actuals)
    if n < 2:
        return 0.0
    hits = sum(
        1 for i in range(1, n)
        if (actuals[i] - actuals[i - 1]) * (predictions[i] - predictions[i - 1]) > 0
    )
    return hits / (n - 1)


def compute_precision(
    actuals: tuple[float, ...],
    predictions: tuple[float, ...],
    threshold: float = 0.0,
) -> float:
    """Compute precision for binary classification."""
    tp = sum(1 for a, p in zip(actuals, predictions) if p > threshold and a > threshold)
    fp = sum(1 for a, p in zip(actuals, predictions) if p > threshold and a <= threshold)
    if tp + fp == 0:
        return 0.0
    return tp / (tp + fp)


def compute_recall(
    actuals: tuple[float, ...],
    predictions: tuple[float, ...],
    threshold: float = 0.0,
) -> float:
    """Compute recall for binary classification."""
    tp = sum(1 for a, p in zip(actuals, predictions) if p > threshold and a > threshold)
    fn = sum(1 for a, p in zip(actuals, predictions) if p <= threshold and a > threshold)
    if tp + fn == 0:
        return 0.0
    return tp / (tp + fn)


def compute_f1(
    actuals: tuple[float, ...],
    predictions: tuple[float, ...],
    threshold: float = 0.0,
) -> float:
    """Compute F1 score for binary classification."""
    p = compute_precision(actuals, predictions, threshold)
    r = compute_recall(actuals, predictions, threshold)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def compute_max_drawdown(values: tuple[float, ...]) -> float:
    """Compute maximum drawdown from peak."""
    if len(values) < 2:
        return 0.0
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def compute_cagr(
    values: tuple[float, ...],
    annual_factor: float = 252.0,
) -> float:
    """Compute compound annual growth rate."""
    if len(values) < 2:
        return 0.0
    start = values[0]
    end = values[-1]
    if start <= 0:
        return 0.0
    periods = len(values) - 1
    return (end / start) ** (annual_factor / periods) - 1.0


def compute_rolling_rmse(
    actuals: tuple[float, ...],
    predictions: tuple[float, ...],
    window: int = 20,
) -> tuple[float, ...]:
    """Compute rolling RMSE over a sliding window."""
    if len(actuals) < window:
        return tuple(compute_rmse(actuals, predictions) for _ in range(len(actuals)))
    result: list[float] = []
    for i in range(window, len(actuals) + 1):
        a_slice = actuals[i - window:i]
        p_slice = predictions[i - window:i]
        result.append(compute_rmse(a_slice, p_slice))
    return tuple(result)


def compute_rolling_sharpe(
    returns: tuple[float, ...],
    window: int = 20,
    annual_factor: float = 252.0,
) -> tuple[float, ...]:
    """Compute rolling Sharpe ratio over a sliding window."""
    if len(returns) < window:
        return tuple(compute_sharpe(returns, annual_factor=annual_factor) for _ in range(len(returns)))
    result: list[float] = []
    for i in range(window, len(returns) + 1):
        r_slice = returns[i - window:i]
        result.append(compute_sharpe(r_slice, annual_factor=annual_factor))
    return tuple(result)


class MetricsCalculator:
    """Computes comprehensive evaluation metrics."""

    def evaluate(
        self,
        request: EvaluationRequest,
        annual_factor: float = 252.0,
        rolling_window: int = 20,
    ) -> EvaluationResult:
        """Compute all metrics for an evaluation request.

        Args:
            request:        Evaluation request with predictions and actuals.
            annual_factor:  Annualization factor for ratios.
            rolling_window: Rolling metrics window.

        Returns:
            EvaluationResult with all computed metrics.
        """
        actuals = request.actuals
        predictions = request.predictions

        if len(actuals) != len(predictions):
            raise EvaluationError(
                f"Length mismatch: {len(actuals)} actuals vs {len(predictions)} predictions"
            )

        n = len(actuals)

        rmse = compute_rmse(actuals, predictions)
        mae = compute_mae(actuals, predictions)
        mape = compute_mape(actuals, predictions)

        returns = tuple(
            (actuals[i] - actuals[i - 1]) / actuals[i - 1]
            for i in range(1, n) if actuals[i - 1] > 0
        )
        sharpe = compute_sharpe(returns, annual_factor=annual_factor)
        sortino = compute_sortino(returns, annual_factor=annual_factor)

        hit_ratio = compute_hit_ratio(actuals, predictions)
        precision = compute_precision(actuals, predictions)
        recall = compute_recall(actuals, predictions)
        f1 = compute_f1(actuals, predictions)

        max_dd = compute_max_drawdown(actuals)
        cagr = compute_cagr(actuals, annual_factor=annual_factor)

        rolling_rmse = compute_rolling_rmse(actuals, predictions, rolling_window)
        rolling_sharpe = compute_rolling_sharpe(returns, rolling_window, annual_factor)

        return EvaluationResult(
            model_name=request.model_name,
            rmse=rmse,
            mae=mae,
            mape=mape,
            sharpe=sharpe,
            sortino=sortino,
            hit_ratio=hit_ratio,
            precision=precision,
            recall=recall,
            f1=f1,
            max_drawdown=max_dd,
            cagr=cagr,
            rolling_rmse=rolling_rmse,
            rolling_sharpe=rolling_sharpe,
            sample_count=n,
            metadata=request.metadata,
        )
