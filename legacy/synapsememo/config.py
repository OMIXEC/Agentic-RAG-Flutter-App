"""Centralised configuration using Pydantic BaseSettings.

All env vars are loaded from the process environment or a `.env` file.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings from env vars / .env file."""

    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "SynapseMemo"
    api_title: str = "SynapseMemo API"
    api_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── Auth (Supabase) ─────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "authenticated"
    jwt_issuer: str = ""

    # ── Database ────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///synapsememo.db",
        description="Async DB URL. Use postgresql+asyncpg://... for production.",
    )

    # ── Pinecone (vector store) ─────────────────────────────────────────
    pinecone_api_key: str = ""
    pinecone_index: str = ""
    pinecone_text_index: str = ""
    pinecone_media_index: str = ""

    # Per-provider dedicated indexes
    pinecone_index_vertex_1408: str = ""
    pinecone_index_openai_text_3072: str = ""
    pinecone_index_openai_clip_512: str = ""
    pinecone_index_aws_nova_1024: str = ""
    pinecone_index_azure_1536: str = ""

    # ── Embedding provider selection ────────────────────────────────────
    multimodal_provider: str = Field(
        default="openai_clip",
        description="Default provider: openai_clip | vertex | aws_nova | azure | legacy",
    )

    # ── OpenAI ──────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_text_embedding_dimension: int = 3072

    # ── Azure OpenAI ────────────────────────────────────────────────────
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment_name: str = ""
    azure_openai_embedding_deployment: str = ""
    azure_openai_embedding_dimension: int = 1536
    azure_openai_chat_deployment: str = ""

    # ── Google / Vertex AI ──────────────────────────────────────────────
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    google_vertex_model: str = "multimodalembedding@001"
    google_vertex_embedding_dimension: int = 1408

    # ── AWS Bedrock / Nova ──────────────────────────────────────────────
    aws_region: str = "us-east-1"
    aws_nova_embedding_model: str = "amazon.nova-2-multimodal-embeddings-v1:0"
    aws_nova_embedding_dimension: int = 1024

    # ── Storage ─────────────────────────────────────────────────────────
    gcs_bucket: str = ""
    supabase_storage_bucket: str = "memories"
    local_storage_root: str = "local_uploads"

    # ── Middleware ───────────────────────────────────────────────────────
    cors_origins: str = "*"
    rate_limit_per_minute: int = 60

    # ── Chunking ────────────────────────────────────────────────────────
    chunk_strategy: str = "paragraph"
    chunk_max_chars: int = 1200
    chunk_min_chars: int = 80
    chunk_overlap_chars: int = 0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Cached singleton for settings."""
    return Settings()
