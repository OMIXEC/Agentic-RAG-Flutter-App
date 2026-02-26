# Vertex AI + Pinecone RAG

**Production-ready multimodal RAG pipeline.** This project implements a unified vector space for text, images, video, and audio using **Google Vertex AI** embeddings and **Pinecone**.

> [!TIP]
> **Complete Developer Guide**: For detailed step-by-step setup, configuration, and integration guidance, see the [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md).

## ✨ Key Features

- **Unified Vertex AI Embedding**: Single 1408-dimensional space for text, images, and video.
- **Audio Clues (2026 Ready)**: Immersive interpretation of soundscapes and reality using **Gemini 2.5 Flash**.
- **Pinecone Native**: Optimized for high-throughput multimodal vector search.
- **Production Fixes**: Includes fixes for Pinecone 5.x, host URLs, and specific NumPy type incompatibilities.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env  # Edit with your keys

# 3. Running
python main.py --ingest --data-dir data --namespace my-namespace
python main.py --query "Find memories about travel" --namespace my-project
```

For advanced usage and cloud deployment patterns, refer to the [Developer Guide](./DEVELOPER_GUIDE.md).
