# Domain Pitfalls

**Domain:** Multimodal Retrieval-Augmented Generation (RAG)
**Researched:** 2026-02-20

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Dimension Mismatch in Vector Index
**What goes wrong:** Storing vectors of different dimensions in the same Pinecone index
**Why it happens:** Pinecone indexes have a fixed dimension set at creation; developers may assume they can store any vector
**Consequences:** 
- Pinecone API errors on upsert
- Corrupted data if somehow stored
- Retrieval failures or wrong results
**Prevention:** 
- Use separate indexes per provider/dimension combination
- Validate vector dimensions before upsert (already implemented in `_validate_vector_dimensions`)
- Document dimension requirements in environment setup
**Detection:** 
- Preflight check (implemented in `_preflight_pinecone_indexes`)
- Monitor Pinecone API error rates

### Pitfall 2: Retrieval Drift Across Modalities
**What goes wrong:** Text and image embeddings diverge semantically when stored in separate vector spaces
**Why it happens:** Different embedding models (text-embedding-3-large vs CLIP) create incompatible semantic spaces
**Consequences:**
- Cross-modal search returns irrelevant results
- "Search image with text" fails
- User trust degradation
**Prevention:**
- Use unified multimodal models (Nova, Vertex) for all modalities
- If using OpenAI, maintain separate text and media indexes and fuse results
- Implement cross-modal validation tests
**Detection:**
- Monitor retrieval precision/recall metrics
- A/B test unified vs separate index approaches

### Pitfall 3: Context Loss from Aggressive Chunking
**What goes wrong:** Chunking breaks semantic context, making retrieval useless
**Why it happens:** Fixed-size chunking ignores document structure (headings, tables, lists)
**Consequences:**
- Retrieved chunks lack necessary context
- LLM generates irrelevant answers
- Users frustrated with "out of context" responses
**Prevention:**
- Use semantic chunking (split on paragraphs, not characters)
- Preserve document structure metadata
- Implement overlap between chunks (10-20%)
**Detection:**
- Evaluate chunk coherence scores
- User feedback on answer quality

### Pitfall 4: Blocking on Long Video Processing
**What goes wrong:** Processing videos > 30 seconds synchronously causes timeouts and poor UX
**Why it happens:** Video embedding APIs have time limits; developers don't account for this
**Consequences:**
- Request timeouts
- Frontend hangs
- Incomplete ingestions
**Prevention:**
- Use async APIs for long content (Nova `start_async_invoke`)
- Implement job queue with status polling
- Chunk long videos into segments
**Detection:**
- Monitor request latency
- Track video processing failures by duration

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: Wrong inputType for Nova Embeddings
**What goes wrong:** Using `search_document` for queries or `search_query` for indexing
**Prevention:** Always use `search_document` when indexing, `search_query` when searching
```python
# Correct usage
if is_indexing:
    payload["inputType"] = "search_document"
else:
    payload["inputType"] = "search_query"
```

### Pitfall 6: Ignoring Audio Transcription for Non-Nova Providers
**What goes wrong:** Audio files ingested without transcription have no searchable content
**Prevention:** Always run Whisper transcription for audio files with OpenAI/Vertex providers
**Current status:** Implemented via `_transcribe()` method

### Pitfall 7: Video Frame Sampling Without GCS Bucket (Vertex)
**What goes wrong:** Vertex video embeddings fail without GCS bucket configured
**Prevention:** 
- Configure `VERTEX_VIDEO_GCS_BUCKET` for Vertex provider
- Implement frame-sampling fallback (already implemented)
**Detection:** Check for `gcsUri` in video embedding requests

### Pitfall 8: Pinecone Namespace Collision
**What goes wrong:** Multiple users share same Pinecone namespace, seeing each other's data
**Prevention:** Always use `user_id` as Pinecone namespace
**Current status:** Implemented correctly in MemoryService

### Pitfall 9: Metadata Size Limits
**What goes wrong:** Pinecone metadata exceeds 40KB limit, causing upsert failures
**Prevention:**
- Truncate text fields in metadata
- Store full text in separate storage, reference by ID
- Current implementation truncates summary to 500 chars

### Pitfall 10: Embedding Model Deprecation
**What goes wrong:** Model deprecated or replaced, breaking existing embeddings
**Prevention:**
- Version embeddings with `embedding_model` metadata
- Plan migration strategy for model updates
- Current implementation stores `embedding_model` in metadata

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 11: CLIP Model Selection
**What goes wrong:** Using smaller CLIP model (ViT-B-32) when larger models available
**Prevention:** Consider upgrading to `clip-ViT-L-14` (768d) or `clip-ViT-H-14` (1024d) for better accuracy
**Trade-off:** Larger models are slower and require more memory

### Pitfall 12: Missing Error Context in Logs
**What goes wrong:** Errors logged without sufficient context to debug
**Prevention:** Include `provider`, `index_name`, `user_id`, `media_type` in all error logs
**Current status:** Partial implementation in error handling

### Pitfall 13: Inconsistent Vector ID Generation
**What goes wrong:** Same content generates different vector IDs, creating duplicates
**Prevention:** Use deterministic hashing based on content + source + index
**Current status:** Implemented via `_sha()` function

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| OpenAI Enhancement | CLIP model accuracy | Offer multiple CLIP model options |
| Nova Integration | Async video processing | Implement job queue early |
| Vertex Enhancement | GCS bucket requirement | Clear setup documentation |
| Multi-provider Fusion | Weight tuning | A/B test fusion weights |
| Flutter Frontend | Large file upload | Implement chunked upload |

## Common Error Messages and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Dimension mismatch" | Vector dimension doesn't match index | Check provider configuration, verify index dimension |
| "Pinecone preflight validation failed" | Index doesn't exist or wrong dimension | Create index with correct dimension |
| "Vertex predict failed" | API authentication or quota issue | Check GOOGLE_APPLICATION_CREDENTIALS, verify quota |
| "Nova invoke_model failed" | Bedrock access or invalid input | Check Bedrock permissions, validate input format |
| "No vectors produced during load" | Empty input or processing failure | Check data folder, verify file formats |

## Testing Checklist

Before deploying to production:

- [ ] Test all providers individually with sample data
- [ ] Verify dimension validation catches mismatches
- [ ] Test cross-modal search (text → image, image → text)
- [ ] Test long video (>30s) with async processing
- [ ] Verify user isolation via namespaces
- [ ] Test metadata size limits with large documents
- [ ] Validate error handling and logging
- [ ] Load test with concurrent requests
- [ ] Test embedding model failover scenarios

## Sources

- Multimodal RAG Production Pitfalls: https://www.augmentcode.com/guides/multimodal-rag-development-12-best-practices-for-production-systems
- RAG Best Practices Study: https://arxiv.org/abs/2501.07391
- Pinecone Documentation: https://docs.pinecone.io/troubleshooting/errors
- AWS Nova Technical Report: https://assets.amazon.science/de/d4/149300334682a464963f01553ffb/nova-mme-technical-report-10.pdf
