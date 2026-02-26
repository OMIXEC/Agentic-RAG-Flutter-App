"""OpenAI + CLIP embedding provider for Pinecone RAG.

Uses OpenAI text-embedding-3-large for text and sentence-transformers
CLIP models for image/video embeddings. Two separate Pinecone indexes
are required due to different embedding dimensions (3072 vs 512).
"""

from __future__ import annotations

import base64
import hashlib
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI

from ..chunking import chunk_text
from ..models import BaseProvider, IndexTarget, QueryTarget


def _resolve_clip_expected_dim(model: str, configured_dim: int) -> int:
    """Map CLIP model names to their embedding dimensions."""
    normalized = (model or "").strip().lower()
    clip_dimensions = {
        "clip-vit-b-32": 512,
        "clip-vit-b-16": 512,
        "clip-vit-l-14": 768,
        "clip-vit-h-14": 1024,
        "clip-vit-bigg-14": 1280,
    }
    for key, dim in clip_dimensions.items():
        if key in normalized:
            return dim
    return configured_dim


class OpenAIClipProvider(BaseProvider):
    """OpenAI text embeddings + CLIP image/video embeddings.

    Requires two separate Pinecone indexes:
    - Text index (3072d for text-embedding-3-large)
    - Media index (512d for CLIP ViT-B/32, or matching model dimension)
    """

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self.openai = OpenAI(api_key=config.openai_api_key)
        self._clip = None
        self._text_idx = getattr(config, "pinecone_index_openai_text_3072", "") or config.pinecone_index
        self._media_idx = getattr(config, "pinecone_index_openai_clip_512", "") or config.pinecone_index
        self._compat_same_index_mode = self._media_idx == self._text_idx

    def validate(self) -> None:
        if not self.config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for openai_clip provider")
        if not self._text_idx:
            raise ValueError("PINECONE_INDEX_OPENAI_TEXT_3072 (or PINECONE_INDEX) is required")
        if self._compat_same_index_mode:
            raise ValueError(
                "OpenAI pipeline requires strict index separation: "
                "PINECONE_INDEX_OPENAI_TEXT_3072 and PINECONE_INDEX_OPENAI_CLIP_512 "
                "must be different indexes."
            )

    def text_index(self) -> str:
        return self._text_idx

    def media_index(self) -> str:
        return self._media_idx

    def _clip_model(self):
        if self._clip is None:
            from sentence_transformers import SentenceTransformer

            model_name = self.config.clip_model_name
            print(f"Loading CLIP model: {model_name}")
            self._clip = SentenceTransformer(model_name)
        return self._clip

    def _embed_text_openai(self, text: str) -> list[float]:
        kwargs: dict[str, Any] = {
            "model": self.config.openai_text_embedding_model,
            "input": text,
        }
        dim = getattr(self.config, "openai_text_embedding_dimension", 3072)
        if dim > 0:
            kwargs["dimensions"] = dim
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
        sample_count = getattr(self.config, "video_frame_sample_count", 4)
        if frame_count <= 0 or sample_count == 1:
            positions = [0]
        else:
            positions = sorted(
                int((frame_count - 1) * i / (sample_count - 1))
                for i in range(sample_count)
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
        model = getattr(self.config, "openai_transcription_model", "gpt-4o-mini-transcribe")
        with file_path.open("rb") as file_obj:
            result = self.openai.audio.transcriptions.create(
                model=model, file=file_obj,
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
                metadata={"filename": str(source_file), "modality": kind, "text": chunk},
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
                index_name=self.media_index() if not self._compat_same_index_mode else self.text_index(),
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
                index_name=self.media_index() if not self._compat_same_index_mode else self.text_index(),
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
        chunked = chunk_text(transcript)
        results: list[IndexTarget] = []
        for c in chunked:
            vector = self._embed_text_openai(c)
            results.append(
                IndexTarget(
                    index_name=self.text_index(),
                    vector=vector,
                    metadata={
                        "filename": str(file_path),
                        "modality": "audio",
                        "text": f"[Audio transcript] {c}",
                    },
                )
            )
        return results

    def build_query_targets(self, query: str) -> list[QueryTarget]:
        text_vec = self._embed_text_openai(query)
        if self._compat_same_index_mode:
            return [QueryTarget(index_name=self.text_index(), vector=text_vec, label="text")]

        clip_vec = list(self._clip_model().encode([query], normalize_embeddings=True)[0])
        return [
            QueryTarget(index_name=self.text_index(), vector=text_vec, label="text"),
            QueryTarget(index_name=self.media_index(), vector=clip_vec, label="media"),
        ]
