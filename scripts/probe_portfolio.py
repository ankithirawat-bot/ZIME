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
    base = Path(tempfile.mkdtemp(prefix="zime_portfolio_probe_"))
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
    from frontend.views.portfolio import PortfolioView

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

    portfolio = stack.widget(3)
    if not isinstance(portfolio, PortfolioView):
        print(f"FAIL: page index 3 is {type(portfolio).__name__}, not PortfolioView")
        return 1
    print("PASS: Portfolio created")

    if portfolio.adapter is None:
        print("FAIL: portfolio adapter is None")
        return 1
    print("PASS: Portfolio adapter instantiated")

    summary_card = getattr(portfolio, "_summary_card", None)
    if summary_card is None:
        print("FAIL: summary card not found")
        return 1
    print("PASS: Summary cards rendered")

    holdings_table = getattr(portfolio, "_holdings_table", None)
    if holdings_table is None:
        print("FAIL: holdings table not found")
        return 1
    print("PASS: Holdings table rendered")

    sector_card = getattr(portfolio, "_sector_card", None)
    if sector_card is None:
        print("FAIL: sector allocation card not found")
        return 1
    print("PASS: Allocation rendered")

    perf_return = getattr(portfolio, "_return_label", None)
    if perf_return is None:
        print("FAIL: performance section not found")
        return 1
    print("PASS: Performance rendered")

    status_frame = getattr(portfolio, "_status_frame", None)
    if status_frame is None:
        print("FAIL: status panel not found")
        return 1
    print("PASS: Status rendered")

    view_model = portfolio.current_view_model()
    if view_model is None:
        print("FAIL: view model is None after initial load")
        return 1
    if view_model.holding_count == 0:
        print("FAIL: view model has zero holdings")
        return 1
    print("PASS: Portfolio loaded")

    try:
        refreshed = portfolio.refresh()
        application.processEvents()
    except Exception as exc:
        print(f"FAIL: refresh raised {exc!r}")
        return 1
    if refreshed is None:
        print("FAIL: refresh returned None")
        return 1
    if refreshed.holding_count == 0:
        print("FAIL: refreshed portfolio has zero holdings")
        return 1
    print("PASS: Refresh successful")

    if view_model.controller_status != "running":
        print(f"FAIL: controller status '{view_model.controller_status}' != 'running'")
        return 1
    if not controller.is_started:
        print("FAIL: controller.is_started is False")
        return 1
    print("PASS: Controller healthy")

    delivered: list[str] = []
    controller.event_bus.subscribe("probe.portfolio.bus", lambda n, p: delivered.append(n))
    n = controller.event_bus.publish("probe.portfolio.bus", payload={"ok": True})
    if n != 1 or delivered != ["probe.portfolio.bus"]:
        print(f"FAIL: event bus publish did not deliver ({delivered})")
        return 1
    controller.event_bus.unsubscribe("probe.portfolio.bus", delivered.append)
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
