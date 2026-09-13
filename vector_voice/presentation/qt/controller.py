"""MainWindow controller: translates UI events into service calls."""
from __future__ import annotations

from PyQt5.QtCore import QObject, QTimer

from vector_voice.application.constants import (
    PLACEHOLDER_TIMEOUT,
    SEND_HINT_TIMEOUT,
    SILENCE_TIMEOUT,
)
from vector_voice.application.services.conversation_service import ConversationService
from vector_voice.application.services.settings_service import SettingsService
from vector_voice.application.services.speech_service import SpeechService
from vector_voice.domain.models import Emotion, SendMode
from vector_voice.domain.ports import TranslationServicePort
from vector_voice.presentation.qt.viewmodel import MainViewModel

# Zoom limits and step, mirroring the original behaviour.
FACE_SCALE_MIN = 0.4
FACE_SCALE_MAX = 8.0
APP_SCALE_MIN = 0.6
APP_SCALE_MAX = 2.4
ZOOM_STEP = 1.05


class MainWindowController(QObject):
    """Glue between MainViewModel, SpeechService, ConversationService.

    The controller owns interaction state that the view model exposes to the
    view. The view stays passive; the controller never touches widgets.
    """

    def __init__(
        self,
        view_model: MainViewModel,
        speech: SpeechService,
        conversation: ConversationService,
        settings: SettingsService,
        translator: TranslationServicePort,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._speech = speech
        self._conversation = conversation
        self._settings = settings
        self._i18n = translator

        # Editing / streaming state.
        self._user_edited = False
        self._vosk_consumed = ""
        self._restore_timer_mode = False
        self._response_buffer = ""

        self._vm.send_mode = settings.get("send_mode", SendMode.ENTER.value)

        # Timers (owned by the controller, not the widgets).
        self._silence_timer = QTimer(self)
        self._silence_timer.setSingleShot(True)
        self._silence_timer.timeout.connect(self._on_silence)

        self._placeholder_timer = QTimer(self)
        self._placeholder_timer.setSingleShot(True)
        self._placeholder_timer.timeout.connect(self._on_placeholder_timeout)
        self._placeholder_timer.start(PLACEHOLDER_TIMEOUT)

        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.timeout.connect(lambda: setattr(self._vm, "hint_visible", False))

        self._speech.on_text(self._on_speech_text)

    # ------------------------------------------------------------------
    # Speech
    # ------------------------------------------------------------------

    def _on_speech_text(self, vosk_text: str) -> None:
        if self._vm.generating:
            self.cancel_generation()

        if self._vm.placeholder_active:
            self._placeholder_timer.stop()
            self._vm.placeholder_active = False

        self._vm.emotion = ""
        self._vm.response_text = ""

        if self._user_edited:
            if len(vosk_text) >= len(self._vosk_consumed):
                delta = vosk_text[len(self._vosk_consumed):]
            else:
                delta = vosk_text
            delta = delta.lstrip()
            if delta:
                base = self._vm.user_text.rstrip()
                self._vm.user_text = (base + " " + delta) if base else delta
            self._vosk_consumed = vosk_text
        else:
            self._vm.user_text = vosk_text
            self._vosk_consumed = vosk_text

        self._hide_hint()
        self._silence_timer.stop()
        if not self._user_edited:
            self._silence_timer.start(SILENCE_TIMEOUT)

    # ------------------------------------------------------------------
    # Text editing
    # ------------------------------------------------------------------

    def on_user_edited(self, text: str) -> None:
        if self._vm.generating:
            return
        self._user_edited = True
        self._vm.user_text = text

        self._silence_timer.stop()
        self._hide_hint()

        if self._settings.get("send_mode") == SendMode.TIMER.value:
            self._restore_timer_mode = True
            self._settings.set("send_mode", SendMode.ENTER.value)

    # ------------------------------------------------------------------
    # Submit / timers
    # ------------------------------------------------------------------

    def submit(self) -> None:
        self._hide_hint()
        self._silence_timer.stop()

        text = self._vm.user_text.strip()
        if not text or self._vm.generating:
            return

        self._vm.user_text = ""
        self._user_edited = False
        self._vosk_consumed = ""
        self._speech.reset()
        self._start_generation(text)

    def _on_silence(self) -> None:
        if self._user_edited:
            return
        text = self._vm.user_text.strip()
        if not text:
            self._vm.response_text = ""
            return

        mode = self._settings.get("send_mode", SendMode.ENTER.value)
        if mode == SendMode.TIMER.value:
            self._vm.user_text = ""
            self._speech.reset()
            self._start_generation(text)
        else:
            self._show_hint()

    def _on_placeholder_timeout(self) -> None:
        if self._vm.placeholder_active:
            self._vm.placeholder_active = False

    def _show_hint(self) -> None:
        self._vm.hint_visible = True
        self._hint_timer.start(SEND_HINT_TIMEOUT)

    def _hide_hint(self) -> None:
        self._hint_timer.stop()
        self._vm.hint_visible = False

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def _start_generation(self, prompt: str) -> None:
        self._vm.generating = True
        self._response_buffer = ""
        self._vm.error_message = ""

        if self._restore_timer_mode:
            self._restore_timer_mode = False
            self._settings.set("send_mode", SendMode.TIMER.value)

        self._vm.emotion = Emotion.THINKING.value
        self._vm.response_text = ""

        self._conversation.send(
            prompt=prompt,
            on_chunk=self._on_llm_chunk,
            on_emotion=self._on_llm_emotion,
            on_done=self._on_llm_done,
            on_error=self._on_llm_error,
        )

    def _on_llm_chunk(self, chunk: str) -> None:
        if not self._vm.generating:
            return
        self._response_buffer += chunk
        self._vm.response_text = self._response_buffer

    def _on_llm_emotion(self, emotion: Emotion) -> None:
        if not self._vm.generating:
            return
        self._vm.emotion = emotion.value

    def _on_llm_done(self) -> None:
        self._vm.generating = False

    def _on_llm_error(self, error_msg: str) -> None:
        self._vm.error_message = f"LLM Error: {error_msg}"
        self._vm.emotion = ""

    def cancel_generation(self) -> None:
        self._conversation.cancel()
        self._vm.generating = False
        self._response_buffer = ""
        self._vm.response_text = ""
        self._vm.error_message = ""

    def on_response_click(self) -> None:
        """Clear the answer and switch back to input mode."""
        if self._vm.generating:
            self.cancel_generation()
        self._response_buffer = ""
        self._vm.response_text = ""
        self._vm.user_text = ""
        self._user_edited = False
        self._vosk_consumed = ""
        self._speech.reset()
        self._hide_hint()
        self._vm.error_message = ""

    # ------------------------------------------------------------------
    # Microphone / settings
    # ------------------------------------------------------------------

    def toggle_mic(self) -> None:
        enabled = self._speech.toggle()
        self._vm.mic_enabled = enabled
        self._hide_hint()

    def set_send_mode(self, mode: str) -> None:
        self._settings.set("send_mode", mode)
        self._settings.save()
        self._vm.send_mode = mode
        self._hide_hint()

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def apply_zoom(self, delta: int, ctrl: bool) -> None:
        if delta == 0:
            return
        factor = ZOOM_STEP if delta > 0 else (1.0 / ZOOM_STEP)
        if ctrl:
            new = max(APP_SCALE_MIN, min(APP_SCALE_MAX, self._vm.app_scale * factor))
            self._vm.app_scale = new
        else:
            new = max(FACE_SCALE_MIN, min(FACE_SCALE_MAX, self._vm.face_scale * factor))
            self._vm.face_scale = new

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        self.cancel_generation()
        self._speech.stop()