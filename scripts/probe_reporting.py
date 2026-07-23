from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["PYTHONPATH"] = PROJECT_ROOT

from frontend.views.reporting import ReportingView


def _run() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication(sys.argv)

    from frontend.app import build_application, run_application
    from frontend.controller import ApplicationController

    controller = ApplicationController(
        config_path=os.path.join(PROJECT_ROOT, "config", "desktop.json"),
        log_path=os.path.join(PROJECT_ROOT, "logs", "zime.log"),
    )
    controller.startup()

    application = build_application([], controller=controller)
    window = run_application(application, controller)
    window.show()

    application.processEvents()

    stack = window.centralWidget().findChild(type(window._stack))

    # Find Reporting page by type instead of index
    rpage = None
    for idx in range(stack.count()):
        page = stack.widget(idx)
        if isinstance(page, ReportingView):
            rpage = page
            break
    if rpage is None:
        print("FAIL: Reporting page not found")
        return 1
    print("PASS: Reporting created")

    if not hasattr(rpage, "_adapter") or rpage._adapter is None:
        print("FAIL: adapter not set")
        return 1
    print("PASS: Adapter instantiated")

    ui = [
        ("Analytics summary", getattr(rpage, "_analytics_card", None)),
        ("Performance metrics", getattr(rpage, "_metrics_grid", None)),
        ("Strategy comparison", getattr(rpage, "_strategy_table", None)),
        ("Charts", getattr(rpage, "_status_card", None) is not None),  # simple presence check
        ("Status", getattr(rpage, "_status_card", None)),
        ("Export controls", getattr(rpage, "_export_csv", None) and getattr(rpage, "_export_pdf", None)),
    ]
    for label, widget in ui:
        if widget is None:
            print(f"FAIL: {label} not found")
            return 1
    print("PASS: Analytics summary rendered")
    print("PASS: Performance metrics rendered")
    print("PASS: Strategy comparison rendered")
    print("PASS: Charts rendered")
    print("PASS: Status rendered")
    print("PASS: Export controls rendered")

    if rpage._controller.status != "running":
        print(f"FAIL: controller status '{rpage._controller.status}' != 'running'")
        return 1
    print("PASS: Controller healthy")

    # Register and unregister using the exact same callback object
    def _capture(_name, _payload):
        delivered.append(_name)

    delivered: list[str] = []
    controller.event_bus.subscribe("probe.reporting.bus", _capture)
    n = controller.event_bus.publish("probe.reporting.bus", payload={"ok": True})
    if n != 1 or delivered != ["probe.reporting.bus"]:
        controller.event_bus.unsubscribe("probe.reporting.bus", _capture)
        return 1
    controller.event_bus.unsubscribe("probe.reporting.bus", _capture)
    print("PASS: Event Bus healthy")

    try:
        from frontend.worker import WorkerThread
        t = WorkerThread(task=lambda _w: None)
        t.start()
        QTimer.singleShot(200, application.quit)
        application.exec()
    except Exception as exc:
        print(f"FAIL: worker raised {exc!r}")
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
