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
