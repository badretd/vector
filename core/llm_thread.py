"""Streaming Ollama client that parses emotions from the reply."""
import json
import re

import requests
from PyQt5.QtCore import QThread, pyqtSignal

import config
from config import EMOTIONS, OLLAMA_URL, SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Stream parser: extracts the leading emotion token and inline *Emotion* markers
# ---------------------------------------------------------------------------

class _StreamParser:
    """Turn a raw token stream into (visible_text, [emotions]).

    * The very first word is expected to be one of EMOTIONS.
    * Anywhere later, the model may insert *Happy* / *Sad* / ... to switch the
      currently displayed emotion. Those markers are stripped from the text.
    * Asterisk markers that don't match an emotion are left untouched.
    """

    def __init__(self):
        self._leading_done = False
        self._buffer = ""
        self._canonical = {e.lower(): e for e in EMOTIONS}
        self._canonical["netral"] = "Neutral"

    # -- public API -------------------------------------------------------

    def feed(self, chunk: str):
        self._buffer += chunk
        emotions = []

        if not self._leading_done:
            done = self._try_leading(emotions)
            if not done:
                return "", emotions

        text, more, tail = self._extract_markers(self._buffer)
        self._buffer = tail
        emotions.extend(more)
        return text, emotions

    def finalize(self):
        emotions = []
        text = self._buffer
        self._buffer = ""

        if not self._leading_done and text.strip():
            parts = text.strip().split(None, 1)
            emo = self._canonical.get(parts[0].strip(".,:;!?\"'`*_").lower())
            if emo:
                emotions.append(emo)
                text = parts[1] if len(parts) > 1 else ""
            else:
                emotions.append("Neutral")

        cleaned, more, tail = self._extract_markers(text)
        emotions.extend(more)
        return cleaned + tail, emotions

    # -- internals --------------------------------------------------------

    def _try_leading(self, emotions) -> bool:
        stripped = self._buffer.lstrip()
        m = re.match(r"[A-Za-z]+", stripped)
        if not m:
            if len(stripped) > 40:
                emotions.append("Neutral")
                self._leading_done = True
                self._buffer = stripped
                return True
            return False

        word = m.group(0)
        end = m.end()

        # Need a terminator to be sure the word is complete
        if end < len(stripped):
            emo = self._canonical.get(word.lower())
            if emo and (stripped[end].isspace() or stripped[end] == "*"):
                emotions.append(emo)
                self._leading_done = True
                self._buffer = stripped[end:].lstrip()
                return True
            if len(stripped) > 40:
                emotions.append("Neutral")
                self._leading_done = True
                self._buffer = stripped
                return True
        elif len(stripped) > 40:
            emotions.append("Neutral")
            self._leading_done = True
            self._buffer = stripped
            return True

        return False

    def _extract_markers(self, text):
        emotions = []
        out = []
        i, n = 0, len(text)
        while i < n:
            if text[i] == "*":
                j = text.find("*", i + 1)
                if j == -1:
                    return "".join(out), emotions, text[i:]
                inner = text[i + 1:j]
                emo = self._canonical.get(inner.strip().lower())
                if emo:
                    emotions.append(emo)
                else:
                    out.append(text[i:j + 1])
                i = j + 1
            else:
                out.append(text[i])
                i += 1
        return "".join(out), emotions, ""


# ---------------------------------------------------------------------------
# Qt thread
# ---------------------------------------------------------------------------

class LLMThread(QThread):
    emotion_received = pyqtSignal(str)
    chunk_received = pyqtSignal(str)
    finished_generating = pyqtSignal()

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt
        self._cancelled = False

    def run(self):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self.prompt},
        ]
        try:
            response = requests.post(
                config.OLLAMA_URL,
                json={
                    "model": config.OLLAMA_MODEL,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.6,
                        "stop": [
                            "\nUser:", "\nuser:", "\nUSER:",
                            "\nAssistant:", "\nassistant:", "\nASSISTANT:",
                            "\nHuman:", "\nhuman:", "\nHUMAN:",
                            "\nSystem:", "\nsystem:", "\nSYSTEM:",
                        ],
                    },
                },
                stream=True,
                timeout=120,
            )
            response.raise_for_status()

            parser = _StreamParser()

            for line in response.iter_lines():
                if self._cancelled:
                    break
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                except Exception:
                    continue

                msg = data.get("message") or {}
                chunk = msg.get("content", "")

                if chunk:
                    text, emotions = parser.feed(chunk)
                    for e in emotions:
                        self.emotion_received.emit(e)
                    if text:
                        self.chunk_received.emit(text)

                if data.get("done"):
                    text, emotions = parser.finalize()
                    for e in emotions:
                        self.emotion_received.emit(e)
                    if text:
                        self.chunk_received.emit(text)
                    break

            response.close()
        except Exception as e:
            if not self._cancelled:
                print(f"LLM error: {e}")
        finally:
            self.finished_generating.emit()

    def cancel(self):
        self._cancelled = True