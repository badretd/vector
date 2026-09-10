"""Main application window: emotion icon, text area, microphone toggle."""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config import (
    EMOTION_DISPLAY_SIZE,
    NORMAL_FONT_SIZE,
    PLACEHOLDER_FONT_SIZE,
    PLACEHOLDER_TEXT,
    PLACEHOLDER_TIMEOUT,
    SILENCE_TIMEOUT,
    STYLE_WHITE,
    STYLE_YELLOW,
)
from core.llm_thread import LLMThread
from core.speech_thread import SpeechThread
from ui.assets import load_emotion_pixmaps, make_mic_pixmap
from ui.widgets import ClickableLabel


class VoiceWindow(QWidget):
    def __init__(self, device_index):
        super().__init__()
        self.setWindowTitle("Voice Text")
        self.resize(900, 560)
        self.setStyleSheet("background-color: #000000;")

        self.placeholder_active = True
        self.recognition_enabled = True

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
        self.emotion_label.setPixmap(QPixmap())

        # --- center: answer text ---
        self.text_label = QLabel(PLACEHOLDER_TEXT, self)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setFont(QFont("Arial", PLACEHOLDER_FONT_SIZE))
        self.text_label.setStyleSheet(STYLE_WHITE)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- bottom: microphone toggle ---
        self.mic_pixmap_normal = make_mic_pixmap(128, crossed=False).scaled(
            80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.mic_pixmap_crossed = make_mic_pixmap(128, crossed=True).scaled(
            80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.mic_label = ClickableLabel(self)
        self.mic_label.setPixmap(self.mic_pixmap_normal)
        self.mic_label.setAlignment(Qt.AlignCenter)
        self.mic_label.setStyleSheet("background-color: #000000;")
        self.mic_label.setFixedSize(100, 100)
        self.mic_label.clicked.connect(self.on_mic_click)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 15, 30, 30)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.emotion_label, alignment=Qt.AlignHCenter)
        main_layout.addWidget(self.text_label, stretch=1)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.mic_label)
        bottom_layout.addStretch(1)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

        self.silence_timer = QTimer(self)
        self.silence_timer.setSingleShot(True)
        self.silence_timer.timeout.connect(self.on_silence)

        self.placeholder_timer = QTimer(self)
        self.placeholder_timer.setSingleShot(True)
        self.placeholder_timer.timeout.connect(self.clear_placeholder)
        self.placeholder_timer.start(PLACEHOLDER_TIMEOUT)

        self.speech_thread = SpeechThread(device_index)
        self.speech_thread.text_recognized.connect(self.update_text)
        self.speech_thread.start()

    # ---------- placeholder ----------

    def clear_placeholder(self):
        if self.placeholder_active:
            self.placeholder_active = False
            self.text_label.clear()
            self.text_label.setFont(QFont("Arial", NORMAL_FONT_SIZE))

    # ---------- speech recognition ----------

    def update_text(self, text):
        if self.generating:
            self.cancel_llm()

        if self.placeholder_active:
            self.placeholder_timer.stop()
            self.placeholder_active = False
            self.text_label.setFont(QFont("Arial", NORMAL_FONT_SIZE))

        self._set_emotion("")
        self.llm_response_text = ""
        self.text_label.setStyleSheet(STYLE_WHITE)
        self.text_label.setText(text)
        self.current_user_text = text

        self.silence_timer.stop()
        self.silence_timer.start(SILENCE_TIMEOUT)

    def on_silence(self):
        text = self.current_user_text.strip()
        self.current_user_text = ""

        self.speech_thread.reset()

        if not text:
            self.text_label.clear()
            return

        self.start_generation(text)

    # ---------- LLM ----------

    def start_generation(self, prompt):
        self.generating = True
        self.llm_response_text = ""

        # Show "Thinking" while the model warms up and produces the first token.
        self._set_emotion("Thinking")
        self.text_label.setStyleSheet(STYLE_YELLOW)
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
        """Set the emotion sprite. Empty string clears it."""
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
        if self.recognition_enabled:
            self.mic_label.setPixmap(self.mic_pixmap_normal)
        else:
            self.mic_label.setPixmap(self.mic_pixmap_crossed)
        self.speech_thread.set_enabled(self.recognition_enabled)

    def closeEvent(self, event):
        self.cancel_llm()
        self.speech_thread.stop()
        event.accept()