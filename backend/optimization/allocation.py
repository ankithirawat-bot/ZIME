"""Advanced allocation engines for portfolio construction.

Implements allocation strategies that build portfolios from expected returns, risks, and constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


class AllocationProtocol(Protocol):
    """Protocol for allocation strategies."""

    def allocate(self, returns: tuple[float, ...], volatilities: tuple[float, ...], corr: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
        """Compute allocation weights."""
        ...



@dataclass(frozen=True)
class AllocationRequest:
    """Request for allocation construction.

    Attributes:
    expected_returns: Expected returns for each asset.
    expected_volatilities: Expected volatilities per asset.
    covariance: Full covariance matrix.
    asset_names: Asset identifiers.
    cash_reserve: Desired cash weight.
    max_weight_per_asset: Max weight per holding.
    min_weight_per_asset: Min weight per holding.
    leverage_limit: Max gross leverage.
    objective_kwargs: Allocator-specific kwargs.
    """

    expected_returns: tuple[float, ...]
    expected_volatilities: tuple[float, ...]
    covariance: tuple[tuple[float, ...], ...]
    asset_names: tuple[str, ...] = field(default=())
    cash_reserve: float = 0.0
    max_weight_per_asset: float = 1.0
    min_weight_per_asset: float = 0.0
    leverage_limit: float = 1.0
    objective_kwargs: dict[str, float] = field(default_factory=dict)



@dataclass(frozen=True)
class AllocationResult:
    """Result of an allocation run.

    Attributes:
    weights: Optimal asset weights including cash reserve.
    objective_value: Scalar value of allocation objective.
    status: Execution status.
    message: Optional diagnostic.
    """

    weights: tuple[float, ...]
    objective_value: float = 0.0
    status: str = "SUCCESS"
    message: str = ""



class EqualWeight:
    """Equal-weight allocation strategy."""

    def allocate(self, asset_names: tuple[str, ...] | None = None, total: float = 1.0) -> tuple[float, ...]:
        n = len(asset_names or ())
        w = total / max(n, 1)
        return tuple([w] * n)



class RiskParity:
    """Risk-parity allocation strategy."""

    def allocate(self, volatilities: tuple[float, ...], corr: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
        vols = np.array(volatilities)
        inv_vol = 1.0 / vols
        weights = inv_vol / np.sum(inv_vol)
        # NaN-safe normalization
        weights = np.nan_to_num(weights, nan=0.0)
        if not np.isfinite(weights).all():
            weights = np.ones_like(vols) / len(vols)
        return tuple(weights.tolist())



class VolatilityTarget:
    """Volatility-targeted allocation."""

    def allocate(
        self, target_vol: float, volatilities: tuple[float, ...], corr: tuple[tuple[float, ...], ...]
    ) -> tuple[float, ...]:
        if target_vol <= 0 or not volatilities:
            n = len(volatilities)
            return tuple([1.0 / max(n, 1)] * n)
        vols = np.array(volatilities)
        corr_mat = np.array(corr)
        # Covariance matrix: Sigma = diag(vols) @ corr @ diag(vols).
        cov = corr_mat * (vols[:, None] * vols[None, :])
        # Equal-weight base scaled to portfolio risk via leverage.
        equal_base = np.full(len(vols), 1.0 / len(vols))
        port_vol = float(np.sqrt(equal_base @ cov @ equal_base))
        lev = 1.0 if port_vol <= 0 else min(1.0, target_vol / port_vol)
        weights = lev * equal_base
        total = float(weights.sum())
        if total > 0:
            weights = weights / total
        return tuple(weights.tolist())



class Kelly:
    """Kelly allocation (fractional growth maximization)."""

    def allocate(
        self, returns: tuple[float, ...], volatilities: tuple[float, ...]
    ) -> tuple[float, ...]:
        w = np.array(returns) / (np.array(volatilities) ** 2)
        w = np.nan_to_num(w, nan=0.0)
        if not w.sum():
            n = len(returns)
            return tuple([1.0 / max(n, 1)] * n)
        return tuple(w / w.sum())
