"""Configuración de logging centralizada."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config import settings

_CONFIGURED = False


def setup_logging(level: str | None = None) -> None:
    """Configura logging a consola y archivo rotativo (idempotente)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = (level or settings.LOG_LEVEL).upper()
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    formatter = logging.Formatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    log_file = settings.LOG_DIR / "apu_bolivia.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger con la configuración global aplicada."""
    setup_logging()
    return logging.getLogger(name)
