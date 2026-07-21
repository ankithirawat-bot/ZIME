"""Market feature extraction.

Extracts normalized market features from price and volume data
for regime detection.
"""

from __future__ import annotations

import math

from backend.regime.exceptions import InsufficientDataError
from backend.regime.models import RegimeConfig, RegimeFeatures


def _mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stdev(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _normalize(value: float, min_v: float, max_v: float) -> float:
    """Normalize a value to [0, 1] range."""
    if max_v <= min_v:
        return 0.5
    return max(0.0, min(1.0, (value - min_v) / (max_v - min_v)))


def _zscore(value: float, mean: float, std: float) -> float:
    """Compute z-score and clamp to [-3, 3]."""
    if std <= 0:
        return 0.0
    return max(-3.0, min(3.0, (value - mean) / std))


def extract_trend_strength(
    prices: tuple[float, ...],
    config: RegimeConfig,
) -> float:
    """Extract normalized trend strength.

    Uses linear regression slope normalized by price level.
    Returns -1 (strong downtrend) to 1 (strong uptrend).
    """
    if len(prices) < config.trend_lookback:
        raise InsufficientDataError(
            f"Need at least {config.trend_lookback} prices for trend"
        )
    window = prices[-config.trend_lookback:]
    n = len(window)
    x_mean = (n - 1) / 2.0
    y_mean = _mean(tuple(window))
    num = sum((i - x_mean) * (window[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den > 0 else 0.0
    norm_slope = slope / (y_mean / n) if y_mean > 0 else 0.0
    return max(-1.0, min(1.0, norm_slope * 100))


def extract_momentum(
    prices: tuple[float, ...],
    config: RegimeConfig,
) -> float:
    """Extract normalized momentum.

    Rate of change over momentum lookback period.
    Returns -1 (strong negative) to 1 (strong positive).
    """
    if len(prices) < config.momentum_lookback + 1:
        raise InsufficientDataError(
            f"Need at least {config.momentum_lookback + 1} prices for momentum"
        )
    lookback = config.momentum_lookback
    current = prices[-1]
    past = prices[-lookback - 1]
    roc = (current - past) / past if past > 0 else 0.0
    return max(-1.0, min(1.0, roc * 10))


def extract_volatility_level(
    prices: tuple[float, ...],
    config: RegimeConfig,
) -> float:
    """Extract normalized volatility level.

    Returns 0 (low vol) to 1 (high vol).
    """
    if len(prices) < config.volatility_lookback + 1:
        raise InsufficientDataError(
            f"Need at least {config.volatility_lookback + 1} prices for vol"
        )
    lookback = config.volatility_lookback
    returns = tuple(
        (prices[i] - prices[i - 1]) / prices[i - 1]
        for i in range(len(prices) - lookback, len(prices))
        if prices[i - 1] > 0
    )
    if len(returns) < 2:
        return 0.0
    vol = _stdev(tuple(returns)) * math.sqrt(config.annual_factor)
    return _normalize(vol, 0.0, 0.50)


def extract_volatility_change(
    prices: tuple[float, ...],
    config: RegimeConfig,
) -> float:
    """Extract volatility change.

    Returns -1 (decreasing vol) to 1 (increasing vol).
    """
    if len(prices) < config.volatility_lookback * 2 + 1:
        raise InsufficientDataError(
            f"Need at least {config.volatility_lookback * 2 + 1} prices for vol change"
        )
    lb = config.volatility_lookback
    recent_returns = tuple(
        (prices[i] - prices[i - 1]) / prices[i - 1]
        for i in range(len(prices) - lb, len(prices))
        if prices[i - 1] > 0
    )
    prior_returns = tuple(
        (prices[i] - prices[i - 1]) / prices[i - 1]
        for i in range(len(prices) - 2 * lb, len(prices) - lb)
        if prices[i - 1] > 0
    )
    recent_vol = _stdev(tuple(recent_returns)) if len(recent_returns) > 1 else 0.0
    prior_vol = _stdev(tuple(prior_returns)) if len(prior_returns) > 1 else 0.0
    if prior_vol <= 0:
        return 0.0
    change = (recent_vol - prior_vol) / prior_vol
    return max(-1.0, min(1.0, change))


def extract_breadth(
    advances: tuple[float, ...],
    declines: tuple[float, ...],
    config: RegimeConfig,
) -> float:
    """Extract market breadth from advance-decline data.

    Returns 0 (poor breadth) to 1 (strong breadth).
    """
    if not advances or not declines:
        return 0.5
    lookback = min(config.breadth_lookback, len(advances), len(declines))
    recent_a = advances[-lookback:]
    recent_d = declines[-lookback:]
    ratios = [
        a / (a + d) if (a + d) > 0 else 0.5
        for a, d in zip(recent_a, recent_d)
    ]
    avg_ratio = _mean(tuple(ratios))
    return _normalize(avg_ratio, 0.3, 0.7)


def extract_volume_expansion(
    volumes: tuple[float, ...],
    config: RegimeConfig,
) -> float:
    """Extract volume expansion score.

    Returns -1 (contracting) to 1 (expanding).
    """
    if len(volumes) < config.short_lookback * 2:
        raise InsufficientDataError(
            f"Need at least {config.short_lookback * 2} volumes"
        )
    lb = config.short_lookback
    recent = _mean(volumes[-lb:])
    prior = _mean(volumes[-(2 * lb):-lb])
    if prior <= 0:
        return 0.0
    ratio = (recent - prior) / prior
    return max(-1.0, min(1.0, ratio))


def extract_market_correlation(
    returns: dict[str, tuple[float, ...]],
    config: RegimeConfig,
) -> float:
    """Extract average market cross-correlation.

    Returns 0 (low correlation) to 1 (high correlation).
    """
    symbols = list(returns.keys())
    if len(symbols) < 2:
        return 0.5
    correlations: list[float] = []
    lb = min(config.correlation_lookback, min(len(r) for r in returns.values()))
    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            ri = returns[symbols[i]][-lb:]
            rj = returns[symbols[j]][-lb:]
            n = min(len(ri), len(rj))
            if n < 5:
                continue
            ri = ri[:n]
            rj = rj[:n]
            mi = _mean(tuple(ri))
            mj = _mean(tuple(rj))
            si = _stdev(tuple(ri))
            sj = _stdev(tuple(rj))
            if si <= 0 or sj <= 0:
                continue
            cov = sum((ri[k] - mi) * (rj[k] - mj) for k in range(n)) / (n - 1)
            corr = cov / (si * sj)
            correlations.append(max(-1.0, min(1.0, corr)))
    if not correlations:
        return 0.5
    avg_corr = _mean(tuple(correlations))
    return _normalize(avg_corr, 0.0, 1.0)


def extract_dispersion(
    returns: dict[str, tuple[float, ...]],
    config: RegimeConfig,
) -> float:
    """Extract cross-sectional dispersion.

    Returns 0 (low dispersion) to 1 (high dispersion).
    """
    symbols = list(returns.keys())
    if len(symbols) < 5:
        return 0.5
    lb = min(config.short_lookback, min(len(r) for r in returns.values()))
    cross_returns: list[float] = []
    for sym in symbols:
        r = returns[sym]
        if len(r) >= lb:
            cross_returns.append(r[-1] if lb == 1 else _mean(tuple(r[-lb:])))
    if len(cross_returns) < 2:
        return 0.5
    disp = _stdev(tuple(cross_returns))
    return _normalize(disp, 0.0, 0.05)


def extract_drawdown(
    prices: tuple[float, ...],
) -> float:
    """Extract current drawdown.

    Returns 0 (no drawdown) to 1 (maximum drawdown).
    """
    if len(prices) < 2:
        return 0.0
    peak = max(prices)
    current = prices[-1]
    dd = (peak - current) / peak if peak > 0 else 0.0
    return min(1.0, max(0.0, dd))


def extract_recovery_strength(
    prices: tuple[float, ...],
    config: RegimeConfig,
) -> float:
    """Extract recovery strength from trough.

    Returns 0 (no recovery) to 1 (full recovery).
    """
    if len(prices) < config.short_lookback + 1:
        raise InsufficientDataError(
            f"Need at least {config.short_lookback + 1} prices for recovery"
        )
    lb = min(config.short_lookback, len(prices) - 1)
    recent = prices[-lb:]
    trough = min(recent)
    peak = max(recent)
    current = recent[-1]
    if peak <= trough:
        return 1.0
    recovery = (current - trough) / (peak - trough)
    return max(0.0, min(1.0, recovery))


def extract_liquidity_score(
    volumes: tuple[float, ...],
    spreads: tuple[float, ...] | None = None,
) -> float:
    """Extract normalized liquidity score.

    Returns 0 (illiquid) to 1 (highly liquid).
    """
    if len(volumes) < 5:
        return 0.5
    recent_vol = _mean(tuple(volumes[-5:]))
    prior_vol = _mean(tuple(volumes[:-5])) if len(volumes) > 5 else recent_vol
    vol_ratio = recent_vol / prior_vol if prior_vol > 0 else 1.0
    vol_score = _normalize(vol_ratio, 0.5, 2.0)
    if spreads and len(spreads) > 0:
        avg_spread = _mean(tuple(spreads))
        spread_score = 1.0 - _normalize(avg_spread, 0.0, 0.01)
        return (vol_score + spread_score) / 2.0
    return vol_score


class FeatureExtractor:
    """Extracts normalized market features from raw data."""

    def extract(
        self,
        prices: tuple[float, ...],
        volumes: tuple[float, ...] | None = None,
        advances: tuple[float, ...] | None = None,
        declines: tuple[float, ...] | None = None,
        returns_map: dict[str, tuple[float, ...]] | None = None,
        spreads: tuple[float, ...] | None = None,
        config: RegimeConfig | None = None,
    ) -> RegimeFeatures:
        """Extract all market features.

        Args:
            prices:      Price series.
            volumes:     Volume series.
            advances:    Advance count series.
            declines:    Decline count series.
            returns_map: Symbol -> returns dict for correlation/dispersion.
            spreads:     Bid-ask spread series.
            config:      Regime configuration.

        Returns:
            RegimeFeatures with all features.
        """
        cfg = config or RegimeConfig()

        try:
            trend = extract_trend_strength(prices, cfg) if len(prices) >= cfg.trend_lookback else 0.0
        except (InsufficientDataError, Exception):
            trend = 0.0

        try:
            momentum = extract_momentum(prices, cfg) if len(prices) >= cfg.momentum_lookback + 1 else 0.0
        except (InsufficientDataError, Exception):
            momentum = 0.0

        try:
            vol_level = extract_volatility_level(prices, cfg)
        except (InsufficientDataError, Exception):
            vol_level = 0.0

        try:
            vol_change = extract_volatility_change(prices, cfg)
        except (InsufficientDataError, Exception):
            vol_change = 0.0

        breadth = 0.5
        if advances is not None and declines is not None:
            try:
                breadth = extract_breadth(advances, declines, cfg)
            except Exception:
                breadth = 0.5

        vol_exp = 0.0
        if volumes is not None:
            try:
                vol_exp = extract_volume_expansion(volumes, cfg)
            except Exception:
                vol_exp = 0.0

        corr = 0.5
        if returns_map is not None:
            try:
                corr = extract_market_correlation(returns_map, cfg)
            except Exception:
                corr = 0.5

        disp = 0.5
        if returns_map is not None:
            try:
                disp = extract_dispersion(returns_map, cfg)
            except Exception:
                disp = 0.5

        drawdown = extract_drawdown(prices)

        try:
            recovery = extract_recovery_strength(prices, cfg)
        except Exception:
            recovery = 0.5

        liq = 0.5
        if volumes is not None:
            liq = extract_liquidity_score(volumes, spreads)

        return RegimeFeatures(
            trend_strength=trend,
            momentum=momentum,
            volatility_level=vol_level,
            volatility_change=vol_change,
            breadth=breadth,
            volume_expansion=vol_exp,
            market_correlation=corr,
            dispersion=disp,
            drawdown=drawdown,
            recovery_strength=recovery,
            liquidity_score=liq,
        )
