import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .config import settings


@dataclass
class MemoryRecord:
    id: str
    user_id: str
    memory_type: str
    media_type: str
    source_uri: str
    title: str
    summary: str
    captured_at: str
    ingested_at: str
    promotion_state: str
    retrieval_count: int
    pinned: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn() -> Iterable[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                media_type TEXT NOT NULL,
                source_uri TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                promotion_state TEXT NOT NULL DEFAULT 'episodic_memory',
                retrieval_count INTEGER NOT NULL DEFAULT 0,
                pinned INTEGER NOT NULL DEFAULT 0,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_vectors (
                vector_id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                index_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def insert_memory(record: MemoryRecord, metadata_json: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO memories (
                id, user_id, memory_type, media_type, source_uri, title, summary,
                captured_at, ingested_at, promotion_state, retrieval_count, pinned, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.user_id,
                record.memory_type,
                record.media_type,
                record.source_uri,
                record.title,
                record.summary,
                record.captured_at,
                record.ingested_at,
                record.promotion_state,
                record.retrieval_count,
                record.pinned,
                metadata_json,
            ),
        )
        conn.commit()


def insert_vectors(memory_id: str, user_id: str, index_name: str, vector_ids: list[str]) -> None:
    with get_conn() as conn:
        for vector_id in vector_ids:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_vectors (vector_id, memory_id, user_id, index_name, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (vector_id, memory_id, user_id, index_name, utc_now_iso()),
            )
        conn.commit()


def list_memories(user_id: str, limit: int, offset: int, memory_type: str | None = None) -> list[sqlite3.Row]:
    query = """
        SELECT * FROM memories
        WHERE user_id = ? AND is_deleted = 0
    """
    params: list[object] = [user_id]
    if memory_type:
        query += " AND memory_type = ?"
        params.append(memory_type)
    query += " ORDER BY captured_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return rows


def increment_retrieval(memory_ids: list[str]) -> None:
    if not memory_ids:
        return
    with get_conn() as conn:
        conn.executemany(
            "UPDATE memories SET retrieval_count = retrieval_count + 1 WHERE id = ?",
            [(memory_id,) for memory_id in memory_ids],
        )
        conn.commit()


def get_memory_with_vectors(user_id: str, memory_id: str) -> tuple[sqlite3.Row | None, list[sqlite3.Row]]:
    with get_conn() as conn:
        memory = conn.execute(
            "SELECT * FROM memories WHERE id = ? AND user_id = ? AND is_deleted = 0",
            (memory_id, user_id),
        ).fetchone()
        vectors = conn.execute(
            "SELECT * FROM memory_vectors WHERE memory_id = ? AND user_id = ?",
            (memory_id, user_id),
        ).fetchall()
    return memory, vectors


def soft_delete_memory(user_id: str, memory_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE memories SET is_deleted = 1 WHERE id = ? AND user_id = ?",
            (memory_id, user_id),
        )
        conn.commit()


def promote_memories(user_id: str) -> int:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id FROM memories
            WHERE user_id = ? AND is_deleted = 0 AND memory_type = 'episodic_memory'
              AND (
                pinned = 1 OR
                retrieval_count >= 3 OR
                (retrieval_count >= 2 AND captured_at <= datetime('now', '-30 day'))
              )
            """,
            (user_id,),
        ).fetchall()
        ids = [row["id"] for row in rows]
        if ids:
            conn.executemany(
                "UPDATE memories SET memory_type = 'long_term_memory', promotion_state='long_term_memory' WHERE id = ?",
                [(memory_id,) for memory_id in ids],
            )
            conn.commit()
    return len(ids)
