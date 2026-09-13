"""Qt implementation of the SetupView protocol."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox


class QtSetupView:
    """Wraps QMessageBox/QInputDialog into the small SetupView surface."""

    def choose_language(self, default: str) -> str | None:
        box = QMessageBox()
        box.setWindowTitle("Language / Язык")
        box.setText("Choose interface language:\nВыберите язык интерфейса:")
        ru_btn = box.addButton("Русский", QMessageBox.AcceptRole)
        en_btn = box.addButton("English", QMessageBox.AcceptRole)
        box.setDefaultButton(en_btn if default != "ru" else ru_btn)
        box.exec_()
        clicked = box.clickedButton()
        if clicked is ru_btn:
            return "ru"
        if clicked is en_btn:
            return "en"
        return None

    def show_message(self, title: str, message: str) -> None:
        QMessageBox.information(None, title, message)

    def show_error(self, title: str, message: str) -> None:
        QMessageBox.warning(None, title, message)

    def confirm(self, title: str, message: str) -> bool:
        reply = QMessageBox.question(
            None, title, message, QMessageBox.Yes | QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def choose_item(
        self, title: str, prompt: str, items: list[str], default_index: int
    ) -> str | None:
        choice, ok = QInputDialog.getItem(
            None, title, prompt, items, default_index, False
        )
        return choice if ok else None

    def ask_remember_mic(self, title: str, message: str, yes: str, no: str) -> bool:
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setText(message)
        yes_btn = box.addButton(yes, QMessageBox.AcceptRole)
        box.addButton(no, QMessageBox.RejectRole)
        box.exec_()
        return box.clickedButton() is yes_btn


def install_vosk_model_with_progress(vosk_installer, archive: str, target: str) -> None:
    """Helper that shows a wait cursor while extracting the model."""
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        vosk_installer.install(archive, target)
    finally:
        QApplication.restoreOverrideCursor()