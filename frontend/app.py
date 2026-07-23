from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from frontend.controller import ApplicationController
from frontend.main_window import MainWindow

STYLES_DIR = Path(__file__).resolve().parent / "styles"
DEFAULT_THEME = "dark"


def _load_stylesheet(theme: str) -> str:
    qss_path = STYLES_DIR / f"{theme}.qss"
    if not qss_path.exists():
        return ""
    return qss_path.read_text(encoding="utf-8")


def build_application(argv: list[str], controller: ApplicationController | None = None) -> QApplication:
    application = QApplication.instance() or QApplication(argv)
    application.setApplicationName("ZIME")
    application.setOrganizationName("ZIME")
    theme = DEFAULT_THEME
    if controller is not None:
        theme = controller.settings.ensure_loaded().theme or theme
    stylesheet = _load_stylesheet(theme)
    if stylesheet:
        application.setStyleSheet(stylesheet)
    return application


def run_application(
    application: QApplication,
    controller: ApplicationController,
) -> MainWindow:
    last_page = controller.settings.ensure_loaded().last_opened_page
    window = MainWindow(application=application, controller=controller)
    window.show()
    window.restore_desktop_state(last_page=last_page)
    return window
