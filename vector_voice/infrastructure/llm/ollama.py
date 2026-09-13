"""Ollama streaming chat provider.

Implements the ``LlmProviderPort`` protocol structurally; it does NOT
inherit from the port because QObject uses its own metaclass.
"""
from __future__ import annotations

import json
from typing import Callable

import requests
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from vector_voice.application.constants import (
    DEFAULT_OLLAMA_URL,
    LLM_REQUEST_TIMEOUT,
    LLM_STOP_SEQUENCES,
    LLM_TEMPERATURE,
)
from vector_voice.domain.models import Message


def _ollama_base(url: str) -> str:
    return url.rsplit("/api", 1)[0]


class _OllamaWorker(QThread):
    chunk_ready = pyqtSignal(str)
    finished_ok = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(
        self,
        url: str,
        model: str,
        messages: list[Message],
    ) -> None:
        super().__init__()
        self._url = url
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
            "options": {
                "temperature": LLM_TEMPERATURE,
                "stop": list(LLM_STOP_SEQUENCES),
            },
        }
        try:
            response = requests.post(
                self._url, json=payload, stream=True, timeout=LLM_REQUEST_TIMEOUT
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if self._cancelled:
                    break
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                except Exception:
                    continue

                chunk = (data.get("message") or {}).get("content", "")
                if chunk:
                    self.chunk_ready.emit(chunk)
                if data.get("done"):
                    break

            response.close()
            if not self._cancelled:
                self.finished_ok.emit()
        except Exception as exc:
            if not self._cancelled:
                self.failed.emit(str(exc))

    def cancel(self) -> None:
        self._cancelled = True


class OllamaProvider(QObject):
    """Streaming Ollama provider. Structurally satisfies ``LlmProviderPort``."""

    def __init__(self, http_client_factory, url: str = DEFAULT_OLLAMA_URL) -> None:
        super().__init__()
        self._http = http_client_factory
        self._url = url
        self._worker: _OllamaWorker | None = None

    @property
    def provider_id(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        try:
            session = self._http.create_session()
            r = session.get(_ollama_base(self._url) + "/api/tags", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            session = self._http.create_session()
            r = session.get(_ollama_base(self._url) + "/api/tags", timeout=4.0)
            r.raise_for_status()
            data = r.json()
            return sorted(m["name"] for m in data.get("models", []))
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
        self._worker = _OllamaWorker(self._url, model, messages)
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