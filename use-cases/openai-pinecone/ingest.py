"""OpenAI + Pinecone RAG — Ingest documents into Pinecone using OpenAI embeddings.

Usage:
    python ingest.py --namespace my-project
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add core to path for standalone usage
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "core"))

from pinecone_rag.chunking import chunk_text_with_strategy
from pinecone_rag.config import ChunkingSettings, OpenAISettings, PineconeSettings
from pinecone_rag.document_loaders import (
    DOC_EXTENSIONS,
    IMAGE_EXTENSIONS,
    TEXT_EXTENSIONS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    collect_files,
    extract_document_text,
    load_media_manifest,
    read_text_file,
    sha256_hash,
)
from pinecone_rag.embeddings.openai_provider import OpenAIClipProvider
from pinecone_rag.pinecone_client import upsert_vectors


class _Config:
    """Minimal config object for OpenAI provider."""
    def __init__(self, openai: OpenAISettings, pinecone: PineconeSettings, chunking: ChunkingSettings):
        self.openai_api_key = openai.openai_api_key
        self.openai_text_embedding_model = openai.openai_text_embedding_model
        self.openai_text_embedding_dimension = openai.openai_text_embedding_dimension
        self.openai_transcription_model = openai.openai_transcription_model
        self.clip_model_name = openai.clip_model_name
        self.openai_clip_embedding_dimension = openai.openai_clip_embedding_dimension
        self.pinecone_index = pinecone.pinecone_index
        self.pinecone_index_openai_text_3072 = pinecone.pinecone_index_openai_text_3072 or pinecone.pinecone_index
        self.pinecone_index_openai_clip_512 = pinecone.pinecone_index_openai_clip_512 or pinecone.pinecone_index
        self.pinecone_api_key = pinecone.pinecone_api_key
        self.video_frame_sample_count = 4
        self.chunk_strategy = chunking.chunk_strategy
        self.chunk_max_chars = chunking.chunk_max_chars
        self.chunk_min_chars = chunking.chunk_min_chars
        self.chunk_overlap_chars = chunking.chunk_overlap_chars


def ingest(namespace: str, data_dir: str = "data") -> None:
    load_dotenv()
    openai_cfg = OpenAISettings()
    pinecone_cfg = PineconeSettings()
    chunking_cfg = ChunkingSettings()
    config = _Config(openai_cfg, pinecone_cfg, chunking_cfg)

    provider = OpenAIClipProvider(config)
    provider.validate()

    root = Path(data_dir)
    text_dir = root / "txt"
    image_dir = root / "image"
    video_dir = root / "video"
    audio_dir = root / "audio"

    all_targets: dict[str, list[dict]] = {}

    # Text files
    for f in collect_files(text_dir, TEXT_EXTENSIONS):
        text = read_text_file(f)
        for chunk in chunk_text_with_strategy(
            text, config.chunk_strategy, config.chunk_max_chars,
            config.chunk_min_chars, config.chunk_overlap_chars,
        ):
            for t in provider.build_text_targets(chunk, f, "text"):
                all_targets.setdefault(t.index_name, []).append({
                    "id": sha256_hash(f"{f}:{chunk[:50]}"),
                    "values": t.vector,
                    "metadata": t.metadata,
                })

    # Documents
    for f in collect_files(text_dir, DOC_EXTENSIONS):
        text = extract_document_text(f)
        if not text:
            continue
        for chunk in chunk_text_with_strategy(
            text, config.chunk_strategy, config.chunk_max_chars,
            config.chunk_min_chars, config.chunk_overlap_chars,
        ):
            for t in provider.build_text_targets(chunk, f, "document"):
                all_targets.setdefault(t.index_name, []).append({
                    "id": sha256_hash(f"{f}:{chunk[:50]}"),
                    "values": t.vector,
                    "metadata": t.metadata,
                })

    # Images
    manifest = load_media_manifest(image_dir)
    for f in collect_files(image_dir, IMAGE_EXTENSIONS):
        meta = manifest.get(f.name, {"description": f.stem, "source_url": ""})
        for t in provider.build_image_targets(f, meta["description"], meta["source_url"]):
            all_targets.setdefault(t.index_name, []).append({
                "id": sha256_hash(f"img:{f}"),
                "values": t.vector,
                "metadata": t.metadata,
            })

    # Videos
    manifest = load_media_manifest(video_dir)
    for f in collect_files(video_dir, VIDEO_EXTENSIONS):
        meta = manifest.get(f.name, {"description": f.stem, "source_url": ""})
        for t in provider.build_video_targets(f, meta["description"]):
            all_targets.setdefault(t.index_name, []).append({
                "id": sha256_hash(f"vid:{f}"),
                "values": t.vector,
                "metadata": t.metadata,
            })

    # Audio
    for f in collect_files(audio_dir, AUDIO_EXTENSIONS):
        for t in provider.build_audio_targets(f):
            all_targets.setdefault(t.index_name, []).append({
                "id": sha256_hash(f"aud:{f}:{t.metadata.get('text', '')[:30]}"),
                "values": t.vector,
                "metadata": t.metadata,
            })

    # Upsert to Pinecone
    for index_name, vectors in all_targets.items():
        print(f"Upserting {len(vectors)} vectors to {index_name} (namespace={namespace})")
        upsert_vectors(
            index_name=index_name,
            vectors=vectors,
            pinecone_api_key=config.pinecone_api_key,
            namespace=namespace,
            expected_dim=None,
        )

    print(f"✅ Ingestion complete — {sum(len(v) for v in all_targets.values())} total vectors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest data into Pinecone using OpenAI embeddings")
    parser.add_argument("--namespace", default="default", help="Pinecone namespace")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    args = parser.parse_args()
    ingest(args.namespace, args.data_dir)
