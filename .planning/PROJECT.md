# Project Context

**Project:** Flutter RAG Demo - Multimodal Retrieval-Augmented Generation
**Type:** Full-stack application with Python backend and Flutter frontend

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Flutter App    │────▶│  FastAPI Backend│────▶│  Pinecone DB    │
│  (mobile/web)   │     │  (Python)       │     │  (vectors)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ OpenAI + CLIP │     │  Vertex AI    │     │  AWS Nova     │
│ (hybrid)      │     │  (unified)    │     │  (unified)    │
└───────────────┘     └───────────────┘     └───────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `pinecone-multimodal-pipeline.py` | Main pipeline: chunking, providers, ingestion |
| `backend/` | FastAPI service with MemoryService |
| `app/` | Flutter frontend |
| `.env_sample` | Configuration template |

## Provider Matrix

| Provider | Text | Image | Video | Audio | Dimension |
|----------|------|-------|-------|-------|-----------|
| OpenAI + CLIP | 3072d | 512d | 512d | transcribe | separate indexes |
| Vertex AI | 1408d | 1408d | 1408d | transcribe | unified |
| AWS Nova | 1024d | 1024d | 1024d | 1024d | unified |

## Current Limitations

1. **Chunking**: Simple paragraph-based, no overlap
2. **CLIP**: Fixed to ViT-B-32 (512d)
3. **Configuration**: Hardcoded chunk sizes
