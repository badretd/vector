"""SQLite + FTS5 implementation of ``MemoryRepositoryPort``.

The database file lives in the OS data directory and is intentionally
*not* touched by ``reset_app.py`` — memory survives a factory reset.

Each operation opens its own connection, so the repository is safe to
call from both the main thread (context building) and the LLM worker
thread (turn persistence).
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from vector_voice.domain.models import (
    MemoryItem,
    MemoryKind,
    Message,
    MessageRole,
)
from vector_voice.domain.ports import MemoryRepositoryPort


def memory_db_path() -> Path:
    """Public helper. Mirrors ``settings_repository.settings_path`` layout."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "vector_voice" / "memory.sqlite3"


_SCHEMA_BASE = """
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_id_desc ON messages(id DESC);

CREATE TABLE IF NOT EXISTS memories (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL,
    text         TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    last_used_at TEXT,
    importance   REAL NOT NULL DEFAULT 0.5
);
CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
"""

_SCHEMA_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
USING fts5(text, content='memories', content_rowid='id');

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, text)
        VALUES ('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, text)
        VALUES ('delete', old.id, old.text);
    INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
END;
"""


class SqliteMemoryRepository(MemoryRepositoryPort):
    """SQLite-backed long-term memory, with FTS5 ranking when available."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._db_path = Path(path) if path else memory_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fts_enabled = False
        self._init_schema()

    # -- public API -------------------------------------------------------

    def add_message(self, role: MessageRole, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages(role, content, created_at) "
                "VALUES (?, ?, datetime('now'))",
                (role.value, content),
            )

    def recent_messages(self, limit: int = 8) -> list[Message]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM ("
                "  SELECT id, role, content FROM messages ORDER BY id DESC LIMIT ?"
                ") ORDER BY id ASC",
                (int(limit),),
            ).fetchall()
        return [
            Message(role=MessageRole(r["role"]), content=r["content"])
            for r in rows
        ]

    def add_memory(self, item: MemoryItem) -> MemoryItem:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO memories(kind, text, created_at, importance) "
                "VALUES (?, ?, ?, ?)",
                (item.kind.value, item.text, item.created_at, item.importance),
            )
            new_id = int(cur.lastrowid)
        return MemoryItem(
            id=new_id,
            kind=item.kind,
            text=item.text,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            importance=item.importance,
        )

    def search(
        self,
        query: str,
        limit: int = 5,
        kinds: set[MemoryKind] | None = None,
    ) -> list[MemoryItem]:
        tokens = [
            t for t in re.findall(r"\w+", query, flags=re.UNICODE)
            if len(t) >= 2
        ][:12]

        with self._connect() as conn:
            if self._fts_enabled and tokens:
                rows = self._search_fts(conn, tokens, limit, kinds)
            elif tokens:
                rows = self._search_like(conn, tokens, limit, kinds)
            else:
                rows = self._recent(conn, limit, kinds)
        return [self._row_to_item(r) for r in rows]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM memories")
            conn.execute("DELETE FROM messages")

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM memories").fetchone()
        return int(row["n"]) if row else 0

    # -- internals --------------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self._db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA_BASE)
            self._fts_enabled = self._supports_fts5(conn)
            if self._fts_enabled:
                conn.executescript(_SCHEMA_FTS)

    @staticmethod
    def _supports_fts5(conn: sqlite3.Connection) -> bool:
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS __fts5_probe__ USING fts5(x)"
            )
            conn.execute("DROP TABLE IF EXISTS __fts5_probe__")
            return True
        except sqlite3.OperationalError:
            return False

    @staticmethod
    def _search_fts(
        conn: sqlite3.Connection,
        tokens: list[str],
        limit: int,
        kinds: set[MemoryKind] | None,
    ) -> list[sqlite3.Row]:
        match = " OR ".join(f"{t}*" for t in tokens)
        sql = (
            "SELECT m.id, m.kind, m.text, m.created_at, m.last_used_at, m.importance "
            "FROM memories m "
            "JOIN memories_fts ON memories_fts.rowid = m.id "
            "WHERE memories_fts MATCH ?"
        )
        params: list[object] = [match]
        if kinds:
            placeholders = ",".join("?" for _ in kinds)
            sql += f" AND m.kind IN ({placeholders})"
            params.extend(k.value for k in kinds)
        sql += " ORDER BY bm25(memories_fts) LIMIT ?"
        params.append(limit)
        try:
            return conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            return SqliteMemoryRepository._search_like(conn, tokens, limit, kinds)

    @staticmethod
    def _search_like(
        conn: sqlite3.Connection,
        tokens: list[str],
        limit: int,
        kinds: set[MemoryKind] | None,
    ) -> list[sqlite3.Row]:
        where = " OR ".join("text LIKE ?" for _ in tokens)
        params: list[object] = [f"%{t}%" for t in tokens]
        sql = (
            "SELECT id, kind, text, created_at, last_used_at, importance "
            f"FROM memories WHERE ({where})"
        )
        if kinds:
            placeholders = ",".join("?" for _ in kinds)
            sql += f" AND kind IN ({placeholders})"
            params.extend(k.value for k in kinds)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return conn.execute(sql, params).fetchall()

    @staticmethod
    def _recent(
        conn: sqlite3.Connection,
        limit: int,
        kinds: set[MemoryKind] | None,
    ) -> list[sqlite3.Row]:
        sql = (
            "SELECT id, kind, text, created_at, last_used_at, importance "
            "FROM memories"
        )
        params: list[object] = []
        if kinds:
            placeholders = ",".join("?" for _ in kinds)
            sql += f" WHERE kind IN ({placeholders})"
            params.extend(k.value for k in kinds)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return conn.execute(sql, params).fetchall()

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            id=int(row["id"]),
            kind=MemoryKind(row["kind"]),
            text=row["text"],
            created_at=row["created_at"],
            last_used_at=row["last_used_at"],
            importance=float(row["importance"]),
        )