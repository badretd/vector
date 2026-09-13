"""Owns the speech recognizer lifecycle and notifies listeners."""
from __future__ import annotations

from typing import Callable

from vector_voice.domain.ports import SpeechRecognizerPort


class SpeechService:
    def __init__(self, recognizer: SpeechRecognizerPort) -> None:
        self._recognizer = recognizer
        self._enabled = True
        self._text_callback: Callable[[str], None] | None = None
        self._recognizer.set_text_callback(self._on_text)

    # -- public API -------------------------------------------------------

    def on_text(self, callback: Callable[[str], None]) -> None:
        self._text_callback = callback

    def start(self) -> None:
        self._recognizer.start()

    def stop(self) -> None:
        self._recognizer.stop()

    def reset(self) -> None:
        self._recognizer.reset()

    def toggle(self) -> bool:
        self._enabled = not self._enabled
        self._recognizer.set_enabled(self._enabled)
        return self._enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    # -- internals --------------------------------------------------------

    def _on_text(self, text: str) -> None:
        if not self._enabled:
            return
        if self._text_callback is not None:
            self._text_callback(text)