"""API request / response schemas.

Extended from the original backend/schemas.py with Azure provider, user
profile models, streaming status, and worldwide user metadata.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Domain literals ─────────────────────────────────────────────────────

MemoryType = Literal[
    "life_memory",
    "preferences",
    "hobbies",
    "general_knowledge",
    "episodic_memory",
    "long_term_memory",
]

MediaType = Literal["text", "document", "image", "video", "audio"]

ProviderName = Literal[
    "openai",
    "openai_clip",
    "azure",
    "azure_openai",
    "aws",
    "aws_nova",
    "bedrock_nova",
    "vertex",
    "gcp_vertex",
    "legacy",
    "legacy_multimodal",
]


# ── Upload ──────────────────────────────────────────────────────────────

class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str
    captured_at: datetime | None = None
    hint_memory_type: MemoryType | None = None


class UploadUrlResponse(BaseModel):
    upload_url: str
    storage_path: str
    expires_in: int = 900


# ── Ingest ──────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    storage_path: str = Field(
        ...,
        description="Path returned from upload-url (gs://, supabase://, file://)",
        alias="gcs_path",  # backward compat with old clients
    )
    media_type: MediaType
    provider: ProviderName | None = None
    title: str | None = None
    notes: str | None = None
    captured_at: datetime | None = None
    hint_memory_type: MemoryType | None = None
    tags: list[str] = Field(default_factory=list)
    locale: str | None = Field(None, description="ISO 639-1 language code")
    timezone: str | None = Field(None, description="IANA tz, e.g. America/New_York")

    model_config = {"populate_by_name": True}


class IngestResponse(BaseModel):
    memory_id: str
    memory_type: MemoryType
    chunks_indexed: int
    provider_used: str


# ── Search ──────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    provider: ProviderName | None = None
    memory_types: list[MemoryType] | None = None
    media_types: list[MediaType] | None = None
    top_k: int = Field(default=8, ge=1, le=30)


class SearchResult(BaseModel):
    memory_id: str
    score: float
    summary: str
    media_type: MediaType
    memory_type: MemoryType
    source_uri: str
    title: str
    captured_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    results: list[SearchResult]


# ── Chat ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    provider: ProviderName | None = None
    memory_types: list[MemoryType] | None = None
    top_k: int = Field(default=8, ge=1, le=30)
    stream: bool = False
    conversation_id: str | None = None


class Citation(BaseModel):
    memory_id: str
    source_uri: str
    title: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved: list[SearchResult]
    confidence: str | None = None
    provider_used: str | None = None
    conversation_id: str | None = None


# ── Timeline ────────────────────────────────────────────────────────────

class TimelineResponse(BaseModel):
    items: list[SearchResult]
    total_count: int = 0


# ── Memory management ──────────────────────────────────────────────────

class PromoteResponse(BaseModel):
    promoted_count: int


class DeleteResponse(BaseModel):
    deleted: bool


# ── Processing status ──────────────────────────────────────────────────

class ProcessingStatus(BaseModel):
    memory_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress_pct: int = 0
    error: str | None = None


# ── User profile ────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    user_id: str
    display_name: str | None = None
    email: str | None = None
    locale: str | None = None
    timezone: str | None = None
    preferred_provider: ProviderName | None = None
    created_at: datetime | None = None


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    locale: str | None = None
    timezone: str | None = None
    preferred_provider: ProviderName | None = None
