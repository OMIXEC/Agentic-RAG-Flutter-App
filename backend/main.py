"""Unified Backend API.

Entry point for the FastAPI service used by the SynapseMemo Flutter app.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query
from .auth import AuthUser, get_current_user
from .config import settings
from .db import init_db
from .llm import synthesize_answer
from .schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    DeleteResponse,
    IngestRequest,
    IngestResponse,
    PromoteResponse,
    SearchRequest,
    SearchResponse,
    TimelineResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from .service import MemoryService
from .storage import StorageService

app = FastAPI(title=settings.api_title)

@app.on_event("startup")
def startup() -> None:
    init_db()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": settings.multimodal_provider}

@app.post("/v1/memories/upload-url", response_model=UploadUrlResponse)
def create_upload_url(
    payload: UploadUrlRequest,
    user: AuthUser = Depends(get_current_user),
) -> UploadUrlResponse:
    storage = StorageService()
    spec = storage.create_upload_url(user_id=user.user_id, filename=payload.filename, content_type=payload.content_type)
    return UploadUrlResponse(upload_url=spec.upload_url, gcs_path=spec.gcs_path, expires_in=spec.expires_in)

@app.post("/v1/memories/ingest", response_model=IngestResponse)
def ingest_memory(
    payload: IngestRequest,
    user: AuthUser = Depends(get_current_user),
) -> IngestResponse:
    service = MemoryService()
    try:
        memory_id, memory_type, chunks, provider = service.ingest(
            user_id=user.user_id,
            payload=payload,
            provider_name=payload.provider,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return IngestResponse(
        memory_id=memory_id,
        memory_type=memory_type,
        chunks_indexed=chunks,
        provider_used=provider,
    )

@app.post("/v1/memories/search", response_model=SearchResponse)
def search_memory(
    payload: SearchRequest,
    user: AuthUser = Depends(get_current_user),
) -> SearchResponse:
    service = MemoryService()
    try:
        results = service.search(
            user_id=user.user_id,
            query=payload.query,
            top_k=payload.top_k,
            memory_types=payload.memory_types,
            media_types=payload.media_types,
            provider_name=payload.provider,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SearchResponse(results=results)

@app.post("/v1/memories/chat", response_model=ChatResponse)
def chat_memory(
    payload: ChatRequest,
    user: AuthUser = Depends(get_current_user),
) -> ChatResponse:
    service = MemoryService()
    provider_name = payload.provider
    results = service.search(
        user_id=user.user_id,
        query=payload.message,
        top_k=payload.top_k,
        memory_types=payload.memory_types,
        media_types=None,
        provider_name=provider_name,
    )

    context = "\n\n".join(
        f"[{r.memory_type}/{r.media_type}] {r.title}: {r.summary} ({r.source_uri})"
        for r in results
    )
    prompt = (
        "You are a grounded memory retrieval assistant.\n"
        f"Question: {payload.message}\n\n"
        f"Retrieved context:\n{context}\n\n"
        "Rules:\n"
        "1) Use retrieved context only.\n"
        "2) If insufficient evidence, reply exactly: I don't have enough info to answer.\n"
        "3) Keep answer concise.\n"
        "4) Do not invent places, dates, events, or sources.\n"
    )
    answer = synthesize_answer(prompt)

    citations = [Citation(memory_id=r.memory_id, source_uri=r.source_uri, title=r.title) for r in results]
    confidence = "high" if len(citations) >= 3 else ("medium" if len(citations) >= 1 else "low")
    return ChatResponse(
        answer=answer,
        citations=citations,
        retrieved=results,
        confidence=confidence,
        provider_used=service.resolve_provider(provider_name),
    )

@app.get("/v1/memories/timeline", response_model=TimelineResponse)
def timeline(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    memory_type: str | None = Query(default=None),
    user: AuthUser = Depends(get_current_user),
) -> TimelineResponse:
    service = MemoryService()
    items = service.timeline(user_id=user.user_id, limit=limit, offset=offset, memory_type=memory_type)
    return TimelineResponse(items=items)

@app.delete("/v1/memories/{memory_id}", response_model=DeleteResponse)
def delete_memory(memory_id: str, user: AuthUser = Depends(get_current_user)) -> DeleteResponse:
    service = MemoryService()
    deleted = service.delete_memory(user_id=user.user_id, memory_id=memory_id)
    return DeleteResponse(deleted=deleted)

@app.post("/v1/memories/promote", response_model=PromoteResponse)
def promote(user: AuthUser = Depends(get_current_user)) -> PromoteResponse:
    service = MemoryService()
    promoted = service.promote(user_id=user.user_id)
    return PromoteResponse(promoted_count=promoted)
