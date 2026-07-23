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
    base = Path(tempfile.mkdtemp(prefix="zime_intelligence_probe_"))
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
    from frontend.views.intelligence import IntelligenceView

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

    intelligence = stack.widget(5)
    if not isinstance(intelligence, IntelligenceView):
        print(f"FAIL: page index 5 is {type(intelligence).__name__}, not IntelligenceView")
        return 1
    print("PASS: Intelligence created")

    if intelligence.adapter is None:
        print("FAIL: intelligence adapter is None")
        return 1
    print("PASS: Intelligence adapter instantiated")

    summary_frame = getattr(intelligence, "_summary_frame", None)
    if summary_frame is None:
        print("FAIL: executive summary not found")
        return 1
    print("PASS: Executive summary rendered")

    rec_container = getattr(intelligence, "_rec_container", None)
    if rec_container is None:
        print("FAIL: recommendation cards not found")
        return 1
    print("PASS: Recommendation cards rendered")

    signal_table = getattr(intelligence, "_signal_table", None)
    if signal_table is None:
        print("FAIL: signals table not found")
        return 1
    print("PASS: Signals table rendered")

    market_health_card = getattr(intelligence, "_market_health_card", None)
    if market_health_card is None:
        print("FAIL: market health card not found")
        return 1
    print("PASS: Market health rendered")

    insights_container = getattr(intelligence, "_insights_container", None)
    if insights_container is None:
        print("FAIL: insights container not found")
        return 1
    print("PASS: Insights rendered")

    status_frame = getattr(intelligence, "_status_frame", None)
    if status_frame is None:
        print("FAIL: status panel not found")
        return 1
    print("PASS: Status rendered")

    view_model = intelligence.current_view_model()
    if view_model is None:
        print("FAIL: view model is None after initial load")
        return 1
    if view_model.recommendation_count == 0:
        print("FAIL: view model has zero recommendations")
        return 1
    print("PASS: Recommendations loaded")

    try:
        refreshed = intelligence.refresh()
        application.processEvents()
    except Exception as exc:
        print(f"FAIL: refresh raised {exc!r}")
        return 1
    if refreshed is None:
        print("FAIL: refresh returned None")
        return 1
    if refreshed.recommendation_count == 0:
        print("FAIL: refreshed intelligence has zero recommendations")
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
    controller.event_bus.subscribe("probe.intelligence.bus", lambda n, p: delivered.append(n))
    n = controller.event_bus.publish("probe.intelligence.bus", payload={"ok": True})
    if n != 1 or delivered != ["probe.intelligence.bus"]:
        print(f"FAIL: event bus publish did not deliver ({delivered})")
        return 1
    controller.event_bus.unsubscribe("probe.intelligence.bus", delivered.append)
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
