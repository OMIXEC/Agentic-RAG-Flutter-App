# Project State

**Updated:** 2026-02-20
**Status:** Active Development

## Current Position

**Phase:** 01-openai-enhancement
**Status:** Planning Complete

## Tech Stack

### Backend
- Python 3.11+
- FastAPI (backend/)
- Pinecone vector storage (multi-index architecture)
- OpenAI API (text-embedding-3-large, Whisper)
- Sentence Transformers (CLIP models)
- Google Vertex AI (multimodalembedding@001)
- AWS Bedrock (Nova multimodal embeddings)

### Frontend
- Flutter 3.x
- Dart with flutter_lints

## Accumulated Decisions

1. **Multi-provider architecture** - Three providers (OpenAI, Vertex, Nova) with separate Pinecone indexes per dimension
2. **CLIP for OpenAI multimodal** - Hybrid approach: OpenAI text embeddings + CLIP for media
3. **Chunk-based ingestion** - 1200 char max, 80 char min, paragraph-based splitting
4. **Dimension separation** - Each provider/dimension combination gets its own Pinecone index

## Active Concerns

1. **Chunking quality** - Current paragraph-based chunking loses semantic context
2. **CLIP model accuracy** - ViT-B-32 (512d) is less accurate than larger models
3. **No chunk overlap** - Context lost at chunk boundaries

## File Ownership Map

| File | Purpose |
|------|---------|
| pinecone-multimodal-pipeline.py | Main pipeline with `_chunk_text()`, providers |
| backend/config.py | FastAPI settings dataclass |
| .env_sample | Environment variable template |
