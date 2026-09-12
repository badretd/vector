"""Streaming Ollama client that parses emotions from the reply."""
import json

import requests
from PyQt5.QtCore import QThread, pyqtSignal

import config
from config import EMOTIONS, OLLAMA_URL, SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Emotion lookup
# ---------------------------------------------------------------------------

# Canonical names lowercased -> canonical form.
_EMOTIONS_LOWER = {e.lower(): e for e in EMOTIONS}

# Tolerate common misspellings small models produce.
_EMOTION_ALIASES = {
    "netral": "Neutral",
    "nutral": "Neutral",
    "netraul": "Neutral",
    "hapy": "Happy",
    "happpy": "Happy",
    "lough": "Laugh",
    "laughing": "Laugh",
    "sadd": "Sad",
    "thinkingg": "Thinking",
}


def _lookup_emotion(word: str):
    """Return the canonical emotion for a word, or None."""
    w = word.strip().lower()
    if w in _EMOTIONS_LOWER:
        return _EMOTIONS_LOWER[w]
    return _EMOTION_ALIASES.get(w)


# ---------------------------------------------------------------------------
# Stream parser
# ---------------------------------------------------------------------------

class _StreamParser:
    """Extract ``[Emotion]`` tags from a streaming LLM reply.

    Expected reply shape::

        [Happy] Sure, that sounds fun! [Laugh] What made you ask?

    The very first non-whitespace characters should be the leading emotion
    tag. Up to two more ``[Emotion]`` tags may appear inline.

    Behaviour:

    * Complete, recognised tags are stripped from the visible text and
      reported as emotions.
    * Unknown ``[Something]`` brackets (``[1]``, ``[note]``...) stay in
      the text untouched.
    * If the reply doesn't begin with a tag, ``Neutral`` is reported and
      the text is passed through as-is.
    * An incomplete ``[`` at the end of a chunk is buffered until the next
      chunk (or ``finalize``).
    """

    _MAX_TAG_LEN = 20

    def __init__(self):
        self._buffer = ""
        self._leading_done = False

    # -- public API -------------------------------------------------------

    def feed(self, chunk: str):
        self._buffer += chunk
        return self._parse(final=False)

    def finalize(self):
        text, emotions = self._parse(final=True)
        self._buffer = ""
        return text, emotions

    # -- internals --------------------------------------------------------

    def _parse(self, final: bool):
        emotions = []
        out = []
        buf = self._buffer
        n = len(buf)
        i = 0

        # ----- leading emotion tag --------------------------------------
        if not self._leading_done:
            while i < n and buf[i].isspace():
                i += 1

            if i >= n:
                # Nothing meaningful yet — hold everything.
                self._buffer = buf[i:]
                return "", emotions

            if buf[i] == "[":
                j = buf.find("]", i + 1)
                if j == -1:
                    if not final and self._looks_like_tag_prefix(buf, i):
                        # Wait for the closing bracket.
                        self._buffer = buf[i:]
                        return "", emotions
                    # Can't be a tag — fall back to Neutral, keep as text.
                    emotions.append("Neutral")
                    self._leading_done = True
                else:
                    emo = _lookup_emotion(buf[i + 1:j])
                    if emo:
                        emotions.append(emo)
                        self._leading_done = True
                        i = j + 1
                        # Drop a single separating space.
                        if i < n and buf[i] == " ":
                            i += 1
                    else:
                        # Unknown tag at the start — treat as text, but
                        # don't keep waiting for another leading tag.
                        emotions.append("Neutral")
                        self._leading_done = True
            else:
                # Reply doesn't start with a tag — model ignored the format.
                emotions.append("Neutral")
                self._leading_done = True

        # ----- inline tags ----------------------------------------------
        start = i
        while i < n:
            if buf[i] != "[":
                i += 1
                continue

            j = buf.find("]", i + 1)
            if j == -1:
                if not final and self._looks_like_tag_prefix(buf, i):
                    # Hold from this '[' — may be a tag split across chunks.
                    out.append(buf[start:i])
                    self._buffer = buf[i:]
                    return "".join(out), emotions
                i += 1
                continue

            out.append(buf[start:i])
            emo = _lookup_emotion(buf[i + 1:j])
            if emo:
                emotions.append(emo)
                i = j + 1
                # Drop a single separating space.
                if i < n and buf[i] == " ":
                    i += 1
            else:
                out.append(buf[i:j + 1])
                i = j + 1
            start = i

        out.append(buf[start:])
        self._buffer = ""
        return "".join(out), emotions

    def _looks_like_tag_prefix(self, buf: str, i: int) -> bool:
        """Return True if ``buf[i:]`` could still become an ``[Emotion]`` tag.

        Called only when ``buf[i] == '['`` and there is no closing ``]`` in
        the rest of the buffer. A prefix is valid while it consists of
        ``[`` + optional whitespace + letters + optional trailing whitespace,
        and hasn't grown past ``_MAX_TAG_LEN``.
        """
        if i >= len(buf) or buf[i] != "[":
            return False
        if len(buf) - i > self._MAX_TAG_LEN:
            return False

        j = i + 1
        n = len(buf)
        while j < n and buf[j].isspace():
            j += 1
        while j < n and buf[j].isalpha():
            j += 1
        if j == n:
            return True
        while j < n and buf[j].isspace():
            j += 1
        return j == n


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