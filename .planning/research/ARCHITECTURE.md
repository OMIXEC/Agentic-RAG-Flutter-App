# Architecture Patterns

**Domain:** Multimodal Retrieval-Augmented Generation (RAG)
**Researched:** 2026-02-20

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flutter Frontend                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐│
│  │ Chat UI  │  │ Memory   │  │ Backend  │  │ OpenAI Client    ││
│  │          │  │ Timeline │  │ API      │  │ (Dart)           ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘│
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP/REST
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ MemoryService│  │ ProviderRuntime│ │ PineconeStore        │  │
│  │              │──▶              │──▶                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         │                  │                       │            │
│         ▼                  ▼                       ▼            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Classifier   │  │ StorageService│ │ SQLite (metadata)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────────┐
│ OpenAI Provider│    │ Vertex Provider│    │ AWS Nova Provider │
│               │    │               │    │                   │
│ • text-embed-3│    │ • multimodal  │    │ • nova-2-multimodal│
│ • CLIP (local)│    │   embedding   │    │   embeddings      │
│ • Whisper     │    │ • GCS video   │    │ • Native audio    │
└───────┬───────┘    └───────┬───────┘    └─────────┬─────────┘
        │                    │                      │
        ▼                    ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────────┐
│ Pinecone      │    │ Pinecone      │    │ Pinecone          │
│ Index:        │    │ Index:        │    │ Index:            │
│ • text-3072   │    │ vertex-1408   │    │ nova-1024         │
│ • clip-512    │    │               │    │                   │
└───────────────┘    └───────────────┘    └───────────────────┘
```

## Recommended Architecture Enhancements

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Flutter Frontend | User interaction, media capture, chat UI | Backend API |
| Backend API (FastAPI) | REST endpoints, authentication, request routing | MemoryService, StorageService |
| MemoryService | Ingestion orchestration, search, memory lifecycle | ProviderRuntime, PineconeStore, DB |
| ProviderRuntime | Embedding generation, provider abstraction | Provider implementations |
| PineconeStore | Vector storage, upsert/query operations | Pinecone API |
| StorageService | File storage, GCS/S3 abstraction | Cloud storage APIs |
| Classifier | Memory type classification | LLM (OpenAI) |

### Data Flow

```
Ingestion Flow:
1. Client → Backend API: POST /ingest with file
2. Backend → StorageService: Store file (GCS/S3/local)
3. Backend → MemoryService.ingest()
4. MemoryService → ProviderRuntime.build_*_targets()
5. ProviderRuntime → Embedding Provider API: Generate embeddings
6. MemoryService → PineconeStore.upsert()
7. MemoryService → SQLite: Store metadata

Query Flow:
1. Client → Backend API: POST /search with query
2. Backend → MemoryService.search()
3. MemoryService → ProviderRuntime.build_query_targets()
4. MemoryService → PineconeStore.query()
5. MemoryService → Fusion.weighted_rrf()
6. Backend → Client: Return SearchResult[]
```

## Patterns to Follow

### Pattern 1: Provider Abstraction
**What:** Abstract embedding providers behind a common interface
**When:** All provider interactions
**Example:**
```python
class BaseProvider:
    def build_text_targets(self, chunk: str, source: Path, kind: str) -> list[IndexTarget]:
        raise NotImplementedError
    
    def build_image_targets(self, file_path: Path, description: str) -> list[IndexTarget]:
        raise NotImplementedError
    
    def build_query_targets(self, query: str) -> list[QueryTarget]:
        raise NotImplementedError

# Already implemented in pinecone-multimodal-pipeline.py
```

### Pattern 2: Index Per Provider/Dimension
**What:** Use separate Pinecone indexes for each provider/dimension combination
**When:** Multiple embedding models in same system
**Example:**
```python
# Current implementation (correct)
PINECONE_INDEX_OPENAI_TEXT_3072 = "openai-text-3072"
PINECONE_INDEX_OPENAI_CLIP_512 = "openai-clip-512"
PINECONE_INDEX_AWS_NOVA_1024 = "nova-multimodal-1024"
PINECONE_INDEX_VERTEX_1408 = "vertex-multimodal-1408"
```

### Pattern 3: Weighted RRF Fusion
**What:** Combine results from multiple indexes using weighted reciprocal rank fusion
**When:** Multi-provider or multi-modal search
**Example:**
```python
# Already implemented in backend/fusion.py
def weighted_rrf(
    per_source_results: dict[str, list[dict]],
    weights: dict[str, float] = None,
    k: int = 60
) -> list[dict]:
    # Combines results from text/media/vertex/aws_nova indexes
    # Default weights: text=1.0, media=0.8, vertex=1.0, aws_nova=0.9
```

### Pattern 4: Async Processing for Long Media
**What:** Use async APIs for videos > 30 seconds
**When:** Nova provider with long videos
**Example:**
```python
# Sync for short content
response = bedrock.invoke_model(modelId="amazon.nova-2-multimodal-embeddings-v1:0", ...)

# Async for long content
response = bedrock.start_async_invoke(
    modelId="amazon.nova-2-multimodal-embeddings-v1:0",
    inputDataConfig={
        "s3InputDataConfig": {"s3Uri": "s3://bucket/video.mp4"}
    },
    outputDataConfig={
        "s3OutputDataConfig": {"s3Uri": "s3://bucket/output/"}
    }
)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Mixed Dimensions in Same Index
**What:** Storing vectors of different dimensions in the same Pinecone index
**Why bad:** Pinecone indexes have fixed dimension; mixing causes errors or corruption
**Instead:** Use separate indexes per dimension (current approach is correct)

### Anti-Pattern 2: Synchronous Long Video Processing
**What:** Processing long videos (>30s) synchronously
**Why bad:** Blocks threads, timeout errors, poor UX
**Instead:** Use async APIs with job queue and status polling

### Anti-Pattern 3: Ignoring Provider-Specific InputType
**What:** Using same embedding parameters for indexing and querying
**Why bad:** Nova optimizes differently for `search_document` vs `search_query`
**Instead:**
```python
# Indexing
payload = {"inputType": "search_document", "texts": [{"text": content}]}

# Querying
payload = {"inputType": "search_query", "texts": [{"text": query}]}
```

### Anti-Pattern 4: CLIP as Primary Multimodal Solution
**What:** Relying solely on CLIP for multimodal embeddings
**Why bad:** CLIP is 512d, less accurate than 1024d+ models; no native audio/video
**Instead:** Use unified multimodal models (Nova, Vertex) for production

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| Embedding API calls | Direct API | Connection pooling + retry | Queue-based batching |
| Pinecone queries | 1 index | Multiple indexes + namespaces | Sharding by user/tenant |
| File storage | Local filesystem | GCS/S3 with lifecycle | Multi-region replication |
| Backend instances | Single FastAPI | Load-balanced containers | Kubernetes + auto-scaling |
| Memory database | SQLite | PostgreSQL | Distributed DB (CockroachDB) |

## Recommended Architecture Changes

### 1. Add Job Queue for Async Processing
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ FastAPI     │───▶│ Redis Queue │───▶│ Worker      │
│ (ingest)    │    │             │    │ (embed)     │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 2. Add Caching Layer
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ FastAPI     │───▶│ Redis Cache │───▶│ Pinecone    │
│ (search)    │    │ (queries)   │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 3. Add Reranking Step
```
Query → Pinecone (retrieve top_k*3) → Reranker → Top K results
```

## Sources

- Multimodal RAG Architecture: https://www.augmentcode.com/guides/multimodal-rag-development-12-best-practices-for-production-systems
- RAG Best Practices: https://arxiv.org/abs/2501.07391
- AWS Nova Architecture: https://aws.amazon.com/blogs/machine-learning/a-practical-guide-to-amazon-nova-multimodal-embeddings/
- Vector Database Comparison: https://www.firecrawl.dev/blog/best-vector-databases-2025
