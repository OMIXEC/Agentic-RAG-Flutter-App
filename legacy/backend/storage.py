import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from google.cloud import storage

from .config import settings


@dataclass
class UploadSpec:
    upload_url: str
    gcs_path: str
    expires_in: int


class StorageService:
    def __init__(self) -> None:
        self.bucket_name = settings.gcs_bucket
        self.local_root = Path(settings.local_storage_root)
        self.local_root.mkdir(parents=True, exist_ok=True)

    def _object_name(self, user_id: str, filename: str) -> str:
        safe = filename.replace("/", "_")
        return f"{user_id}/{uuid.uuid4()}-{safe}"

    def create_upload_url(self, user_id: str, filename: str, content_type: str) -> UploadSpec:
        object_name = self._object_name(user_id, filename)
        if self.bucket_name:
            client = storage.Client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(object_name)
            upload_url = blob.generate_signed_url(
                version="v4",
                expiration=15 * 60,
                method="PUT",
                content_type=content_type,
            )
            return UploadSpec(
                upload_url=upload_url,
                gcs_path=f"gs://{self.bucket_name}/{object_name}",
                expires_in=900,
            )

        local_path = self.local_root / object_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        return UploadSpec(upload_url=f"file://{local_path}", gcs_path=f"file://{local_path}", expires_in=900)

    def read_bytes(self, source_path: str) -> bytes:
        if source_path.startswith("gs://"):
            if not self.bucket_name:
                raise ValueError("GCS path provided but GCS_BUCKET is not configured")
            without_prefix = source_path.removeprefix("gs://")
            bucket_name, _, object_name = without_prefix.partition("/")
            if not bucket_name or not object_name:
                raise ValueError("Invalid gs:// path")
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            return blob.download_as_bytes()

        if source_path.startswith("file://"):
            path = Path(source_path.removeprefix("file://"))
            return path.read_bytes()

        path = Path(source_path)
        if path.exists():
            return path.read_bytes()

        raise FileNotFoundError(f"Source does not exist: {source_path}")
