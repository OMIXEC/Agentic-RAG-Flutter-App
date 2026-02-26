"""Pinecone index management — upsert, query, preflight validation.

Provides a clean interface for Pinecone operations independent of
any specific embedding provider.
"""

from __future__ import annotations

from typing import Any, Iterable

from pinecone import Pinecone, PineconeException

from .models import BaseProvider


def validate_vector_dimensions(
    index_name: str, vectors: list[dict[str, Any]], expected_dim: int | None
) -> None:
    """Fail-fast dimension validation before Pinecone upsert."""
    if not vectors or expected_dim is None:
        return
    bad = [
        len(vector.get("values", []))
        for vector in vectors
        if len(vector.get("values", [])) != expected_dim
    ]
    if bad:
        sample = bad[0]
        raise ValueError(
            f"Dimension mismatch before Pinecone upsert for index '{index_name}': "
            f"expected {expected_dim}, got {sample}"
        )


def get_index_client(
    pc: Pinecone,
    index_name: str,
    index_host: str = "",
):
    """Get a Pinecone index client, preferring host-based connection."""
    if not index_host and (index_name.startswith("http://") or index_name.startswith("https://")):
        index_host = index_name
    
    if index_host:
        return pc.Index(host=index_host)
    return pc.Index(index_name)


def upsert_vectors(
    index_name: str,
    vectors: Iterable[dict[str, Any]],
    pinecone_api_key: str,
    namespace: str,
    expected_dim: int | None,
    index_host: str = "",
) -> None:
    """Upsert vectors to a Pinecone index with dimension validation."""
    vectors_list = list(vectors)
    if not vectors_list:
        return
    validate_vector_dimensions(
        index_name=index_name, vectors=vectors_list, expected_dim=expected_dim
    )
    try:
        pc = Pinecone(api_key=pinecone_api_key)
        index = get_index_client(pc, index_name, index_host)
        index.upsert(vectors=vectors_list, namespace=namespace, show_progress=True)
    except PineconeException as exc:
        detail = getattr(exc, "body", "") or str(exc)
        raise RuntimeError(
            "Pinecone upsert failed. "
            f"index={index_name}, namespace={namespace}, expected_dim={expected_dim}, "
            f"vector_count={len(vectors_list)}. detail={detail}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            "Pinecone upsert failed with unexpected error. "
            f"index={index_name}, namespace={namespace}, expected_dim={expected_dim}, "
            f"vector_count={len(vectors_list)}. detail={exc}"
        ) from exc


def query_index(
    index_name: str,
    vector: list[float],
    pinecone_api_key: str,
    namespace: str,
    top_k: int = 5,
    index_host: str = "",
    include_metadata: bool = True,
) -> list[dict[str, Any]]:
    """Query a Pinecone index and return matches."""
    pc = Pinecone(api_key=pinecone_api_key)
    index = get_index_client(pc, index_name, index_host)
    response = index.query(
        vector=vector,
        top_k=top_k,
        namespace=namespace,
        include_metadata=include_metadata,
    )
    return response.get("matches", [])


def preflight_pinecone_indexes(
    pinecone_api_key: str,
    provider: BaseProvider,
    expected_dims: dict[str, int | None] | None = None,
) -> None:
    """Validate Pinecone indexes exist with correct dimensions before operations.

    Args:
        pinecone_api_key: Pinecone API key
        provider: The embedding provider to get target indexes from
        expected_dims: Mapping of index_name -> expected dimension
    """
    if expected_dims is None:
        expected_dims = {}

    pc = Pinecone(api_key=pinecone_api_key)
    indexes = {provider.text_index(), provider.media_index()}
    errors: list[str] = []

    for index_name in sorted(indexes):
        expected_dim = expected_dims.get(index_name)
        try:
            info = pc.describe_index(name=index_name)
        except Exception as exc:
            errors.append(
                f"index={index_name}: describe failed ({exc}). "
                "Check if index exists and API key can access Pinecone control plane."
            )
            continue

        actual_dim = getattr(info, "dimension", None)
        if (
            expected_dim is not None
            and actual_dim is not None
            and int(actual_dim) != int(expected_dim)
        ):
            errors.append(
                f"index={index_name}: dimension mismatch "
                f"(expected {expected_dim}, actual {actual_dim}). "
                "Create/use a dedicated index with matching dimension."
            )

    if errors:
        detail = "\n".join(f"- {line}" for line in errors)
        raise RuntimeError(
            "Pinecone preflight validation failed.\n" f"{detail}"
        )
