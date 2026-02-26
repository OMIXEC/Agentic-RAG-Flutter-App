# Agentic RAG Flutter App (SynapseMemo)

A production-grade, multimodal RAG (Retrieval-Augmented Generation) application designed for the "User Life Memory" use case. This repository implements a high-performance vector search backend across multiple cloud providers and a full-featured Flutter mobile companion.

## 🚀 Key Features

- **Multimodal Search**: Native support for Text, Images, Video, and Immersive Audio.
- **Multi-Cloud Integration**: Seamlessly switch between GCP Vertex AI, AWS Bedrock, and OpenAI/Azure.
- **Immersive Audio Interpretation**: Uses Gemini 2.5 Flash (2026-ready) to interpret raw audio and soundscapes for semantic retrieval.
- **Unified Embedding Space**: Optimized 1024-3072 dimensional vector space with cross-modal retrieval.
- **Clean Architecture**: Decoupled core logic from provider-specific implementations.

## 📂 Project Structure

### [Core Framework](./core/)

The central `pinecone_rag` library containing shared logic for:

- Vector state management and Pinecone indexing.
- Multimodal file processing and chunking.
- Unified provider interfaces for Vertex, Bedrock, and OpenAI.

### [Use Cases](./use-cases/)

Production artifacts and scripts for specific deployment patterns:

- **[Vertex AI + Pinecone](./use-cases/vertexai-pinecone/)**: Multimodal model embedding via GCP with Gemini 2.5 immersive audio and audio, video, image, text support.
- **[OpenAI + Pinecone](./use-cases/openai-pinecone/)**: Standard OpenAI embedding pipeline.
- **[AWS Bedrock + Pinecone](./use-cases/aws-bedrock-pinecone/)**: Native AWS implementation with Nova models (support txt and/or multimodal Nova model).
- **[Azure OpenAI + Pinecone](./use-cases/azure-openai-pinecone/)**: Enterprise-grade Azure OpenAI integration.
- **[OpenAI + Chainlit](./use-cases/openai-chainlit/)**: A verified web-based UI for multimodal RAG using Chainlit.

### [Flutter Mobile App](./app/)

A premium Flutter application for life memory capture and retrieval.

## 🛠️ Getting Started

1. **Environment Setup**:

   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   ```

2. **Ingest Data (Vertex Example)**:

   ```bash
   cd use-cases/vertexai-pinecone
   python3 main.py --ingest --data-dir data --namespace my-memory
   ```

3. **Query Data**:
   ```bash
   python3 main.py --query "Find memories about my trip to the mountains" --namespace my-memory
   ```

## 🛡️ Best Practices

- **Isolation**: Each use case is self-contained with its own `README.md` and configuration.
- **Security**: Environment files (`.env`) are recursively excluded from Git.
- **Robustness**: Integrated file existence checks and graceful error handling for multimodal streams.

## 📜 Documentation

- [Developer Guide (Vertex)](./use-cases/vertexai-pinecone/DEVELOPER_GUIDE.md)
- [Deployment Plans](./docs/plans/)
