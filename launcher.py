from __future__ import annotations

import atexit
import sys

from frontend.app import build_application, run_application
from frontend.controller import ApplicationController


def main() -> int:
    controller = ApplicationController()
    controller.startup()

    application = build_application(sys.argv, controller=controller)
    window = run_application(application, controller)
    window.show()

    def _shutdown() -> None:
        try:
            controller.shutdown()
        except Exception:
            pass

    atexit.register(_shutdown)

    def _on_quit() -> None:
        _shutdown()

    try:
        application.aboutToQuit.connect(_on_quit)
    except Exception:
        pass

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
