"""Azure OpenAI embedding provider for Pinecone RAG.

Uses Azure OpenAI Service for text embeddings. Single Pinecone index
(1536d by default for text-embedding-ada-002 or text-embedding-3-small).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import OpenAI

from ..models import BaseProvider, IndexTarget, QueryTarget


class AzureOpenAIProvider(BaseProvider):
    """Azure OpenAI text embeddings — single unified Pinecone index.

    Uses the Azure OpenAI SDK (via openai library with azure endpoint).
    Supports text-only embeddings; media is indexed via text descriptions.
    """

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self._client = OpenAI(
            api_key=config.azure_openai_api_key,
            base_url=(
                f"{config.azure_openai_endpoint}/openai/deployments/"
                f"{config.azure_openai_embedding_deployment or config.azure_openai_deployment_name}"
            ),
            default_headers={"api-key": config.azure_openai_api_key},
            default_query={"api-version": getattr(config, "azure_openai_api_version", "2024-12-01-preview")},
        )
        self._idx = getattr(config, "pinecone_index_azure_1536", "") or config.pinecone_index
        self._dim = getattr(config, "azure_openai_embedding_dimension", 1536)
        self._deployment = (
            getattr(config, "azure_openai_embedding_deployment", "")
            or getattr(config, "azure_openai_deployment_name", "")
        )

    def validate(self) -> None:
        if not self.config.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is required for azure provider")
        if not self.config.azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required for azure provider")
        if not self._deployment:
            raise ValueError(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT or AZURE_OPENAI_DEPLOYMENT_NAME is required"
            )
        if not self._idx:
            raise ValueError("PINECONE_INDEX_AZURE_1536 (or PINECONE_INDEX) is required")

    def text_index(self) -> str:
        return self._idx

    def media_index(self) -> str:
        return self._idx

    def _embed_text(self, text: str) -> list[float]:
        response = self._client.embeddings.create(
            model=self._deployment,
            input=text,
        )
        return list(response.data[0].embedding)

    def build_text_targets(
        self, chunk: str, source_file: Path, kind: str
    ) -> list[IndexTarget]:
        vector = self._embed_text(chunk)
        return [
            IndexTarget(
                index_name=self.text_index(),
                vector=vector,
                metadata={"filename": str(source_file), "modality": kind, "text": chunk},
            )
        ]

    def build_image_targets(
        self, file_path: Path, description: str, source_url: str
    ) -> list[IndexTarget]:
        # Azure OpenAI is text-only — embed the image description
        vector = self._embed_text(description)
        return [
            IndexTarget(
                index_name=self.text_index(),
                vector=vector,
                metadata={
                    "filename": str(file_path),
                    "modality": "image",
                    "media_type": "image",
                    "text": description,
                    "source_url": source_url,
                },
            )
        ]

    def build_video_targets(
        self, file_path: Path, description: str
    ) -> list[IndexTarget]:
        # Azure OpenAI is text-only — embed the video description
        vector = self._embed_text(description)
        if not vector:
            return []
        return [
            IndexTarget(
                index_name=self.text_index(),
                vector=vector,
                metadata={
                    "filename": str(file_path),
                    "modality": "video",
                    "media_type": "video",
                    "text": description,
                },
            )
        ]

    def build_audio_targets(self, file_path: Path) -> list[IndexTarget]:
        # Azure doesn't have native audio embedding — transcribe first if possible
        return []

    def build_query_targets(self, query: str) -> list[QueryTarget]:
        vector = self._embed_text(query)
        return [
            QueryTarget(index_name=self.text_index(), vector=vector, label="azure_openai")
        ]
