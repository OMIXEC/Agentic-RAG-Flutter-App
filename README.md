# Multimodal Pinecone RAG Pipeline

This repository now supports full multimodal ingestion/query across:
- GCP Vertex AI (`multimodalembedding@001`)
- AWS Bedrock Nova (`amazon.nova-2-multimodal-embeddings-v1:0`)
- OpenAI text embeddings + CLIP media embeddings (pattern aligned with OpenAI cookbook custom image embedding search)

## Supported Input Types
- Text: `.txt .md .csv .json .yaml .yml .xml`
- Documents: `.pdf .docx`
- Images: `.png .jpg .jpeg .webp .bmp`
- Videos: `.mp4 .mov .mkv .webm .avi`
- Audio: `.mp3 .wav .m4a .aac .flac .ogg`

## Scripts
- `pinecone-multimodal-pipeline.py`: shared pipeline core (`--provider openai_clip|vertex|aws_nova`).
- `ingest-openai.py` / `query-openai.py`: split OpenAI ingest/retrieval.
- `ingest-vertex.py` / `query-vertex.py`: split Vertex ingest/retrieval.
- `ingest-aws.py` / `query-aws.py`: split AWS ingest/retrieval.
- `ingest-legacy.py` / `query-legacy.py`: split legacy multimodal ingest/retrieval.
- `run-all-providers.py`: interactive runner for one/all providers and ingest/query/both.
- `pinecone-openai-load.py`: wrapper for OpenAI + CLIP mode.
- `pinecone-vertexai-load.py`: wrapper for Vertex mode.
- `pinecone-aws-load.py`: wrapper for AWS Nova mode.
- `pincecone-openai-load.py`: typo-compatible alias wrapper.
- `pinecone-db.py`: dispatcher wrapper (provider-specific ingest/query scripts).
- `backend/main.py`: FastAPI backend for user-isolated Search Memory APIs.

`pinecone-db.py` now routes to multimodal ingestion/query by default.  
Set `LEGACY_TXT_ONLY=true` to route through legacy multimodal wrappers.

## Separate Ingest/Retrieve
```bash
python ingest-openai.py --namespace user-a
python query-openai.py --namespace user-a --query "Find latest news image references"

python ingest-vertex.py --namespace user-a
python query-vertex.py --namespace user-a --query "What happened in tech this week?"

python ingest-aws.py --namespace user-a
python query-aws.py --namespace user-a --query "Find video memories about travel"
```

Interactive all-providers runner:
```bash
python run-all-providers.py
```

## Install
```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp .env app/.env
```

## Run Pipelines

### OpenAI + CLIP
```bash
python pinecone-openai-load.py --load
python pinecone-openai-load.py --query "Find media about architecture"
```

Strict isolated variant:
```bash
cp openai/.env.example openai/.env
python openai/ensure_pinecone_indexes.py --write-env
python openai/pinecone-openai-load.py --load
python openai/pinecone-openai-load.py --query "Find news images and related context"
```

### Vertex AI (GCP)
```bash
python pinecone-vertexai-load.py --load
python pinecone-vertexai-load.py --query "What is in the latest news snapshot?"
```

Strict isolated variant:
```bash
cp gcp/.env.example gcp/.env
python gcp/pinecone-vertex-load.py --load
python gcp/pinecone-vertex-load.py --query "Summarize recent memories"
```

### AWS Nova (Bedrock)
```bash
python pinecone-aws-load.py --load
python pinecone-aws-load.py --query "Find references to hard-to-find IDs"
```

Strict isolated variant:
```bash
cp aws/.env.example aws/.env
python aws/pinecone-aws-load.py --load
python aws/pinecone-aws-load.py --query "Find travel videos and related notes"
```

### Direct Core Invocation
```bash
python pinecone-multimodal-pipeline.py --provider aws_nova --load
python pinecone-multimodal-pipeline.py --provider vertex --query "..."
```

## Data Folders
- `data/txt`
- `data/image`
- `data/video`
- `data/audio`

## Random Test Data Download
When network is available:
```bash
./scripts/download_test_data.sh
```

## Provider Notes
- OpenAI+CLIP uses two Pinecone indexes (`PINECONE_TEXT_INDEX`, `PINECONE_MEDIA_INDEX`) because text and CLIP vectors have different dimensions.
  - Strict mode is enforced for separated pipelines: `PINECONE_INDEX_OPENAI_TEXT_3072` and `PINECONE_INDEX_OPENAI_CLIP_512` must be distinct.
- Vertex mode uses one unified index (`PINECONE_INDEX`) for text/image/video embeddings; audio is transcribed then embedded as text.
  - Vertex requests now try multiple payload shapes automatically to avoid common `400 Bad Request` schema mismatches.
- AWS Nova mode uses one unified index (`PINECONE_INDEX`) with native multimodal embedding payloads.

## Scale-Safe Index Routing
- Use dedicated indexes per embedding family to avoid dimension mismatches:
  - `PINECONE_INDEX_VERTEX_1408`
  - `PINECONE_INDEX_OPENAI_TEXT_3072`
  - `PINECONE_INDEX_OPENAI_CLIP_512`
  - `PINECONE_INDEX_AWS_NOVA_1024`
- Namespaces are used for partitioning (`PINECONE_NAMESPACE` in scripts, `user_id` namespace in backend APIs).
- Pipeline now performs pre-upsert dimension validation and fails fast with a clear error before Pinecone rejects writes.
- Optional host-based clients are supported per index (recommended by Pinecone for faster connect):
  - `PINECONE_INDEX_HOST_OPENAI_TEXT_3072`
  - `PINECONE_INDEX_HOST_OPENAI_CLIP_512`
  - `PINECONE_INDEX_HOST_VERTEX_1408`
  - `PINECONE_INDEX_HOST_AWS_NOVA_1024`
  - `PINECONE_INDEX_HOST_LEGACY_TEXT`
  - `PINECONE_INDEX_HOST_LEGACY_MEDIA`

## Unit Tests
```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Search Memory Backend (JWT + User Isolation)
Run API:
```bash
./scripts/run_backend.sh
```

Alternative:
```bash
PYTHONPATH=$(pwd) uvicorn backend.main:app --reload --app-dir $(pwd) --port 8000
```

Auth:
- Bearer JWT required on `/v1/memories/*`.
- `sub` claim is the canonical `user_id`.
- Pinecone namespace is always `user_id`.

Flutter integration (backend-first):
- Set `BACKEND_API_BASE_URL` and `BACKEND_AUTH_TOKEN` in `app/.env`.
- App chat uses `/v1/memories/chat` and renders backend citations.

Key APIs:
- `POST /v1/memories/upload-url`
- `POST /v1/memories/ingest`
- `POST /v1/memories/search`
- `POST /v1/memories/chat`
- `GET /v1/memories/timeline`
- `POST /v1/memories/promote`
- `DELETE /v1/memories/{memory_id}`
