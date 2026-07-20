"""
Market Data Platform.

Provider-agnostic data ingestion architecture for the ZIME platform.
"""

from backend.data.adapters import (
    CorporateActionAdapter,
    FinancialAdapter,
    NewsAdapter,
    PriceAdapter,
    ShareholdingAdapter,
)
from backend.data.data_engine import DataEngine
from backend.data.datasource import DataSource, NormalizedRecord
from backend.data.exceptions import (
    InvalidRequestError,
    UnsupportedDataTypeError,
    UnsupportedProviderError,
    ValidationError,
)
from backend.data.models import (
    DataRequest,
    DataResponse,
    DataStatus,
    DataType,
    NormalizedData,
    ProviderIdentity,
    ProviderType,
    RawDataResponse,
    ValidationResult,
)
from backend.data.normalizer import DataNormalizer
from backend.data.provider import MarketDataProvider
from backend.data.provider_registry import ProviderRegistry
from backend.data.schemas import (
    CorporateAction,
    DailyOHLCV,
    FinancialStatement,
    IntradayOHLCV,
    NewsRecord,
    ShareholdingRecord,
)

__all__ = [
    "CorporateAction",
    "CorporateActionAdapter",
    "DataEngine",
    "DataNormalizer",
    "DataRequest",
    "DataResponse",
    "DataStatus",
    "DataType",
    "DataSource",
    "FinancialAdapter",
    "FinancialStatement",
    "InvalidRequestError",
    "IntradayOHLCV",
    "DailyOHLCV",
    "MarketDataProvider",
    "NewsAdapter",
    "NewsRecord",
    "NormalizedData",
    "NormalizedRecord",
    "PriceAdapter",
    "ProviderIdentity",
    "ProviderRegistry",
    "ProviderType",
    "RawDataResponse",
    "ShareholdingAdapter",
    "ShareholdingRecord",
    "UnsupportedDataTypeError",
    "UnsupportedProviderError",
    "ValidationError",
    "ValidationResult",
]
