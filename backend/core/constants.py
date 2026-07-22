"""
Shared constants used across multiple engines.

Only constants referenced by two or more engines are placed here.
Engine-specific constants remain in their respective modules.
"""

# Maximum number of items in reasons/warnings lists
MAX_ITEMS: int = 15

# Maximum risk per trade (percent of capital)
DEFAULT_MAX_RISK: float = 1.0

# Minimum acceptable risk/reward ratio
MIN_RR_ACCEPTABLE: float = 2.0

# Default confidence when none is computed
DEFAULT_CONFIDENCE: float = 50.0

# ======================= Exchange & Market Defaults =======================

DEFAULT_EXCHANGE: str = "NSE"
DEFAULT_INSTRUMENT_TYPE: str = "EQ"

# ======================= Numeric Thresholds =======================

DEFAULT_INITIAL_CAPITAL: float = 1_000_000.0
DEFAULT_MAX_ITERATIONS: int = 1000
DEFAULT_TOLERANCE: float = 1e-8
DEFAULT_MAX_POSITIONS: int = 50
DEFAULT_MIN_POSITIONS: int = 5
DEFAULT_MAX_POSITION_SIZE: float = 0.25
DEFAULT_MIN_POSITION_SIZE: float = 0.01
DEFAULT_MAX_VOLATILITY: float = 0.25
DEFAULT_CONFIDENCE_LEVEL: float = 0.95

# ======================= Solver Name Strings (shared across optimization) =======================

SOLVER_QUADRATIC: str = "quadratic"
SOLVER_GRADIENT: str = "gradient"
SOLVER_GREEDY: str = "greedy"
SOLVER_COORDINATE: str = "coordinate"
SOLVER_HEURISTIC: str = "heuristic"

# ======================= Status Strings =======================

STATUS_SUCCESS: str = "success"
STATUS_FAILED: str = "failed"
STATUS_PARTIAL: str = "partial"
STATUS_PENDING: str = "pending"
STATUS_SKIPPED: str = "skipped"
STATUS_CANCELLED: str = "cancelled"
STATUS_RUNNING: str = "running"
STATUS_COMPLETED: str = "completed"
STATUS_OPTIMAL: str = "OPTIMAL"
STATUS_INFEASIBLE: str = "INFEASIBLE"
STATUS_UNKNOWN: str = "UNKNOWN"

# ======================= Date/Time Format Strings =======================

DATE_FORMAT_YMD: str = "%Y-%m-%d"
DATE_FORMAT_YM: str = "%Y-%m"
DATE_FORMAT_Y: str = "%Y"
DATE_FORMAT_COMPACT: str = "%Y%m%d%H%M%S"
DATETIME_FORMAT_ISO: str = "%Y-%m-%dT%H:%M:%S"
DATETIME_FORMAT_FULL: str = "%Y-%m-%d %H:%M:%S"

# ======================= Risk & Financial Constants =======================

RISK_FREE_RATE_BACKTESTING: float = 0.06
RISK_FREE_RATE_OPTIMIZATION: float = 0.02
RISK_FREE_RATE_INTELLIGENCE: float = 0.0

CURRENCY_INR: str = "INR"
CURRENCY_USD: str = "USD"

BENCHMARK_NIFTY50: str = "NIFTY50"
BENCHMARK_SPX: str = "SPX"

# ======================= Data Period/Interval Defaults =======================

DEFAULT_DATA_PERIOD: str = "1y"
DEFAULT_DATA_INTERVAL: str = "1d"

# ======================= Python & System Constants =======================

DB_HOST_DEFAULT: str = "localhost"
DB_PORT_DEFAULT: int = 5432
DB_NAME_DEFAULT: str = "zime"
DB_USER_DEFAULT: str = "zime"
DB_POOL_SIZE_DEFAULT: int = 5
DB_MAX_OVERFLOW_DEFAULT: int = 10

# ======================= Logging Event Names =======================

EVENT_STARTUP: str = "application.startup"
EVENT_SHUTDOWN: str = "application.shutdown"
EVENT_ORDER_SUBMITTED: str = "order.submitted"
EVENT_ORDER_FILLED: str = "order.filled"
EVENT_ORDER_CANCELLED: str = "order.cancelled"
EVENT_ORDER_REJECTED: str = "order.rejected"
EVENT_TRADE_EXECUTED: str = "trade.executed"
EVENT_ERROR: str = "application.error"
EVENT_HEALTH_CHECK: str = "health.check"
EVENT_SYNC_STARTED: str = "sync.started"
EVENT_SYNC_COMPLETED: str = "sync.completed"

# ======================= Pipeline Stage Names =======================

STAGE_FETCH: str = "fetch"
STAGE_VALIDATE: str = "validate"
STAGE_NORMALIZE: str = "normalize"
STAGE_CORPORATE_ACTION: str = "corporate_action"
STAGE_DATA_QUALITY: str = "data_quality"
STAGE_PERSIST: str = "persist"
STAGE_REPORT: str = "report"

# ======================= Retry Configuration Defaults =======================

RETRY_MAX_ATTEMPTS: int = 3
RETRY_BASE_DELAY: float = 1.0
RETRY_BACKOFF_FACTOR: float = 2.0
RETRY_MAX_DELAY: float = 30.0

ORCHESTRATION_RETRY_MAX_ATTEMPTS: int = 1
