# OpenAI + Pinecone RAG

Self-contained multimodal RAG pipeline using **OpenAI text embeddings** + **CLIP image/video embeddings** with **Pinecone** vector database.

## Supported Input Types

- **Text**: `.txt .md .csv .json .yaml .yml .xml`
- **Documents**: `.pdf .docx`
- **Images**: `.png .jpg .jpeg .webp .bmp` (via CLIP)
- **Videos**: `.mp4 .mov .mkv .webm .avi` (via CLIP frame sampling)
- **Audio**: `.mp3 .wav .m4a` (via OpenAI transcription → text embedding)

## Pinecone Index Requirements

Two separate indexes are needed (different embedding dimensions):

- **Text index**: `3072` dimensions (text-embedding-3-large)
- **Media index**: `512` dimensions (CLIP ViT-B/32) — or matching your CLIP model

## Quick Start

```bash
# 1. Install dependencies
pip install -e ../../core/          # Install shared core library
pip install -r requirements.txt     # Install OpenAI-specific deps

# 2. Configure
cp .env.example .env
# Edit .env with your API keys and Pinecone index names

# 3. Add data to data/ folders
mkdir -p data/{txt,image,video,audio}

# 4. Ingest
python main.py --ingest --namespace my-project

# 5. Query
python main.py --query "Find documents about AI" --namespace my-project
```

## Standalone Usage

This directory can be copied to any location and used independently.
Just ensure the `core/` library is installed (`pip install -e path/to/core/`).
