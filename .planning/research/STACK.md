# Technology Stack

**Project:** Flutter Multimodal RAG Demo
**Researched:** 2026-02-20

## Recommended Stack

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11+ | Backend runtime | Current implementation, excellent AI/ML ecosystem |
| FastAPI | 0.115+ | REST API framework | Already implemented, async support, OpenAPI docs |
| Flutter | 3.24+ | Mobile frontend | Cross-platform, existing implementation |

### Embedding Providers
| Provider | Model | Dimension | Modalities | When to Use |
|----------|-------|-----------|------------|-------------|
| AWS Nova | nova-2-multimodal-embeddings-v1:0 | 1024/3072/384/256 (Matryoshka) | Text, Image, Video, Audio, Documents | **Primary recommendation** - Most complete unified solution |
| Vertex AI | multimodalembedding@001 | 1408/512/256/128 | Text, Image, Video | GCP ecosystems, enterprise compliance |
| OpenAI | text-embedding-3-large | 3072 (configurable) | Text only | Text-heavy workloads, highest text accuracy |
| Cohere | embed-4 | 1024 | Text, Image | Enterprise with multilingual needs (100+ languages) |

### Vector Database
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Pinecone | Serverless | Vector storage | Already implemented, managed scaling, integrated inference |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openai | 1.60+ | OpenAI API client | OpenAI provider |
| boto3 | 1.37+ | AWS SDK | Nova provider |
| google-auth | 2.38+ | GCP authentication | Vertex provider |
| google-cloud-storage | 3.1+ | GCS integration | Vertex video processing |
| sentence-transformers | 3.4+ | CLIP models | OpenAI multimodal fallback |
| opencv-python | 4.11+ | Video frame extraction | Video processing |
| Pillow | 11.1+ | Image handling | Image processing |
| pypdf | 5.4+ | PDF extraction | Document ingestion |
| python-docx | 1.1+ | DOCX extraction | Document ingestion |
| tiktoken | 0.8+ | Token counting | Text chunking |
| numpy | 1.26+ | Vector operations | Embedding math |

### Flutter Dependencies
| Package | Purpose |
|---------|---------|
| flutter_dotenv | Environment configuration |
| http | API client |
| image_picker | Image/video capture |
| file_picker | Document selection |

## Provider-Specific Recommendations

### OpenAI Provider (Current Implementation)
```bash
# Text embeddings
pip install openai==1.60.1 tiktoken==0.8.0

# Multimodal fallback (CLIP)
pip install sentence-transformers==3.4.1 Pillow==11.1.0 opencv-python==4.11.0.86
```

**Recommendation:** Keep text-embedding-3-large for text. Consider upgrading CLIP model:
- Current: `clip-ViT-B-32` (512d)
- Upgrade options:
  - `clip-ViT-L-14` (768d) - Better accuracy
  - `clip-ViT-H-14` (1024d) - Best accuracy, slower

### AWS Nova Provider (Recommended Primary)
```bash
pip install boto3==1.37.11
```

**Configuration:**
```python
# Synchronous API (videos < 30s)
response = bedrock_runtime.invoke_model(
    modelId="amazon.nova-2-multimodal-embeddings-v1:0",
    body=json.dumps({
        "schemaVersion": "1.0",
        "inputType": "search_document",  # or "search_query"
        "embeddingConfig": {"outputEmbeddingLength": 1024},
        "texts": [{"text": "..."}],
        # or "images", "videos", "audios" for multimodal
    })
)

# Async API (videos > 30s)
response = bedrock_runtime.start_async_invoke(
    modelId="amazon.nova-2-multimodal-embeddings-v1:0",
    # ... with segmentation config
)
```

### Vertex AI Provider
```bash
pip install google-auth==2.38.0 google-cloud-storage==3.1.0
```

**Configuration:**
```python
# Multimodal embeddings endpoint
url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/multimodalembedding@001:predict"

# Request body
payload = {
    "instances": [{
        "text": "optional text",
        "image": {"bytesBase64Encoded": "..."},
        "video": {"gcsUri": "gs://bucket/video.mp4"}
    }],
    "parameters": {"dimension": 1408}  # or 128, 256, 512
}
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Embedding | AWS Nova | OpenAI CLIP | Nova is unified multimodal, OpenAI requires hybrid |
| Embedding | AWS Nova | Cohere Embed 4 | Cohere lacks audio support; Nova is more complete |
| Vector DB | Pinecone | Milvus | Current implementation uses Pinecone; Milvus requires self-hosting |
| Vector DB | Pinecone | Weaviate | Pinecone has integrated inference; Weaviate similar capability |
| Text Embedding | text-embedding-3-large | text-embedding-3-small | Large has 64.6% vs 62.3% MTEB benchmark |

## Installation

```bash
# Core backend
pip install fastapi==0.115.12 uvicorn==0.34.0 pydantic==2.10.6 pydantic-settings==2.7.1

# Vector database
pip install pinecone-client==5.0.1

# OpenAI provider
pip install openai==1.60.1 tiktoken==0.8.0 sentence-transformers==3.4.1

# AWS Nova provider
pip install boto3==1.37.11

# Vertex AI provider
pip install google-auth==2.38.0 google-cloud-storage==3.1.0

# Document processing
pip install pypdf==5.4.0 python-docx==1.1.2

# Media processing
pip install opencv-python==4.11.0.86 Pillow==11.1.0

# Database
pip install SQLAlchemy==2.0.37

# Utilities
pip install python-dotenv==1.0.1 requests==2.32.3 numpy==1.26.4
```

## Environment Variables

```bash
# Required
PINECONE_API_KEY="pcsk-..."

# Provider selection
MULTIMODAL_PROVIDER="aws_nova"  # openai_clip | vertex | aws_nova

# OpenAI
OPENAI_API_KEY="sk-..."
OPENAI_TEXT_EMBEDDING_MODEL="text-embedding-3-large"
OPENAI_TEXT_EMBEDDING_DIMENSION="3072"

# AWS Nova
AWS_REGION="us-east-1"
AWS_NOVA_EMBEDDING_MODEL="amazon.nova-2-multimodal-embeddings-v1:0"
AWS_NOVA_EMBEDDING_DIMENSION="1024"

# Vertex AI
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"
GOOGLE_VERTEX_MODEL="multimodalembedding@001"
GOOGLE_VERTEX_EMBEDDING_DIMENSION="1408"
VERTEX_VIDEO_GCS_BUCKET="your-bucket"

# Pinecone indexes
PINECONE_INDEX_OPENAI_TEXT_3072="openai-text-index"
PINECONE_INDEX_OPENAI_CLIP_512="openai-clip-index"
PINECONE_INDEX_AWS_NOVA_1024="nova-multimodal-index"
PINECONE_INDEX_VERTEX_1408="vertex-multimodal-index"
```

## Sources

- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
- AWS Nova Multimodal: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-nova-embed.html
- Vertex AI Multimodal: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-embeddings-api
- Cohere Embed 4: https://docs.cohere.com/reference/embed
- Pinecone Integrated Inference: https://www.pinecone.io/blog/simplifying-vector-embeddings-with-pinecone-integrated-inference/
