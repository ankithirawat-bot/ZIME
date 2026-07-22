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

    Supports:
    - Expected return
    - Expected volatility
    - Sharpe ratio
    - Sortino ratio
    - Diversification ratio
    - Effective number of holdings
    - HHI concentration
    - Largest position weight
    - Cash exposure if cash label present
    """

    @staticmethod
    def calculate_analytics(returns: tuple[float, ...], weights: tuple[float, ...]) -> dict[str, float]:
        rvals = np.array(returns)
        w = np.array(weights)
        w = w / w.sum()
        ret = float(rvals @ w)
        vol = float(np.sqrt(w.T @ rvals.var(axis=1) @ w)) if len(weights) > 1 else float(rvals.std() if len(returns) > 1 else 0.0)
        sharpe = ret / max(vol, 1e-12)
        downside_vol = rvals[rvals < 0].std() if (rvals < 0).any() else 0.0
        sortino = ret / max(downside_vol, 1e-12)
        div_ratio = float(vol / max(weights.std(), 1e-12))
        eff_n = float(np.exp(-1 * np.sum(w * np.log(w + 1e-12))))
        hhi = float(np.sum(w ** 2))
        largest_pos = float(np.max(w) if len(w) else 0.0)
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
