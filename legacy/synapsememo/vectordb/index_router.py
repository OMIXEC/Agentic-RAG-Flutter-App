"""Provider → Pinecone-index routing.

Maps each embedding provider to the correct Pinecone index and its
expected vector dimension.  Now includes Azure OpenAI.
"""

from __future__ import annotations

from dataclasses import dataclass

from synapsememo.config import get_settings


@dataclass(frozen=True)
class IndexRoute:
    text_index: str
    media_index: str
    expected_text_dim: int | None
    expected_media_dim: int | None


def route_for_provider(provider: str) -> IndexRoute:
    """Return the Pinecone index route for the given provider name."""
    settings = get_settings()
    provider = provider.lower().strip()

    if provider == "openai_clip":
        return IndexRoute(
            text_index=settings.pinecone_text_index or settings.pinecone_index,
            media_index=settings.pinecone_media_index or settings.pinecone_index,
            expected_text_dim=settings.openai_text_embedding_dimension,
            expected_media_dim=512,
        )

    if provider in {"azure", "azure_openai"}:
        return IndexRoute(
            text_index=settings.pinecone_index_azure_1536 or settings.pinecone_index,
            media_index=settings.pinecone_index_azure_1536 or settings.pinecone_index,
            expected_text_dim=settings.azure_openai_embedding_dimension,
            expected_media_dim=settings.azure_openai_embedding_dimension,
        )

    if provider == "vertex":
        return IndexRoute(
            text_index=settings.pinecone_index_vertex_1408 or settings.pinecone_index,
            media_index=settings.pinecone_index_vertex_1408 or settings.pinecone_index,
            expected_text_dim=settings.google_vertex_embedding_dimension,
            expected_media_dim=settings.google_vertex_embedding_dimension,
        )

    if provider in {"aws_nova", "aws", "bedrock_nova"}:
        return IndexRoute(
            text_index=settings.pinecone_index_aws_nova_1024 or settings.pinecone_index,
            media_index=settings.pinecone_index_aws_nova_1024 or settings.pinecone_index,
            expected_text_dim=settings.aws_nova_embedding_dimension,
            expected_media_dim=settings.aws_nova_embedding_dimension,
        )

    if provider == "openai":
        return IndexRoute(
            text_index=settings.pinecone_index_openai_text_3072 or settings.pinecone_index,
            media_index=settings.pinecone_index_openai_text_3072 or settings.pinecone_index,
            expected_text_dim=settings.openai_text_embedding_dimension,
            expected_media_dim=settings.openai_text_embedding_dimension,
        )

    # Fallback — generic index
    return IndexRoute(
        text_index=settings.pinecone_index,
        media_index=settings.pinecone_index,
        expected_text_dim=None,
        expected_media_dim=None,
    )


def validate_dim(vector: list[float], expected: int | None, index_name: str) -> None:
    """Fail-fast dimension validation before Pinecone upsert."""
    if expected is None:
        return
    if len(vector) != expected:
        raise ValueError(
            f"Embedding dimension mismatch for index {index_name}: "
            f"expected {expected}, got {len(vector)}"
        )
