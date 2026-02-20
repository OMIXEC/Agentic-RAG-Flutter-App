# Project State

**Updated:** 2026-02-20
**Status:** Active Development

## Current Position

**Phase:** 01-openai-enhancement (complete — all 3 plans executed)
**Plan:** 3 of 3 in current phase
**Status:** Phase complete
**Last activity:** 2026-02-20 - Completed 01-03-PLAN.md

Progress: ███░░░░░░░ 30% (3/10 estimated plans)

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

## Active Concerns

1. **Chunking quality** - Paragraph-based chunking available; semantic strategy available but needs testing
2. **CLIP model accuracy** - ViT-B-32 (512d) default; ViT-L-14/H-14 now supported via env var
3. **No chunk overlap by default** - CHUNK_OVERLAP_CHARS="0" in config; overlap support now implemented

## Session Continuity

**Last session:** 2026-02-20 03:58 UTC
**Stopped at:** Completed 01-03-PLAN.md
**Resume file:** None

## File Ownership Map

| File | Purpose |
|------|---------|
| pinecone-multimodal-pipeline.py | Main pipeline with `_chunk_text()`, providers |
| backend/config.py | FastAPI settings dataclass |
| .env_sample | Environment variable template |
