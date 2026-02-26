"""Unified Memory Service.

Orchestrates ingestion, search, and chat using core multimodal providers.
"""

from __future__ import annotations

import json
import uuid
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import db
from .classifier import classify_hybrid
from .config import settings
from .diagnostics import IngestDiagnostic
from .fusion import weighted_rrf
from .schemas import IngestRequest, SearchResult, SearchResponse
from .storage import StorageService

# Core RAG imports
from core.pinecone_rag.embeddings.openai_provider import OpenAIProvider
from core.pinecone_rag.embeddings.vertex_provider import VertexProvider
from core.pinecone_rag.embeddings.aws_nova_provider import AWSNovaProvider
from core.pinecone_rag.pinecone_client import upsert_vectors, query_index
from core.pinecone_rag.chunking import chunk_text

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class MemoryService:
    def __init__(self) -> None:
        self.storage = StorageService()
        self._providers = {
            "openai": OpenAIProvider(settings),
            "vertex": VertexProvider(settings),
            "aws_nova": AWSNovaProvider(settings),
        }
        self.default_provider_name = settings.multimodal_provider
        
    def _get_provider(self, name: str | None = None):
        name = name or self.default_provider_name
        if name not in self._providers:
            # Fallback to vertex if configured, else openai
            name = "vertex" if "vertex" in self._providers else "openai"
        return self._providers[name]

    def resolve_provider(self, name: str | None = None) -> str:
        return self._get_provider(name).name

    def ingest(self, user_id: str, payload: IngestRequest, provider_name: str | None = None) -> tuple[str, str, int, str]:
        provider = self._get_provider(provider_name)
        file_bytes = self.storage.read_bytes(payload.gcs_path)
        suffix = Path(payload.gcs_path).suffix.lower() or self._suffix_for_media(payload.media_type)
        diagnostics = IngestDiagnostic()

        text_for_classification = payload.notes or payload.title or payload.gcs_path
        targets = []

        # Handle different media types using core providers
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            tmp_path = Path(tmp.name)

            if payload.media_type == "text":
                text = file_bytes.decode("utf-8", errors="ignore")
                text_for_classification = payload.notes or text[:2000]
                # Use core chunking
                for chunk in chunk_text(text):
                    targets.extend(provider.build_text_targets(chunk, Path(payload.gcs_path), kind="text"))
            elif payload.media_type == "document":
                # For now, treat documents as text if possible, or use provider's document handling if available
                # Note: core providers mostly assume file paths for multimodal
                text = file_bytes.decode("utf-8", errors="ignore")
                text_for_classification = payload.notes or text[:2000]
                for chunk in chunk_text(text):
                    targets.extend(provider.build_text_targets(chunk, Path(payload.gcs_path), kind="doc"))
            elif payload.media_type == "image":
                desc = payload.notes or f"Image memory: {payload.gcs_path}"
                text_for_classification = desc
                targets = provider.build_image_targets(tmp_path, description=desc, source_url=payload.gcs_path)
            elif payload.media_type == "video":
                desc = payload.notes or f"Video memory: {payload.gcs_path}"
                text_for_classification = desc
                targets = provider.build_video_targets(tmp_path, description=desc)
            elif payload.media_type == "audio":
                targets = provider.build_audio_targets(tmp_path)
            else:
                raise ValueError(f"Unsupported media type: {payload.media_type}")

        if not targets:
            raise ValueError("No embeddings were produced for the provided payload")

        # Classify memory type
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
            metadata.update({
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
            })
            
            # Simple unique ID for the vector
            vector_id = f"{memory_id}_{chunk_idx}"
            
            grouped_vectors[target.index_name].append({
                "id": vector_id,
                "values": target.vector,
                "metadata": metadata
            })
            vector_ids_by_index[target.index_name].append(vector_id)
            diagnostics.add_success()

        # Upsert to Pinecone using core client
        for index_name, vectors in grouped_vectors.items():
            upsert_vectors(
                index_name=index_name,
                vectors=vectors,
                pinecone_api_key=settings.pinecone_api_key,
                namespace=user_id,
                expected_dim=None, # Dimensions validated inside providers
                index_host=getattr(settings, f"pinecone_index_host", "") # Simplified host resolution
            )
            db.insert_vectors(memory_id=memory_id, user_id=user_id, index_name=index_name, vector_ids=vector_ids_by_index[index_name])

        # Save to Local DB
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

        return memory_id, memory_type, diagnostics.success_count, provider.name

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int,
        memory_types: list[str] | None,
        media_types: list[str] | None,
        provider_name: str | None = None,
    ) -> list[SearchResult]:
        provider = self._get_provider(provider_name)
        query_targets = provider.build_query_targets(query)

        # Build Pinecone filters
        metadata_filter = {}
        if memory_types:
            metadata_filter["memory_type"] = {"$in": memory_types}
        if media_types:
            metadata_filter["media_type"] = {"$in": media_types}
            
        per_source_results: dict[str, list[dict[str, Any]]] = {}

        for target in query_targets:
            matches = query_index(
                index_name=target.index_name,
                vector=target.vector,
                pinecone_api_key=settings.pinecone_api_key,
                namespace=user_id,
                top_k=top_k,
                index_host=getattr(settings, f"pinecone_index_host", "")
            )
            
            source_rows = []
            for match in matches:
                meta = match.get("metadata", {})
                mid = meta.get("memory_id")
                if not mid: continue
                source_rows.append({
                    "memory_id": mid,
                    "score": float(match.get("score", 0.0)),
                    "summary": meta.get("summary", meta.get("text", "")),
                    "media_type": meta.get("media_type", "text"),
                    "memory_type": meta.get("memory_type", "general_knowledge"),
                    "source_uri": meta.get("source_uri", ""),
                    "title": meta.get("title", "Untitled"),
                })
            per_source_results[target.label] = source_rows

        # Fusion
        fused = weighted_rrf(per_source_results)
        retrieved_ids = [row["memory_id"] for row in fused]
        db.increment_retrieval(retrieved_ids)
        
        return [
            SearchResult(
                memory_id=row["memory_id"],
                score=row.get("fused_score", row.get("score", 0.0)),
                summary=row["summary"],
                media_type=row["media_type"],
                memory_type=row["memory_type"],
                source_uri=row["source_uri"],
                title=row["title"],
            )
            for row in fused[:top_k]
        ]

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
        
        # Group by index for batch deletion
        by_index = defaultdict(list)
        for row in vector_rows:
            by_index[row["index_name"]].append(row["vector_id"])
            
        # TODO: Implement batch delete in core client if missing, but for now use direct pc
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        for index_name, ids in by_index.items():
            idx = pc.Index(index_name)
            idx.delete(ids=ids, namespace=user_id)
            
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
