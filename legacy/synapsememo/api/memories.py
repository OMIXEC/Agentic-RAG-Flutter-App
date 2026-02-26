"""Memory API routes — /v1/memories/*.

Handles upload-url, ingest, search, chat, timeline, promote, delete.
Replaces the monolithic backend/main.py route handlers.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from synapsememo.auth import AuthUser, get_current_user
from synapsememo.config import Settings, get_settings
from synapsememo.db.database import get_db
from synapsememo.models.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    DeleteResponse,
    IngestRequest,
    IngestResponse,
    PromoteResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    TimelineResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from synapsememo.providers.router import canonical_provider_name
from synapsememo.services.chat_service import synthesize_answer, synthesize_stream
from synapsememo.services.memory_service import MemoryService
from synapsememo.storage.backends import get_storage

router = APIRouter(prefix="/v1/memories", tags=["memories"])


# ── Helpers ─────────────────────────────────────────────────────────────

def _resolve_provider(
    path_prov: str | None, payload_prov: str | None, settings: Settings
) -> str:
    raw = path_prov or payload_prov or settings.multimodal_provider
    return canonical_provider_name(raw)


# ── Upload URL ──────────────────────────────────────────────────────────

@router.post("/upload-url", response_model=UploadUrlResponse)
async def create_upload_url(
    payload: UploadUrlRequest,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    storage = get_storage(settings)
    spec = storage.create_upload_url(user.user_id, payload.filename, payload.content_type)
    return UploadUrlResponse(
        upload_url=spec.upload_url,
        storage_path=spec.storage_path,
        expires_in=spec.expires_in,
    )


# ── Ingest ──────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest_memory(
    payload: IngestRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    provider = _resolve_provider(None, payload.provider, settings)
    svc = MemoryService(db)

    memory = await svc.create_memory(
        user_id=user.user_id,
        media_type=payload.media_type,
        source_uri=payload.storage_path,
        title=payload.title or payload.storage_path.split("/")[-1],
        summary=payload.notes or "",
        captured_at=payload.captured_at,
        hint_memory_type=payload.hint_memory_type,
        tags=payload.tags,
        notes=payload.notes,
        locale=payload.locale,
        timezone_str=payload.timezone,
        provider_used=provider,
    )

    # TODO: trigger background embedding + Pinecone upsert task
    # For now, return success with 0 chunks (embedding happens async)
    return IngestResponse(
        memory_id=memory.id,
        memory_type=memory.memory_type,
        chunks_indexed=0,
        provider_used=provider,
    )


@router.post("/{provider}/ingest", response_model=IngestResponse)
async def provider_ingest_memory(
    provider: str,
    payload: IngestRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    resolved = _resolve_provider(provider, payload.provider, settings)
    svc = MemoryService(db)

    memory = await svc.create_memory(
        user_id=user.user_id,
        media_type=payload.media_type,
        source_uri=payload.storage_path,
        title=payload.title or payload.storage_path.split("/")[-1],
        summary=payload.notes or "",
        captured_at=payload.captured_at,
        hint_memory_type=payload.hint_memory_type,
        tags=payload.tags,
        notes=payload.notes,
        locale=payload.locale,
        timezone_str=payload.timezone,
        provider_used=resolved,
    )

    return IngestResponse(
        memory_id=memory.id,
        memory_type=memory.memory_type,
        chunks_indexed=0,
        provider_used=resolved,
    )


# ── Search ──────────────────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
async def search_memory(
    payload: SearchRequest,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    # TODO: wire up actual vector search via Pinecone + embedding
    # Placeholder: return empty results until embedding pipeline is wired.
    return SearchResponse(results=[])


@router.post("/{provider}/search", response_model=SearchResponse)
async def provider_search_memory(
    provider: str,
    payload: SearchRequest,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    return SearchResponse(results=[])


# ── Chat ────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_memory(
    payload: ChatRequest,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    # If client requests streaming, return SSE
    if payload.stream:
        async def event_stream() -> AsyncIterator[str]:
            async for chunk in synthesize_stream(
                f"User question: {payload.message}",
                settings=settings,
            ):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
        )

    # Non-streaming
    prompt = f"User question: {payload.message}"
    answer = await synthesize_answer(prompt, settings=settings)

    return ChatResponse(
        answer=answer,
        citations=[],
        retrieved=[],
        provider_used=canonical_provider_name(
            payload.provider or settings.multimodal_provider
        ),
    )


@router.post("/{provider}/chat", response_model=ChatResponse)
async def provider_chat_memory(
    provider: str,
    payload: ChatRequest,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    prompt = f"User question: {payload.message}"
    answer = await synthesize_answer(prompt, settings=settings)

    return ChatResponse(
        answer=answer,
        citations=[],
        retrieved=[],
        provider_used=canonical_provider_name(provider),
    )


# ── Timeline ────────────────────────────────────────────────────────────

@router.get("/timeline", response_model=TimelineResponse)
async def timeline(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    memory_type: str | None = Query(default=None),
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = MemoryService(db)
    items, total = await svc.timeline(user.user_id, limit, offset, memory_type)
    return TimelineResponse(items=items, total_count=total)


# ── Delete ──────────────────────────────────────────────────────────────

@router.delete("/{memory_id}", response_model=DeleteResponse)
async def delete_memory(
    memory_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = MemoryService(db)
    deleted = await svc.delete_memory(user.user_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return DeleteResponse(deleted=True)


# ── Promote ─────────────────────────────────────────────────────────────

@router.post("/promote", response_model=PromoteResponse)
async def promote(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = MemoryService(db)
    count = await svc.promote(user.user_id)
    return PromoteResponse(promoted_count=count)
