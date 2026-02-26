"""Storage backends — Supabase Storage, GCS, and local filesystem.

Provides a unified interface for file upload URL generation and
file downloads regardless of where files are stored.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from synapsememo.config import Settings, get_settings


@dataclass
class UploadSpec:
    upload_url: str
    storage_path: str
    expires_in: int = 900


class StorageBackend(Protocol):
    """Protocol for pluggable storage backends."""

    def create_upload_url(
        self, user_id: str, filename: str, content_type: str
    ) -> UploadSpec: ...

    def read_bytes(self, source_path: str) -> bytes: ...


# ── Local Storage ───────────────────────────────────────────────────────

class LocalStorage:
    """Filesystem-based storage for development."""

    def __init__(self, root: str = "local_uploads") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _object_path(self, user_id: str, filename: str) -> Path:
        safe = filename.replace("/", "_")
        return self.root / user_id / f"{uuid.uuid4()}-{safe}"

    def create_upload_url(
        self, user_id: str, filename: str, content_type: str
    ) -> UploadSpec:
        path = self._object_path(user_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        return UploadSpec(
            upload_url=f"file://{path}",
            storage_path=f"file://{path}",
        )

    def read_bytes(self, source_path: str) -> bytes:
        if source_path.startswith("file://"):
            source_path = source_path.removeprefix("file://")
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {source_path}")
        return path.read_bytes()


# ── GCS Storage ─────────────────────────────────────────────────────────

class GCSStorage:
    """Google Cloud Storage backend."""

    def __init__(self, bucket_name: str) -> None:
        from google.cloud import storage
        self.client = storage.Client()
        self.bucket_name = bucket_name
        self.bucket = self.client.bucket(bucket_name)

    def _object_name(self, user_id: str, filename: str) -> str:
        safe = filename.replace("/", "_")
        return f"{user_id}/{uuid.uuid4()}-{safe}"

    def create_upload_url(
        self, user_id: str, filename: str, content_type: str
    ) -> UploadSpec:
        obj = self._object_name(user_id, filename)
        blob = self.bucket.blob(obj)
        url = blob.generate_signed_url(
            version="v4", expiration=900, method="PUT", content_type=content_type
        )
        return UploadSpec(
            upload_url=url,
            storage_path=f"gs://{self.bucket_name}/{obj}",
        )

    def read_bytes(self, source_path: str) -> bytes:
        if not source_path.startswith("gs://"):
            raise ValueError(f"Not a GCS path: {source_path}")
        without_prefix = source_path.removeprefix("gs://")
        bucket_name, _, object_name = without_prefix.partition("/")
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        return blob.download_as_bytes()


# ── Factory ─────────────────────────────────────────────────────────────

def get_storage(settings: Settings | None = None) -> StorageBackend:
    """Return the appropriate storage backend based on configuration."""
    settings = settings or get_settings()

    if settings.gcs_bucket:
        return GCSStorage(settings.gcs_bucket)

    return LocalStorage(settings.local_storage_root)
