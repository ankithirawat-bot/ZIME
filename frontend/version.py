"""Application version and metadata module.

Never store version strings directly elsewhere.
"""

import platform
import sys
from datetime import datetime

APP_NAME = "ZIME"
ORG_NAME = "ZIME Technologies"

VERSION = "1.0.0"
BUILD = "RC1"
BUILD_DATE = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
COPYRIGHT = f"© 2021-{datetime.utcnow().year} {ORG_NAME}. All rights reserved."
PLATFORM = platform.system()
PY_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
