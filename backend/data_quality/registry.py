"""
Rule and detector registry.

Stores validation rules and anomaly detectors in dictionaries keyed by name.
Dispatch is data-driven (no switch statements); new rules/detectors are added
by registration without touching engine code.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from backend.data_quality.exceptions import DetectorNotFoundError, RuleNotFoundError
from backend.data_quality.models import Anomaly, Issue, PriceBar, ValidationRequest

ValidationRule = Callable[[ValidationRequest], list[Issue]]
AnomalyDetector = Callable[[Sequence[PriceBar], str, str, str], list[Anomaly]]


class RuleRegistry:
    """Registry of named validation rules and anomaly detectors."""

    def __init__(self) -> None:
        self._validation_rules: dict[str, ValidationRule] = {}
        self._anomaly_detectors: dict[str, AnomalyDetector] = {}

    def register_validation_rule(self, name: str, rule: ValidationRule) -> None:
        """Register a validation rule under a name."""
        self._validation_rules[name] = rule

    def get_validation_rule(self, name: str) -> ValidationRule:
        """Return a validation rule by name.

        Raises:
            RuleNotFoundError: When the rule is not registered.
        """
        rule = self._validation_rules.get(name)
        if rule is None:
            raise RuleNotFoundError(name)
        return rule

    def validation_rules(self) -> dict[str, ValidationRule]:
        """Return a copy of all registered validation rules."""
        return dict(self._validation_rules)

    def is_registered(self, name: str) -> bool:
        """Return True if a validation rule name is registered."""
        return name in self._validation_rules

    def register_anomaly_detector(self, name: str, detector: AnomalyDetector) -> None:
        """Register an anomaly detector under a name."""
        self._anomaly_detectors[name] = detector

    def get_anomaly_detector(self, name: str) -> AnomalyDetector:
        """Return an anomaly detector by name.

        Raises:
            DetectorNotFoundError: When the detector is not registered.
        """
        detector = self._anomaly_detectors.get(name)
        if detector is None:
            raise DetectorNotFoundError(name)
        return detector

    def anomaly_detectors(self) -> dict[str, AnomalyDetector]:
        """Return a copy of all registered anomaly detectors."""
        return dict(self._anomaly_detectors)
