"""Main window: centered avatar, bottom text, top-left mic icon, top-right menu."""
from __future__ import annotations

from typing import Callable

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from vector_voice.domain.ports import AssetRepositoryPort, TranslationServicePort
from vector_voice.presentation.qt.avatar_widget import SpriteAvatarWidget
from vector_voice.presentation.qt.controller import MainWindowController
from vector_voice.presentation.qt.theme import QtThemeManager
from vector_voice.presentation.qt.viewmodel import MainViewModel
from vector_voice.presentation.qt.widgets import ClickableLabel, EditableTextEdit

PLACEHOLDER_TEXT = "Vector 0.2 alpha"


class VoiceWindow(QWidget):
    def __init__(
        self,
        view_model: MainViewModel,
        controller: MainWindowController,
        assets: AssetRepositoryPort,
        translator: TranslationServicePort,
        theme: QtThemeManager,
        open_settings: Callable[[QWidget], None],
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._controller = controller
        self._assets = assets
        self._i18n = translator
        self._theme = theme
        self._open_settings = open_settings
        tokens = theme.tokens()

        self.setWindowTitle(translator.t("app_title"))
        self.resize(900, 560)
        theme.apply(self)
        self.setFocusPolicy(Qt.StrongFocus)

        # ----- avatar ---------------------------------------------------
        self.avatar = SpriteAvatarWidget(
            assets,
            source_size=tokens.emotion_source_size,
            scale=tokens.emotion_scale,
        )
        self.avatar.setParent(self)
        self.avatar.set_emotion(self._vm.emotion or None)
        self.avatar.set_scale(self._vm.face_scale * self._vm.app_scale)

        # ----- text stack ----------------------------------------------
        self.text_stack = QStackedWidget(self)
        self.text_stack.setStyleSheet(f"background-color: {tokens.window_bg};")
        self.text_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(
            f"color: {tokens.text_primary}; "
            f"background-color: {tokens.window_bg}; padding: 20px;"
        )
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.text_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.text_stack.addWidget(self.text_label)

        self.text_edit = EditableTextEdit(tokens.normal_font_size)
        self.text_edit.submitted.connect(self._controller.submit)
        self.text_edit.user_edited.connect(self._on_user_edited)

        self.text_edit_page = QWidget()
        self.text_edit_page.setStyleSheet(f"background-color: {tokens.window_bg};")
        edit_layout = QVBoxLayout(self.text_edit_page)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.addWidget(self.text_edit)
        self.text_stack.addWidget(self.text_edit_page)

        self.text_stack.setCurrentWidget(self.text_label)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 15, 40, 20)
        main_layout.setSpacing(0)
        main_layout.addStretch(1)
        main_layout.addWidget(self.text_stack, 0, Qt.AlignBottom)
        self.setLayout(main_layout)

        # ----- mic icon ------------------------------------------------
        self.mic_label = QLabel(self)
        self.mic_label.setAlignment(Qt.AlignCenter)
        self.mic_label.setStyleSheet("background-color: transparent;")
        self.mic_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.mic_label.setVisible(False)
        self._update_mic_icon()

        # ----- settings icon -------------------------------------------
        self.settings_icon = ClickableLabel(self)
        self.settings_icon.setAlignment(Qt.AlignCenter)
        self.settings_icon.setStyleSheet("background-color: transparent;")
        self.settings_icon.setToolTip(translator.t("settings_tooltip"))
        self.settings_icon.clicked.connect(self._on_settings_clicked)
        self.settings_icon.setVisible(False)
        self._update_settings_icon()

        # ----- hint ----------------------------------------------------
        self.hint_label = QLabel(self)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet(
            f"color: {tokens.text_hint}; background-color: transparent; padding: 6px;"
        )
        self.hint_label.setText(translator.t("send_hint"))
        self.hint_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.hint_label.setVisible(False)
        self._update_hint_font()

        # ----- error label ---------------------------------------------
        self.error_label = ClickableLabel(self)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(False)
        self.error_label.setStyleSheet(
            f"color: #ff4444; background-color: rgba(255, 68, 68, 0.15); "
            f"padding: 8px 20px; border-radius: 6px; "
            f"font-size: 10pt;"
        )
        self.error_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.error_label.setMinimumHeight(30)
        self.error_label.clicked.connect(self._on_error_click)
        self.error_label.setVisible(False)

        # ----- bind view model ----------------------------------------
        self._vm.placeholder_active_changed.connect(self._render_placeholder)
        self._vm.user_text_changed.connect(self._render_user_text)
        self._vm.response_text_changed.connect(self._render_response)
        self._vm.emotion_changed.connect(self._render_emotion)
        self._vm.mic_enabled_changed.connect(self._render_mic_state)
        self._vm.hint_visible_changed.connect(self._render_hint)
        self._vm.face_scale_changed.connect(self._render_zoom)
        self._vm.app_scale_changed.connect(self._render_zoom)
        self._vm.error_message_changed.connect(self._render_error)

        # Initial render from the current view-model state.
        self._render_placeholder(self._vm.placeholder_active)
        self._render_mic_state(self._vm.mic_enabled)
        self._render_hint(self._vm.hint_visible)
        if self._vm.user_text:
            self._render_user_text(self._vm.user_text)
        if self._vm.response_text:
            self._render_response(self._vm.response_text)

        QApplication.instance().installEventFilter(self)
        self._reposition_overlays()

    # ------------------------------------------------------------------
    # View-model reactions
    # ------------------------------------------------------------------

    def _render_placeholder(self, active: bool) -> None:
        tokens = self._theme.tokens()
        scale = self._vm.app_scale
        if active:
            self.text_label.setTextFormat(Qt.RichText)
            self.text_label.setText(
                f'<div style="font-size: {tokens.placeholder_font_size * scale:.1f}pt;">'
                f'{PLACEHOLDER_TEXT}</div>'
                f'<div style="font-size: {tokens.subtitle_font_size * scale:.1f}pt; '
                f'color: {tokens.text_subtitle};">'
                f'{self._i18n.t("placeholder_subtitle")}</div>'
            )
        else:
            self.text_label.setTextFormat(Qt.PlainText)
            f = QFont(tokens.font_family)
            f.setPointSizeF(tokens.normal_font_size * scale)
            self.text_label.setFont(f)
            self.text_label.clear()

    def _render_user_text(self, text: str) -> None:
        # Only rewrite the document when the content actually differs,
        # otherwise typing would reset the cursor on every keystroke.
        if self.text_edit.get_text() != text:
            self.text_edit.set_text(text, color=self._theme.tokens().text_user)
        if self.text_stack.currentWidget() is not self.text_edit_page:
            self.text_stack.setCurrentWidget(self.text_edit_page)
        self.text_edit.setFocus()

    def _render_response(self, text: str) -> None:
        # Only force the label page when there is something to show; an
        # empty response means "clear the label" without stealing focus
        # from the edit page.
        if text and self.text_stack.currentWidget() is not self.text_label:
            self.text_stack.setCurrentWidget(self.text_label)
        self.text_label.setTextFormat(Qt.PlainText)
        self.text_label.setText(text)

    def _render_emotion(self, emotion: str) -> None:
        self.avatar.set_emotion(emotion or None)

    def _render_mic_state(self, enabled: bool) -> None:
        self.mic_label.setVisible(not enabled)
        self.settings_icon.setVisible(not enabled)

    def _render_hint(self, visible: bool) -> None:
        self.hint_label.setVisible(visible)
        if visible:
            self.hint_label.raise_()

    def _render_error(self, message: str) -> None:
        if message:
            self.error_label.setText(message)
            self.error_label.setVisible(True)
            self.error_label.raise_()
            self._reposition_overlays()
        else:
            self.error_label.setVisible(False)

    def _render_zoom(self, _value: float) -> None:
        self.avatar.set_scale(self._vm.face_scale * self._vm.app_scale)
        self._update_mic_icon()
        self._update_settings_icon()
        self._update_hint_font()
        if not self._vm.placeholder_active:
            f = QFont(self._theme.tokens().font_family)
            f.setPointSizeF(self._theme.tokens().normal_font_size * self._vm.app_scale)
            self.text_label.setFont(f)
        else:
            self._render_placeholder(True)
        self.text_edit.apply_font_size(
            self._theme.tokens().normal_font_size * self._vm.app_scale
        )
        self._reposition_overlays()

    # ------------------------------------------------------------------
    # Icon helpers
    # ------------------------------------------------------------------

    def _update_mic_icon(self) -> None:
        tokens = self._theme.tokens()
        size = max(24, int(tokens.mic_source_size * tokens.mic_scale * self._vm.app_scale))
        src = self._assets.mic_off_source_pixmap()
        if src is not None:
            self.mic_label.setPixmap(
                src.scaled(size, size, Qt.IgnoreAspectRatio, Qt.FastTransformation)
            )
        self.mic_label.setFixedSize(size, size)

    def _update_settings_icon(self) -> None:
        tokens = self._theme.tokens()
        size = max(20, int(tokens.settings_icon_size * self._vm.app_scale))
        pix = self._assets.settings_icon(max(64, size * 4)).scaled(
            size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.settings_icon.setPixmap(pix)
        self.settings_icon.setFixedSize(size, size)

    def _update_hint_font(self) -> None:
        tokens = self._theme.tokens()
        f = QFont(tokens.font_family)
        f.setPointSizeF(tokens.hint_font_size * self._vm.app_scale)
        self.hint_label.setFont(f)
        self.hint_label.adjustSize()

    # ------------------------------------------------------------------
    # Overlay layout
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_overlays()

    def _reposition_overlays(self) -> None:
        face = self.avatar.width()
        self.avatar.move(
            (self.width() - face) // 2,
            (self.height() - face) // 2,
        )
        self.avatar.raise_()

        self.mic_label.move(20, 20)
        self.mic_label.raise_()

        self.settings_icon.move(
            self.width() - self.settings_icon.width() - 20, 20
        )
        self.settings_icon.raise_()

        self.hint_label.adjustSize()
        stack_top = self.text_stack.y()
        hy = max(10, stack_top - self.hint_label.height() - 6)
        hx = (self.width() - self.hint_label.width()) // 2
        self.hint_label.move(hx, hy)
        if self._vm.hint_visible:
            self.hint_label.raise_()

        if self._vm.error_message:
            error_width = min(self.width() - 60, 800)
            self.error_label.setFixedWidth(error_width)
            # Position at bottom, above the window edge
            ey = self.height() - self.error_label.height() - 30
            ex = (self.width() - error_width) // 2
            self.error_label.move(ex, ey)
            self.error_label.raise_()

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self._click_on_response(event.pos()):
            self._controller.on_response_click()
            event.accept()
            return
        self._controller.toggle_mic()

    def _click_on_response(self, pos) -> bool:
        if self._vm.placeholder_active:
            return False
        if self.text_stack.currentWidget() is not self.text_label:
            return False
        if not self._vm.generating and not self._vm.response_text.strip():
            return False
        label_pos = self.text_label.mapFrom(self, pos)
        return self.text_label.rect().contains(label_pos)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._controller.submit()
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and isinstance(obj, QWidget):
            if obj.window() is self:
                delta = event.angleDelta().y()
                ctrl = bool(event.modifiers() & Qt.ControlModifier)
                self._controller.apply_zoom(delta, ctrl)
                return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        self._controller.apply_zoom(delta, ctrl)
        event.accept()

    def _on_user_edited(self) -> None:
        self._controller.on_user_edited(self.text_edit.get_text())

    def _on_error_click(self) -> None:
        """Clear error message when user clicks on it."""
        self._vm.error_message = ""

    def _on_settings_clicked(self) -> None:
        self._open_settings(self)

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        app = QApplication.instance()
        if app is not None:
            try:
                app.removeEventFilter(self)
            except Exception:
                pass
        self._controller.shutdown()
        event.accept()