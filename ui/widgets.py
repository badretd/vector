"""Reusable Qt widgets."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel


class ClickableLabel(QLabel):
    """QLabel that emits `clicked` on a left click and swallows the event."""

    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)