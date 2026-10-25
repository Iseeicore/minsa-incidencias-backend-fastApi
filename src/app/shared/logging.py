import logging
from typing import Any

import structlog

from app.enums.log_level import LogLevel

LEVEL_BY_NAME: dict[LogLevel, int] = {
    LogLevel.FATAL: logging.CRITICAL,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.WARN: logging.WARNING,
    LogLevel.INFO: logging.INFO,
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.TRACE: logging.DEBUG,
    LogLevel.SILENT: logging.CRITICAL,
}


def _drop_everything(_logger: Any, _method: str, _event: Any) -> Any:  # noqa: ANN401
    raise structlog.DropEvent


def configure_logging(level: LogLevel | str) -> None:
    log_level = LogLevel(level)
    numeric_level = LEVEL_BY_NAME[log_level]
    logging.basicConfig(level=numeric_level, format="%(message)s")
    structlog.configure(
        processors=[
            *([_drop_everything] if log_level is LogLevel.SILENT else []),
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        cache_logger_on_first_use=False,
    )
