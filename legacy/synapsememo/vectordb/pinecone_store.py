"""Pinecone vector-store operations.

Migrated from backend/pinecone_store.py with identical API but cleaner
package-level imports.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from pinecone import Pinecone


class PineconeStore:
    """Thin wrapper around Pinecone client for upsert / query / delete."""

    def __init__(self, api_key: str) -> None:
        self.pc = Pinecone(api_key=api_key)

    # ── Vector ID generation ────────────────────────────────────────────

    @staticmethod
    def build_vector_id(
        memory_id: str, source: str, text: str, chunk_index: int
    ) -> str:
        payload = f"{memory_id}|{source}|{chunk_index}|{text}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    # ── Upsert ──────────────────────────────────────────────────────────

    def upsert(
        self,
        index_name: str,
        namespace: str,
        vectors: list[dict[str, Any]],
    ) -> None:
        if not vectors:
            return
        index = self.pc.Index(index_name)
        index.upsert(vectors=vectors, namespace=namespace, show_progress=True)

    # ── Query ───────────────────────────────────────────────────────────

    def query(
        self,
        index_name: str,
        namespace: str,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        index = self.pc.Index(index_name)
        response = index.query(
            namespace=namespace,
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter=metadata_filter,
        )
        return response.get("matches", [])

    # ── Delete ──────────────────────────────────────────────────────────

    def delete_ids(
        self, namespace: str, by_index: dict[str, list[str]]
    ) -> None:
        for index_name, ids in by_index.items():
            if not ids:
                continue
            index = self.pc.Index(index_name)
            index.delete(ids=ids, namespace=namespace)


def group_ids_by_index(rows: list[Any]) -> dict[str, list[str]]:
    """Group vector rows by their Pinecone index name."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        idx = row.index_name if hasattr(row, "index_name") else row["index_name"]
        vid = row.vector_id if hasattr(row, "vector_id") else row["vector_id"]
        grouped[idx].append(vid)
    return dict(grouped)
