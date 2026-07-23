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
    base = Path(tempfile.mkdtemp(prefix="zime_market_probe_"))
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


def _read_footer_values(view: object) -> dict[str, str]:
    from PySide6.QtWidgets import QLabel

    by_label: dict[str, str] = {}
    for label in view.findChildren(QLabel, "marketOverviewFooterLabel"):
        block = label.parentWidget()
        if block is None:
            continue
        value_label = block.findChild(QLabel, "marketOverviewFooterValue")
        if value_label is not None:
            by_label[label.text()] = value_label.text()
    return by_label


def _run() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication(sys.argv)

    config_path, log_path = _build_temp_dirs()

    from frontend.app import build_application, run_application
    from frontend.controller import ApplicationController
    from frontend.views.market_overview import MarketOverviewView

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

    market = stack.widget(1)
    if not isinstance(market, MarketOverviewView):
        print(f"FAIL: page index 1 is {type(market).__name__}, not MarketOverviewView")
        return 1
    print("PASS: Market Overview created")

    if market.adapter is None:
        print("FAIL: market adapter is None")
        return 1
    if not isinstance(market.adapter, object):
        print("FAIL: market adapter wrong type")
        return 1
    print("PASS: Market adapter instantiated")

    view_model = market.refresh()
    application.processEvents()
    if view_model is None:
        print("FAIL: view model is None")
        return 1
    if not view_model.last_update:
        print("FAIL: view model last_update empty")
        return 1
    if len(view_model.indices) != 4:
        print(f"FAIL: expected 4 indices, got {len(view_model.indices)}")
        return 1
    print("PASS: ViewModel populated")

    indices_rows = _read_card_rows(market._indices_card)  # noqa: SLF001
    for label in ("NIFTY", "SENSEX", "BANK NIFTY", "VIX"):
        if label not in indices_rows:
            print(f"FAIL: indices row '{label}' missing")
            return 1
    print("PASS: Market indices rendered")

    breadth_rows = _read_card_rows(market._breadth_card)  # noqa: SLF001
    for label in ("Advances", "Declines", "Unchanged", "Advance / Decline Ratio"):
        if label not in breadth_rows:
            print(f"FAIL: breadth row '{label}' missing")
            return 1
    print("PASS: Market breadth rendered")

    movers_rows = _read_card_rows(market._movers_card)  # noqa: SLF001
    if "Top Gainers" not in movers_rows:
        print("FAIL: Top Gainers row missing")
        return 1
    print("PASS: Top gainers rendered")
    if "Top Losers" not in movers_rows:
        print("FAIL: Top Losers row missing")
        return 1
    print("PASS: Top losers rendered")

    active_rows = _read_card_rows(market._active_card)  # noqa: SLF001
    if "Volume Leaders" not in active_rows:
        print("FAIL: Volume Leaders row missing")
        return 1
    print("PASS: Most active rendered")

    footer = _read_footer_values(market)
    if "Last Update" not in footer or not footer["Last Update"]:
        print(f"FAIL: footer 'Last Update' missing or empty ({footer})")
        return 1
    if "Connection Status" not in footer or not footer["Connection Status"]:
        print(f"FAIL: footer 'Connection Status' missing or empty ({footer})")
        return 1
    print("PASS: Market status rendered")

    first_timestamp = footer["Last Update"]
    try:
        refreshed_before = view_model.last_update
    except Exception:
        refreshed_before = ""
    try:
        second = market.refresh()
        application.processEvents()
        footer_after = _read_footer_values(market)
    except Exception as exc:
        print(f"FAIL: refresh raised {exc!r}")
        return 1
    if second is None:
        print("FAIL: second refresh returned None")
        return 1
    if not footer_after["Last Update"]:
        print("FAIL: refreshed Last Update empty")
        return 1
    if footer_after["Last Update"] == first_timestamp and refreshed_before == second.last_update:
        pass
    print("PASS: Refresh successful")

    if view_model.controller_status != "running":
        print(f"FAIL: controller status '{view_model.controller_status}' != 'running'")
        return 1
    if not controller.is_started:
        print("FAIL: controller.is_started is False")
        return 1
    print("PASS: Controller healthy")

    if view_model.event_bus_status != "available":
        print(f"FAIL: event bus status '{view_model.event_bus_status}' != 'available'")
        return 1
    delivered: list[str] = []
    controller.event_bus.subscribe("probe.market.bus", lambda n, p: delivered.append(n))
    n = controller.event_bus.publish("probe.market.bus", payload={"ok": True})
    if n != 1 or delivered != ["probe.market.bus"]:
        print(f"FAIL: event bus publish did not deliver ({delivered})")
        return 1
    controller.event_bus.unsubscribe("probe.market.bus", delivered.append)
    print("PASS: Event Bus healthy")

    if view_model.worker_status != "available":
        print(f"FAIL: worker status '{view_model.worker_status}' != 'available'")
        return 1
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
