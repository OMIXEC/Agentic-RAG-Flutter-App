from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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
    "aws",
    "aws_nova",
    "bedrock_nova",
    "vertex",
    "gcp_vertex",
    "legacy",
    "legacy_multimodal",
]


class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str
    captured_at: datetime | None = None
    hint_memory_type: MemoryType | None = None


class UploadUrlResponse(BaseModel):
    upload_url: str
    gcs_path: str
    expires_in: int


class IngestRequest(BaseModel):
    gcs_path: str
    media_type: MediaType
    provider: ProviderName | None = None
    title: str | None = None
    notes: str | None = None
    captured_at: datetime | None = None
    hint_memory_type: MemoryType | None = None
    tags: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    memory_id: str
    memory_type: MemoryType
    chunks_indexed: int
    provider_used: str


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


class SearchResponse(BaseModel):
    results: list[SearchResult]


class ChatRequest(BaseModel):
    message: str
    provider: ProviderName | None = None
    memory_types: list[MemoryType] | None = None
    top_k: int = Field(default=8, ge=1, le=30)


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


class TimelineResponse(BaseModel):
    items: list[SearchResult]


class PromoteResponse(BaseModel):
    promoted_count: int


class DeleteResponse(BaseModel):
    deleted: bool
