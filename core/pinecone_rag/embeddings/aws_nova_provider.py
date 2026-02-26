"""AWS Bedrock Nova multimodal embedding provider for Pinecone RAG.

All modalities (text, image, video, audio) share a single unified
embedding space via amazon.nova-2-multimodal-embeddings-v1.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from ..chunking import chunk_text_with_strategy
from ..models import BaseProvider, IndexTarget, QueryTarget


class AwsNovaProvider(BaseProvider):
    """AWS Bedrock Nova unified multimodal embedding.

    Single Pinecone index (1024d default) for all modalities.
    """

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        import boto3

        self.runtime = boto3.client("bedrock-runtime", region_name=config.aws_region)
        self._openai = None
        if getattr(config, "openai_api_key", ""):
            from openai import OpenAI
            self._openai = OpenAI(api_key=config.openai_api_key)
        self._idx = getattr(config, "pinecone_index_aws_nova_1024", "") or config.pinecone_index

    def validate(self) -> None:
        if not self._idx:
            raise ValueError(
                "PINECONE_INDEX_AWS_NOVA_1024 (or PINECONE_INDEX) is required for aws_nova provider"
            )
        embed_dim = self.config.aws_nova_embedding_dimension
        expected_dim = getattr(self.config, "aws_nova_expected_dim", embed_dim)
        if embed_dim != expected_dim:
            print(
                f"[nova] WARNING: AWS_NOVA_EMBEDDING_DIMENSION={embed_dim} "
                f"!= AWS_NOVA_EXPECTED_DIMENSION={expected_dim}. "
                "Both values should match your Pinecone index dimension."
            )

    def text_index(self) -> str:
        return self._idx

    def media_index(self) -> str:
        return self._idx

    def _invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        model_id = getattr(self.config, "aws_nova_embedding_model",
                           "amazon.nova-2-multimodal-embeddings-v1:0")
        response = self.runtime.invoke_model(
            modelId=model_id,
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
        payload["images"] = [{
            "format": ext,
            "source": {"bytes": base64.b64encode(file_path.read_bytes()).decode("utf-8")},
        }]
        body = self._invoke(payload)
        return self._extract_first_vector(body)

    def _embed_video(self, file_path: Path) -> list[float]:
        max_bytes = getattr(self.config, "aws_nova_video_max_bytes", 20 * 1024 * 1024)
        file_size = file_path.stat().st_size
        if file_size > max_bytes:
            print(
                f"[nova] Video {file_path.name} ({file_size // (1024 * 1024)}MB) exceeds "
                f"AWS_NOVA_VIDEO_MAX_BYTES ({max_bytes // (1024 * 1024)}MB). Skipping."
            )
            return []
        payload = self._single_embed_payload("search_document")
        ext = file_path.suffix.lower().lstrip(".") or "mp4"
        payload["videos"] = [{
            "format": ext,
            "source": {"bytes": base64.b64encode(file_path.read_bytes()).decode("utf-8")},
        }]
        body = self._invoke(payload)
        return self._extract_first_vector(body)

    def _embed_audio(self, file_path: Path) -> list[float]:
        payload = self._single_embed_payload("search_document")
        ext = file_path.suffix.lower().lstrip(".") or "wav"
        payload["audios"] = [{
            "format": ext,
            "source": {"bytes": base64.b64encode(file_path.read_bytes()).decode("utf-8")},
        }]
        body = self._invoke(payload)
        return self._extract_first_vector(body)

    def _transcribe_fallback(self, file_path: Path) -> str:
        if not self._openai:
            return ""
        model = getattr(self.config, "openai_transcription_model", "gpt-4o-mini-transcribe")
        with file_path.open("rb") as file_obj:
            response = self._openai.audio.transcriptions.create(model=model, file=file_obj)
        return getattr(response, "text", "")

    def build_text_targets(
        self, chunk: str, source_file: Path, kind: str
    ) -> list[IndexTarget]:
        vector = self._embed_text(chunk)
        if not vector:
            return []
        return [IndexTarget(
            index_name=self.text_index(),
            vector=vector,
            metadata={"filename": str(source_file), "modality": kind, "text": chunk},
        )]

    def build_image_targets(
        self, file_path: Path, description: str, source_url: str
    ) -> list[IndexTarget]:
        vector = self._embed_image(file_path)
        if not vector:
            return []
        return [IndexTarget(
            index_name=self.text_index(),
            vector=vector,
            metadata={
                "filename": str(file_path), "modality": "image", "media_type": "image",
                "text": description, "source_url": source_url,
            },
        )]

    def build_video_targets(
        self, file_path: Path, description: str
    ) -> list[IndexTarget]:
        vector = self._embed_video(file_path)
        if not vector:
            return []
        return [IndexTarget(
            index_name=self.text_index(),
            vector=vector,
            metadata={
                "filename": str(file_path), "modality": "video", "media_type": "video",
                "text": description,
            },
        )]

    def build_audio_targets(self, file_path: Path) -> list[IndexTarget]:
        vector = self._embed_audio(file_path)
        if vector:
            return [IndexTarget(
                index_name=self.text_index(),
                vector=vector,
                metadata={
                    "filename": str(file_path), "modality": "audio",
                    "text": f"Audio asset: {file_path.name}",
                },
            )]

        transcript = self._transcribe_fallback(file_path)
        targets: list[IndexTarget] = []
        strategy = getattr(self.config, "chunk_strategy", "paragraph")
        max_chars = getattr(self.config, "chunk_max_chars", 1200)
        min_chars = getattr(self.config, "chunk_min_chars", 80)
        overlap = getattr(self.config, "chunk_overlap_chars", 0)
        for c in chunk_text_with_strategy(transcript, strategy, max_chars, min_chars, overlap):
            text_vector = self._embed_text(c)
            if text_vector:
                targets.append(IndexTarget(
                    index_name=self.text_index(),
                    vector=text_vector,
                    metadata={
                        "filename": str(file_path), "modality": "audio",
                        "text": f"[Audio transcript] {c}",
                    },
                ))
        return targets

    def build_query_targets(self, query: str) -> list[QueryTarget]:
        vector = self._embed_text(query)
        return [QueryTarget(index_name=self.text_index(), vector=vector, label="aws_nova")]
