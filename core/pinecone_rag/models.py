"""Shared data models for the RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class IndexTarget:
    """A vector + metadata destined for a specific Pinecone index."""
    index_name: str
    vector: list[float]
    metadata: dict[str, Any]


@dataclass
class QueryTarget:
    """A query vector targeting a specific Pinecone index."""
    index_name: str
    vector: list[float]
    label: str


class BaseProvider:
    """Abstract base for embedding providers.

    Each provider must implement: validate, text_index, media_index,
    build_text_targets, build_image_targets, build_video_targets,
    build_audio_targets, build_query_targets.
    """

    def __init__(self, config: Any) -> None:
        self.config = config

    def validate(self) -> None:
        raise NotImplementedError

    def text_index(self) -> str:
        return self.config.pinecone_index

    def media_index(self) -> str:
        return self.config.pinecone_index

    def build_text_targets(
        self, chunk: str, source_file: Path, kind: str
    ) -> list[IndexTarget]:
        raise NotImplementedError

    def build_image_targets(
        self, file_path: Path, description: str, source_url: str
    ) -> list[IndexTarget]:
        raise NotImplementedError

    def build_video_targets(
        self, file_path: Path, description: str
    ) -> list[IndexTarget]:
        raise NotImplementedError

    def build_audio_targets(self, file_path: Path) -> list[IndexTarget]:
        raise NotImplementedError

    def build_query_targets(self, query: str) -> list[QueryTarget]:
        raise NotImplementedError
