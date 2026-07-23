from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APPLICATION_LOG_NAME = "zime"
LOG_RELATIVE_PATH = Path("logs") / "zime.log"
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s :: %(message)s"


_RESERVED_LOG_NAMES: frozenset[str] = frozenset(
    {"", "root", "main", "__main__"},
)


class _ExceptionHookHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.formatter.format(record) if self.formatter else None
            exc_text = getattr(record, "exc_text", None) or self.format(record)
            sys.stderr.write(exc_text)
            sys.stderr.write("\n")
            sys.stderr.flush()
        except Exception:
            pass


def _resolve_log_path(log_path: Path | str | None) -> Path:
    path = Path(log_path) if isinstance(log_path, str) else log_path
    if path is None or str(path) == "":
        project_root = Path(__file__).resolve().parents[1]
        path = project_root / LOG_RELATIVE_PATH
    path = path if isinstance(path, Path) else Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def configure_logging(
    log_path: Path | None = None,
    *,
    level: int = logging.INFO,
    console: bool = False,
) -> logging.Logger:
    """Configure the application-wide rotating-file logger.

    Idempotent: calling multiple times returns the same logger without adding
    duplicate handlers.
    """
    log_path = _resolve_log_path(log_path)
    logger = logging.getLogger(APPLICATION_LOG_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if not any(
        isinstance(h, RotatingFileHandler)
        and getattr(h, "baseFilename", "") == str(log_path)
        for h in logger.handlers
    ):
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(file_handler)

    if console and not any(
        isinstance(h, logging.StreamHandler)
        and getattr(h, "_zime_console_marker", False)
        for h in logger.handlers
    ):
        console_handler = logging.StreamHandler(stream=sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        console_handler._zime_console_marker = True  # type: ignore[attr-defined]
        logger.addHandler(console_handler)

    return logger


def install_excepthook(logger: logging.Logger | None = None) -> logging.Logger | None:
    """Install a global sys.excepthook that pipes unhandled exceptions to the logger."""
    target_logger = logger or logging.getLogger(APPLICATION_LOG_NAME)

    def _hook(exc_type, exc_value, exc_traceback) -> None:
        try:
            target_logger.error(
                "Unhandled exception",
                exc_info=(exc_type, exc_value, exc_traceback),
            )
        finally:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _hook
    return target_logger


def get_logger(name: str | None = None) -> logging.Logger:
    base = name or APPLICATION_LOG_NAME
    if base in _RESERVED_LOG_NAMES:
        return logging.getLogger(APPLICATION_LOG_NAME)
    if base == APPLICATION_LOG_NAME:
        return logging.getLogger(APPLICATION_LOG_NAME)
    if base.startswith(APPLICATION_LOG_NAME + "."):
        return logging.getLogger(base)
    return logging.getLogger(f"{APPLICATION_LOG_NAME}.{base}")
