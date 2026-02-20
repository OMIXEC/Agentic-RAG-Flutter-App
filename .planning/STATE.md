# Project State

**Updated:** 2026-02-20
**Status:** Active Development

## Current Position

**Phase:** 02-aws-nova-integration (in progress)
**Plan:** 1 of 3 in current phase
**Status:** In progress
**Last activity:** 2026-02-20 - Completed 02-01-PLAN.md

Progress: ████░░░░░░ 40% (4/10 estimated plans)

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
3. **Chunk-based ingestion** - 1200 char max, 80 char min, paragraph-based splitting with configurable overlap
4. **Dimension separation** - Each provider/dimension combination gets its own Pinecone index
5. **CLIP dimension warnings (not exceptions)** - Mismatch between model name and config dimension is surfaced via print() to allow user choice; Pinecone preflight handles hard enforcement
6. **CLIP model auto-detection** - `_resolve_clip_expected_dim()` maps model name to dimension; OPENAI_CLIP_EMBEDDING_DIMENSION can override
7. **Nova video size guard returns [] not raises** - Oversized files (>20MB) skip embed cleanly; raising would crash the entire ingestion run
8. **AWS_NOVA_VIDEO_MAX_BYTES default = 20MB** - Base64 encoding adds ~33% overhead; 20MB raw → ~26.7MB encoded is near Bedrock's 25MB limit; margin prevents payload rejection

## Active Concerns

1. **Chunking quality** - Paragraph-based chunking available; semantic strategy available but needs testing
2. **CLIP model accuracy** - ViT-B-32 (512d) default; ViT-L-14/H-14 now supported via env var
3. **No chunk overlap by default** - CHUNK_OVERLAP_CHARS="0" in config; overlap support now implemented

## Session Continuity

**Last session:** 2026-02-20 04:13 UTC
**Stopped at:** Completed 02-01-PLAN.md
**Resume file:** None

## File Ownership Map

| File | Purpose |
|------|---------|
| pinecone-multimodal-pipeline.py | Main pipeline with `_chunk_text()`, providers |
| backend/config.py | FastAPI settings dataclass |
| .env_sample | Environment variable template |
