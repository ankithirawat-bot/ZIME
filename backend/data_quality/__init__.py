"""
Data Quality & Multi-Provider Validation Platform.

Validates, compares and scores market data from multiple providers without
any provider-specific assumptions. Validation rules and anomaly detectors are
registered in a :class:`RuleRegistry`, so new checks are added by registration
rather than by editing engine code.
"""

from backend.data_quality.anomaly_detector import (
    AnomalyDetectorEngine,
    _detect_abnormal_volume,
    _detect_impossible_gaps,
    _detect_negative_prices,
    _detect_price_spikes,
    _detect_stale_data,
)
from backend.data_quality.comparator import DataComparator
from backend.data_quality.confidence import ConfidenceEngine
from backend.data_quality.exceptions import (
    DataQualityError,
    DetectorNotFoundError,
    RuleNotFoundError,
    ValidationError,
)
from backend.data_quality.models import (
    Anomaly,
    ComparisonResult,
    ConfidenceScore,
    CorporateActionDivergence,
    Issue,
    MissingRecord,
    PriceBar,
    ProviderComparison,
    ValidationReport,
    ValidationRequest,
    ValidationResult,
)
from backend.data_quality.registry import AnomalyDetector, RuleRegistry, ValidationRule
from backend.data_quality.report import ReportGenerator
from backend.data_quality.validator import DataValidator

__all__ = [
    "Anomaly",
    "AnomalyDetector",
    "AnomalyDetectorEngine",
    "ComparisonResult",
    "ConfidenceEngine",
    "ConfidenceScore",
    "CorporateActionDivergence",
    "DataComparator",
    "DataQualityError",
    "DataValidator",
    "DetectorNotFoundError",
    "Issue",
    "MissingRecord",
    "PriceBar",
    "ProviderComparison",
    "ReportGenerator",
    "RuleNotFoundError",
    "RuleRegistry",
    "ValidationError",
    "ValidationRequest",
    "ValidationResult",
    "ValidationRule",
    "ValidationReport",
    "_detect_abnormal_volume",
    "_detect_impossible_gaps",
    "_detect_negative_prices",
    "_detect_price_spikes",
    "_detect_stale_data",
]
