"""Reusable Qt widgets."""

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor, QTextOption
from PyQt5.QtWidgets import QFrame, QLabel, QSizePolicy, QTextEdit

from config import NORMAL_FONT_SIZE


class ClickableLabel(QLabel):
    """QLabel that emits `clicked` on a left click and swallows the event."""

    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class EditableTextEdit(QTextEdit):
    """QTextEdit styled like a centered label, used to edit user text.

    Signals:
        submitted   — Enter (without Shift) was pressed.
        user_edited — the user changed the text (not a programmatic update).
    """

    submitted = pyqtSignal()
    user_edited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._suppress_edit = False
        self._syncing = False

        self.setFrameStyle(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptRichText(False)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setTabChangesFocus(True)
        self.setFont(QFont("Arial", NORMAL_FONT_SIZE))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            "QTextEdit { color: #ffff00; background: transparent; border: none; }"
        )

        self.document().documentLayout().documentSizeChanged.connect(
            self._schedule_sync
        )
        self.textChanged.connect(self._on_text_changed)

    # -- public API -------------------------------------------------------

    def set_text(self, text: str, color: str = "#ffff00") -> None:
        """Replace the text without emitting ``user_edited``."""
        self._suppress_edit = True
        try:
            self.setStyleSheet(
                f"QTextEdit {{ color: {color}; background: transparent; "
                f"border: none; }}"
            )
            self.setPlainText(text)
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)
        finally:
            self._suppress_edit = False
        self._schedule_sync()

    def get_text(self) -> str:
        return self.toPlainText()

    # -- events -----------------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
                return
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_sync()

    # -- internals --------------------------------------------------------

    def _on_text_changed(self):
        if self._suppress_edit:
            return
        self.user_edited.emit()

    def _schedule_sync(self, *_):
        if self._syncing:
            return
        QTimer.singleShot(0, self._sync_height)

    def _sync_height(self):
        """Auto-grow the widget to fit its content (used with vbox stretches)."""
        if self._syncing:
            return
        self._syncing = True
        try:
            doc = self.document()
            doc.setTextWidth(self.viewport().width())
            target = int(doc.size().height()) + 4
            if abs(target - self.height()) > 1:
                self.setFixedHeight(target)
        finally:
            self._syncing = False