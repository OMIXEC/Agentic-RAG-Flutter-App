import argparse
import base64
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from pinecone.core.openapi.shared.exceptions import PineconeApiException

load_dotenv()

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".xml"}
DOC_EXTENSIONS = {".pdf", ".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def _env(key: str, default: str = "") -> str:
    value = os.getenv(key)
    return value if value else default


def _resolve_openai_text_expected_dim(model: str, configured_dim: int) -> int:
    normalized_model = (model or "").strip().lower()
    if normalized_model == "text-embedding-3-large":
        return 3072
    return configured_dim


def _resolve_clip_expected_dim(model: str, configured_dim: int) -> int:
    """Map CLIP model names to their embedding dimensions."""
    normalized_model = (model or "").strip().lower()
    # Known CLIP model dimensions from sentence-transformers
    clip_dimensions = {
        "clip-vit-b-32": 512,
        "clip-vit-b-16": 512,
        "clip-vit-l-14": 768,
        "clip-vit-h-14": 1024,
        "clip-vit-bigg-14": 1280,
    }
    for key, dim in clip_dimensions.items():
        if key in normalized_model:
            return dim
    return configured_dim


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _collect_files(folder: Path, extensions: set[str]) -> list[Path]:
    if not folder.exists():
        return []
    files: list[Path] = []
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            files.append(path)
    return sorted(files)


def _chunk_text(
    text: str,
    max_chars: int = 1200,
    min_chars: int = 80,
    overlap_chars: int = 0,
) -> list[str]:
    """
    Split text into chunks with optional overlap.

    Args:
        text: Input text to chunk
        max_chars: Maximum characters per chunk
        min_chars: Minimum characters for a valid chunk
        overlap_chars: Characters to overlap between adjacent chunks

    Returns:
        List of text chunks
    """
    chunks: list[str] = []
    pending = ""

    for part in text.split("\n\n"):
        block = part.strip()
        if not block:
            continue

        if len(pending) + len(block) + 2 <= max_chars:
            pending = f"{pending}\n\n{block}".strip()
        else:
            if len(pending) >= min_chars:
                chunks.append(pending)
            pending = block

    if len(pending) >= min_chars:
        chunks.append(pending)

    # Apply overlap if configured
    if overlap_chars > 0 and len(chunks) > 1:
        overlapped: list[str] = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk: append from next
                if i + 1 < len(chunks):
                    suffix = chunks[i + 1][:overlap_chars]
                    overlapped.append(f"{chunk}\n...{suffix}")
                else:
                    overlapped.append(chunk)
            elif i == len(chunks) - 1:
                # Last chunk: prepend from previous
                prefix = chunks[i - 1][-overlap_chars:]
                overlapped.append(f"{prefix}...\n{chunk}")
            else:
                # Middle chunk: prepend and append
                prefix = chunks[i - 1][-overlap_chars:]
                suffix = chunks[i + 1][:overlap_chars]
                overlapped.append(f"{prefix}...\n{chunk}\n...{suffix}")
        return overlapped

    return chunks


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using regex patterns."""
    # Pattern matches sentence-ending punctuation followed by space or end
    sentence_endings = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
    sentences = sentence_endings.split(text)
    return [s.strip() for s in sentences if s.strip()]


def _chunk_semantic(
    text: str,
    max_chars: int = 1200,
    min_chars: int = 80,
    overlap_chars: int = 0,
) -> list[str]:
    """
    Chunk text respecting sentence boundaries.

    Groups sentences into chunks that don't exceed max_chars,
    preferring to break at paragraph boundaries when possible.
    """
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        sentences = _split_sentences(para)

        for sentence in sentences:
            sent_len = len(sentence)

            if current_length + sent_len + 1 <= max_chars:
                current_chunk.append(sentence)
                current_length += sent_len + 1
            else:
                # Flush current chunk if it meets minimum
                if current_chunk and sum(len(s) for s in current_chunk) >= min_chars:
                    chunks.append(" ".join(current_chunk))

                # Start new chunk with this sentence
                current_chunk = [sentence]
                current_length = sent_len

        # End of paragraph - flush if we have enough
        if current_chunk and sum(len(s) for s in current_chunk) >= min_chars:
            chunk_text = " ".join(current_chunk)
            if not chunks or chunks[-1] != chunk_text:
                chunks.append(chunk_text)
            current_chunk = []
            current_length = 0

    # Handle remaining content
    if current_chunk and sum(len(s) for s in current_chunk) >= min_chars:
        chunks.append(" ".join(current_chunk))

    # Apply overlap (same logic as _chunk_text)
    if overlap_chars > 0 and len(chunks) > 1:
        overlapped: list[str] = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                if i + 1 < len(chunks):
                    suffix = chunks[i + 1][:overlap_chars]
                    overlapped.append(f"{chunk} ...{suffix}")
                else:
                    overlapped.append(chunk)
            elif i == len(chunks) - 1:
                prefix = chunks[i - 1][-overlap_chars:]
                overlapped.append(f"{prefix}... {chunk}")
            else:
                prefix = chunks[i - 1][-overlap_chars:]
                suffix = chunks[i + 1][:overlap_chars]
                overlapped.append(f"{prefix}... {chunk} ...{suffix}")
        return overlapped

    return chunks


def chunk_text_with_strategy(
    text: str,
    strategy: str,
    max_chars: int = 1200,
    min_chars: int = 80,
    overlap_chars: int = 0,
) -> list[str]:
    """
    Chunk text using the specified strategy.

    Args:
        text: Input text to chunk
        strategy: Chunking strategy ("paragraph", "semantic", "recursive")
        max_chars: Maximum characters per chunk
        min_chars: Minimum characters for a valid chunk
        overlap_chars: Characters to overlap between adjacent chunks

    Returns:
        List of text chunks
    """
    strategy = (strategy or "paragraph").lower().strip()

    if strategy == "semantic":
        return _chunk_semantic(text, max_chars, min_chars, overlap_chars)
    elif strategy == "paragraph":
        return _chunk_text(text, max_chars, min_chars, overlap_chars)
    else:
        # Default to paragraph for unknown strategies
        print(f"Warning: Unknown chunking strategy '{strategy}', using 'paragraph'")
        return _chunk_text(text, max_chars, min_chars, overlap_chars)


def _hard_split_text(text: str, max_chars: int) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    chunks: list[str] = []
    cursor = 0
    while cursor < len(normalized):
        chunks.append(normalized[cursor : cursor + max_chars])
        cursor += max_chars
    return chunks


def _provider_folder_env(provider: str, kind: str) -> str:
    alias = {
        "openai_clip": "OPENAI",
        "vertex": "VERTEX",
        "aws_nova": "AWS",
        "aws": "AWS",
        "bedrock_nova": "AWS",
        "legacy_multimodal": "LEGACY",
        "legacy": "LEGACY",
    }.get(provider, provider.upper())
    return f"{kind}_DATA_FOLDER_{alias}"


def _resolve_data_folder(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path

    env_file = _env("ENV_FILE")
    if env_file:
        base = Path(env_file).expanduser().resolve().parent
        return (base / path).resolve()

    # Default to repository root (where this pipeline file lives) for stable behavior
    # when scripts are launched from subdirectories.
    repo_root = Path(__file__).resolve().parent
    return (repo_root / path).resolve()


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def _extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _extract_docx_text(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def _extract_document_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf_text(path)
    if ext == ".docx":
        return _extract_docx_text(path)
    return ""


def _load_media_manifest(folder: Path) -> dict[str, dict[str, str]]:
    manifest_path = folder / "media_manifest.txt"
    if not manifest_path.exists():
        return {}

    data: dict[str, dict[str, str]] = {}
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        data[parts[0]] = {
            "description": parts[1],
            "source_url": parts[2] if len(parts) > 2 else "",
        }
    return data


@dataclass
class IndexTarget:
    index_name: str
    vector: list[float]
    metadata: dict[str, Any]


@dataclass
class QueryTarget:
    index_name: str
    vector: list[float]
    label: str


@dataclass
class PipelineConfig:
    provider: str

    pinecone_api_key: str
    pinecone_index: str
    pinecone_text_index: str
    pinecone_media_index: str
    pinecone_index_vertex_1408: str
    pinecone_index_openai_text_3072: str
    pinecone_index_openai_clip_512: str
    pinecone_index_aws_nova_1024: str
    pinecone_index_legacy_text: str
    pinecone_index_legacy_media: str
    pinecone_index_host: str
    pinecone_index_host_vertex_1408: str
    pinecone_index_host_openai_text_3072: str
    pinecone_index_host_openai_clip_512: str
    pinecone_index_host_aws_nova_1024: str
    pinecone_index_host_legacy_text: str
    pinecone_index_host_legacy_media: str
    pinecone_namespace: str

    text_folder: Path
    image_folder: Path
    video_folder: Path
    audio_folder: Path

    openai_api_key: str
    openai_text_embedding_model: str
    openai_chat_model: str
    openai_transcription_model: str
    clip_model_name: str
    openai_clip_strict: bool
    openai_text_expected_dim: int
    openai_clip_expected_dim: int

    google_cloud_project: str
    google_cloud_location: str
    google_vertex_model: str
    google_vertex_embedding_dimension: int
    google_vertex_access_token: str
    gcs_upload_bucket: str
    google_vertex_expected_dim: int

    aws_region: str
    aws_nova_model_id: str
    aws_nova_embedding_dimension: int
    aws_nova_expected_dim: int

    # Chunking configuration
    chunk_strategy: str
    chunk_max_chars: int
    chunk_min_chars: int
    chunk_overlap_chars: int

    video_frame_sample_count: int
    pinecone_preflight: bool

    @classmethod
    def from_env(cls, provider_override: str | None = None) -> "PipelineConfig":
        provider = (
            provider_override or _env("MULTIMODAL_PROVIDER", "openai_clip")
        ).lower()
        generic_index = _env("PINECONE_INDEX")
        vertex_index = _env("PINECONE_INDEX_VERTEX_1408", generic_index)
        openai_text_index = _env(
            "PINECONE_INDEX_OPENAI_TEXT_3072",
            _env("PINECONE_TEXT_INDEX", generic_index),
        )
        openai_clip_index = _env(
            "PINECONE_INDEX_OPENAI_CLIP_512",
            _env("PINECONE_MEDIA_INDEX", openai_text_index),
        )
        aws_index = _env("PINECONE_INDEX_AWS_NOVA_1024", generic_index)
        legacy_text_index = _env(
            "PINECONE_INDEX_LEGACY_TEXT", _env("PINECONE_TEXT_INDEX", generic_index)
        )
        legacy_media_index = _env(
            "PINECONE_INDEX_LEGACY_MEDIA",
            _env("PINECONE_MEDIA_INDEX", legacy_text_index),
        )

        provider_default_index = {
            "vertex": vertex_index,
            "openai_clip": openai_text_index,
            "aws_nova": aws_index,
            "aws": aws_index,
            "bedrock_nova": aws_index,
            "legacy_multimodal": legacy_text_index,
        }.get(provider, generic_index)

        text_folder = _resolve_data_folder(
            _env(
                _provider_folder_env(provider, "TEXT"),
                _env("TEXT_DATA_FOLDER", _env("DATA_FOLDER", "data/txt")),
            )
        )
        image_folder = _resolve_data_folder(
            _env(
                _provider_folder_env(provider, "IMAGE"),
                _env("IMAGE_DATA_FOLDER", "data/image"),
            )
        )
        video_folder = _resolve_data_folder(
            _env(
                _provider_folder_env(provider, "VIDEO"),
                _env("VIDEO_DATA_FOLDER", "data/video"),
            )
        )
        audio_folder = _resolve_data_folder(
            _env(
                _provider_folder_env(provider, "AUDIO"),
                _env("AUDIO_DATA_FOLDER", "data/audio"),
            )
        )

        openai_text_embedding_model = _env(
            "OPENAI_TEXT_EMBEDDING_MODEL",
            _env("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
        )
        configured_openai_text_dim = int(
            _env("OPENAI_TEXT_EMBEDDING_DIMENSION", "3072")
        )
        resolved_openai_text_dim = _resolve_openai_text_expected_dim(
            model=openai_text_embedding_model,
            configured_dim=configured_openai_text_dim,
        )

        return cls(
            provider=provider,
            pinecone_api_key=_env("PINECONE_API_KEY"),
            pinecone_index=provider_default_index,
            pinecone_text_index=openai_text_index,
            pinecone_media_index=openai_clip_index,
            pinecone_index_vertex_1408=vertex_index,
            pinecone_index_openai_text_3072=openai_text_index,
            pinecone_index_openai_clip_512=openai_clip_index,
            pinecone_index_aws_nova_1024=aws_index,
            pinecone_index_legacy_text=legacy_text_index,
            pinecone_index_legacy_media=legacy_media_index,
            pinecone_index_host=_env("PINECONE_INDEX_HOST"),
            pinecone_index_host_vertex_1408=_env("PINECONE_INDEX_HOST_VERTEX_1408"),
            pinecone_index_host_openai_text_3072=_env(
                "PINECONE_INDEX_HOST_OPENAI_TEXT_3072"
            ),
            pinecone_index_host_openai_clip_512=_env(
                "PINECONE_INDEX_HOST_OPENAI_CLIP_512"
            ),
            pinecone_index_host_aws_nova_1024=_env("PINECONE_INDEX_HOST_AWS_NOVA_1024"),
            pinecone_index_host_legacy_text=_env("PINECONE_INDEX_HOST_LEGACY_TEXT"),
            pinecone_index_host_legacy_media=_env("PINECONE_INDEX_HOST_LEGACY_MEDIA"),
            pinecone_namespace=_env("PINECONE_NAMESPACE", "global"),
            text_folder=text_folder,
            image_folder=image_folder,
            video_folder=video_folder,
            audio_folder=audio_folder,
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_text_embedding_model=openai_text_embedding_model,
            openai_chat_model=_env("OPENAI_CHAT_MODEL", "gpt-4.1-mini"),
            openai_transcription_model=_env(
                "OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe"
            ),
            clip_model_name=_env("CLIP_MODEL_NAME", "clip-ViT-B-32"),
            openai_clip_strict=_env("OPENAI_CLIP_STRICT", "true").lower()
            in {"1", "true", "yes"},
            openai_text_expected_dim=resolved_openai_text_dim,
            openai_clip_expected_dim=_resolve_clip_expected_dim(
                _env("CLIP_MODEL_NAME", "clip-ViT-B-32"),
                int(_env("OPENAI_CLIP_EMBEDDING_DIMENSION", "512")),
            ),
            google_cloud_project=_env("GOOGLE_CLOUD_PROJECT"),
            google_cloud_location=_env("GOOGLE_CLOUD_LOCATION", "us-central1"),
            google_vertex_model=_env("GOOGLE_VERTEX_MODEL", "multimodalembedding@001"),
            google_vertex_embedding_dimension=int(
                _env("GOOGLE_VERTEX_EMBEDDING_DIMENSION", "1408")
            ),
            google_vertex_access_token=_env("GOOGLE_VERTEX_ACCESS_TOKEN"),
            gcs_upload_bucket=_env("VERTEX_VIDEO_GCS_BUCKET"),
            google_vertex_expected_dim=int(
                _env("GOOGLE_VERTEX_EXPECTED_DIMENSION", "1408")
            ),
            aws_region=_env("AWS_REGION", "us-east-1"),
            aws_nova_model_id=_env(
                "AWS_NOVA_EMBEDDING_MODEL", "amazon.nova-2-multimodal-embeddings-v1:0"
            ),
            aws_nova_embedding_dimension=int(
                _env("AWS_NOVA_EMBEDDING_DIMENSION", "1024")
            ),
            aws_nova_expected_dim=int(_env("AWS_NOVA_EXPECTED_DIMENSION", "1024")),
            chunk_strategy=_env("CHUNK_STRATEGY", "paragraph"),
            chunk_max_chars=int(_env("CHUNK_MAX_CHARS", "1200")),
            chunk_min_chars=int(_env("CHUNK_MIN_CHARS", "80")),
            chunk_overlap_chars=int(_env("CHUNK_OVERLAP_CHARS", "0")),
            video_frame_sample_count=max(1, int(_env("VIDEO_FRAME_SAMPLE_COUNT", "4"))),
            pinecone_preflight=_env("PINECONE_PREFLIGHT", "true").lower()
            in {"1", "true", "yes", "on"},
        )


class BaseProvider:
    def __init__(self, config: PipelineConfig):
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


class OpenAIClipProvider(BaseProvider):
    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.openai = OpenAI(api_key=config.openai_api_key)
        self._clip = None
        self._compat_same_index_mode = (
            config.pinecone_media_index == config.pinecone_text_index
        )

    def validate(self) -> None:
        if not self.config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for openai_clip provider")
        if not self.config.pinecone_text_index:
            raise ValueError("PINECONE_TEXT_INDEX (or PINECONE_INDEX) is required")
        if self._compat_same_index_mode:
            raise ValueError(
                "OpenAI pipeline requires strict index separation: "
                "PINECONE_INDEX_OPENAI_TEXT_3072 and PINECONE_INDEX_OPENAI_CLIP_512 "
                "must be different indexes."
            )

        # Validate CLIP dimension matches expected index dimension
        expected_clip_dim = self.config.openai_clip_expected_dim
        # This will be validated during preflight, but early warning is helpful
        clip_model = self.config.clip_model_name.lower()
        if "vit-l-14" in clip_model and expected_clip_dim != 768:
            print(
                f"Warning: CLIP model {self.config.clip_model_name} produces 768d vectors, "
                f"but OPENAI_CLIP_EMBEDDING_DIMENSION is {expected_clip_dim}. "
                f"Ensure Pinecone index dimension matches."
            )
        elif "vit-h-14" in clip_model and expected_clip_dim != 1024:
            print(
                f"Warning: CLIP model {self.config.clip_model_name} produces 1024d vectors, "
                f"but OPENAI_CLIP_EMBEDDING_DIMENSION is {expected_clip_dim}. "
                f"Ensure Pinecone index dimension matches."
            )
        elif "vit-bigg-14" in clip_model and expected_clip_dim != 1280:
            print(
                f"Warning: CLIP model {self.config.clip_model_name} produces 1280d vectors, "
                f"but OPENAI_CLIP_EMBEDDING_DIMENSION is {expected_clip_dim}. "
                f"Ensure Pinecone index dimension matches."
            )

    def text_index(self) -> str:
        return self.config.pinecone_text_index

    def media_index(self) -> str:
        return self.config.pinecone_media_index

    def _clip_model(self):
        if self._clip is None:
            from sentence_transformers import SentenceTransformer

            model_name = self.config.clip_model_name
            print(f"Loading CLIP model: {model_name}")
            self._clip = SentenceTransformer(model_name)
            # Verify dimension matches expected
            test_embedding = self._clip.encode(["test"], normalize_embeddings=True)[0]
            actual_dim = len(test_embedding)
            if actual_dim != self.config.openai_clip_expected_dim:
                print(
                    f"Warning: CLIP model {model_name} produces {actual_dim}d vectors, "
                    f"but config expects {self.config.openai_clip_expected_dim}d. "
                    f"Update OPENAI_CLIP_EMBEDDING_DIMENSION or use matching Pinecone index."
                )
        return self._clip

    def _embed_text_openai(self, text: str) -> list[float]:
        kwargs: dict[str, Any] = {
            "model": self.config.openai_text_embedding_model,
            "input": text,
        }
        # text-embedding-3-* models support dimension shortening.
        if self.config.openai_text_expected_dim > 0:
            kwargs["dimensions"] = self.config.openai_text_expected_dim
        response = self.openai.embeddings.create(**kwargs)
        return list(response.data[0].embedding)

    def _embed_image_clip(self, file_path: Path) -> list[float]:
        from PIL import Image

        with Image.open(file_path) as image:
            vector = self._clip_model().encode(
                [image.convert("RGB")], normalize_embeddings=True
            )[0]
        return list(vector)

    def _embed_video_clip(self, file_path: Path) -> list[float]:
        import cv2
        from PIL import Image

        capture = cv2.VideoCapture(str(file_path))
        if not capture.isOpened():
            return []

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0 or self.config.video_frame_sample_count == 1:
            positions = [0]
        else:
            positions = sorted(
                int((frame_count - 1) * i / (self.config.video_frame_sample_count - 1))
                for i in range(self.config.video_frame_sample_count)
            )

        vectors: list[np.ndarray] = []
        for pos in positions:
            capture.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ok, frame = capture.read()
            if not ok:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            vec = self._clip_model().encode([image], normalize_embeddings=True)[0]
            vectors.append(np.array(vec))
        capture.release()

        if not vectors:
            return []
        pooled = np.mean(np.array(vectors), axis=0)
        norm = np.linalg.norm(pooled)
        if norm > 0:
            pooled = pooled / norm
        return list(pooled)

    def _transcribe(self, file_path: Path) -> str:
        with file_path.open("rb") as file_obj:
            result = self.openai.audio.transcriptions.create(
                model=self.config.openai_transcription_model,
                file=file_obj,
            )
        return getattr(result, "text", "")

    def build_text_targets(
        self, chunk: str, source_file: Path, kind: str
    ) -> list[IndexTarget]:
        vector = self._embed_text_openai(chunk)
        return [
            IndexTarget(
                index_name=self.text_index(),
                vector=vector,
                metadata={
                    "filename": str(source_file),
                    "modality": kind,
                    "text": chunk,
                },
            )
        ]

    def build_image_targets(
        self, file_path: Path, description: str, source_url: str
    ) -> list[IndexTarget]:
        vector = (
            self._embed_image_clip(file_path)
            if not self._compat_same_index_mode
            else self._embed_text_openai(description)
        )
        return [
            IndexTarget(
                index_name=self.media_index()
                if not self._compat_same_index_mode
                else self.text_index(),
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
        vector = (
            self._embed_video_clip(file_path)
            if not self._compat_same_index_mode
            else self._embed_text_openai(description)
        )
        if not vector:
            return []
        return [
            IndexTarget(
                index_name=self.media_index()
                if not self._compat_same_index_mode
                else self.text_index(),
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
        transcript = self._transcribe(file_path)
        if not transcript:
            return []
        chunked = _chunk_text(transcript)
        results: list[IndexTarget] = []
        for chunk in chunked:
            vector = self._embed_text_openai(chunk)
            results.append(
                IndexTarget(
                    index_name=self.text_index(),
                    vector=vector,
                    metadata={
                        "filename": str(file_path),
                        "modality": "audio",
                        "text": f"[Audio transcript] {chunk}",
                    },
                )
            )
        return results

    def build_query_targets(self, query: str) -> list[QueryTarget]:
        text_vec = self._embed_text_openai(query)
        if self._compat_same_index_mode:
            return [
                QueryTarget(index_name=self.text_index(), vector=text_vec, label="text")
            ]

        clip_vec = list(
            self._clip_model().encode([query], normalize_embeddings=True)[0]
        )
        return [
            QueryTarget(index_name=self.text_index(), vector=text_vec, label="text"),
            QueryTarget(index_name=self.media_index(), vector=clip_vec, label="media"),
        ]


class VertexProvider(BaseProvider):
    _MAX_TEXT_CHARS = 1000

    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self._openai = (
            OpenAI(api_key=config.openai_api_key) if config.openai_api_key else None
        )

    def validate(self) -> None:
        if not self.config.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for vertex provider")
        if not self.config.pinecone_index_vertex_1408:
            raise ValueError(
                "PINECONE_INDEX_VERTEX_1408 (or PINECONE_INDEX) is required for vertex provider"
            )

    def text_index(self) -> str:
        return self.config.pinecone_index_vertex_1408

    def media_index(self) -> str:
        return self.config.pinecone_index_vertex_1408

    def _access_token(self) -> str:
        if self.config.google_vertex_access_token:
            return self.config.google_vertex_access_token

        credentials_path = _env("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_path:
            raise ValueError(
                "Set GOOGLE_VERTEX_ACCESS_TOKEN or GOOGLE_APPLICATION_CREDENTIALS"
            )

        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        credentials.refresh(Request())
        if not credentials.token:
            raise ValueError("Failed to fetch Google access token")
        return credentials.token

    def _predict(
        self, instance: dict[str, Any], include_dimension: bool = True
    ) -> dict[str, Any]:
        url = (
            f"https://{self.config.google_cloud_location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.config.google_cloud_project}/locations/{self.config.google_cloud_location}/"
            f"publishers/google/models/{self.config.google_vertex_model}:predict"
        )
        headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
        }

        candidate_payloads: list[dict[str, Any]] = []
        instance_with_video_defaults = dict(instance)
        if "video" in instance_with_video_defaults and isinstance(
            instance_with_video_defaults["video"], dict
        ):
            video_obj = dict(instance_with_video_defaults["video"])
            if "videoSegmentConfig" not in video_obj:
                video_obj["videoSegmentConfig"] = {
                    "startOffsetSec": 0,
                    "endOffsetSec": 5,
                    "intervalSec": 5,
                }
            instance_with_video_defaults["video"] = video_obj

        payload_main: dict[str, Any] = {"instances": [instance_with_video_defaults]}
        if include_dimension:
            payload_main["parameters"] = {
                "dimension": self.config.google_vertex_embedding_dimension
            }
        candidate_payloads.append(payload_main)

        payload_instance_params: dict[str, Any] = {
            "instances": [
                {
                    **instance_with_video_defaults,
                    "parameters": {
                        "dimension": self.config.google_vertex_embedding_dimension
                    },
                }
            ]
        }
        candidate_payloads.append(payload_instance_params)
        candidate_payloads.append({"instances": [instance_with_video_defaults]})

        errors: list[str] = []
        for payload in candidate_payloads:
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=120
                )
            except requests.RequestException as exc:
                errors.append(f"request_error: {exc}")
                continue
            if response.ok:
                return response.json()
            snippet = response.text[:500] if response.text else ""
            errors.append(f"{response.status_code}: {snippet}")

        raise RuntimeError(
            "Vertex predict failed for all request variants. "
            f"Model={self.config.google_vertex_model}. Errors={errors}"
        )

    def _extract_first_vector(self, payload: Any) -> list[float]:
        if isinstance(payload, list):
            if payload and all(isinstance(x, (int, float)) for x in payload):
                return [float(x) for x in payload]
            for item in payload:
                vec = self._extract_first_vector(item)
                if vec:
                    return vec
        if isinstance(payload, dict):
            for value in payload.values():
                vec = self._extract_first_vector(value)
                if vec:
                    return vec
        return []

    def _embed_text(self, text: str) -> list[float]:
        body = self._predict({"text": text})
        return self._extract_first_vector(body.get("predictions", []))

    def _vertex_text_chunks(self, text: str) -> list[str]:
        return _hard_split_text(text, self._MAX_TEXT_CHARS)

    def _embed_image(self, file_path: Path) -> list[float]:
        content = base64.b64encode(file_path.read_bytes()).decode("utf-8")
        body = self._predict({"image": {"bytesBase64Encoded": content}})
        return self._extract_first_vector(body.get("predictions", []))

    def _upload_to_gcs(self, file_path: Path) -> str:
        if not self.config.gcs_upload_bucket:
            return ""
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(self.config.gcs_upload_bucket)
        object_name = f"multimodal-ingest/{file_path.name}"
        blob = bucket.blob(object_name)
        blob.upload_from_filename(str(file_path))
        return f"gs://{self.config.gcs_upload_bucket}/{object_name}"

    def _embed_video(self, file_path: Path) -> list[float]:
        gcs_uri = self._upload_to_gcs(file_path)
        if gcs_uri:
            body = self._predict(
                {"video": {"gcsUri": gcs_uri}}, include_dimension=False
            )
            return self._extract_first_vector(body.get("predictions", []))

        # Fallback if no bucket configured: frame sampling + image embeddings.
        import cv2
        from PIL import Image

        capture = cv2.VideoCapture(str(file_path))
        if not capture.isOpened():
            return []

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0 or self.config.video_frame_sample_count == 1:
            positions = [0]
        else:
            positions = sorted(
                int((frame_count - 1) * i / (self.config.video_frame_sample_count - 1))
                for i in range(self.config.video_frame_sample_count)
            )

        vectors: list[np.ndarray] = []
        for pos in positions:
            capture.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ok, frame = capture.read()
            if not ok:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
                Image.fromarray(rgb).save(tmp.name)
                vec = self._embed_image(Path(tmp.name))
                if vec:
                    vectors.append(np.array(vec))
        capture.release()

        if not vectors:
            return []
        pooled = np.mean(np.array(vectors), axis=0)
        return list(pooled)

    def _transcribe(self, file_path: Path) -> str:
        if not self._openai:
            return ""
        with file_path.open("rb") as file_obj:
            response = self._openai.audio.transcriptions.create(
                model=self.config.openai_transcription_model,
                file=file_obj,
            )
        return getattr(response, "text", "")

    def build_text_targets(
        self, chunk: str, source_file: Path, kind: str
    ) -> list[IndexTarget]:
        targets: list[IndexTarget] = []
        for safe_chunk in self._vertex_text_chunks(chunk):
            vector = self._embed_text(safe_chunk)
            if not vector:
                continue
            targets.append(
                IndexTarget(
                    index_name=self.text_index(),
                    vector=vector,
                    metadata={
                        "filename": str(source_file),
                        "modality": kind,
                        "text": safe_chunk,
                    },
                )
            )
        return targets

    def build_image_targets(
        self, file_path: Path, description: str, source_url: str
    ) -> list[IndexTarget]:
        vector = self._embed_image(file_path)
        if not vector:
            return []
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
        vector = self._embed_video(file_path)
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
        transcript = self._transcribe(file_path)
        if not transcript:
            return []
        targets: list[IndexTarget] = []
        for chunk in _chunk_text(transcript):
            for safe_chunk in self._vertex_text_chunks(chunk):
                vector = self._embed_text(safe_chunk)
                if vector:
                    targets.append(
                        IndexTarget(
                            index_name=self.text_index(),
                            vector=vector,
                            metadata={
                                "filename": str(file_path),
                                "modality": "audio",
                                "text": f"[Audio transcript] {safe_chunk}",
                            },
                        )
                    )
        return targets

    def build_query_targets(self, query: str) -> list[QueryTarget]:
        safe_query = self._vertex_text_chunks(query)
        if not safe_query:
            return []
        vector = self._embed_text(safe_query[0])
        return [
            QueryTarget(index_name=self.text_index(), vector=vector, label="vertex")
        ]


class AwsNovaProvider(BaseProvider):
    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        import boto3

        self.runtime = boto3.client("bedrock-runtime", region_name=config.aws_region)
        self._openai = (
            OpenAI(api_key=config.openai_api_key) if config.openai_api_key else None
        )

    def validate(self) -> None:
        if not self.config.pinecone_index_aws_nova_1024:
            raise ValueError(
                "PINECONE_INDEX_AWS_NOVA_1024 (or PINECONE_INDEX) is required for aws_nova provider"
            )

    def text_index(self) -> str:
        return self.config.pinecone_index_aws_nova_1024

    def media_index(self) -> str:
        return self.config.pinecone_index_aws_nova_1024

    def _invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.runtime.invoke_model(
            modelId=self.config.aws_nova_model_id,
            body=json.dumps(payload),
            accept="application/json",
            contentType="application/json",
        )
        body = response["body"].read().decode("utf-8")
        return json.loads(body)

    def _extract_first_vector(self, payload: Any) -> list[float]:
        if isinstance(payload, list):
            if payload and all(isinstance(x, (int, float)) for x in payload):
                return [float(x) for x in payload]
            for item in payload:
                vec = self._extract_first_vector(item)
                if vec:
                    return vec
        if isinstance(payload, dict):
            for value in payload.values():
                vec = self._extract_first_vector(value)
                if vec:
                    return vec
        return []

    def _single_embed_payload(self, input_type: str) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "inputType": input_type,
            "embeddingConfig": {
                "outputEmbeddingLength": self.config.aws_nova_embedding_dimension
            },
        }

    def _embed_text(self, text: str) -> list[float]:
        payload = self._single_embed_payload("search_document")
        payload["texts"] = [{"text": text}]
        body = self._invoke(payload)
        return self._extract_first_vector(body)

    def _embed_image(self, file_path: Path) -> list[float]:
        payload = self._single_embed_payload("search_document")
        ext = file_path.suffix.lower().lstrip(".") or "png"
        payload["images"] = [
            {
                "format": ext,
                "source": {
                    "bytes": base64.b64encode(file_path.read_bytes()).decode("utf-8")
                },
            }
        ]
        body = self._invoke(payload)
        return self._extract_first_vector(body)

    def _embed_video(self, file_path: Path) -> list[float]:
        payload = self._single_embed_payload("search_document")
        ext = file_path.suffix.lower().lstrip(".") or "mp4"
        payload["videos"] = [
            {
                "format": ext,
                "source": {
                    "bytes": base64.b64encode(file_path.read_bytes()).decode("utf-8")
                },
            }
        ]
        body = self._invoke(payload)
        return self._extract_first_vector(body)

    def _embed_audio(self, file_path: Path) -> list[float]:
        payload = self._single_embed_payload("search_document")
        ext = file_path.suffix.lower().lstrip(".") or "wav"
        payload["audios"] = [
            {
                "format": ext,
                "source": {
                    "bytes": base64.b64encode(file_path.read_bytes()).decode("utf-8")
                },
            }
        ]
        body = self._invoke(payload)
        return self._extract_first_vector(body)

    def _transcribe_fallback(self, file_path: Path) -> str:
        if not self._openai:
            return ""
        with file_path.open("rb") as file_obj:
            response = self._openai.audio.transcriptions.create(
                model=self.config.openai_transcription_model,
                file=file_obj,
            )
        return getattr(response, "text", "")

    def build_text_targets(
        self, chunk: str, source_file: Path, kind: str
    ) -> list[IndexTarget]:
        vector = self._embed_text(chunk)
        if not vector:
            return []
        return [
            IndexTarget(
                index_name=self.text_index(),
                vector=vector,
                metadata={
                    "filename": str(source_file),
                    "modality": kind,
                    "text": chunk,
                },
            )
        ]

    def build_image_targets(
        self, file_path: Path, description: str, source_url: str
    ) -> list[IndexTarget]:
        vector = self._embed_image(file_path)
        if not vector:
            return []
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
        vector = self._embed_video(file_path)
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
        vector = self._embed_audio(file_path)
        if vector:
            return [
                IndexTarget(
                    index_name=self.text_index(),
                    vector=vector,
                    metadata={
                        "filename": str(file_path),
                        "modality": "audio",
                        "text": f"Audio asset: {file_path.name}",
                    },
                )
            ]

        transcript = self._transcribe_fallback(file_path)
        targets: list[IndexTarget] = []
        for chunk in chunk_text_with_strategy(
            transcript,
            self.config.chunk_strategy,
            self.config.chunk_max_chars,
            self.config.chunk_min_chars,
            self.config.chunk_overlap_chars,
        ):
            text_vector = self._embed_text(chunk)
            if text_vector:
                targets.append(
                    IndexTarget(
                        index_name=self.text_index(),
                        vector=text_vector,
                        metadata={
                            "filename": str(file_path),
                            "modality": "audio",
                            "text": f"[Audio transcript] {chunk}",
                        },
                    )
                )
        return targets

    def build_query_targets(self, query: str) -> list[QueryTarget]:
        vector = self._embed_text(query)
        return [
            QueryTarget(index_name=self.text_index(), vector=vector, label="aws_nova")
        ]


class LegacyMultimodalProvider(OpenAIClipProvider):
    def validate(self) -> None:
        if not self.config.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for legacy_multimodal provider"
            )
        if not self.config.pinecone_index_legacy_text:
            raise ValueError(
                "PINECONE_INDEX_LEGACY_TEXT (or PINECONE_INDEX) is required for legacy_multimodal"
            )
        if not self.config.pinecone_index_legacy_media:
            raise ValueError(
                "PINECONE_INDEX_LEGACY_MEDIA (or PINECONE_INDEX) is required for legacy_multimodal"
            )

    def text_index(self) -> str:
        return self.config.pinecone_index_legacy_text

    def media_index(self) -> str:
        return self.config.pinecone_index_legacy_media

    def build_query_targets(self, query: str) -> list[QueryTarget]:
        targets = super().build_query_targets(query)
        for target in targets:
            target.label = f"legacy_{target.label}"
        return targets


def _build_provider(config: PipelineConfig) -> BaseProvider:
    if config.provider == "openai_clip":
        return OpenAIClipProvider(config)
    if config.provider == "vertex":
        return VertexProvider(config)
    if config.provider in {"aws", "aws_nova", "bedrock_nova"}:
        return AwsNovaProvider(config)
    if config.provider in {"legacy", "legacy_multimodal"}:
        return LegacyMultimodalProvider(config)
    raise ValueError(
        "Unsupported provider. Use: openai_clip | vertex | aws_nova | legacy_multimodal"
    )


def _expected_dim_for_index(config: PipelineConfig, index_name: str) -> int | None:
    provider = config.provider

    # Provider-first routing avoids wrong dimension assumptions when multiple
    # env vars point to the same physical index name.
    if provider == "openai_clip":
        if index_name == config.pinecone_index_openai_text_3072:
            return config.openai_text_expected_dim
        if index_name == config.pinecone_index_openai_clip_512:
            if (
                config.pinecone_index_openai_clip_512
                == config.pinecone_index_openai_text_3072
            ):
                return config.openai_text_expected_dim
            return config.openai_clip_expected_dim
    if provider in {"legacy", "legacy_multimodal"}:
        if index_name == config.pinecone_index_legacy_text:
            return config.openai_text_expected_dim
        if index_name == config.pinecone_index_legacy_media:
            if config.pinecone_index_legacy_media == config.pinecone_index_legacy_text:
                return config.openai_text_expected_dim
            return config.openai_clip_expected_dim
    if provider == "vertex":
        if index_name == config.pinecone_index_vertex_1408:
            return config.google_vertex_expected_dim
    if provider in {"aws_nova", "aws", "bedrock_nova"}:
        if index_name == config.pinecone_index_aws_nova_1024:
            return config.aws_nova_expected_dim

    # Fallback for mixed/debug flows.
    if index_name == config.pinecone_index_openai_text_3072:
        return config.openai_text_expected_dim
    if index_name == config.pinecone_index_openai_clip_512:
        return config.openai_clip_expected_dim
    if index_name == config.pinecone_index_legacy_text:
        return config.openai_text_expected_dim
    if index_name == config.pinecone_index_legacy_media:
        return config.openai_clip_expected_dim
    if index_name == config.pinecone_index_vertex_1408:
        return config.google_vertex_expected_dim
    if index_name == config.pinecone_index_aws_nova_1024:
        return config.aws_nova_expected_dim
    return None


def _validate_vector_dimensions(
    index_name: str, vectors: list[dict[str, Any]], expected_dim: int | None
) -> None:
    if not vectors:
        return
    if expected_dim is None:
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


def _upsert(
    index_name: str,
    vectors: Iterable[dict[str, Any]],
    pinecone_api_key: str,
    namespace: str,
    expected_dim: int | None,
    config: PipelineConfig,
) -> None:
    vectors_list = list(vectors)
    if not vectors_list:
        return
    _validate_vector_dimensions(
        index_name=index_name, vectors=vectors_list, expected_dim=expected_dim
    )
    try:
        pc = Pinecone(api_key=pinecone_api_key)
        index = _index_client(pc, config, index_name)
        index.upsert(vectors=vectors_list, namespace=namespace, show_progress=True)
    except PineconeApiException as exc:
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


def _resolve_index_host(config: PipelineConfig, index_name: str) -> str:
    host_by_index = {
        config.pinecone_index_vertex_1408: config.pinecone_index_host_vertex_1408,
        config.pinecone_index_openai_text_3072: config.pinecone_index_host_openai_text_3072,
        config.pinecone_index_openai_clip_512: config.pinecone_index_host_openai_clip_512,
        config.pinecone_index_aws_nova_1024: config.pinecone_index_host_aws_nova_1024,
        config.pinecone_index_legacy_text: config.pinecone_index_host_legacy_text,
        config.pinecone_index_legacy_media: config.pinecone_index_host_legacy_media,
    }
    host = host_by_index.get(index_name, "")
    if host:
        return host
    if config.pinecone_index_host and index_name == config.pinecone_index:
        return config.pinecone_index_host
    return ""


def _index_client(pc: Pinecone, config: PipelineConfig, index_name: str):
    host = _resolve_index_host(config, index_name)
    if host:
        return pc.Index(host=host)
    return pc.Index(index_name)


def _target_indexes_for_provider(
    config: PipelineConfig, provider: BaseProvider
) -> list[str]:
    indexes = {provider.text_index(), provider.media_index()}
    return sorted(indexes)


def _preflight_pinecone_indexes(config: PipelineConfig, provider: BaseProvider) -> None:
    if not config.pinecone_preflight:
        return

    pc = Pinecone(api_key=config.pinecone_api_key)
    errors: list[str] = []
    for index_name in _target_indexes_for_provider(config, provider):
        expected_dim = _expected_dim_for_index(config, index_name)
        try:
            info = pc.describe_index(name=index_name)
        except Exception as exc:
            errors.append(
                f"index={index_name}: describe failed ({exc}). "
                "Check if index exists and API key/environment can access Pinecone control plane."
            )
            continue

        actual_dim = getattr(info, "dimension", None)
        if (
            expected_dim is not None
            and actual_dim is not None
            and int(actual_dim) != int(expected_dim)
        ):
            errors.append(
                f"index={index_name}: dimension mismatch (expected {expected_dim}, actual {actual_dim}). "
                "Create/use a dedicated index with matching dimension."
            )

    if errors:
        detail = "\n".join(f"- {line}" for line in errors)
        raise RuntimeError(
            "Pinecone preflight validation failed before ingestion/query.\n"
            f"provider={config.provider}\n"
            f"{detail}"
        )


def _embedding_family_for_index(
    config: PipelineConfig, index_name: str
) -> tuple[str, str]:
    if index_name == config.pinecone_index_vertex_1408:
        return "vertex_multimodal_1408", config.google_vertex_model
    if index_name == config.pinecone_index_openai_text_3072:
        return "openai_text_3072", config.openai_text_embedding_model
    if index_name == config.pinecone_index_openai_clip_512:
        return "openai_clip_512", config.clip_model_name
    if index_name == config.pinecone_index_aws_nova_1024:
        return "aws_nova_1024", config.aws_nova_model_id
    if index_name == config.pinecone_index_legacy_text:
        return "legacy_text_3072", config.openai_text_embedding_model
    if index_name == config.pinecone_index_legacy_media:
        return "legacy_clip_512", config.clip_model_name
    return "unknown", "unknown"


def _to_pinecone_vector(target: IndexTarget, config: PipelineConfig) -> dict[str, Any]:
    metadata = dict(target.metadata)
    embedding_family, embedding_model = _embedding_family_for_index(
        config, target.index_name
    )
    metadata.setdefault("embedding_family", embedding_family)
    metadata.setdefault("embedding_model", embedding_model)
    metadata.setdefault("embedding_dim", len(target.vector))
    metadata.setdefault("provider_family", config.provider)
    source_text = metadata.get("text", "")
    source_path = metadata.get("filename", "")
    vector_id = _sha(
        f"{target.index_name}|{source_path}|{source_text}|{metadata.get('modality', '')}"
    )
    return {"id": vector_id, "values": target.vector, "metadata": metadata}


def load_all(config: PipelineConfig, provider: BaseProvider, namespace: str) -> None:
    manifest = _load_media_manifest(config.image_folder)

    grouped: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []

    text_files = _collect_files(config.text_folder, TEXT_EXTENSIONS)
    doc_files = _collect_files(config.text_folder, DOC_EXTENSIONS)
    image_files = _collect_files(config.image_folder, IMAGE_EXTENSIONS)
    video_files = _collect_files(config.video_folder, VIDEO_EXTENSIONS)
    audio_files = _collect_files(config.audio_folder, AUDIO_EXTENSIONS)

    total_files = (
        len(text_files)
        + len(doc_files)
        + len(image_files)
        + len(video_files)
        + len(audio_files)
    )
    if total_files == 0:
        raise RuntimeError(
            "No input files found for ingestion. "
            f"provider={config.provider}, namespace={namespace}, "
            f"text_folder={config.text_folder}, image_folder={config.image_folder}, "
            f"video_folder={config.video_folder}, audio_folder={config.audio_folder}"
        )

    for text_file in text_files:
        try:
            text = _read_text_file(text_file)
            for chunk in chunk_text_with_strategy(
                text,
                config.chunk_strategy,
                config.chunk_max_chars,
                config.chunk_min_chars,
                config.chunk_overlap_chars,
            ):
                for target in provider.build_text_targets(
                    chunk, text_file, kind="text"
                ):
                    grouped.setdefault(target.index_name, []).append(
                        _to_pinecone_vector(target, config)
                    )
        except Exception as exc:
            errors.append(f"text:{text_file}: {exc}")

    for doc_file in doc_files:
        try:
            text = _extract_document_text(doc_file)
            for chunk in chunk_text_with_strategy(
                text,
                config.chunk_strategy,
                config.chunk_max_chars,
                config.chunk_min_chars,
                config.chunk_overlap_chars,
            ):
                for target in provider.build_text_targets(chunk, doc_file, kind="doc"):
                    grouped.setdefault(target.index_name, []).append(
                        _to_pinecone_vector(target, config)
                    )
        except Exception as exc:
            errors.append(f"doc:{doc_file}: {exc}")

    for image_file in image_files:
        try:
            info = manifest.get(image_file.name, {})
            description = info.get("description") or f"Image asset: {image_file.name}"
            source_url = info.get("source_url", "")
            for target in provider.build_image_targets(
                image_file, description, source_url
            ):
                grouped.setdefault(target.index_name, []).append(
                    _to_pinecone_vector(target, config)
                )
        except Exception as exc:
            errors.append(f"image:{image_file}: {exc}")

    for video_file in video_files:
        # Ignore known placeholders / unreadable dummy samples.
        if "placeholder" in video_file.name.lower():
            print(f"Skipping placeholder video file: {video_file}")
            continue
        try:
            description = f"Video asset: {video_file.name}"
            for target in provider.build_video_targets(video_file, description):
                grouped.setdefault(target.index_name, []).append(
                    _to_pinecone_vector(target, config)
                )
        except Exception as exc:
            errors.append(f"video:{video_file}: {exc}")

    for audio_file in audio_files:
        try:
            for target in provider.build_audio_targets(audio_file):
                grouped.setdefault(target.index_name, []).append(
                    _to_pinecone_vector(target, config)
                )
        except Exception as exc:
            errors.append(f"audio:{audio_file}: {exc}")

    if not grouped and errors:
        preview = "; ".join(errors[:5])
        raise RuntimeError(
            "No vectors produced during load. "
            f"provider={config.provider}, namespace={namespace}. sample_errors={preview}"
        )

    for index_name, vectors in grouped.items():
        try:
            print(f"Upserting {len(vectors)} vectors into {index_name}")
            _upsert(
                index_name=index_name,
                vectors=vectors,
                pinecone_api_key=config.pinecone_api_key,
                namespace=namespace,
                expected_dim=_expected_dim_for_index(config, index_name),
                config=config,
            )
        except Exception as exc:
            errors.append(f"upsert:{index_name}: {exc}")

    if errors:
        preview = "\n".join(f"- {err}" for err in errors[:10])
        raise RuntimeError(
            "Load finished with errors.\n"
            f"provider={config.provider}, namespace={namespace}\n"
            f"error_count={len(errors)}\n"
            f"{preview}"
        )


def query_all(
    config: PipelineConfig,
    provider: BaseProvider,
    query: str,
    top_k: int,
    namespace: str,
) -> None:
    query_targets = provider.build_query_targets(query)
    if not query_targets:
        print("I don't have enough info to answer.")
        return

    pc = Pinecone(api_key=config.pinecone_api_key)
    context_parts: list[str] = []
    citations: list[str] = []

    for target in query_targets:
        try:
            index = _index_client(pc, config, target.index_name)
            response = index.query(
                namespace=namespace,
                vector=target.vector,
                top_k=top_k,
                include_metadata=True,
            )
        except PineconeApiException as exc:
            detail = getattr(exc, "body", "") or str(exc)
            raise RuntimeError(
                "Pinecone query failed. "
                f"index={target.index_name}, namespace={namespace}, top_k={top_k}. detail={detail}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                "Pinecone query failed with unexpected error. "
                f"index={target.index_name}, namespace={namespace}, top_k={top_k}. detail={exc}"
            ) from exc
        for match in response.get("matches", []):
            metadata = match.get("metadata", {}) if match else {}
            text = metadata.get("text", "")
            filename = metadata.get("filename", "")
            modality = metadata.get("modality", "")
            if text:
                context_parts.append(
                    f"[{target.label}/{modality}] {filename} -> {text}"
                )
                citations.append(f"- [{target.label}/{modality}] {filename}")

    context = "\n\n".join(context_parts).strip()
    if not context:
        print("I don't have enough info to answer.")
        return

    if not config.openai_api_key:
        print(context)
        return

    client = OpenAI(api_key=config.openai_api_key)
    prompt = (
        "You are a grounded retrieval assistant.\n"
        f"Question: {query}\n\n"
        f"Retrieved Context:\n{context}\n\n"
        "Rules:\n"
        "1) Answer using retrieved context only.\n"
        "2) If evidence is insufficient, reply exactly: I don't have enough info to answer.\n"
        "3) Return concise answer first, then a short citation list."
    )
    result = client.chat.completions.create(
        model=config.openai_chat_model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "You are a concise multimodal retrieval assistant.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    answer = result.choices[0].message.content or "I don't have enough info to answer."
    print(answer)
    if citations:
        print("\nCitations:")
        for citation in citations[: min(len(citations), top_k * 2)]:
            print(citation)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multimodal provider pipeline for Pinecone"
    )
    parser.add_argument(
        "--provider",
        choices=["openai_clip", "vertex", "aws_nova", "legacy_multimodal"],
        help="Provider override",
    )
    parser.add_argument("--namespace", type=str, help="Pinecone namespace override")
    parser.add_argument(
        "-L", "--load", action="store_true", help="Ingest all supported data"
    )
    parser.add_argument("-Q", "--query", type=str, help="Query indexed data")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("-l", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("-q", type=str, help=argparse.SUPPRESS)
    return parser.parse_args()


def validate_common(config: PipelineConfig) -> None:
    missing = []
    if not config.pinecone_api_key:
        missing.append("PINECONE_API_KEY")
    if config.provider == "openai_clip":
        if not config.pinecone_index_openai_text_3072:
            missing.append("PINECONE_INDEX_OPENAI_TEXT_3072 (or PINECONE_TEXT_INDEX)")
        if not config.pinecone_index_openai_clip_512:
            missing.append("PINECONE_INDEX_OPENAI_CLIP_512 (or PINECONE_MEDIA_INDEX)")
        if (
            config.pinecone_index_openai_text_3072
            and config.pinecone_index_openai_clip_512
            and config.pinecone_index_openai_text_3072
            == config.pinecone_index_openai_clip_512
        ):
            missing.append(
                "OpenAI requires distinct indexes: "
                "PINECONE_INDEX_OPENAI_TEXT_3072 != PINECONE_INDEX_OPENAI_CLIP_512"
            )
    elif config.provider in {"legacy", "legacy_multimodal"}:
        if not config.pinecone_index_legacy_text:
            missing.append("PINECONE_INDEX_LEGACY_TEXT (or PINECONE_INDEX)")
        if not config.pinecone_index_legacy_media:
            missing.append("PINECONE_INDEX_LEGACY_MEDIA (or PINECONE_INDEX)")
    else:
        if config.provider == "vertex" and not config.pinecone_index_vertex_1408:
            missing.append("PINECONE_INDEX_VERTEX_1408 (or PINECONE_INDEX)")
        if (
            config.provider in {"aws_nova", "aws", "bedrock_nova"}
            and not config.pinecone_index_aws_nova_1024
        ):
            missing.append("PINECONE_INDEX_AWS_NOVA_1024 (or PINECONE_INDEX)")

    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")

    if config.provider == "openai_clip":
        if (
            config.openai_text_embedding_model.strip().lower()
            == "text-embedding-3-large"
        ):
            configured_dim_raw = _env("OPENAI_TEXT_EMBEDDING_DIMENSION", "3072").strip()
            if configured_dim_raw and int(configured_dim_raw) != 3072:
                raise ValueError(
                    "OPENAI_TEXT_EMBEDDING_DIMENSION must be 3072 when "
                    "OPENAI_TEXT_EMBEDDING_MODEL=text-embedding-3-large."
                )
        if (
            config.pinecone_index_openai_text_3072
            and config.pinecone_index_vertex_1408
            and config.pinecone_index_openai_text_3072
            == config.pinecone_index_vertex_1408
            and config.openai_text_expected_dim != config.google_vertex_expected_dim
        ):
            raise ValueError(
                "OpenAI text index is configured to the same name as Vertex index, "
                "but expected dimensions differ (3072 vs 1408). "
                "Set PINECONE_INDEX_OPENAI_TEXT_3072 to a dedicated 3072 index."
            )


def main(provider_override: str | None = None) -> None:
    env_file = _env("ENV_FILE")
    if env_file:
        load_dotenv(env_file, override=True)
    args = parse_args()
    load_flag = args.load or args.l
    query_value = args.query or args.q

    config = PipelineConfig.from_env(
        provider_override=provider_override or args.provider
    )
    namespace = args.namespace or config.pinecone_namespace
    validate_common(config)
    provider = _build_provider(config)
    provider.validate()
    _preflight_pinecone_indexes(config, provider)

    print(f"Provider: {config.provider}")
    print(f"Namespace: {namespace}")

    if load_flag:
        load_all(config, provider, namespace=namespace)
        return

    if query_value:
        query_all(config, provider, query_value, top_k=args.top_k, namespace=namespace)
        return

    print(
        'Usage: python pinecone-multimodal-pipeline.py --provider openai_clip|vertex|aws_nova|legacy_multimodal --load | --query "..."'
    )


if __name__ == "__main__":
    main()
