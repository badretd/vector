"""Observable state for the main window."""
from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal


class MainViewModel(QObject):
    placeholder_active_changed = pyqtSignal(bool)
    user_text_changed = pyqtSignal(str)
    response_text_changed = pyqtSignal(str)
    emotion_changed = pyqtSignal(str)          # "" means hidden
    generating_changed = pyqtSignal(bool)
    mic_enabled_changed = pyqtSignal(bool)
    hint_visible_changed = pyqtSignal(bool)
    face_scale_changed = pyqtSignal(float)
    app_scale_changed = pyqtSignal(float)
    send_mode_changed = pyqtSignal(str)
    error_message_changed = pyqtSignal(str)    # "" means no error

    def __init__(self) -> None:
        super().__init__()
        self._placeholder_active = True
        self._user_text = ""
        self._response_text = ""
        self._emotion = "Happy"
        self._generating = False
        self._mic_enabled = True
        self._hint_visible = False
        self._face_scale = 3.0
        self._app_scale = 1.0
        self._send_mode = "enter"
        self._error_message = ""

    # -- properties -------------------------------------------------------

    @property
    def placeholder_active(self) -> bool:
        return self._placeholder_active

    @placeholder_active.setter
    def placeholder_active(self, value: bool) -> None:
        if value == self._placeholder_active:
            return
        self._placeholder_active = value
        self.placeholder_active_changed.emit(value)

    @property
    def user_text(self) -> str:
        return self._user_text

    @user_text.setter
    def user_text(self, value: str) -> None:
        # Always emit: the view needs to react to page switches even when
        # the text itself did not change (e.g. after clearing a response,
        # or when the recognizer re-emits the same partial result).
        self._user_text = value
        self.user_text_changed.emit(value)

    @property
    def response_text(self) -> str:
        return self._response_text

    @response_text.setter
    def response_text(self, value: str) -> None:
        # Always emit for the same reason as user_text.
        self._response_text = value
        self.response_text_changed.emit(value)

    @property
    def emotion(self) -> str:
        return self._emotion

    @emotion.setter
    def emotion(self, value: str) -> None:
        if value == self._emotion:
            return
        self._emotion = value
        self.emotion_changed.emit(value)

    @property
    def generating(self) -> bool:
        return self._generating

    @generating.setter
    def generating(self, value: bool) -> None:
        if value == self._generating:
            return
        self._generating = value
        self.generating_changed.emit(value)

    @property
    def mic_enabled(self) -> bool:
        return self._mic_enabled

    @mic_enabled.setter
    def mic_enabled(self, value: bool) -> None:
        if value == self._mic_enabled:
            return
        self._mic_enabled = value
        self.mic_enabled_changed.emit(value)

    @property
    def hint_visible(self) -> bool:
        return self._hint_visible

    @hint_visible.setter
    def hint_visible(self, value: bool) -> None:
        if value == self._hint_visible:
            return
        self._hint_visible = value
        self.hint_visible_changed.emit(value)

    @property
    def face_scale(self) -> float:
        return self._face_scale

    @face_scale.setter
    def face_scale(self, value: float) -> None:
        if abs(value - self._face_scale) < 1e-3:
            return
        self._face_scale = value
        self.face_scale_changed.emit(value)

    @property
    def app_scale(self) -> float:
        return self._app_scale

    @app_scale.setter
    def app_scale(self, value: float) -> None:
        if abs(value - self._app_scale) < 1e-3:
            return
        self._app_scale = value
        self.app_scale_changed.emit(value)

    @property
    def send_mode(self) -> str:
        return self._send_mode

    @send_mode.setter
    def send_mode(self, value: str) -> None:
        if value == self._send_mode:
            return
        self._send_mode = value
        self.send_mode_changed.emit(value)

    @property
    def error_message(self) -> str:
        return self._error_message

    @error_message.setter
    def error_message(self, value: str) -> None:
        if value == self._error_message:
            return
        self._error_message = value
        self.error_message_changed.emit(value)