from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)


def _build_temp_dirs() -> tuple[Path, Path]:
    base = Path(tempfile.mkdtemp(prefix="zime_probe_"))
    cfg_dir = base / "config"
    logs_dir = base / "logs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "desktop.json", logs_dir / "zime.log"


def _read_card_rows(card: object) -> dict[str, str]:
    from PySide6.QtWidgets import QLabel

    keys = card.findChildren(QLabel, "cardRowKey")
    values = card.findChildren(QLabel, "cardRowValue")
    pairs: dict[str, str] = {}
    for key_label, value_label in zip(keys, values, strict=False):
        pairs[key_label.text()] = value_label.text()
    return pairs


def _run() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication(sys.argv)

    config_path, log_path = _build_temp_dirs()

    from frontend.app import build_application, run_application
    from frontend.controller import ApplicationController

    controller = ApplicationController(
        config_path=config_path,
        log_path=log_path,
    )
    controller.startup()

    application = build_application(sys.argv, controller=controller)
    window = run_application(application, controller)
    window.show()

    QTimer.singleShot(0, lambda: None)
    application.processEvents()

    if window is None or window.windowTitle() != "ZIME":
        print("FAIL: Dashboard window missing or wrong title")
        return 1

    central = window.centralWidget()

    from PySide6.QtWidgets import QStackedWidget
    stack = central.findChild(QStackedWidget, "contentStack")
    if stack is None:
        print("FAIL: content stack not found")
        return 1

    from frontend.views.dashboard import DashboardView

    dashboard = stack.widget(0)
    if not isinstance(dashboard, DashboardView):
        print("FAIL: dashboard page is not DashboardView")
        return 1
    print("PASS: Dashboard created")

    summary = dashboard.refresh()
    application.processEvents()

    expected_titles = ("Application", "System", "Status", "Recent Activity")

    cards = {
        "Application": dashboard._application_card,  # noqa: SLF001
        "System": dashboard._system_card,  # noqa: SLF001
        "Status": dashboard._status_card,  # noqa: SLF001
        "Recent Activity": dashboard._recent_card,  # noqa: SLF001
    }
    card_objects = list(cards.values())
    titles_present = [c.property("cardTitle") for c in card_objects]
    if tuple(titles_present) != expected_titles:
        print(f"FAIL: card titles == {titles_present}")
        return 1
    if not all(card_objects):
        print("FAIL: not all cards created")
        return 1
    print("PASS: Cards rendered")

    adapter = dashboard._adapter  # noqa: SLF001
    if adapter is None:
        print("FAIL: adapter not instantiated")
        return 1
    print("PASS: Dashboard adapter instantiated")

    app_rows = _read_card_rows(dashboard._application_card)  # noqa: SLF001
    sys_rows = _read_card_rows(dashboard._system_card)  # noqa: SLF001
    status_rows = _read_card_rows(dashboard._status_card)  # noqa: SLF001
    recent_rows = _read_card_rows(dashboard._recent_card)  # noqa: SLF001

    if not app_rows.get("Version"):
        print(f"FAIL: Application Version empty ({app_rows})")
        return 1
    py_version = sys_rows.get("Python Version", "")
    if not py_version:
        print("FAIL: Python Version empty")
        return 1
    print("PASS: Application Version + Python Version populated")

    theme = sys_rows.get("Theme", "")
    if not theme:
        print("FAIL: Theme empty")
        return 1
    if not summary.window_size or summary.window_size[0] <= 0 or summary.window_size[1] <= 0:
        print(f"FAIL: Window size invalid ({summary.window_size})")
        return 1
    print("PASS: Theme + Window Size populated")

    controller_status = status_rows.get("Controller", "")
    event_bus = status_rows.get("Event Bus", "")
    worker = status_rows.get("Worker", "")
    logging_status = status_rows.get("Logging", "")
    if controller_status not in ("running", "stopped"):
        print(f"FAIL: Controller status '{controller_status}' not in expected set")
        return 1
    if event_bus != "available":
        print(f"FAIL: Event Bus '{event_bus}' != 'available'")
        return 1
    if worker != "available":
        print(f"FAIL: Worker '{worker}' != 'available'")
        return 1
    if logging_status not in ("configured", "not_configured"):
        print(f"FAIL: Logging status '{logging_status}' invalid")
        return 1
    print("PASS: Controller healthy, Event Bus + Worker available, Logging enabled")

    last_start = recent_rows.get("Last Start", "")
    log_file = recent_rows.get("Log File", "")
    if not last_start or last_start == "n/a":
        print(f"FAIL: Last start not populated ({last_start})")
        return 1
    if not log_file:
        print("FAIL: Log file path empty")
        return 1
    print("PASS: Adapter populated")

    try:
        dashboard.refresh()
        application.processEvents()
        print("PASS: Refresh successful")
    except Exception as exc:
        print(f"FAIL: Refresh raised {exc!r}")
        return 1

    try:
        controller.shutdown()
    except Exception:
        pass
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
