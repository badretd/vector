"""Streaming Ollama client that parses the emotion prefix from the reply."""

import json

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from config import EMOTIONS, OLLAMA_MODEL, OLLAMA_URL, SYSTEM_PROMPT


class LLMThread(QThread):
    """Streams tokens from Ollama and splits the leading emotion token off.

    The model is instructed (see SYSTEM_PROMPT) to start every reply with
    one canonical emotion word. We consume just enough of the stream to
    identify that word, emit it, and then forward the rest as plain text.
    """

    emotion_received = pyqtSignal(str)
    chunk_received = pyqtSignal(str)
    finished_generating = pyqtSignal()

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt
        self._cancelled = False

    def run(self):
        full_prompt = SYSTEM_PROMPT + "\n\nUser: " + self.prompt + "\nAssistant:"
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "stream": True,
                    "options": {"temperature": 0.6},
                },
                stream=True,
                timeout=120,
            )
            response.raise_for_status()

            emotion_parsed = False
            buffer = ""

            for line in response.iter_lines():
                if self._cancelled:
                    break
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                except Exception:
                    continue

                chunk = data.get("response", "")

                if not emotion_parsed:
                    buffer += chunk

                    # Wait until we have at least one whitespace to split
                    # the leading word from the actual answer.
                    if any(c.isspace() for c in buffer):
                        parts = buffer.split(None, 1)
                        first = parts[0] if parts else ""
                        rest = parts[1] if len(parts) > 1 else ""

                        canonical = self._normalize_emotion(first)
                        if canonical is not None:
                            self.emotion_received.emit(canonical)
                            emotion_parsed = True
                            if rest:
                                self.chunk_received.emit(rest)
                        elif len(buffer) > 40:
                            # Model ignored the format — fall back to Neutral
                            # rather than blocking the UI forever.
                            self.emotion_received.emit("Neutral")
                            emotion_parsed = True
                            self.chunk_received.emit(buffer)
                    elif len(buffer) > 40:
                        self.emotion_received.emit("Neutral")
                        emotion_parsed = True
                        self.chunk_received.emit(buffer)
                else:
                    if chunk:
                        self.chunk_received.emit(chunk)

                if data.get("done"):
                    if not emotion_parsed and buffer:
                        self.emotion_received.emit("Neutral")
                        self.chunk_received.emit(buffer)
                    break

            response.close()
        except Exception as e:
            if not self._cancelled:
                print(f"LLM error: {e}")
        finally:
            self.finished_generating.emit()

    @staticmethod
    def _normalize_emotion(word):
        """Map an arbitrary token to a canonical emotion name, or None.

        Tolerates surrounding punctuation and the historical "netral" typo.
        """
        w = word.strip().strip(".,:;!?\"'`*_")
        w_lower = w.lower()
        if w_lower == "netral":
            return "Neutral"
        for e in EMOTIONS:
            if e.lower() == w_lower:
                return e
        return None

    def cancel(self):
        self._cancelled = True