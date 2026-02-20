# Feature Landscape

**Domain:** Multimodal Retrieval-Augmented Generation (RAG)
**Researched:** 2026-02-20

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Text ingestion | Core RAG functionality | Low | Implemented - chunking with 1200 char max |
| Semantic search | Primary use case | Low | Implemented - cosine similarity via Pinecone |
| PDF/DOCX support | Common document formats | Medium | Implemented via pypdf, python-docx |
| Image ingestion | Multimodal expectation | Medium | Implemented via CLIP (OpenAI) or native (Nova/Vertex) |
| Chat interface | User interaction pattern | Low | Implemented in Flutter |
| Query history | UX expectation | Low | Partially implemented via memory timeline |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Native audio embeddings | Most RAG systems use transcription only | High | **Nova only** - true audio semantic search |
| Native video embeddings | Rare in RAG systems | High | Nova/Vertex support; OpenAI uses frame sampling |
| Cross-modal search | Search images with text, videos with images | High | Unified embedding space enables this |
| Multi-provider fusion | Combine results from multiple embedding models | Medium | Implemented via weighted RRF fusion |
| Matryoshka dimensions | Adjustable embedding size (256-3072d) | Low | **Nova only** - cost/performance tradeoff |
| Memory classification | Auto-categorize memories (episodic, semantic, etc.) | Medium | Implemented via backend/classifier.py |
| Promotion system | Automatic promotion to long-term memory | Medium | Implemented via db.promote_memories() |
| Async video processing | Handle long videos without blocking | High | Nova supports async API for >30s videos |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Single index for all providers | Dimension mismatches cause retrieval failures | Use separate indexes per provider/dimension |
| Fixed chunk size | Ignores document structure, loses context | Use semantic chunking or recursive splitting |
| CLIP-only multimodal | 512d CLIP vectors are less accurate than 1024d+ | Use unified multimodal models (Nova, Vertex) |
| Synchronous long video processing | Blocks threads, poor UX | Use async APIs with segmentation |
| Ignoring transcript for audio | Loses semantic content | Always extract transcript as fallback |
| Same embedding for indexing/query | Suboptimal retrieval | Use `search_document` for indexing, `search_query` for queries |

## Feature Dependencies

```
Text Ingestion
    └── Semantic Search (depends on Text Ingestion)

Image Ingestion
    └── Cross-modal Search (depends on Text + Image)

Video Ingestion
    ├── Frame Extraction (OpenAI/Vertex fallback)
    └── Native Video Embeddings (Nova/Vertex)
        └── Cross-modal Search

Audio Ingestion
    ├── Transcription (OpenAI/Vertex fallback)
    └── Native Audio Embeddings (Nova only)
        └── Cross-modal Search

All Modalities
    └── Multi-provider Fusion
        └── Memory Classification
            └── Promotion System
```

## Provider Feature Matrix

| Feature | OpenAI + CLIP | Vertex AI | AWS Nova |
|---------|---------------|-----------|----------|
| Text embeddings | text-embedding-3-large (3072d) | multimodalembedding (1408d) | nova-embed (1024d) |
| Image embeddings | CLIP (512d) - separate index | Native (1408d) | Native (1024d) |
| Video embeddings | CLIP frame sampling (512d) | Native with GCS (1408d) | Native (1024d) |
| Audio embeddings | Transcription only | Transcription only | **Native (1024d)** |
| Document embeddings | Text extraction | Text extraction | **Native (1024d)** |
| Cross-modal search | Separate indexes required | Unified space | Unified space |
| Dimension options | 3072, 1536, etc. | 1408, 512, 256, 128 | 3072, 1024, 384, 256 |
| Async processing | No | No | **Yes (for video)** |
| Max text length | 8191 tokens | 1000 chars | 8192 tokens |
| Video length limit | N/A (frame sampling) | 2 min per request | 30s sync, async for longer |

## MVP Recommendation

For MVP, prioritize:
1. **Text ingestion with semantic search** (already implemented)
2. **Image ingestion with cross-modal search** (enhance Nova/Vertex support)
3. **AWS Nova as primary provider** (most complete multimodal support)

Defer to post-MVP:
- **Async video processing**: Requires job queue infrastructure
- **Cohere Embed 4 integration**: Additional provider complexity
- **Advanced chunking strategies**: Semantic/LLM-based chunking

## Feature Implementation Status

### Already Implemented
- [x] Text ingestion with chunking
- [x] PDF/DOCX document ingestion
- [x] Image ingestion (CLIP for OpenAI, native for Nova/Vertex)
- [x] Video ingestion (frame sampling for OpenAI, native for Nova/Vertex)
- [x] Audio ingestion (transcription for OpenAI/Vertex, native for Nova)
- [x] Semantic search across all modalities
- [x] Multi-provider support (OpenAI, Vertex, Nova)
- [x] Weighted RRF fusion for multi-provider results
- [x] Memory classification system
- [x] Memory promotion to long-term
- [x] Pinecone integration with multiple indexes
- [x] FastAPI backend with REST endpoints
- [x] Flutter frontend with chat UI

### Needs Enhancement
- [ ] Better chunking strategies (semantic, recursive)
- [ ] Async video processing for long videos
- [ ] Native audio embeddings (Nova)
- [ ] Document-native embeddings (Nova)
- [ ] Cross-modal search optimization
- [ ] Streaming responses in Flutter
- [ ] Image/video capture from mobile

### Not Implemented
- [ ] Cohere Embed 4 provider
- [ ] Evaluation/benchmarking framework
- [ ] Reranking after retrieval
- [ ] Query expansion
- [ ] Hybrid BM25 + dense retrieval

## Sources

- Multimodal RAG Best Practices: https://www.augmentcode.com/guides/multimodal-rag-development-12-best-practices-for-production-systems
- AWS Nova Multimodal Guide: https://aws.amazon.com/blogs/machine-learning/a-practical-guide-to-amazon-nova-multimodal-embeddings/
- Vertex AI Multimodal: https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-multimodal-embeddings
- RAG Chunking Strategies: https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025
