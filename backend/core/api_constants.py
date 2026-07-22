"""
API-specific constants for route paths, prefixes, and metadata.

Centralizes all API routing strings to eliminate duplication across
route definitions, tests, and documentation.
"""

# ======================= API Prefixes =======================

API_PREFIX: str = "/api"
API_VERSION_V1: str = "v1"
API_V1_PREFIX: str = f"{API_PREFIX}/{API_VERSION_V1}"

# ======================= Health Endpoints =======================

HEALTH_ENDPOINT: str = "/health"
LIVENESS_ENDPOINT: str = "/health/live"
READINESS_ENDPOINT: str = "/health/ready"

# ======================= Domain Route Prefixes =======================

ROUTE_RESEARCH: str = f"{API_V1_PREFIX}/research"
ROUTE_ANALYTICS: str = f"{API_V1_PREFIX}/analytics"
ROUTE_STRATEGY: str = f"{API_V1_PREFIX}/strategy"
ROUTE_OPTIMIZATION: str = f"{API_V1_PREFIX}/optimization"
ROUTE_VALIDATION: str = f"{API_V1_PREFIX}/validation"
ROUTE_TRADING: str = f"{API_V1_PREFIX}/trading"
ROUTE_PORTFOLIO: str = f"{API_V1_PREFIX}/portfolio"
ROUTE_ORDERS: str = f"{API_V1_PREFIX}/orders"
ROUTE_POSITIONS: str = f"{API_V1_PREFIX}/positions"
ROUTE_BROKERS: str = f"{API_V1_PREFIX}/brokers"
ROUTE_SYSTEM: str = f"{API_V1_PREFIX}/system"
ROUTE_RECOMMENDATIONS: str = f"{API_V1_PREFIX}/recommendations"

# ======================= Route Path Segments =======================

ROUTE_SEGMENT_ANALYZE: str = "analyze"
ROUTE_SEGMENT_EVALUATE: str = "evaluate"
ROUTE_SEGMENT_RUN: str = "run"
ROUTE_SEGMENT_COMPARE: str = "compare"
ROUTE_SEGMENT_HISTORY: str = "history"
ROUTE_SEGMENT_SEARCH: str = "search"
ROUTE_SEGMENT_REPORT: str = "report"
ROUTE_SEGMENT_EXPORT: str = "export"
ROUTE_SEGMENT_SYNC: str = "sync"
ROUTE_SEGMENT_RECONCILE: str = "reconcile"
ROUTE_SEGMENT_SUBSCRIBE: str = "subscribe"
ROUTE_SEGMENT_UNSUBSCRIBE: str = "unsubscribe"
ROUTE_SEGMENT_PAPER: str = "paper"
ROUTE_SEGMENT_LIVE: str = "live"

# ======================= Pagination Defaults =======================

DEFAULT_PAGE: int = 1
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# ======================= API Metadata =======================

API_TITLE: str = "ZIME API"
API_VERSION: str = "1.0.0"
API_DESCRIPTION: str = "ZIME Investment Research Platform API"
CONTACT_NAME: str = "ZIME Team"
CONTACT_EMAIL: str = "dev@zime.ai"

# ======================= HTTP Header Names =======================

HEADER_CORRELATION_ID: str = "X-Correlation-ID"
HEADER_REQUEST_ID: str = "X-Request-ID"
HEADER_API_KEY: str = "X-API-Key"
HEADER_IDEMPOTENCY_KEY: str = "X-Idempotency-Key"
