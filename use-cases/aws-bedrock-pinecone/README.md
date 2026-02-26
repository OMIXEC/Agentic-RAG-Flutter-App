# AWS Bedrock Nova + Pinecone RAG

Self-contained multimodal RAG pipeline using **AWS Bedrock Nova** (`amazon.nova-2-multimodal-embeddings-v1`) with **Pinecone**.

## Unified Embedding Space

Nova provides a **single unified embedding** for all modalities — text, image, video, and audio share the same Pinecone index (1024d default).

## Quick Start

```bash
pip install -e ../../core/ && pip install -r requirements.txt
cp .env.example .env  # Edit with your Pinecone key
aws configure         # Ensure AWS credentials are set
python main.py --ingest --namespace my-project
python main.py --query "Find documents about AI" --namespace my-project
```
