from dataclasses import dataclass

from .config import settings


@dataclass(frozen=True)
class IndexRoute:
    text_index: str
    media_index: str
    expected_text_dim: int | None
    expected_media_dim: int | None


def route_for_provider(provider: str) -> IndexRoute:
    provider = provider.lower()
    if provider == "openai_clip":
        return IndexRoute(
            text_index=settings.pinecone_text_index,
            media_index=settings.pinecone_media_index,
            expected_text_dim=3072,
            expected_media_dim=512,
        )
    if provider == "vertex":
        return IndexRoute(
            text_index=settings.pinecone_index,
            media_index=settings.pinecone_index,
            expected_text_dim=1408,
            expected_media_dim=1408,
        )
    if provider in {"aws_nova", "aws", "bedrock_nova"}:
        return IndexRoute(
            text_index=settings.pinecone_index,
            media_index=settings.pinecone_index,
            expected_text_dim=1024,
            expected_media_dim=1024,
        )
    return IndexRoute(
        text_index=settings.pinecone_index,
        media_index=settings.pinecone_index,
        expected_text_dim=None,
        expected_media_dim=None,
    )


def validate_dim(vector: list[float], expected: int | None, index_name: str) -> None:
    if expected is None:
        return
    if len(vector) != expected:
        raise ValueError(
            f"Embedding dimension mismatch for index {index_name}: expected {expected}, got {len(vector)}"
        )
