"""Risk budgeting utilities.

Compute risk contributions, marginal contributions, and validate risk constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


class RiskBudgetProtocol(Protocol):
    """Protocol for risk budget engine."""

    @staticmethod
    def portfolio_risk(weights: tuple[float, ...], volatilities: tuple[float, ...], corr: tuple[tuple[float, ...], ...], rf: float = 0.0) -> float:
        ...

    @staticmethod
    def asset_risk_contributions(weights: tuple[float, ...], volatilities: tuple[float, ...], corr: tuple[tuple[float, ...], ...], rf: float = 0.0) -> dict[str, float]:
        ...

    @staticmethod
    def risk_contribution_percentages(weights: tuple[float, ...], volatilities: tuple[float, ...], corr: tuple[tuple[float, ...], ...], rf: float = 0.0) -> tuple[float, ...]:
        ...

    @staticmethod
    def marginal_risk_contributions(weights: tuple[float, ...], returns: tuple[float, ...], volatilities: tuple[float, ...] = (), corr: tuple[tuple[float, ...], ...] = (), rf: float = 0.0) -> tuple[float, ...]:
        ...

    @staticmethod
    def validate_risk_budget(targets: dict[str, float] | tuple[float, ...], weights: tuple[float, ...]) -> tuple[bool, dict[str, float]]:
        ...


@dataclass(frozen=True)
class RiskContribution:
    asset_name: str
    contribution: float
    marginal_contribution: float
    percentage_contribution: float


@dataclass(frozen=True)
class RiskBudget:
    equal_risk_contributions: bool
    targets: tuple[RiskContribution, ...]


def portfolio_risk(weights: tuple[float, ...], volatilities: tuple[float, ...], corr: tuple[tuple[float, ...], ...], rf: float = 0.0) -> float:
    w = np.array(weights)
    vol = np.array(volatilities)
    if vol.size == 0:
        return 0.0 - rf
    if not corr or len(corr) == 0:
        # When no correlation matrix is supplied treat the assets as independent
        # (diagonal identity), which makes |vol| the only contributor.
        return float(np.sqrt(np.sum((w * vol) ** 2))) - rf
    mat = np.array(corr) * (vol[:, None] * vol[None, :])
    sigma_w = float(np.sqrt(w.T @ mat @ w))
    return sigma_w - rf


def asset_risk_contributions(weights: tuple[float, ...], volatilities: tuple[float, ...], corr: tuple[tuple[float, ...], ...], rf: float = 0.0) -> list[RiskContribution]:
    w = np.array(weights)
    s = np.array(volatilities)
    if s.size == 0:
        return []
    if not corr or len(corr) == 0:
        mat = np.diag(s ** 2)
    else:
        mat = np.array(corr) * (s[:, None] * s[None, :])
    sigma_w = portfolio_risk(weights, volatilities, corr, rf)
    mrc = mat @ w
    rc = w * mrc
    percent = (rc / max(sigma_w, 1e-12)) * 100
    pairs = list(RiskContribution(
        asset_name="", contribution=float(ri), marginal_contribution=float(mi), percentage_contribution=float(pi)
    ) for ri, mi, pi in zip(rc, mrc, percent))
    return pairs


def marginal_risk_contributions(weights: tuple[float, ...], returns: tuple[float, ...], volatilities=(), corr=(), rf: float = 0.0, *, vols=None, **kwargs) -> tuple[float, ...]:
    # Backward-compatible alias: accept either ``vols`` (legacy kwarg) or ``volatilities``.
    if vols is not None:
        volatilities = vols
    # if volatilities empty, compute from returns
    s = np.array(volatilities) if volatilities else np.array(returns)
    if s.size == 0:
        # No sigma info at all — return a zero tuple of len(weights).
        return tuple(0.0 for _ in weights)
    sigma_w = portfolio_risk(weights, s, corr, rf)
    if sigma_w == 0:
        return tuple(0.0 for _ in weights)
    # MRC approx: partial derivative of portfolio volatility w.r.t weight i
    eps = 1e-8
    mrc = []
    for i in range(len(weights)):
        w = np.array(weights)
        wi = w.copy()
        wi[i] += eps
        wi /= wi.sum()
        mrc_i = (portfolio_risk(tuple(wi), s, corr, rf) - sigma_w) / eps
        mrc.append(float(mrc_i))
    return tuple(mrc)


def risk_contribution_percentages(weights: tuple[float, ...], volatilities: tuple[float, ...], corr: tuple[tuple[float, ...], ...], rf: float = 0.0) -> tuple[float, ...]:
    w = np.array(weights)
    excl_rf = portfolio_risk(weights, volatilities, corr, rf)
    if excl_rf <= 0:
        return tuple(0.0 for _ in weights)
    s = np.array(volatilities)
    mat = np.array(corr) * (s[:, None] * s[None, :])
    cov_port = mat @ w
    rc = w * cov_port
    pcts = rc / max(excl_rf, 1e-12) * 100.0
    return tuple(float(p) for p in pcts)


def validate_risk_budget(targets: dict[str, float] | tuple[float, ...], weights: tuple[float, ...]) -> tuple[bool, list]:
    tw = list(weights)
    tv = {k: v for k, v in targets.items()}
    violations = []
    total = sum(tv.values()) if isinstance(targets, dict) else sum(targets)
    if abs(total - 1.0) > 1e-4:
        violations.append("weights_sum=not_one")
    for k, v in tv.items():
        idx = int(k)
        if idx >= len(tw) or abs(tw[idx] - tv[k]) > 0.01:
            violations.append("target_violation")
    return (len(violations) == 0), violations
