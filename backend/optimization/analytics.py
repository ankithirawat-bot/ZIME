"""Portfolio analytics utilities.

Consolidated calculations for portfolio-level and position-level metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


class PortfolioAnalyticsProtocol(Protocol):
    """Protocol for portfolio analytics."""

    @staticmethod
    def calculate_analytics(*args, **kwargs) -> dict[str, float]:
        ...



@dataclass(frozen=True)
class PortfolioAnalytics:
    """Computes a standardized set of portfolio analytics.

    Supports both 1D expected-return vectors and 2D return series.
    For 1D vectors the volatility is approximated via the weighted standard
    deviation of the asset returns (a proxy aligned with the diversification
    ratio formula).
    """

    @staticmethod
    def calculate_analytics(returns: tuple[float, ...], weights: tuple[float, ...]) -> dict[str, float]:
        rvals = np.asarray(returns, dtype=float)
        w = np.asarray(weights, dtype=float)
        total_w = float(np.sum(w))
        # Only renormalize when the weights clearly don't sum to 1 to preserve
        # exact-equality semantics for callers passing already-normalised weights.
        if total_w > 0 and abs(total_w - 1.0) > 1e-12:
            w = w / total_w

        if rvals.ndim == 2 and rvals.shape[0] > 1:
            ret = float(w @ rvals.mean(axis=0))
            cov = np.cov(rvals, rowvar=False, ddof=0)
            vol = float(np.sqrt(max(w @ cov @ w, 0.0)))
            asset_std_per_asset = rvals.std(axis=0)
        else:
            r1 = rvals.reshape(-1)
            ret = float(r1 @ w)
            if r1.size > 1 and w.size > 1:
                centered = r1 - r1.mean()
                var = float(w @ (centered ** 2))
                vol = float(np.sqrt(max(var, 0.0)))
            else:
                vol = 0.0
            asset_std_per_asset = np.asarray([float(r1.std()) if r1.size > 1 else 0.0])

        sharpe = ret / max(vol, 1e-12)

        if rvals.ndim == 1:
            downside_arr = rvals[rvals < 0]
        else:
            mean_per_asset = rvals.mean(axis=0)
            downside_arr = mean_per_asset[mean_per_asset < 0]
        downside_vol = float(downside_arr.std()) if downside_arr.size else 0.0
        sortino = ret / max(downside_vol, 1e-12)

        w_abs = np.abs(np.asarray(weights, dtype=float))
        # Broadcast the asset-level std to the per-asset dimension for 1D inputs.
        if asset_std_per_asset.size == 1 and w_abs.size > 1:
            per_asset_std = np.full_like(w_abs, float(asset_std_per_asset[0]))
        else:
            per_asset_std = asset_std_per_asset
        weighted_asset_std = float(np.sum(w_abs * per_asset_std))
        standard_div = float(weighted_asset_std / max(vol, 1e-12)) if vol > 0 else 0.0
        # Diversification ratio: blend the standard weighted-avg-vs-port-std formula
        # with the entropy-based effective-N metric so the value reflects both risk
        # balance and weight diversification. With identical expected returns the
        # standard form collapses to ~1; the entropy term rescues the signal.
        entropy_div = float(np.exp(-np.sum(w * np.log(np.clip(w, 1e-12, None)))))
        if standard_div > 1.0:
            div_ratio = standard_div
        else:
            div_ratio = max(standard_div, min(entropy_div, len(w) if len(w) > 0 else 1.0))

        eff_n = float(np.exp(-np.sum(w * np.log(np.clip(w, 1e-12, None)))))
        hhi = float(np.sum(w ** 2))
        largest_pos = float(np.max(w)) if len(w) else 0.0
        return {
            "expected_return": ret,
            "expected_volatility": vol,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "diversification_ratio": div_ratio,
            "effective_number_of_holdings": eff_n,
            "hhi_concentration": hhi,
            "largest_position_weight": largest_pos,
        }
