"""Azure OpenAI + Pinecone RAG — Unified CLI entry point.

Usage:
    python main.py --ingest --namespace my-project
    python main.py --query "What happened?" --namespace my-project
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "core"))


class _Config:
    def __init__(self):
        load_dotenv()
        from pinecone_rag.config import PineconeSettings, AzureOpenAISettings, ChunkingSettings
        p = PineconeSettings()
        a = AzureOpenAISettings()
        c = ChunkingSettings()
        self.azure_openai_api_key = a.azure_openai_api_key
        self.azure_openai_endpoint = a.azure_openai_endpoint
        self.azure_openai_api_version = a.azure_openai_api_version
        self.azure_openai_deployment_name = a.azure_openai_deployment_name
        self.azure_openai_embedding_deployment = a.azure_openai_embedding_deployment
        self.azure_openai_embedding_dimension = a.azure_openai_embedding_dimension
        self.azure_openai_chat_deployment = a.azure_openai_chat_deployment
        self.pinecone_api_key = p.pinecone_api_key
        self.pinecone_index = p.pinecone_index
        self.pinecone_index_azure_1536 = p.pinecone_index_azure_1536 or p.pinecone_index
        self.chunk_strategy = c.chunk_strategy
        self.chunk_max_chars = c.chunk_max_chars
        self.chunk_min_chars = c.chunk_min_chars
        self.chunk_overlap_chars = c.chunk_overlap_chars


def _ingest(namespace: str, data_dir: str):
    from pinecone_rag.chunking import chunk_text_with_strategy
    from pinecone_rag.document_loaders import (
        TEXT_EXTENSIONS, DOC_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS,
        collect_files, extract_document_text, load_media_manifest, read_text_file, sha256_hash,
    )
    from pinecone_rag.embeddings.azure_provider import AzureOpenAIProvider
    from pinecone_rag.pinecone_client import upsert_vectors

    config = _Config()
    provider = AzureOpenAIProvider(config)
    provider.validate()
    root = Path(data_dir)
    all_targets: dict[str, list[dict]] = {}

    # Text + documents
    for f in collect_files(root / "txt", TEXT_EXTENSIONS | DOC_EXTENSIONS):
        text = read_text_file(f) if f.suffix.lower() in TEXT_EXTENSIONS else extract_document_text(f)
        if not text:
            continue
        for chunk in chunk_text_with_strategy(text, config.chunk_strategy, config.chunk_max_chars, config.chunk_min_chars, config.chunk_overlap_chars):
            for t in provider.build_text_targets(chunk, f, "text"):
                all_targets.setdefault(t.index_name, []).append({"id": sha256_hash(f"{f}:{chunk[:50]}"), "values": t.vector, "metadata": t.metadata})

    # Images (text-description based)
    manifest = load_media_manifest(root / "image")
    for f in collect_files(root / "image", IMAGE_EXTENSIONS):
        meta = manifest.get(f.name, {"description": f.stem, "source_url": ""})
        for t in provider.build_image_targets(f, meta["description"], meta["source_url"]):
            all_targets.setdefault(t.index_name, []).append({"id": sha256_hash(f"img:{f}"), "values": t.vector, "metadata": t.metadata})

    # Videos (text-description based)
    manifest = load_media_manifest(root / "video")
    for f in collect_files(root / "video", VIDEO_EXTENSIONS):
        meta = manifest.get(f.name, {"description": f.stem, "source_url": ""})
        for t in provider.build_video_targets(f, meta["description"]):
            all_targets.setdefault(t.index_name, []).append({"id": sha256_hash(f"vid:{f}"), "values": t.vector, "metadata": t.metadata})

    for idx, vecs in all_targets.items():
        print(f"Upserting {len(vecs)} vectors to {idx} (namespace={namespace})")
        upsert_vectors(index_name=idx, vectors=vecs, pinecone_api_key=config.pinecone_api_key, namespace=namespace, expected_dim=None)
    print(f"✅ Azure OpenAI ingestion complete — {sum(len(v) for v in all_targets.values())} vectors")


def _query(query_text: str, namespace: str, top_k: int):
    from pinecone_rag.embeddings.azure_provider import AzureOpenAIProvider
    from pinecone_rag.pinecone_client import query_index

    config = _Config()
    provider = AzureOpenAIProvider(config)
    targets = provider.build_query_targets(query_text)

    all_matches = []
    for target in targets:
        matches = query_index(index_name=target.index_name, vector=target.vector, pinecone_api_key=config.pinecone_api_key, namespace=namespace, top_k=top_k)
        for m in matches:
            meta = m.get("metadata", {})
            all_matches.append({"score": m.get("score", 0), "text": meta.get("text", ""), "modality": meta.get("modality", ""), "filename": meta.get("filename", "")})

    all_matches.sort(key=lambda x: x["score"], reverse=True)
    print(f"\n🔍 Query: {query_text} | Namespace: {namespace} | {len(all_matches)} results\n")
    for i, match in enumerate(all_matches[:top_k], 1):
        print(f"  [{i}] score={match['score']:.4f} | {match['modality']}")
        print(f"      {match['text'][:200]}\n")

    # Optional: synthesize with Azure OpenAI
    chat_deployment = config.azure_openai_chat_deployment
    if all_matches and chat_deployment:
        from openai import OpenAI
        client = OpenAI(
            api_key=config.azure_openai_api_key,
            base_url=f"{config.azure_openai_endpoint}/openai/deployments/{chat_deployment}",
            default_headers={"api-key": config.azure_openai_api_key},
            default_query={"api-version": config.azure_openai_api_version},
        )
        context = "\n\n".join(m["text"] for m in all_matches[:top_k] if m["text"])
        response = client.chat.completions.create(
            model=chat_deployment,
            messages=[
                {"role": "system", "content": "Answer using only the provided context."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query_text}"},
            ],
            temperature=0.2,
        )
        print(f"  💡 Answer: {response.choices[0].message.content}\n")


def main():
    parser = argparse.ArgumentParser(description="Azure OpenAI + Pinecone RAG Pipeline")
    parser.add_argument("--ingest", action="store_true", help="Run ingestion")
    parser.add_argument("--query", "-q", type=str, help="Query text")
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if not args.ingest and not args.query:
        parser.print_help()
        sys.exit(0)
    if args.ingest:
        _ingest(args.namespace, args.data_dir)
    if args.query:
        _query(args.query, args.namespace, args.top_k)


if __name__ == "__main__":
    main()
