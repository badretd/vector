"""Main window: centered emotion sprite, bottom text, top-left mic icon.

Zoom:
  • Mouse wheel        — smoothly scales the face sprite.
  • Ctrl + mouse wheel — smoothly scales the whole app (fonts, icons, face).
"""
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QLabel,
    QMenu,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import (
    EMOTION_DISPLAY_SIZE,
    HINT_FONT_SIZE,
    MIC_DISPLAY_SIZE,
    NORMAL_FONT_SIZE,
    PLACEHOLDER_FONT_SIZE,
    PLACEHOLDER_TEXT,
    PLACEHOLDER_TIMEOUT,
    SEND_HINT_TIMEOUT,
    SETTINGS_ICON_SIZE,
    SILENCE_TIMEOUT,
    STYLE_WHITE,
    SUBTITLE_FONT_SIZE,
)
from core.i18n import t
from core.llm_thread import LLMThread
from core.speech_thread import SpeechThread
from ui.assets import (
    load_emotion_source_pixmaps,
    load_mic_off_source_pixmap,
    make_settings_pixmap,
)
from ui.widgets import ClickableLabel, EditableTextEdit


class VoiceWindow(QWidget):
    MIC_ICON_SIZE = 96

    # Zoom limits and step.
    FACE_SCALE_MIN = 0.4
    FACE_SCALE_MAX = 8.0
    FACE_SCALE_DEFAULT = 3.0
    APP_SCALE_MIN = 0.6
    APP_SCALE_MAX = 2.4
    ZOOM_STEP = 1.05

    def __init__(self, device_index, settings):
        super().__init__()
        self.settings = settings

        self.setWindowTitle(t("app_title"))
        self.resize(900, 560)
        self.setStyleSheet("background-color: #000000;")
        self.setFocusPolicy(Qt.StrongFocus)

        self.placeholder_active = True
        self.recognition_enabled = True
        self.hint_visible = False

        self.current_user_text = ""
        self.llm_response_text = ""
        self.generating = False
        self.llm_thread = None

        # Editing / mode-switch state
        self._user_edited = False
        self._vosk_consumed = ""
        self._restore_timer_mode = False
        self._current_emotion = "Happy"

        # Zoom state
        self.face_scale = self.FACE_SCALE_DEFAULT
        self.app_scale = 1.0

        # Source (unscaled) assets — we re-scale them on every zoom change.
        self.emotion_source_pixmaps = load_emotion_source_pixmaps()
        self.mic_source_pixmap = load_mic_off_source_pixmap()

        # ---------- face overlay (centered, big) ----------
        self.emotion_label = QLabel(self)
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setStyleSheet("background-color: transparent;")
        self.emotion_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.emotion_label.setFixedSize(
            self._face_display_size(), self._face_display_size()
        )

        self._refresh_face_pixmap()

        # ---------- bottom text stack ----------
        self.text_stack = QStackedWidget(self)
        self.text_stack.setStyleSheet("background-color: #000000;")
        self.text_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Page 1 — QLabel (placeholder + streamed LLM response)
        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(STYLE_WHITE)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.text_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.text_stack.addWidget(self.text_label)

        # Page 2 — EditableTextEdit (user text)
        self.text_edit = EditableTextEdit()
        self.text_edit.submitted.connect(self.on_submit)
        self.text_edit.user_edited.connect(self.on_user_edit)

        self.text_edit_page = QWidget()
        self.text_edit_page.setStyleSheet("background-color: #000000;")
        edit_layout = QVBoxLayout(self.text_edit_page)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.addWidget(self.text_edit)
        self.text_stack.addWidget(self.text_edit_page)

        self._show_placeholder()
        self.text_stack.setCurrentWidget(self.text_label)

        # ---------- main layout: push the text stack to the bottom ----------
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 15, 40, 20)
        main_layout.setSpacing(0)
        main_layout.addStretch(1)
        main_layout.addWidget(self.text_stack, 0, Qt.AlignBottom)
        self.setLayout(main_layout)

        # ---------- microphone overlay (top-left, visible when mic is OFF) ----------
        self.mic_label = QLabel(self)
        self.mic_label.setAlignment(Qt.AlignCenter)
        self.mic_label.setStyleSheet("background-color: transparent;")
        self.mic_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.mic_label.setVisible(False)

        # ---------- settings icon (top-right, visible when mic is OFF) ----------
        self.settings_icon = ClickableLabel(self)
        self.settings_icon.setAlignment(Qt.AlignCenter)
        self.settings_icon.setStyleSheet("background-color: transparent;")
        self.settings_icon.setToolTip(t("settings_tooltip"))
        self.settings_icon.clicked.connect(self.open_settings_menu)
        self.settings_icon.setVisible(False)

        # ---------- send hint (just above the text area) ----------
        self.hint_label = QLabel(self)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet(
            "color: #ffcc00; background-color: transparent; padding: 6px;"
        )
        self.hint_label.setText(t("send_hint"))
        self.hint_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.hint_label.setVisible(False)

        # ---------- timers ----------
        self.silence_timer = QTimer(self)
        self.silence_timer.setSingleShot(True)
        self.silence_timer.timeout.connect(self.on_silence)

        self.placeholder_timer = QTimer(self)
        self.placeholder_timer.setSingleShot(True)
        self.placeholder_timer.timeout.connect(self.clear_placeholder)
        self.placeholder_timer.start(PLACEHOLDER_TIMEOUT)

        self.hint_timer = QTimer(self)
        self.hint_timer.setSingleShot(True)
        self.hint_timer.timeout.connect(self.hide_hint)

        # ---------- apply initial scaling to icons / fonts ----------
        self._update_icons()
        self._update_text_fonts()

        # ---------- recognition ----------
        self.speech_thread = SpeechThread(device_index)
        self.speech_thread.text_recognized.connect(self.update_text)
        self.speech_thread.start()

        # ---------- global wheel hook (so zoom works anywhere) ----------
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self._reposition_overlays()

    # ==================================================================
    # Zoom
    # ==================================================================

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and isinstance(obj, QWidget):
            # Only intercept wheel events that belong to our window.
            if obj.window() is self:
                self._handle_wheel(event)
                return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event):
        # Fallback if the app-level filter wasn't installed.
        self._handle_wheel(event)

    def _handle_wheel(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = self.ZOOM_STEP if delta > 0 else (1.0 / self.ZOOM_STEP)

        if event.modifiers() & Qt.ControlModifier:
            self._set_app_scale(self.app_scale * factor)
        else:
            self._set_face_scale(self.face_scale * factor)
        event.accept()

    def _set_face_scale(self, value):
        value = max(self.FACE_SCALE_MIN, min(self.FACE_SCALE_MAX, value))
        if abs(value - self.face_scale) < 1e-3:
            return
        self.face_scale = value
        self._update_face_size()

    def _set_app_scale(self, value):
        value = max(self.APP_SCALE_MIN, min(self.APP_SCALE_MAX, value))
        if abs(value - self.app_scale) < 1e-3:
            return
        self.app_scale = value
        self._update_icons()
        self._update_text_fonts()
        self._update_face_size()

    # ==================================================================
    # Scaling helpers
    # ==================================================================

    def _face_display_size(self):
        return max(
            24,
            int(EMOTION_DISPLAY_SIZE * self.face_scale * self.app_scale),
        )

    def _update_face_size(self):
        size = self._face_display_size()
        self.emotion_label.setFixedSize(size, size)
        self._refresh_face_pixmap()
        self._reposition_overlays()

    def _refresh_face_pixmap(self):
        emo = self._current_emotion
        if not emo:
            return
        src = self.emotion_source_pixmaps.get(emo)
        if src is None:
            return
        size = self._face_display_size()
        self.emotion_label.setPixmap(
            src.scaled(size, size, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        )

    def _update_icons(self):
        s = self.app_scale

        # Mic — nearest-neighbour keeps the pixel-art look crisp.
        mic_size = max(24, int(MIC_DISPLAY_SIZE * s))
        if self.mic_source_pixmap is not None:
            self.mic_label.setPixmap(
                self.mic_source_pixmap.scaled(
                    mic_size, mic_size,
                    Qt.IgnoreAspectRatio, Qt.FastTransformation,
                )
            )
        self.mic_label.setFixedSize(mic_size, mic_size)

        # Settings — drawn procedurally, regenerate for crispness.
        st_size = max(20, int(SETTINGS_ICON_SIZE * s))
        pix = make_settings_pixmap(max(64, st_size * 4)).scaled(
            st_size, st_size, Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.settings_icon.setPixmap(pix)
        self.settings_icon.setFixedSize(st_size, st_size)

    def _update_text_fonts(self):
        s = self.app_scale

        if self.placeholder_active:
            self._show_placeholder()
        else:
            f = QFont("Arial")
            f.setPointSizeF(NORMAL_FONT_SIZE * s)
            self.text_label.setFont(f)

        f = QFont("Arial")
        f.setPointSizeF(NORMAL_FONT_SIZE * s)
        self.text_edit.setFont(f)

        f = QFont("Arial")
        f.setPointSizeF(HINT_FONT_SIZE * s)
        self.hint_label.setFont(f)
        self.hint_label.adjustSize()

    # ==================================================================
    # Placeholder
    # ==================================================================

    def _show_placeholder(self):
        s = self.app_scale
        self.text_label.setTextFormat(Qt.RichText)
        self.text_label.setText(
            f'<div style="font-size: {PLACEHOLDER_FONT_SIZE * s:.1f}pt;">'
            f'{PLACEHOLDER_TEXT}</div>'
            f'<div style="font-size: {SUBTITLE_FONT_SIZE * s:.1f}pt; color: #888888;">'
            f'{t("placeholder_subtitle")}</div>'
        )

    # ==================================================================
    # Overlay positioning
    # ==================================================================

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_overlays()

    def _reposition_overlays(self):
        # Face — dead center of the window.
        face = self.emotion_label.width()
        self.emotion_label.move(
            (self.width() - face) // 2,
            (self.height() - face) // 2,
        )
        self.emotion_label.raise_()

        # Microphone — top-left corner.
        self.mic_label.move(20, 20)
        self.mic_label.raise_()

        # Settings — top-right corner.
        self.settings_icon.move(
            self.width() - self.settings_icon.width() - 20, 20
        )
        self.settings_icon.raise_()

        # Hint — centered horizontally, just above the text area.
        self.hint_label.adjustSize()
        stack_top = self.text_stack.y()
        hy = max(10, stack_top - self.hint_label.height() - 6)
        hx = (self.width() - self.hint_label.width()) // 2
        self.hint_label.move(hx, hy)
        if self.hint_visible:
            self.hint_label.raise_()

    # ==================================================================
    # Click anywhere toggles the mic
    # ==================================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Click on an actual answer → clear it and switch back to input.
            if self._click_on_response(event.pos()):
                self.on_response_click()
                event.accept()
                return
            # Anywhere else → toggle the microphone, as before.
            self.on_mic_click()

    def _click_on_response(self, pos):
        """True when the click landed on a non-empty answer / stream."""
        # The placeholder is not an answer — let the mic toggle handle it.
        if self.placeholder_active:
            return False
        # Only the label page counts; while editing, clicks should not fire.
        if self.text_stack.currentWidget() is not self.text_label:
            return False
        # Nothing to clear (finished with empty body, no stream yet).
        if not self.generating and not self.llm_response_text.strip():
            return False
        # Map the window-space click into the label's own coordinates.
        label_pos = self.text_label.mapFrom(self, pos)
        return self.text_label.rect().contains(label_pos)

    def on_response_click(self):
        """Clear the LLM answer and let the user speak / type again."""
        if self.generating:
            self.cancel_llm()

        self.llm_response_text = ""
        self.text_label.setTextFormat(Qt.PlainText)
        self.text_label.clear()

        # Fresh input state.
        self.current_user_text = ""
        self._user_edited = False
        self._vosk_consumed = ""
        self.speech_thread.reset()

        self.text_edit.set_text("", color="#ffff00")
        self.text_stack.setCurrentWidget(self.text_edit_page)
        self.text_edit.setFocus()
        self.hide_hint()

    # ==================================================================
    # Enter key
    # ==================================================================

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.on_submit()
            event.accept()
            return
        super().keyPressEvent(event)

    def on_submit(self):
        self.hide_hint()
        self.silence_timer.stop()

        if self.text_stack.currentWidget() is not self.text_edit_page:
            return

        text = self.current_user_text.strip()
        if not text or self.generating:
            return

        self.current_user_text = ""
        self._user_edited = False
        self._vosk_consumed = ""
        self.speech_thread.reset()
        self.start_generation(text)

    # ==================================================================
    # Placeholder lifecycle
    # ==================================================================

    def clear_placeholder(self):
        if self.placeholder_active:
            self.placeholder_active = False
            self.text_label.setTextFormat(Qt.PlainText)
            self.text_label.clear()
            f = QFont("Arial")
            f.setPointSizeF(NORMAL_FONT_SIZE * self.app_scale)
            self.text_label.setFont(f)

    # ==================================================================
    # Speech recognition
    # ==================================================================

    def update_text(self, vosk_text):
        if self.generating:
            self.cancel_llm()

        if self.placeholder_active:
            self.placeholder_timer.stop()
            self.placeholder_active = False

        self._set_emotion("")
        self.llm_response_text = ""

        if self._user_edited:
            if len(vosk_text) >= len(self._vosk_consumed):
                delta = vosk_text[len(self._vosk_consumed):]
            else:
                delta = vosk_text
            delta = delta.lstrip()
            if delta:
                base = self.current_user_text.rstrip()
                self.current_user_text = (base + " " + delta) if base else delta
            self._vosk_consumed = vosk_text
        else:
            self.current_user_text = vosk_text
            self._vosk_consumed = vosk_text

        self.text_edit.set_text(self.current_user_text, color="#ffff00")
        self.text_stack.setCurrentWidget(self.text_edit_page)
        self.text_edit.setFocus()

        self.hide_hint()
        self.silence_timer.stop()
        if not self._user_edited:
            self.silence_timer.start(SILENCE_TIMEOUT)

    def on_user_edit(self):
        if self.generating:
            return
        self._user_edited = True
        self.current_user_text = self.text_edit.get_text()

        self.silence_timer.stop()
        self.hide_hint()

        if self.settings.get("send_mode", "enter") == "timer":
            self._restore_timer_mode = True
            self.settings["send_mode"] = "enter"

    def on_silence(self):
        if self._user_edited:
            return

        text = self.current_user_text.strip()
        if not text:
            self.text_label.clear()
            self.text_stack.setCurrentWidget(self.text_label)
            return

        mode = self.settings.get("send_mode", "enter")
        if mode == "timer":
            self.current_user_text = ""
            self.speech_thread.reset()
            self.start_generation(text)
        else:
            self.show_hint()

    # ==================================================================
    # Send hint
    # ==================================================================

    def show_hint(self):
        self.hint_visible = True
        self._reposition_overlays()
        self.hint_label.setVisible(True)
        self.hint_label.raise_()
        self.hint_timer.start(SEND_HINT_TIMEOUT)

    def hide_hint(self):
        self.hint_timer.stop()
        if self.hint_visible:
            self.hint_visible = False
            self.hint_label.setVisible(False)

    # ==================================================================
    # LLM
    # ==================================================================

    def start_generation(self, prompt):
        self.generating = True
        self.llm_response_text = ""

        if self._restore_timer_mode:
            self._restore_timer_mode = False
            self.settings["send_mode"] = "timer"

        self._set_emotion("Thinking")

        self.text_label.setStyleSheet(STYLE_WHITE)
        self.text_label.setTextFormat(Qt.PlainText)
        f = QFont("Arial")
        f.setPointSizeF(NORMAL_FONT_SIZE * self.app_scale)
        self.text_label.setFont(f)
        self.text_label.clear()
        self.text_stack.setCurrentWidget(self.text_label)

        self.llm_thread = LLMThread(prompt)
        self.llm_thread.emotion_received.connect(self.on_llm_emotion)
        self.llm_thread.chunk_received.connect(self.on_llm_chunk)
        self.llm_thread.finished_generating.connect(self.on_llm_finished)
        self.llm_thread.start()

    def on_llm_emotion(self, emotion):
        if self.sender() is not self.llm_thread or not self.generating:
            return
        self._set_emotion(emotion)

    def on_llm_chunk(self, chunk):
        if self.sender() is not self.llm_thread or not self.generating:
            return
        self.llm_response_text += chunk
        self.text_label.setText(self.llm_response_text)

    def on_llm_finished(self):
        if self.sender() is not self.llm_thread:
            return
        self.generating = False

    def cancel_llm(self):
        old_thread = self.llm_thread
        self.llm_thread = None
        self.generating = False
        self.llm_response_text = ""

        if old_thread is not None and old_thread.isRunning():
            old_thread.cancel()
            old_thread.wait(2000)

    def _set_emotion(self, emotion):
        if emotion == self._current_emotion:
            return
        self._current_emotion = emotion

        if not emotion:
            self.emotion_label.clear()
            return

        src = self.emotion_source_pixmaps.get(emotion)
        if src is None:
            self.emotion_label.clear()
            return

        size = self._face_display_size()
        self.emotion_label.setPixmap(
            src.scaled(size, size, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        )

    # ==================================================================
    # Microphone
    # ==================================================================

    def on_mic_click(self):
        self.recognition_enabled = not self.recognition_enabled
        self.mic_label.setVisible(not self.recognition_enabled)
        self.settings_icon.setVisible(not self.recognition_enabled)
        self.speech_thread.set_enabled(self.recognition_enabled)
        self.hide_hint()

    # ==================================================================
    # Settings menu
    # ==================================================================

    def open_settings_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu {"
            "  background-color: #1e1e1e;"
            "  color: #ffffff;"
            "  border: 1px solid #444444;"
            "  padding: 4px;"
            "}"
            "QMenu::item { padding: 6px 18px; }"
            "QMenu::item:selected { background-color: #333333; }"
            "QMenu::item:disabled { color: #888888; }"
            "QMenu::separator { height: 1px; background: #444444; margin: 4px 8px; }"
        )

        header = menu.addAction(t("settings_send_mode_header"))
        header.setEnabled(False)
        menu.addSeparator()

        group = QActionGroup(menu)
        group.setExclusive(True)

        current = self.settings.get("send_mode", "enter")

        action_enter = QAction(t("settings_send_enter"), self, checkable=True)
        action_enter.setChecked(current == "enter")
        action_enter.triggered.connect(lambda: self.set_send_mode("enter"))
        group.addAction(action_enter)
        menu.addAction(action_enter)

        action_timer = QAction(t("settings_send_timer"), self, checkable=True)
        action_timer.setChecked(current == "timer")
        action_timer.triggered.connect(lambda: self.set_send_mode("timer"))
        group.addAction(action_timer)
        menu.addAction(action_timer)

        menu.exec_(QCursor.pos())

    def set_send_mode(self, mode):
        self.settings["send_mode"] = mode
        self.settings.save()
        self.hide_hint()

    # ==================================================================
    # Close
    # ==================================================================

    def closeEvent(self, event):
        app = QApplication.instance()
        if app is not None:
            try:
                app.removeEventFilter(self)
            except Exception:
                pass
        self.cancel_llm()
        self.speech_thread.stop()
        event.accept()