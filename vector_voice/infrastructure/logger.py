"""Logging configuration for Vector Voice."""
from __future__ import annotations

import logging
from pathlib import Path


_LOGGER_NAME = "vector_voice"
_configured = False


def setup_logger(log_dir: Path | None = None) -> logging.Logger:
    """Configure the root vector_voice logger. Safe to call multiple times.

    log_dir defaults to the project root, but is passed explicitly from
    bootstrap so we never rely on a hardcoded path.
    """
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)

    if _configured and logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove stale handlers (e.g. after reload in tests).
    for h in list(logger.handlers):
        logger.removeHandler(h)

    target_dir = log_dir or Path.cwd()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_file = target_dir / "vector_voice.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(stream_handler)

    _configured = True
    return logger


def get_logger(module_name: str) -> logging.Logger:
    return logging.getLogger(f"{_LOGGER_NAME}.{module_name}")