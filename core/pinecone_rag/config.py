"""Unified configuration for multi-cloud RAG pipelines.

Provides Pydantic BaseSettings that can be used by any use case
or the backend API.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class PineconeSettings(BaseSettings):
    """Pinecone vector database configuration."""

    pinecone_api_key: str = ""
    pinecone_index: str = ""
    pinecone_text_index: str = ""
    pinecone_media_index: str = ""
    pinecone_namespace: str = "default"

    # Per-provider dedicated indexes (by embedding dimension)
    pinecone_index_vertex_1408: str = ""
    pinecone_index_openai_text_3072: str = ""
    pinecone_index_openai_clip_512: str = ""
    pinecone_index_aws_nova_1024: str = ""
    pinecone_index_azure_1536: str = ""

    # Optional host-based connections (faster than name-based)
    pinecone_index_host: str = ""
    pinecone_index_host_vertex_1408: str = ""
    pinecone_index_host_openai_text_3072: str = ""
    pinecone_index_host_openai_clip_512: str = ""
    pinecone_index_host_aws_nova_1024: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class OpenAISettings(BaseSettings):
    """OpenAI + CLIP embedding configuration."""

    openai_api_key: str = ""
    openai_text_embedding_model: str = "text-embedding-3-large"
    openai_text_embedding_dimension: int = 3072
    openai_chat_model: str = "gpt-4.1-mini"
    openai_transcription_model: str = "gpt-4o-mini-transcribe"

    # CLIP configuration
    clip_model_name: str = "clip-ViT-B-32"
    openai_clip_embedding_dimension: int = 512

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class VertexAISettings(BaseSettings):
    """Google Vertex AI multimodal embedding configuration."""

    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    google_vertex_model: str = "multimodalembedding@001"
    google_vertex_embedding_dimension: int = 1408
    google_vertex_access_token: str = ""
    google_application_credentials: str = ""
    google_vertex_gemini_model: str = "gemini-2.5-flash"
    vertex_video_gcs_bucket: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class AWSNovaSettings(BaseSettings):
    """AWS Bedrock Nova multimodal embedding configuration."""

    aws_region: str = "us-east-1"
    aws_nova_embedding_model: str = "amazon.nova-2-multimodal-embeddings-v1:0"
    aws_nova_embedding_dimension: int = 1024
    aws_nova_video_max_bytes: int = 20 * 1024 * 1024  # 20MB

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class AzureOpenAISettings(BaseSettings):
    """Azure OpenAI embedding configuration."""

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment_name: str = ""
    azure_openai_embedding_deployment: str = ""
    azure_openai_embedding_dimension: int = 1536
    azure_openai_chat_deployment: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class ChunkingSettings(BaseSettings):
    """Text chunking configuration."""

    chunk_strategy: str = "paragraph"
    chunk_max_chars: int = 1200
    chunk_min_chars: int = 80
    chunk_overlap_chars: int = 0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class DataSettings(BaseSettings):
    """Data folder configuration."""

    data_folder: str = "data/txt"
    text_data_folder: str = "data/txt"
    image_data_folder: str = "data/image"
    video_data_folder: str = "data/video"
    audio_data_folder: str = "data/audio"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def resolve_folder(self, path_value: str) -> Path:
        """Resolve a data folder path relative to the project root."""
        path = Path(path_value)
        if path.is_absolute():
            return path
        return Path.cwd() / path
