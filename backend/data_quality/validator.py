"""
Validation engine.

Runs every registered validation rule over a :class:`ValidationRequest` and
aggregates the resulting :class:`Issue` objects into a structured
:class:`ValidationResult`. Six default rules are registered automatically;
callers may register additional rules without code changes here.
"""

from __future__ import annotations

from datetime import date, timedelta

from backend.data_quality.models import Issue, PriceBar, ValidationRequest, ValidationResult
from backend.data_quality.registry import RuleRegistry, ValidationRule


def _rule_missing_days(request: ValidationRequest) -> list[Issue]:
    bars = request.bars
    if len(bars) < 2:
        return []
    dates = sorted(b.trade_date for b in bars)
    present = set(dates)
    start, end = dates[0], dates[-1]
    issues: list[Issue] = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5 and cursor not in present:
            issues.append(
                Issue(
                    code="missing_days",
                    message=f"Missing trading day {cursor.isoformat()}",
                    severity="medium",
                    value=cursor,
                )
            )
        cursor += timedelta(days=1)
    return issues


def _rule_duplicate_rows(request: ValidationRequest) -> list[Issue]:
    seen: dict[date, int] = {}
    issues: list[Issue] = []
    for i, bar in enumerate(request.bars):
        if bar.trade_date in seen:
            issues.append(
                Issue(
                    code="duplicate_rows",
                    message=f"Duplicate bar for {bar.trade_date.isoformat()} (index {i})",
                    index=i,
                    severity="medium",
                )
            )
        else:
            seen[bar.trade_date] = i
    return issues


def _rule_invalid_ohlc(request: ValidationRequest) -> list[Issue]:
    issues: list[Issue] = []
    for i, bar in enumerate(request.bars):
        if _is_invalid_ohlc(bar):
            issues.append(
                Issue(
                    code="invalid_ohlc",
                    message=f"Invalid OHLC on {bar.trade_date.isoformat()} (index {i})",
                    index=i,
                    severity="high",
                )
            )
    return issues


def _is_invalid_ohlc(bar: PriceBar) -> bool:
    if (
        bar.open != bar.open
        or bar.high != bar.high
        or bar.low != bar.low
        or bar.close != bar.close
    ):
        return True
    if min(bar.open, bar.high, bar.low, bar.close) <= 0:
        return True
    if bar.high < max(bar.open, bar.close) - 1e-9:
        return True
    if bar.low > min(bar.open, bar.close) + 1e-9:
        return True
    return False


def _rule_invalid_volume(request: ValidationRequest) -> list[Issue]:
    issues: list[Issue] = []
    for i, bar in enumerate(request.bars):
        if bar.volume != bar.volume or bar.volume < 0:
            issues.append(
                Issue(
                    code="invalid_volume",
                    message=f"Invalid volume on {bar.trade_date.isoformat()} (index {i})",
                    index=i,
                    severity="high",
                )
            )
    return issues


def _rule_timestamp_order(request: ValidationRequest) -> list[Issue]:
    issues: list[Issue] = []
    previous: date | None = None
    for i, bar in enumerate(request.bars):
        if previous is not None and bar.trade_date < previous:
            issues.append(
                Issue(
                    code="timestamp_order",
                    message=f"Out-of-order timestamp at index {i} ({bar.trade_date.isoformat()})",
                    index=i,
                    severity="high",
                )
            )
        previous = bar.trade_date
    return issues


def _rule_future_dates(request: ValidationRequest) -> list[Issue]:
    baseline = request.as_of or date.today()
    issues: list[Issue] = []
    for i, bar in enumerate(request.bars):
        if bar.trade_date > baseline:
            issues.append(
                Issue(
                    code="future_date",
                    message=f"Future-dated bar at index {i} ({bar.trade_date.isoformat()})",
                    index=i,
                    severity="high",
                )
            )
    return issues


def _register_default_rules(registry: RuleRegistry) -> None:
    defaults: dict[str, ValidationRule] = {
        "missing_days": _rule_missing_days,
        "duplicate_rows": _rule_duplicate_rows,
        "invalid_ohlc": _rule_invalid_ohlc,
        "invalid_volume": _rule_invalid_volume,
        "timestamp_order": _rule_timestamp_order,
        "future_dates": _rule_future_dates,
    }
    for name, rule in defaults.items():
        if not registry.is_registered(name):
            registry.register_validation_rule(name, rule)


class DataValidator:
    """Runs registered validation rules and builds a ValidationResult."""

    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self._registry = registry or RuleRegistry()
        _register_default_rules(self._registry)

    def register_rule(self, name: str, rule: ValidationRule) -> None:
        """Register an additional validation rule."""
        self._registry.register_validation_rule(name, rule)

    def validate(self, request: ValidationRequest) -> ValidationResult:
        """Validate a request, returning a structured result."""
        issues: list[Issue] = []
        for rule in self._registry.validation_rules().values():
            issues.extend(rule(request))

        missing_days = tuple(i.value for i in issues if i.code == "missing_days" and i.value is not None)
        duplicate_rows = tuple(i.index for i in issues if i.code == "duplicate_rows" and i.index is not None)
        invalid_ohlc = tuple(i.index for i in issues if i.code == "invalid_ohlc" and i.index is not None)
        invalid_volume = tuple(i.index for i in issues if i.code == "invalid_volume" and i.index is not None)
        timestamp_issues = tuple(i.index for i in issues if i.code == "timestamp_order" and i.index is not None)
        future_dates = tuple(i.index for i in issues if i.code == "future_date" and i.index is not None)

        return ValidationResult(
            symbol=request.symbol,
            exchange=request.exchange,
            provider=request.provider,
            missing_days=missing_days,
            duplicate_rows=duplicate_rows,
            invalid_ohlc=invalid_ohlc,
            invalid_volume=invalid_volume,
            timestamp_issues=timestamp_issues,
            future_dates=future_dates,
            issues=tuple(issues),
            is_valid=len(issues) == 0,
        )
