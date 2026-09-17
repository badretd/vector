"""Streams a user prompt to the LLM and parses emotion tags."""
from __future__ import annotations

import logging
import traceback
from typing import Callable

from vector_voice.application.emotion_parser import EmotionParser
from vector_voice.application.prompts import SYSTEM_PROMPT
from vector_voice.domain.models import Emotion, Message, MessageRole
from vector_voice.domain.ports import LlmProviderPort
from vector_voice.infrastructure.logger import get_logger

logger = logging.getLogger(__name__)


class ConversationService:
    """Wraps a provider into a per-prompt session with emotion parsing."""

    def __init__(self, provider: LlmProviderPort, model: str) -> None:
        self._provider = provider
        self._model = model
        self._parser: EmotionParser | None = None

    def set_model(self, model: str) -> None:
        self._model = model

    def set_provider(self, provider: LlmProviderPort, model: str) -> None:
        """Swap the underlying provider at runtime (e.g. after settings change)."""
        self.cancel()
        self._provider = provider
        self._model = model

    def send(
        self,
        prompt: str,
        on_chunk: Callable[[str], None],
        on_emotion: Callable[[Emotion], None],
        on_done: Callable[[], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Start streaming. Callbacks are invoked from the provider thread."""
        self._parser = EmotionParser()

        def _handle_chunk(chunk: str) -> None:
            assert self._parser is not None
            text, emotions = self._parser.feed(chunk)
            for emo in emotions:
                on_emotion(emo)
            if text:
                on_chunk(text)

        def _handle_done() -> None:
            if self._parser is not None:
                text, emotions = self._parser.finalize()
                for emo in emotions:
                    on_emotion(emo)
                if text:
                    on_chunk(text)
                self._parser = None
            on_done()

        def _handle_error(exc: Exception) -> None:
            prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
            logger.error(
                f"LLM conversation error | Model: {self._model} | "
                f"Prompt: {prompt_preview} | Error: {exc} | "
                f"Traceback: {traceback.format_exc()}"
            )
            if self._parser is not None:
                self._parser = None
            if on_error:
                on_error(str(exc))
            on_done()

        messages = [
            Message(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT),
            Message(role=MessageRole.USER, content=prompt),
        ]
        self._provider.stream_chat(
            model=self._model,
            messages=messages,
            on_chunk=_handle_chunk,
            on_done=_handle_done,
            on_error=_handle_error,
        )

    def cancel(self) -> None:
        self._provider.cancel()
        self._parser = None