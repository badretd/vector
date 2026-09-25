"""Application-level facade over the memory repository.

Stage 1 scope:

* persist the last N conversation turns and replay them into the prompt;
* persist explicit "remember that ..." facts the user asks for;
* retrieve relevant facts by keyword (FTS5) and inject them as a hint.

Automatic fact extraction via the LLM and embeddings are intentionally
out of scope and will be layered on top of this service later.
"""
from __future__ import annotations

from datetime import datetime, timezone

from vector_voice.domain.models import (
    MemoryItem,
    MemoryKind,
    Message,
    MessageRole,
)
from vector_voice.domain.ports import MemoryRepositoryPort, SettingsServicePort

# Prefixes that mark an explicit "remember this" instruction.
# Longest prefixes first so that e.g. "remember that " wins over "remember ".
_REMEMBER_PREFIXES: tuple[str, ...] = (
    "please remember that ",
    "please remember ",
    "remember that ",
    "remember: ",
    "remember ",
    "note that ",
    "keep in mind that ",
    "запомни, что ",
    "запомни что ",
    "запомни: ",
    "запомни, ",
    "запомни ",
    "учти, что ",
    "учти что ",
)

_MEMORY_KINDS: set[MemoryKind] = {
    MemoryKind.FACT,
    MemoryKind.PREFERENCE,
    MemoryKind.NOTE,
}


class MemoryService:
    """Thin, testable facade. All persistence goes through the port."""

    def __init__(
        self,
        repository: MemoryRepositoryPort,
        settings: SettingsServicePort,
    ) -> None:
        self._repo = repository
        self._settings = settings

    # -- state ------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return bool(self._settings.get("memory_enabled", True))

    def count(self) -> int:
        try:
            return self._repo.count()
        except Exception:
            return 0

    # -- context for the LLM ---------------------------------------------

    def history(self, limit: int | None = None) -> list[Message]:
        """Recent user/assistant turns, oldest first."""
        if not self.enabled:
            return []
        if limit is None:
            limit = int(self._settings.get("memory_recent_turns", 8))
        return self._repo.recent_messages(limit=limit)

    def build_context(self, query: str) -> str:
        """Return a system block with relevant memories, or '' if none."""
        if not self.enabled:
            return ""

        limit = int(self._settings.get("memory_retrieval_limit", 5))
        items = self._repo.search(query, limit=limit, kinds=_MEMORY_KINDS)
        if not items:
            return ""

        lines = "\n".join(f"- {m.text}" for m in items)
        return (
            "Relevant things you remember about the user from past "
            "conversations:\n" + lines
        )

    # -- persistence ------------------------------------------------------

    def remember_turn(self, user_text: str, assistant_text: str) -> None:
        if not self.enabled:
            return
        self._repo.add_message(MessageRole.USER, user_text)
        self._repo.add_message(MessageRole.ASSISTANT, assistant_text)
        self._capture_explicit_fact(user_text)

    def remember_fact(
        self,
        text: str,
        kind: MemoryKind = MemoryKind.FACT,
    ) -> None:
        text = text.strip()
        if not text:
            return
        self._repo.add_memory(MemoryItem(
            id=None,
            kind=kind,
            text=text,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ))

    def clear(self) -> None:
        self._repo.clear()

    # -- explicit-command detection --------------------------------------

    def _capture_explicit_fact(self, user_text: str) -> None:
        """Rule-based extraction of "remember that X" style commands."""
        stripped = user_text.strip()
        if not stripped:
            return
        lower = stripped.lower()
        for prefix in _REMEMBER_PREFIXES:
            if not lower.startswith(prefix):
                continue
            fact = stripped[len(prefix):].strip(" \t.,!?;:—-")
            if len(fact) >= 3:
                self.remember_fact(fact, MemoryKind.FACT)
            return