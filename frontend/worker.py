from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal


class Worker(QObject):
    started = Signal()
    finished = Signal()
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, task: Callable[[Worker], Any] | None = None) -> None:
        super().__init__()
        self._task = task

    def run(self) -> None:
        self.started.emit()
        try:
            if self._task is not None:
                self._task(self)
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished.emit()

    def report_progress(self, value: int) -> None:
        try:
            value_int = int(value)
        except (TypeError, ValueError):
            return
        self.progress.emit(value_int)

    def report_error(self, message: str) -> None:
        self.error.emit(str(message))


class WorkerThread(QThread):
    worker_started = Signal()
    worker_finished = Signal()
    worker_progress = Signal(int)
    worker_error = Signal(str)

    def __init__(self, task: Callable[[Worker], Any] | None = None) -> None:
        super().__init__()
        self._worker = Worker(task=task)
        self._worker.moveToThread(self)

        self._worker.started.connect(self.worker_started.emit)
        self._worker.finished.connect(self.worker_finished.emit)
        self._worker.progress.connect(self.worker_progress.emit)
        self._worker.error.connect(self.worker_error.emit)
        self._worker.finished.connect(self._cleanup)

    def worker(self) -> Worker:
        return self._worker

    def _cleanup(self) -> None:
        self.quit()

    def run(self) -> None:
        self._worker.run()
