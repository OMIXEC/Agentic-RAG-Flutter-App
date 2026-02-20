# Project State

**Updated:** 2026-02-20
**Status:** Active Development

## Current Position

**Phase:** 03-vertex-ai-enhancement (in progress)
**Plan:** 1 of 2 in current phase
**Status:** In progress
**Last activity:** 2026-02-20 - Completed 03-01-PLAN.md

Progress: ███████░░░ 70% (7/10 estimated plans)

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
9. **Mock Path.stat at class level in tests** - PosixPath instance attributes are read-only; use `mock.patch.object(Path, 'stat', ...)` not instance-level patching
10. **Audio fallback tests need >80 char transcripts** - chunk_min_chars=80 silently drops short strings; tests must use long enough transcript to produce chunks
11. **Nova dimension validation uses print() not raise** - Matches CLIP pattern; Pinecone preflight is the hard enforcement; users can proceed if they know what they're doing
12. **AWS_NOVA_EMBEDDING_DIMENSION was undocumented** - Pipeline already read it (line 542-543) but .env_sample didn't list it; added in 02-03
13. **Vertex dimension validation uses print() + fallback to 1408d** - Consistent with CLIP/Nova pattern; invalid GOOGLE_VERTEX_EMBEDDING_DIMENSION auto-corrects to 1408d (max quality); Pinecone preflight handles hard enforcement
14. **Nova defaults corrected to 3072d** - 3072d is the AWS-documented native maximum for amazon.nova-2-multimodal-embeddings-v1; prior 1024d default was a placeholder
15. **pinecone_index_aws_nova_1024 attribute name preserved** - Renaming Python attribute would break existing tests and configs; field name left as-is even after Nova default correction to 3072d
16. **PINECONE_INDEX_VERTEX_1408 locked name** - .env_sample uses 'multimodal-embedding-vertex-1408d' as the locked naming convention for Vertex indexes

## Active Concerns

1. **Chunking quality** - Paragraph-based chunking available; semantic strategy available but needs testing
2. **CLIP model accuracy** - ViT-B-32 (512d) default; ViT-L-14/H-14 now supported via env var
3. **No chunk overlap by default** - CHUNK_OVERLAP_CHARS="0" in config; overlap support now implemented

## Session Continuity

**Last session:** 2026-02-20 14:27 UTC
**Stopped at:** Completed 03-01-PLAN.md (Vertex dimension validation + Nova defaults)
**Resume file:** None

## File Ownership Map

| File | Purpose |
|------|---------|
| pinecone-multimodal-pipeline.py | Main pipeline with `_chunk_text()`, providers, `_VERTEX_ALLOWED_DIMS` |
| backend/config.py | FastAPI settings dataclass |
| .env_sample | Environment variable template (8 Vertex vars documented) |
| tests/test_multimodal_pipeline.py | 22 tests covering all providers and Nova multimodal paths |
