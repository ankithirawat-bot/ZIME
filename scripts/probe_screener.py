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
    base = Path(tempfile.mkdtemp(prefix="zime_screener_probe_"))
    cfg_dir = base / "config"
    logs_dir = base / "logs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "desktop.json", logs_dir / "zime.log"


def _run() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication(sys.argv)

    config_path, log_path = _build_temp_dirs()

    from frontend.app import build_application, run_application
    from frontend.controller import ApplicationController
    from frontend.views.screener import ScreenerView

    controller = ApplicationController(
        config_path=config_path,
        log_path=log_path,
    )
    controller.startup()

    application = build_application(sys.argv, controller=controller)
    window = run_application(application, controller)
    window.show()

    application.processEvents()

    central = window.centralWidget()
    from PySide6.QtWidgets import QStackedWidget

    stack = central.findChild(QStackedWidget, "contentStack")
    if stack is None:
        print("FAIL: content stack not found")
        return 1

    screener = stack.widget(2)
    if not isinstance(screener, ScreenerView):
        print(f"FAIL: page index 2 is {type(screener).__name__}, not ScreenerView")
        return 1
    print("PASS: Screener created")

    if screener.adapter is None:
        print("FAIL: screener adapter is None")
        return 1
    print("PASS: Screener adapter instantiated")

    filter_frame = getattr(screener, "_filter_frame", None)
    if filter_frame is None:
        print("FAIL: filter panel not found")
        return 1
    print("PASS: Filter panel rendered")

    results_table = getattr(screener, "_results_table", None)
    if results_table is None:
        print("FAIL: results table not found")
        return 1
    print("PASS: Results table rendered")

    run_button = getattr(screener, "run_button", None)
    if run_button is None:
        print("FAIL: Run Screen button not found")
        return 1
    print("PASS: Run Screen available")

    status_frame = getattr(screener, "_status_frame", None)
    if status_frame is None:
        print("FAIL: status panel not found")
        return 1
    print("PASS: Status rendered")

    view_model = screener.refresh()
    application.processEvents()

    adapter = screener.adapter
    execute_result = adapter.execute()
    application.processEvents()
    if execute_result is None:
        print("FAIL: execute result is None")
        return 1
    print("PASS: Screen execution started")

    if execute_result.result_count() == 0:
        print("FAIL: execute returned zero results")
        return 1
    print("PASS: Results populated")

    if execute_result.status.state != "completed":
        print(f"FAIL: screen state '{execute_result.status.state}' != 'completed'")
        return 1
    print("PASS: Screen completed")

    if view_model.status.controller_status != "running":
        print(f"FAIL: controller status '{view_model.status.controller_status}' != 'running'")
        return 1
    if not controller.is_started:
        print("FAIL: controller.is_started is False")
        return 1
    print("PASS: Controller healthy")

    delivered: list[str] = []
    controller.event_bus.subscribe("probe.screener.bus", lambda n, p: delivered.append(n))
    n = controller.event_bus.publish("probe.screener.bus", payload={"ok": True})
    if n != 1 or delivered != ["probe.screener.bus"]:
        print(f"FAIL: event bus publish did not deliver ({delivered})")
        return 1
    controller.event_bus.unsubscribe("probe.screener.bus", delivered.append)
    print("PASS: Event Bus healthy")

    try:
        from frontend.worker import WorkerThread  # noqa: PLC0415

        t = WorkerThread(task=lambda _w: None)
        t.start()
        QTimer.singleShot(200, application.quit)
        application.exec()
    except Exception as exc:
        print(f"FAIL: worker construction/exec raised {exc!r}")
        return 1
    print("PASS: Worker available")

    try:
        controller.shutdown()
    except Exception:
        pass
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
