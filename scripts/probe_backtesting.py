from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["PYTHONPATH"] = PROJECT_ROOT


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

    BT = type(window._pages[int(next(i for i, p in enumerate(window._pages) if type(p).__name__ == "BacktestingView"))])
    backtesting = stack.widget(4) if hasattr(stack, "widget") else next((w for w in window._pages if isinstance(w, BT)), None)
    if backtesting is None:
        print("FAIL: Backtesting page not found")
        return 1
    print("PASS: Backtesting created")

    if not hasattr(backtesting, "_controller") or backtesting._controller is None:
        print("FAIL: controller not set")
        return 1
    print("PASS: Adapter instantiated")

    ui = [
        ("Configuration", getattr(backtesting, "_config_row", None)),
        ("Summary", getattr(backtesting, "_summary_card", None)),
        ("Equity curve", getattr(backtesting, "_equity_widget", None)),
        ("Trades table", getattr(backtesting, "_trades_table", None)),
        ("Status", getattr(backtesting, "_status_row", None)),
    ]
    for label, widget in ui:
        if widget is None:
            print(f"FAIL: {label} not found")
            return 1
    print("PASS: Configuration rendered")
    print("PASS: Summary rendered")
    print("PASS: Equity curve rendered")
    print("PASS: Trades table rendered")
    print("PASS: Status rendered")

    if backtesting._controller.status != "running":
        print(f"FAIL: controller status '{backtesting._controller.status}' != 'running'")
        return 1
    print("PASS: Controller healthy")

    delivered: list[str] = []
    backtesting._controller.event_bus.subscribe("probe.backtesting.bus", lambda n, p: delivered.append(n))
    n = backtesting._controller.event_bus.publish("probe.backtesting.bus", payload={"ok": True})
    if n != 1 or delivered != ["probe.backtesting.bus"]:
        print(f"FAIL: event bus publish did not deliver ({delivered})")
        return 1
    backtesting._controller.event_bus.unsubscribe("probe.backtesting.bus", delivered.append)
    print("PASS: Event Bus healthy")

    try:
        from frontend.worker import WorkerThread  # noqa: PLC0415

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
