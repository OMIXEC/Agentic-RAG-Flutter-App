"""Unified backend configuration.

Combines core RAG settings with API-specific settings like Auth and DB.
"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

# Import core settings classes
from core.pinecone_rag.config import (
    PineconeSettings,
    OpenAISettings,
    VertexAISettings,
    AWSNovaSettings,
    AzureOpenAISettings,
)

class BackendSettings(
    PineconeSettings,
    OpenAISettings,
    VertexAISettings,
    AWSNovaSettings,
    AzureOpenAISettings,
):
    """Aggregated settings for the backend API."""

    api_title: str = Field(default="Search Memory API", env="API_TITLE")
    
    # JWT / Auth
    jwt_secret: str = Field(default="dev-secret-change-me", env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_audience: str = Field(default="search-memory", env="JWT_AUDIENCE")
    jwt_issuer: str = Field(default="search-memory-backend", env="JWT_ISSUER")
    
    # Provider selection
    multimodal_provider: str = Field(default="vertex", env="MULTIMODAL_PROVIDER")
    
    # Storage
    gcs_bucket: str = Field(default="", env="GCS_BUCKET")
    local_storage_root: str = Field(default="local_uploads", env="LOCAL_STORAGE_ROOT")
    
    # Relational DB
    db_path: str = Field(default="search_memory.db", env="MEMORY_DB_PATH")

    # Supabase
    supabase_url: str = Field(default="", env="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", env="SUPABASE_ANON_KEY")
    supabase_jwt_secret: str = Field(default="", env="SUPABASE_JWT_SECRET")

    @property
    def resolved_gcs_bucket(self) -> str:
        """Fallback to vertex_video_gcs_bucket if gcs_bucket is not set."""
        return self.gcs_bucket or self.vertex_video_gcs_bucket

@lru_cache()
def get_settings() -> BackendSettings:
    """Singleton settings instance."""
    return BackendSettings()

settings = get_settings()
