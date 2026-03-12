from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from backend.config.settings import _settings


DEFAULT_LOG_EXTRA = {
    "service": "-",
    "request_id": "-",
    "user_id": "-",
}

CONSOLE_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>service={extra[service]}</cyan> "
    "<magenta>request_id={extra[request_id]}</magenta> "
    "<yellow>user_id={extra[user_id]}</yellow> | "
    "<blue>{name}:{function}:{line}</blue> | "
    "<level>{message}</level>"
)


def configure_logging() -> None:
    """Configure Loguru sinks and default extra fields for bound log records."""

    log_file = Path(_settings.logging.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.configure(extra=DEFAULT_LOG_EXTRA)

    logger.add(
        sys.stdout,
        level=_settings.logging.log_level,
        format=CONSOLE_LOG_FORMAT,
        colorize=True,
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        log_file,
        level=_settings.logging.log_level,
        format=_settings.logging.log_format,
        backtrace=False,
        diagnose=False,
        encoding="utf-8",
    )
