"""OpenRouter streaming chat provider with proxy support.

Structurally satisfies ``LlmProviderPort``. Uses the shared HTTP client
factory so that the configured proxy is honoured for the actual streaming
request, not only for the auxiliary calls.
"""
from __future__ import annotations

import json
import traceback
from typing import Callable

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from vector_voice.application.constants import (
    DEFAULT_OPENROUTER_MODELS_URL,
    DEFAULT_OPENROUTER_URL,
    LLM_REQUEST_TIMEOUT,
    LLM_STOP_SEQUENCES,
    LLM_TEMPERATURE,
    OPENROUTER_REFERER,
    OPENROUTER_TITLE,
)
from vector_voice.domain.models import Message
from vector_voice.infrastructure.logger import get_logger

logger = get_logger("llm.openrouter")


class _OpenRouterWorker(QThread):
    chunk_ready = pyqtSignal(str)
    finished_ok = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, session, url: str, api_key: str, model: str,
                 messages: list[Message]) -> None:
        super().__init__()
        self._session = session
        self._url = url
        self._api_key = api_key
        self._model = model
        self._messages = messages
        self._cancelled = False

    def run(self) -> None:
        payload = {
            "model": self._model,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in self._messages
            ],
            "stream": True,
            "temperature": LLM_TEMPERATURE,
            "stop": list(LLM_STOP_SEQUENCES),
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "HTTP-Referer": OPENROUTER_REFERER,
            "X-Title": OPENROUTER_TITLE,
        }
        try:
            response = self._session.post(
                self._url, json=payload, headers=headers,
                stream=True, timeout=LLM_REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            for raw in response.iter_lines():
                if self._cancelled:
                    break
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if line.startswith("data:"):
                    line = line[5:].strip()
                if not line or line == "[DONE]":
                    if line == "[DONE]":
                        break
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                for choice in data.get("choices") or ():
                    delta = choice.get("delta") or {}
                    content = delta.get("content")
                    if content:
                        self.chunk_ready.emit(content)

            response.close()
            if not self._cancelled:
                self.finished_ok.emit()
        except Exception as exc:
            if not self._cancelled:
                logger.error(
                    f"OpenRouter request failed | Model: {self._model} | "
                    f"Error: {exc} | Traceback: {traceback.format_exc()}"
                )
                self.failed.emit(str(exc))

    def cancel(self) -> None:
        self._cancelled = True


class OpenRouterProvider(QObject):
    """Streaming OpenRouter provider. Structurally satisfies ``LlmProviderPort``."""

    def __init__(self, http_client_factory, api_key: str | None = None,
                 url: str = DEFAULT_OPENROUTER_URL) -> None:
        super().__init__()
        self._http = http_client_factory
        self._api_key = api_key or ""
        self._url = url or DEFAULT_OPENROUTER_URL
        self._worker: _OpenRouterWorker | None = None

    @property
    def provider_id(self) -> str:
        return "openrouter"

    def set_api_key(self, api_key: str | None) -> None:
        self._api_key = api_key or ""

    def has_api_key(self) -> bool:
        return bool(self._api_key)

    def is_available(self) -> bool:
        return self.has_api_key()

    def list_models(self) -> list[str]:
        if not self.has_api_key():
            return []
        try:
            session = self._http.create_session()
            r = session.get(
                DEFAULT_OPENROUTER_MODELS_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=4.0,
            )
            r.raise_for_status()
            data = r.json()
            return sorted(m["id"] for m in data.get("data", []) if m.get("id"))
        except Exception:
            return []

    def stream_chat(
        self,
        model: str,
        messages: list[Message],
        on_chunk: Callable[[str], None],
        on_done: Callable[[], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        session = self._http.create_session()
        self._worker = _OpenRouterWorker(
            session, self._url, self._api_key, model, messages
        )
        self._worker.chunk_ready.connect(on_chunk)
        self._worker.finished_ok.connect(on_done)

        def _handle_error(msg: str) -> None:
            on_error(RuntimeError(msg))

        self._worker.failed.connect(_handle_error)
        self._worker.start()

    def cancel(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        self._worker = None