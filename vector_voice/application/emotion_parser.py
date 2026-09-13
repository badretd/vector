"""Stream parser that extracts [Emotion] tags from a streaming LLM reply.

Expected reply shape::

    [Happy] Sure, that sounds fun! [Laugh] What made you ask?

The first non-whitespace characters should be the leading emotion tag. Up
to two more tags may appear inline. Unknown ``[Something]`` brackets are
kept in the visible text. If the reply doesn't start with a tag, ``Neutral``
is reported and the text is passed through as-is.
"""
from __future__ import annotations

from vector_voice.domain.models import Emotion

_EMOTIONS_LOWER: dict[str, Emotion] = {e.value.lower(): e for e in Emotion}

# Tolerate common misspellings small models produce.
_ALIASES: dict[str, Emotion] = {
    "netral": Emotion.NEUTRAL,
    "nutral": Emotion.NEUTRAL,
    "netraul": Emotion.NEUTRAL,
    "hapy": Emotion.HAPPY,
    "happpy": Emotion.HAPPY,
    "lough": Emotion.LAUGH,
    "laughing": Emotion.LAUGH,
    "sadd": Emotion.SAD,
    "thinkingg": Emotion.THINKING,
}

_MAX_TAG_LEN = 20


def _lookup_emotion(word: str) -> Emotion | None:
    w = word.strip().lower()
    if w in _EMOTIONS_LOWER:
        return _EMOTIONS_LOWER[w]
    return _ALIASES.get(w)


class EmotionParser:
    """Incremental parser. Feed chunks, receive (visible_text, emotions)."""

    def __init__(self) -> None:
        self._buffer = ""
        self._leading_done = False

    # -- public API -------------------------------------------------------

    def feed(self, chunk: str) -> tuple[str, list[Emotion]]:
        self._buffer += chunk
        return self._parse(final=False)

    def finalize(self) -> tuple[str, list[Emotion]]:
        text, emotions = self._parse(final=True)
        self._buffer = ""
        return text, emotions

    # -- internals --------------------------------------------------------

    def _parse(self, final: bool) -> tuple[str, list[Emotion]]:
        emotions: list[Emotion] = []
        out: list[str] = []
        buf = self._buffer
        n = len(buf)
        i = 0

        # ----- leading emotion tag --------------------------------------
        if not self._leading_done:
            while i < n and buf[i].isspace():
                i += 1

            if i >= n:
                self._buffer = buf[i:]
                return "", emotions

            if buf[i] == "[":
                j = buf.find("]", i + 1)
                if j == -1:
                    if not final and self._looks_like_tag_prefix(buf, i):
                        self._buffer = buf[i:]
                        return "", emotions
                    emotions.append(Emotion.NEUTRAL)
                    self._leading_done = True
                else:
                    emo = _lookup_emotion(buf[i + 1:j])
                    if emo:
                        emotions.append(emo)
                        self._leading_done = True
                        i = j + 1
                        if i < n and buf[i] == " ":
                            i += 1
                    else:
                        emotions.append(Emotion.NEUTRAL)
                        self._leading_done = True
            else:
                emotions.append(Emotion.NEUTRAL)
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
                if i < n and buf[i] == " ":
                    i += 1
            else:
                out.append(buf[i:j + 1])
                i = j + 1
            start = i

        out.append(buf[start:])
        self._buffer = ""
        return "".join(out), emotions

    @staticmethod
    def _looks_like_tag_prefix(buf: str, i: int) -> bool:
        if i >= len(buf) or buf[i] != "[":
            return False
        if len(buf) - i > _MAX_TAG_LEN:
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