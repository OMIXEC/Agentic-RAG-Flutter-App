"""Memory CRUD service — async, ORM-based.

Replaces the SQLite-direct operations from backend/db.py and the 
MemoryService.timeline / delete / promote methods from backend/service.py.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from synapsememo.models.db_models import Memory, MemoryVector, UserProfile
from synapsememo.models.schemas import (
    IngestResponse,
    MemoryType,
    SearchResult,
)
from synapsememo.services.classifier import classify_hybrid


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryService:
    """High-level memory CRUD backed by async SQLAlchemy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Create ──────────────────────────────────────────────────────────

    async def create_memory(
        self,
        *,
        user_id: str,
        media_type: str,
        source_uri: str,
        title: str,
        summary: str,
        captured_at: datetime | None = None,
        hint_memory_type: MemoryType | None = None,
        tags: list[str] | None = None,
        notes: str | None = None,
        locale: str | None = None,
        timezone_str: str | None = None,
        provider_used: str | None = None,
    ) -> Memory:
        memory_type, _conf, _reason = classify_hybrid(
            text=f"{title} {summary}",
            media_type=media_type,
            hint=hint_memory_type,
        )
        memory = Memory(
            id=uuid.uuid4().hex,
            user_id=user_id,
            memory_type=memory_type,
            media_type=media_type,
            source_uri=source_uri,
            title=title or "Untitled",
            summary=summary,
            captured_at=captured_at or _utc_now(),
            ingested_at=_utc_now(),
            tags_json=json.dumps(tags or []),
            notes=notes,
            locale=locale,
            timezone_str=timezone_str,
            provider_used=provider_used,
        )
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        return memory

    # ── Record vectors ──────────────────────────────────────────────────

    async def record_vectors(
        self,
        memory_id: str,
        user_id: str,
        index_name: str,
        vector_ids: list[str],
    ) -> None:
        for vid in vector_ids:
            self.db.add(
                MemoryVector(
                    vector_id=vid,
                    memory_id=memory_id,
                    user_id=user_id,
                    index_name=index_name,
                    created_at=_utc_now(),
                )
            )
        await self.db.commit()

    # ── Timeline / List ─────────────────────────────────────────────────

    async def timeline(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        memory_type: str | None = None,
    ) -> tuple[list[SearchResult], int]:
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id, Memory.is_deleted == False)
        )
        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)

        count_result = await self.db.execute(
            select(Memory.id).where(Memory.user_id == user_id, Memory.is_deleted == False)
        )
        total = len(count_result.all())

        stmt = stmt.order_by(Memory.captured_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        items = [
            SearchResult(
                memory_id=m.id,
                score=0.0,
                summary=m.summary,
                media_type=m.media_type,
                memory_type=m.memory_type,
                source_uri=m.source_uri,
                title=m.title,
                captured_at=m.captured_at,
                tags=json.loads(m.tags_json) if m.tags_json else [],
            )
            for m in rows
        ]
        return items, total

    # ── Delete (soft) ───────────────────────────────────────────────────

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        stmt = (
            update(Memory)
            .where(Memory.id == memory_id, Memory.user_id == user_id)
            .values(is_deleted=True)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0  # type: ignore[union-attr]

    # ── Promote episodic → long-term ────────────────────────────────────

    async def promote(self, user_id: str) -> int:
        stmt = (
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.is_deleted == False,
                Memory.memory_type == "episodic_memory",
            )
            .where(
                (Memory.pinned == True)
                | (Memory.retrieval_count >= 3)
                | (Memory.retrieval_count >= 2)
            )
        )
        result = await self.db.execute(stmt)
        candidates = result.scalars().all()

        count = 0
        for mem in candidates:
            mem.memory_type = "long_term_memory"
            mem.promotion_state = "long_term_memory"
            count += 1

        if count:
            await self.db.commit()
        return count

    # ── Increment retrieval count ───────────────────────────────────────

    async def increment_retrieval(self, memory_ids: list[str]) -> None:
        if not memory_ids:
            return
        for mid in memory_ids:
            await self.db.execute(
                update(Memory)
                .where(Memory.id == mid)
                .values(retrieval_count=Memory.retrieval_count + 1)
            )
        await self.db.commit()

    # ── Get memory with vectors ─────────────────────────────────────────

    async def get_memory_with_vectors(
        self, user_id: str, memory_id: str
    ) -> tuple[Memory | None, list[MemoryVector]]:
        mem_result = await self.db.execute(
            select(Memory).where(
                Memory.id == memory_id,
                Memory.user_id == user_id,
                Memory.is_deleted == False,
            )
        )
        memory = mem_result.scalar_one_or_none()

        vec_result = await self.db.execute(
            select(MemoryVector).where(
                MemoryVector.memory_id == memory_id,
                MemoryVector.user_id == user_id,
            )
        )
        vectors = list(vec_result.scalars().all())
        return memory, vectors

    # ── User profile ────────────────────────────────────────────────────

    async def get_or_create_profile(
        self, user_id: str, email: str | None = None
    ) -> UserProfile:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile

        profile = UserProfile(
            user_id=user_id,
            email=email,
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile
