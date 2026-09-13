"""Logging configuration for Vector Voice."""
from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logger(name: str = "vector_voice") -> logging.Logger:
    """Create and configure logger for Vector Voice.

    Logs are written to vector_voice.log in the project root.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # File handler - logs to project root
    project_root = Path(__file__).resolve().parent.parent.parent
    log_file = project_root / "vector_voice.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # Format: timestamp | level | module | message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """Get a logger for the specified module."""
    return logging.getLogger(f"vector_voice.{module_name}")
