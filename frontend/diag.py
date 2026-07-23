"""Diagnostics presenter and registry."""

from __future__ import annotations

import PySide6

__pyqt_version__ = PySide6.__version__
from PySide6.QtCore import QSysInfo

from frontend.version import APP_NAME, BUILD_DATE, ORG_NAME, PLATFORM, PY_VERSION, VERSION

_DIAGNOSTICS: dict[str, str | None] = {}

def register_diagnostic(name: str, value: str | None) -> None:
    _DIAGNOSTICS[name] = value

def get_diagnostics_dict() -> dict[str, str]:
    return _DIAGNOSTICS.copy()

def reset():
    global _DIAGNOSTICS
    _DIAGNOSTICS = {}


register_diagnostic("Application", APP_NAME)
register_diagnostic("Version", VERSION)
register_diagnostic("Build Number", BUILD_DATE)
register_diagnostic("Organization", ORG_NAME)
register_diagnostic("Python Version", PY_VERSION)
register_diagnostic("Qt Version", QT_VERSION_STR)
register_diagnostic("OS", PLATFORM or QSysInfo.productType())
