"""Main window: emotion sprite, text area, click-anywhere mic toggle."""
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor, QFont, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QLabel,
    QMenu,
    QSizePolicy,
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
    STYLE_YELLOW,
    SUBTITLE_FONT_SIZE,
)
from core.i18n import t
from core.llm_thread import LLMThread
from core.speech_thread import SpeechThread
from ui.assets import load_emotion_pixmaps, load_mic_off_pixmap, make_settings_pixmap
from ui.widgets import ClickableLabel


class VoiceWindow(QWidget):
    MIC_ICON_SIZE = 96

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

        self.emotion_pixmaps = load_emotion_pixmaps()

        # --- top: emotion sprite ---
        self.emotion_label = QLabel(self)
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setStyleSheet("background-color: #000000;")
        self.emotion_label.setFixedHeight(EMOTION_DISPLAY_SIZE + 20)
        self.emotion_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.emotion_label.setPixmap(QPixmap())
        self._current_emotion = None

        # --- center: text ---
        self.text_label = QLabel(self)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(STYLE_WHITE)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.text_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._show_placeholder()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 15, 30, 30)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.emotion_label, alignment=Qt.AlignHCenter)
        main_layout.addWidget(self.text_label, stretch=1)
        self.setLayout(main_layout)

        # --- microphone overlay (bottom center, visible when mic is OFF) ---
        self.mic_pixmap_crossed = load_mic_off_pixmap().scaled(
            self.MIC_ICON_SIZE, self.MIC_ICON_SIZE,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.mic_label = QLabel(self)
        self.mic_label.setPixmap(self.mic_pixmap_crossed)
        self.mic_label.setAlignment(Qt.AlignCenter)
        self.mic_label.setStyleSheet("background-color: transparent;")
        self.mic_label.setFixedSize(self.MIC_ICON_SIZE, self.MIC_ICON_SIZE)
        self.mic_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.mic_label.setVisible(False)

        # --- settings icon (top-right, visible when mic is OFF) ---
        settings_pixmap = make_settings_pixmap(128).scaled(
            SETTINGS_ICON_SIZE, SETTINGS_ICON_SIZE,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.settings_icon = ClickableLabel(self)
        self.settings_icon.setPixmap(settings_pixmap)
        self.settings_icon.setAlignment(Qt.AlignCenter)
        self.settings_icon.setStyleSheet("background-color: transparent;")
        self.settings_icon.setFixedSize(SETTINGS_ICON_SIZE, SETTINGS_ICON_SIZE)
        self.settings_icon.setToolTip(t("settings_tooltip"))
        self.settings_icon.clicked.connect(self.open_settings_menu)
        self.settings_icon.setVisible(False)

        # --- send hint (overlaid near the bottom) ---
        self.hint_label = QLabel(self)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setFont(QFont("Arial", HINT_FONT_SIZE))
        self.hint_label.setStyleSheet(
            "color: #ffcc00; background-color: transparent; padding: 6px;"
        )
        self.hint_label.setText(t("send_hint"))
        self.hint_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.hint_label.adjustSize()
        self.hint_label.setVisible(False)

        # --- timers ---
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

        # --- recognition ---
        self.speech_thread = SpeechThread(device_index)
        self.speech_thread.text_recognized.connect(self.update_text)
        self.speech_thread.start()

    # ---------- placeholder ----------

    def _show_placeholder(self):
        self.text_label.setTextFormat(Qt.RichText)
        self.text_label.setText(
            f'<div style="font-size: {PLACEHOLDER_FONT_SIZE}pt;">'
            f'{PLACEHOLDER_TEXT}</div>'
            f'<div style="font-size: {SUBTITLE_FONT_SIZE}pt; color: #888888;">'
            f'{t("placeholder_subtitle")}</div>'
        )

    # ---------- overlay positioning ----------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_overlays()

    def _reposition_overlays(self):
        # Mic icon: bottom center.
        x = (self.width() - self.mic_label.width()) // 2
        y = self.height() - self.mic_label.height() - 20
        self.mic_label.move(x, y)

        # Settings icon: top-right corner.
        sx = self.width() - self.settings_icon.width() - 20
        sy = 20
        self.settings_icon.move(sx, sy)

        # Hint: bottom center, just above the mic icon.
        self.hint_label.adjustSize()
        hx = (self.width() - self.hint_label.width()) // 2
        hy = self.height() - self.hint_label.height() - 40
        self.hint_label.move(hx, hy)

    # ---------- click anywhere toggles the mic ----------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_mic_click()
        super().mousePressEvent(event)

    # ---------- Enter key ----------

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.on_enter_pressed()
            event.accept()
            return
        super().keyPressEvent(event)

    def on_enter_pressed(self):
        self.hide_hint()
        self.silence_timer.stop()
        text = self.current_user_text.strip()
        if not text or self.generating:
            return
        self.current_user_text = ""
        self.speech_thread.reset()
        self.start_generation(text)

    # ---------- placeholder lifecycle ----------

    def clear_placeholder(self):
        if self.placeholder_active:
            self.placeholder_active = False
            self.text_label.setTextFormat(Qt.PlainText)
            self.text_label.clear()
            self.text_label.setFont(QFont("Arial", NORMAL_FONT_SIZE))

    # ---------- speech recognition ----------

    def update_text(self, text):
        if self.generating:
            self.cancel_llm()

        if self.placeholder_active:
            self.placeholder_timer.stop()
            self.placeholder_active = False
            self.text_label.setTextFormat(Qt.PlainText)
            self.text_label.setFont(QFont("Arial", NORMAL_FONT_SIZE))

        self._set_emotion("")
        self.llm_response_text = ""
        # User text is yellow.
        self.text_label.setStyleSheet(STYLE_YELLOW)
        self.text_label.setText(text)
        self.current_user_text = text

        self.hide_hint()
        self.silence_timer.stop()
        self.silence_timer.start(SILENCE_TIMEOUT)

    def on_silence(self):
        text = self.current_user_text.strip()
        if not text:
            self.text_label.clear()
            return

        mode = self.settings.get("send_mode", "enter")
        if mode == "timer":
            # Auto-send after the silence timeout.
            self.current_user_text = ""
            self.speech_thread.reset()
            self.start_generation(text)
        else:
            # Enter mode: show the hint and wait for the user.
            self.show_hint()

    # ---------- send hint ----------

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

    # ---------- LLM ----------

    def start_generation(self, prompt):
        self.generating = True
        self.llm_response_text = ""

        self._set_emotion("Thinking")
        # Model answer is white.
        self.text_label.setStyleSheet(STYLE_WHITE)
        self.text_label.setText("")

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
        pix = self.emotion_pixmaps.get(emotion)
        if pix is None:
            self.emotion_label.clear()
            return
        self.emotion_label.setPixmap(pix)

    # ---------- microphone ----------

    def on_mic_click(self):
        self.recognition_enabled = not self.recognition_enabled
        # Icons appear only while the mic is OFF.
        self.mic_label.setVisible(not self.recognition_enabled)
        self.settings_icon.setVisible(not self.recognition_enabled)
        self.speech_thread.set_enabled(self.recognition_enabled)
        self.hide_hint()

    # ---------- settings menu ----------

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

    # ---------- close ----------

    def closeEvent(self, event):
        self.cancel_llm()
        self.speech_thread.stop()
        event.accept()