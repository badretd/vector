"""Qt application bootstrap helper."""
from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication


def create_application(argv: list[str] | None = None) -> QApplication:
    return QApplication(argv if argv is not None else sys.argv)