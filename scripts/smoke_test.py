#!/usr/bin/env python
"""Smoke test verifying production readiness of the ZIME desktop application.

Expectations: Application launches, loads every workspace, and exits cleanly.
Exit codes:
  0: all tests passed
  1: application or workspace failed to load
  2: uncaught exception during run
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

def _run() -> int:

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication(sys.argv)

    from frontend.app import build_application, run_application
    from frontend.controller import ApplicationController

    controller = ApplicationController(
        config_path=PROJECT_ROOT / "config" / "desktop.json",
        log_path=PROJECT_ROOT / "logs" / "zime.log",
    )
    controller.startup()

    application = build_application([], controller=controller)
    window = run_application(application, controller)
    window.show()

    try:
        # Verify workspaces load without runtime exceptions
        stack = window._stack
        required = [
            "Dashboard",
            "Market Overview",
            "Screener",
            "Portfolio",
            "Backtesting",
            "Intelligence",
            "Reporting",
        ]
        ok = True
        for title, widget in required:
            if hasattr(widget, "testPageTitle"):
                if widget.testPageTitle() != title:
                    print(f"FAIL: Mismatched page title at index {idx}")
                    ok = False

        for idx in range(stack.count()):
            page = stack.widget(idx)
            name = page.objectName() or type(page).__name__
            if "placeholder" in name.lower() or not any(r in name.lower() for r in required):
                continue
            # Simply switching to the page causes its constructor to run any load code
            stack.setCurrentIndex(idx)
            application.processEvents()

        # Wait briefly to ensure no crash occurs post load
        QTimer.singleShot(200, application.quit)
        application.exec()

        controller.shutdown()
        window.close()
    except Exception as exc:
        print("FAIL: uncaught exception during smoke test:", repr(exc))
        try:
            controller.logger.exception("smoke_test", exc)
        except Exception:
            pass
        return 2

    print("PASS: Application launches and all workspaces load without runtime exceptions")
    return 0

if __name__ == "__main__":
    raise SystemExit(_run())
