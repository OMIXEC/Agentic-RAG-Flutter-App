# Azure OpenAI + Pinecone RAG

Self-contained RAG pipeline using **Azure OpenAI** text embeddings with **Pinecone**.

## Text-Only Embeddings

Azure OpenAI provides text embeddings only. Images and videos are indexed via their text descriptions from `media_manifest.txt`.

## Quick Start

```bash
pip install -e ../../core/ && pip install -r requirements.txt
cp .env.example .env  # Edit with Azure & Pinecone keys
python main.py --ingest --namespace my-project
python main.py --query "Find documents about AI" --namespace my-project
```

## Pinecone Index

Single index with **1536 dimensions** (text-embedding-ada-002) or **3072d** (text-embedding-3-large).
