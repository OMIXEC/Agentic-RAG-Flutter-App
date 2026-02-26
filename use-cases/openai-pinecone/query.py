"""OpenAI + Pinecone RAG — Query Pinecone and synthesize answers.

Usage:
    python query.py --namespace my-project --query "What happened last week?"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "core"))

from pinecone_rag.config import OpenAISettings, PineconeSettings
from pinecone_rag.embeddings.openai_provider import OpenAIClipProvider
from pinecone_rag.pinecone_client import query_index


class _Config:
    def __init__(self, openai: OpenAISettings, pinecone: PineconeSettings):
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


def query(query_text: str, namespace: str, top_k: int = 5) -> None:
    load_dotenv()
    openai_cfg = OpenAISettings()
    pinecone_cfg = PineconeSettings()
    config = _Config(openai_cfg, pinecone_cfg)

    provider = OpenAIClipProvider(config)
    targets = provider.build_query_targets(query_text)

    all_matches = []
    for target in targets:
        matches = query_index(
            index_name=target.index_name,
            vector=target.vector,
            pinecone_api_key=config.pinecone_api_key,
            namespace=namespace,
            top_k=top_k,
        )
        for m in matches:
            meta = m.get("metadata", {})
            all_matches.append({
                "score": m.get("score", 0),
                "text": meta.get("text", ""),
                "modality": meta.get("modality", "unknown"),
                "filename": meta.get("filename", ""),
                "index": target.label,
            })

    # Sort by relevance
    all_matches.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n🔍 Query: {query_text}")
    print(f"   Namespace: {namespace} | Top-K: {top_k}")
    print(f"   Found: {len(all_matches)} results\n")

    for i, match in enumerate(all_matches[:top_k], 1):
        print(f"  [{i}] score={match['score']:.4f} | {match['modality']} | {match['index']}")
        print(f"      {match['text'][:200]}")
        print(f"      file: {match['filename']}")
        print()

    # Optional: synthesize answer with OpenAI
    if all_matches and openai_cfg.openai_api_key:
        from openai import OpenAI
        client = OpenAI(api_key=openai_cfg.openai_api_key)
        context = "\n\n".join(m["text"] for m in all_matches[:top_k] if m["text"])
        prompt = (
            f"Answer the following question using ONLY the context below.\n\n"
            f"Context:\n{context}\n\nQuestion: {query_text}\n\nAnswer:"
        )
        response = client.chat.completions.create(
            model=openai_cfg.openai_chat_model,
            messages=[
                {"role": "system", "content": "You are a helpful RAG assistant. Answer using only the provided context."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        answer = response.choices[0].message.content
        print(f"  💡 Synthesized Answer:\n  {answer}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query Pinecone using OpenAI embeddings")
    parser.add_argument("--query", "-q", required=True, help="Query text")
    parser.add_argument("--namespace", default="default", help="Pinecone namespace")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    args = parser.parse_args()
    query(args.query, args.namespace, args.top_k)
