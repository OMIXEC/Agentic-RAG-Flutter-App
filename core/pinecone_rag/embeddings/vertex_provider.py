"""Google Vertex AI multimodal embedding provider for Pinecone RAG.

Uses multimodalembedding@001 for text, image, and video embeddings
in a unified 1408-dimensional space. Audio is transcribed then embedded as text.
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import requests

from ..chunking import chunk_text, hard_split_text
from ..models import BaseProvider, IndexTarget, QueryTarget

_VERTEX_ALLOWED_DIMS = {128, 256, 512, 1408}


class VertexProvider(BaseProvider):
    """Vertex AI multimodal embedding — unified text/image/video index.

    Single Pinecone index (1408d by default) for all modalities.
    """

    _MAX_TEXT_CHARS = 1000

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self._idx = getattr(config, "pinecone_index_vertex_1408", "") or config.pinecone_index

    def validate(self) -> None:
        if not self.config.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for vertex provider")
        if not self._idx:
            raise ValueError("PINECONE_INDEX_VERTEX_1408 (or PINECONE_INDEX) is required")
        dim = self.config.google_vertex_embedding_dimension
        if dim not in _VERTEX_ALLOWED_DIMS:
            print(
                f"[vertex] WARNING: GOOGLE_VERTEX_EMBEDDING_DIMENSION={dim} is not valid. "
                f"Valid: {sorted(_VERTEX_ALLOWED_DIMS)}. Falling back to 1408d."
            )
            self.config.google_vertex_embedding_dimension = 1408

    def text_index(self) -> str:
        return self._idx

    def media_index(self) -> str:
        return self._idx

    def _access_token(self) -> str:
        token = getattr(self.config, "google_vertex_access_token", "")
        if token:
            return token

        creds_path = getattr(self.config, "google_application_credentials", "")
        if not creds_path:
            import os
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        
        if not creds_path:
            print("[vertex] No GOOGLE_APPLICATION_CREDENTIALS found, attempting default credentials...")
            import google.auth
            credentials, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        else:
            if not Path(creds_path).exists():
                raise FileNotFoundError(f"GCP credentials file not found: {creds_path}")
            
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        from google.auth.transport.requests import Request
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

        # Build candidate payloads with video segment defaults
        instance_with_defaults = dict(instance)
        if "video" in instance_with_defaults and isinstance(instance_with_defaults["video"], dict):
            video_obj = dict(instance_with_defaults["video"])
            if "videoSegmentConfig" not in video_obj:
                video_obj["videoSegmentConfig"] = {
                    "startOffsetSec": 0, "endOffsetSec": 5, "intervalSec": 5,
                }
            instance_with_defaults["video"] = video_obj

        candidate_payloads: list[dict[str, Any]] = []
        payload_main: dict[str, Any] = {"instances": [instance_with_defaults]}
        if include_dimension:
            payload_main["parameters"] = {"dimension": self.config.google_vertex_embedding_dimension}
        candidate_payloads.append(payload_main)

        # Fallback: parameters inside instance
        candidate_payloads.append({
            "instances": [{
                **instance_with_defaults,
                "parameters": {"dimension": self.config.google_vertex_embedding_dimension},
            }]
        })
        # Fallback: no parameters
        candidate_payloads.append({"instances": [instance_with_defaults]})

        errors: list[str] = []
        for i, payload in enumerate(candidate_payloads):
            try:
                print(f"[vertex] Calling predict (attempt {i+1})...")
                response = requests.post(url, headers=headers, json=payload, timeout=120)
            except requests.RequestException as exc:
                print(f"[vertex] Request error: {exc}")
                errors.append(f"request_error: {exc}")
                continue
            if response.ok:
                return response.json()
            snippet = response.text[:500] if response.text else ""
            print(f"[vertex] Predict failed ({response.status_code}): {snippet}")
            errors.append(f"{response.status_code}: {snippet}")

        raise RuntimeError(
            f"Vertex predict failed. Model={self.config.google_vertex_model}. Errors={errors}"
        )

    def _extract_first_vector(self, payload: Any) -> list[float]:
        if isinstance(payload, list):
            if payload and all(isinstance(x, (int, float, np.number)) for x in payload):
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
        return hard_split_text(text, self._MAX_TEXT_CHARS)

    def _embed_image(self, file_path: Path) -> list[float]:
        if not file_path.exists():
            print(f"[vertex] Image not found: {file_path}")
            return []
        content = base64.b64encode(file_path.read_bytes()).decode("utf-8")
        body = self._predict({"image": {"bytesBase64Encoded": content}})
        return self._extract_first_vector(body.get("predictions", []))

    def _upload_to_gcs(self, file_path: Path) -> str:
        bucket_name = getattr(self.config, "vertex_video_gcs_bucket", "") or getattr(self.config, "gcs_upload_bucket", "")
        if not bucket_name:
            return ""
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        object_name = f"multimodal-ingest/{file_path.name}"
        blob = bucket.blob(object_name)
        blob.upload_from_filename(str(file_path))
        return f"gs://{bucket_name}/{object_name}"

    def _embed_video(self, file_path: Path) -> list[float]:
        gcs_uri = self._upload_to_gcs(file_path)
        if gcs_uri:
            body = self._predict({"video": {"gcsUri": gcs_uri}}, include_dimension=False)
            return self._extract_first_vector(body.get("predictions", []))

        # Fallback: frame sampling + image embeddings
        import cv2
        from PIL import Image

        capture = cv2.VideoCapture(str(file_path))
        if not capture.isOpened():
            return []

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_count = getattr(self.config, "video_frame_sample_count", 4)
        positions = [0] if frame_count <= 0 or sample_count == 1 else sorted(
            int((frame_count - 1) * i / (sample_count - 1)) for i in range(sample_count)
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
        
        # Ensure results are standard Python floats for Pinecone compatibility
        mean_vec = np.mean(np.array(vectors), axis=0)
        return [float(x) for x in mean_vec]

    def _interpret_audio_immersive(self, file_path: Path) -> str:
        """Use Gemini to interpret the audio and soundscape for immersive RAG."""
        if not file_path.exists():
            print(f"[vertex] Audio not found: {file_path}")
            return ""
        model_id = getattr(self.config, "google_vertex_gemini_model", "gemini-2.5-flash")
        url = (
            f"https://{self.config.google_cloud_location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.config.google_cloud_project}/locations/{self.config.google_cloud_location}/"
            f"publishers/google/models/{model_id}:generateContent"
        )
        headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
        }

        # Embed audio directly (multimodal)
        audio_content = base64.b64encode(file_path.read_bytes()).decode("utf-8")
        mime_type = "audio/mpeg" if file_path.suffix.lower() == ".mp3" else f"audio/{file_path.suffix[1:]}"
        
        prompt = (
            "Interpret the immersive reality of this audio. Describe the soundscape (ambient noise, spatial context), "
            "the voices (identity, gender, emotion, cadence), and the overall vibe and setting. "
            "Identify any animals, machinery, or nature sounds. Provide a dense, semantic description."
        )

        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": mime_type, "data": audio_content}}
                ]
            }],
            "generationConfig": {"temperature": 0.2, "topP": 0.8, "topK": 40}
        }

        try:
            print(f"[vertex] Calling {model_id} for immersive interpretation...")
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                result = response.json()
                text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return text.strip()
            else:
                print(f"[vertex] Gemini failed: {response.text}")
                return ""
        except Exception as exc:
            print(f"[vertex] Error interpreting audio: {exc}")
            return ""

    def build_audio_targets(self, file_path: Path) -> list[IndexTarget]:
        """Build enriched RAG targets using immersive audio interpretation."""
        interpretation = self._interpret_audio_immersive(file_path)
        if not interpretation:
            print(f"[vertex] Skipping audio {file_path} - interpretation failed.")
            return []
            
        targets: list[IndexTarget] = []
        # Embed the interpretation text into the unified multimodal space (1408d)
        for safe_chunk in self._vertex_text_chunks(interpretation):
            vector = self._embed_text(safe_chunk)
            if vector:
                targets.append(IndexTarget(
                    index_name=self.text_index(),
                    vector=vector,
                    metadata={
                        "filename": str(file_path), 
                        "modality": "audio", 
                        "text": f"[Immersive Interpretation] {safe_chunk}"
                    },
                ))
        return targets


    def build_text_targets(
        self, chunk: str, source_file: Path, kind: str
    ) -> list[IndexTarget]:
        targets: list[IndexTarget] = []
        for safe_chunk in self._vertex_text_chunks(chunk):
            vector = self._embed_text(safe_chunk)
            if not vector:
                continue
            targets.append(IndexTarget(
                index_name=self.text_index(),
                vector=vector,
                metadata={"filename": str(source_file), "modality": kind, "text": safe_chunk},
            ))
        return targets

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


    def build_query_targets(self, query: str) -> list[QueryTarget]:
        safe_query = self._vertex_text_chunks(query)
        if not safe_query:
            return []
        vector = self._embed_text(safe_query[0])
        return [QueryTarget(index_name=self.text_index(), vector=vector, label="vertex")]
