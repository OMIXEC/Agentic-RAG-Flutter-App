import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import db
from .classifier import classify_hybrid
from .config import settings
from .diagnostics import IngestDiagnostic
from .fusion import weighted_rrf
from .index_router import route_for_provider, validate_dim
from .pinecone_store import PineconeStore, group_ids_by_index
from .provider_runtime import ProviderRuntime
from .schemas import IngestRequest, SearchResult
from .storage import StorageService
from providers.router import canonical_provider_name


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryService:
    def __init__(self) -> None:
        self._default_provider = canonical_provider_name(settings.multimodal_provider, default="openai")
        self.runtime = ProviderRuntime(self._default_provider)
        self.storage = StorageService()
        self.pinecone = PineconeStore(settings.pinecone_api_key)
        self.route = route_for_provider(self.runtime.provider_name)
        self._runtime_cache: dict[str, ProviderRuntime] = {self.runtime.provider_name: self.runtime}
        self._route_cache = {self.runtime.provider_name: self.route}

    def resolve_provider(self, provider: str | None = None) -> str:
        return self._normalize_provider(provider)

    def _default_provider_name(self) -> str:
        if hasattr(self, "_default_provider"):
            return getattr(self, "_default_provider")
        runtime = getattr(self, "runtime", None)
        if runtime and getattr(runtime, "provider_name", None):
            return canonical_provider_name(runtime.provider_name, default="openai")
        return canonical_provider_name(settings.multimodal_provider, default="openai")

    def _normalize_provider(self, provider: str | None = None) -> str:
        return canonical_provider_name(provider, default=self._default_provider_name())

    def _runtime_for(self, provider: str | None = None) -> ProviderRuntime:
        normalized = self._normalize_provider(provider)
        cache: dict[str, ProviderRuntime] = getattr(self, "_runtime_cache", {})
        if normalized in cache:
            return cache[normalized]

        runtime = getattr(self, "runtime", None)
        if runtime and getattr(runtime, "provider_name", None) == normalized:
            cache[normalized] = runtime
            self._runtime_cache = cache
            return runtime

        runtime = ProviderRuntime(normalized)
        cache[normalized] = runtime
        self._runtime_cache = cache
        return runtime

    def _route_for(self, provider: str | None = None):
        normalized = self._normalize_provider(provider)
        cache = getattr(self, "_route_cache", {})
        if normalized in cache:
            return cache[normalized]

        default_route = getattr(self, "route", None)
        if provider is None and default_route is not None:
            cache[normalized] = default_route
            self._route_cache = cache
            return default_route

        route = route_for_provider(normalized)
        cache[normalized] = route
        self._route_cache = cache
        return route

    def ingest(self, user_id: str, payload: IngestRequest, provider: str | None = None) -> tuple[str, str, int, str]:
        runtime = self._runtime_for(provider)
        route = self._route_for(provider)

        file_bytes = self.storage.read_bytes(payload.gcs_path)
        suffix = Path(payload.gcs_path).suffix.lower() or self._suffix_for_media(payload.media_type)
        diagnostics = IngestDiagnostic()

        text_for_classification = payload.notes or payload.title or payload.gcs_path

        targets = []
        if payload.media_type == "text":
            text = file_bytes.decode("utf-8", errors="ignore")
            text_for_classification = payload.notes or text[:2000]
            targets = runtime.build_text_targets(text=text, source_name=payload.gcs_path, kind="text")
        elif payload.media_type == "document":
            # v1 backend-first: treat bytes as decodable text if possible.
            text = file_bytes.decode("utf-8", errors="ignore")
            text_for_classification = payload.notes or text[:2000]
            targets = runtime.build_text_targets(text=text, source_name=payload.gcs_path, kind="doc")
        elif payload.media_type == "image":
            desc = payload.notes or f"Image memory: {payload.gcs_path}"
            text_for_classification = desc
            targets = runtime.build_image_targets(
                file_bytes=file_bytes,
                suffix=suffix,
                description=desc,
                source_url=payload.gcs_path,
            )
        elif payload.media_type == "video":
            desc = payload.notes or f"Video memory: {payload.gcs_path}"
            text_for_classification = desc
            targets = runtime.build_video_targets(file_bytes=file_bytes, suffix=suffix, description=desc)
        elif payload.media_type == "audio":
            targets = runtime.build_audio_targets(file_bytes=file_bytes, suffix=suffix)
        else:
            raise ValueError(f"Unsupported media type: {payload.media_type}")

        if not targets:
            raise ValueError("No embeddings were produced for the provided payload")

        memory_type, confidence, reason = classify_hybrid(
            text=text_for_classification,
            media_type=payload.media_type,
            hint=payload.hint_memory_type,
        )

        memory_id = str(uuid.uuid4())
        grouped_vectors: dict[str, list[dict[str, Any]]] = defaultdict(list)
        vector_ids_by_index: dict[str, list[str]] = defaultdict(list)

        for chunk_idx, target in enumerate(targets):
            metadata = dict(target.metadata)
            metadata.update(
                {
                    "memory_id": memory_id,
                    "user_id": user_id,
                    "memory_type": memory_type,
                    "media_type": payload.media_type,
                    "source_uri": payload.gcs_path,
                    "title": payload.title or Path(payload.gcs_path).name,
                    "summary": (payload.notes or metadata.get("text", ""))[:500],
                    "captured_at": (payload.captured_at.isoformat() if payload.captured_at else now_iso()),
                    "ingested_at": now_iso(),
                    "classification_confidence": confidence,
                    "classification_reason": reason,
                    "chunk_index": chunk_idx,
                    "tags": payload.tags,
                }
            )
            vector_id = self.pinecone.build_vector_id(
                memory_id=memory_id,
                source=payload.gcs_path,
                text=metadata.get("text", ""),
                chunk_index=chunk_idx,
            )
            expected_dim = route.expected_media_dim if payload.media_type in {"image", "video"} else route.expected_text_dim
            validate_dim(target.vector, expected_dim, target.index_name)
            grouped_vectors[target.index_name].append(
                {"id": vector_id, "values": target.vector, "metadata": metadata}
            )
            vector_ids_by_index[target.index_name].append(vector_id)
            diagnostics.add_success()

        for index_name, vectors in grouped_vectors.items():
            self.pinecone.upsert(index_name=index_name, namespace=user_id, vectors=vectors)
            db.insert_vectors(memory_id=memory_id, user_id=user_id, index_name=index_name, vector_ids=vector_ids_by_index[index_name])

        db.insert_memory(
            db.MemoryRecord(
                id=memory_id,
                user_id=user_id,
                memory_type=memory_type,
                media_type=payload.media_type,
                source_uri=payload.gcs_path,
                title=payload.title or Path(payload.gcs_path).name,
                summary=(payload.notes or text_for_classification)[:500],
                captured_at=(payload.captured_at.isoformat() if payload.captured_at else now_iso()),
                ingested_at=now_iso(),
                promotion_state=("long_term_memory" if memory_type == "long_term_memory" else "episodic_memory"),
                retrieval_count=0,
                pinned=0,
            ),
            metadata_json=json.dumps({"tags": payload.tags, "classification_reason": reason}),
        )

        return memory_id, memory_type, diagnostics.success_count, runtime.provider_name

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int,
        memory_types: list[str] | None,
        media_types: list[str] | None,
        provider: str | None = None,
    ) -> list[SearchResult]:
        runtime = self._runtime_for(provider)
        query_targets = runtime.query_targets(query)

        memory_type_filter = None
        if memory_types:
            memory_type_filter = {"memory_type": {"$in": memory_types}}

        media_type_filter = None
        if media_types:
            media_type_filter = {"media_type": {"$in": media_types}}

        merged_filter: dict[str, Any] | None = None
        if memory_type_filter and media_type_filter:
            merged_filter = {"$and": [memory_type_filter, media_type_filter]}
        elif memory_type_filter:
            merged_filter = memory_type_filter
        elif media_type_filter:
            merged_filter = media_type_filter

        per_source_results: dict[str, list[dict[str, Any]]] = {}

        for target in query_targets:
            matches = self.pinecone.query(
                index_name=target.index_name,
                namespace=user_id,
                vector=target.vector,
                top_k=top_k,
                metadata_filter=merged_filter,
            )
            source_rows: list[dict[str, Any]] = []
            for match in matches:
                metadata = match.get("metadata", {})
                memory_id = metadata.get("memory_id")
                if not memory_id:
                    continue
                source_rows.append(
                    {
                        "memory_id": memory_id,
                        "score": float(match.get("score", 0.0)),
                        "summary": metadata.get("summary", metadata.get("text", "")),
                        "media_type": metadata.get("media_type", metadata.get("modality", "text")),
                        "memory_type": metadata.get("memory_type", "general_knowledge"),
                        "source_uri": metadata.get("source_uri", metadata.get("filename", "")),
                        "title": metadata.get("title", "Untitled"),
                    }
                )
            per_source_results[target.label] = source_rows

        fused = weighted_rrf(
            per_source_results,
            weights={"text": 1.0, "media": 0.8, "vertex": 1.0, "aws_nova": 0.9},
        )
        retrieved_ids = [row["memory_id"] for row in fused]
        db.increment_retrieval(retrieved_ids)
        output = [
            SearchResult(
                memory_id=row["memory_id"],
                score=float(row.get("fused_score", row.get("score", 0.0))),
                summary=row["summary"],
                media_type=row["media_type"],
                memory_type=row["memory_type"],
                source_uri=row["source_uri"],
                title=row["title"],
            )
            for row in fused[:top_k]
        ]
        return output

    def timeline(self, user_id: str, limit: int, offset: int, memory_type: str | None) -> list[SearchResult]:
        items = db.list_memories(user_id=user_id, limit=limit, offset=offset, memory_type=memory_type)
        return [
            SearchResult(
                memory_id=row["id"],
                score=0.0,
                summary=row["summary"],
                media_type=row["media_type"],
                memory_type=row["memory_type"],
                source_uri=row["source_uri"],
                title=row["title"],
            )
            for row in items
        ]

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        memory, vector_rows = db.get_memory_with_vectors(user_id=user_id, memory_id=memory_id)
        if not memory:
            return False
        by_index = group_ids_by_index(vector_rows)
        self.pinecone.delete_ids(namespace=user_id, by_index=by_index)
        db.soft_delete_memory(user_id=user_id, memory_id=memory_id)
        return True

    def promote(self, user_id: str) -> int:
        return db.promote_memories(user_id=user_id)

    @staticmethod
    def _suffix_for_media(media_type: str) -> str:
        return {
            "text": ".txt",
            "document": ".txt",
            "image": ".jpg",
            "video": ".mp4",
            "audio": ".wav",
        }.get(media_type, ".bin")
