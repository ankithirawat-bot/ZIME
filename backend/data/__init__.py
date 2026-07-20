"""
Market Data Platform.

Provider-agnostic data ingestion architecture for the ZIME platform.
"""

from backend.data.data_engine import DataEngine
from backend.data.exceptions import (
    InvalidRequestError,
    UnsupportedDataTypeError,
    UnsupportedProviderError,
    ValidationError,
)
from backend.data.models import DataRequest, DataResponse, DataType, ValidationResult
from backend.data.provider import MarketDataProvider
from backend.data.provider_registry import ProviderRegistry

__all__ = [
    "DataEngine",
    "DataRequest",
    "DataResponse",
    "DataType",
    "InvalidRequestError",
    "MarketDataProvider",
    "ProviderRegistry",
    "UnsupportedDataTypeError",
    "UnsupportedProviderError",
    "ValidationError",
    "ValidationResult",
]
