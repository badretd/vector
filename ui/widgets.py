"""Reusable Qt widgets."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QLabel


class ClickableLabel(QLabel):
    """QLabel that emits `clicked` on any mouse press."""

    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)