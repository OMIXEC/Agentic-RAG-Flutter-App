# Developer Guide: Multimodal RAG with Vertex AI & Pinecone

This guide provides step-by-step instructions for developers to implement and extend the multimodal RAG (Retrieval-Augmented Generation) pipeline using Google Vertex AI and Pinecone.

## 🚀 Overview

The system uses **Vertex AI Multimodal Embeddings** (`multimodalembedding@001`) to generate a unified 1408-dimensional vector space for text, images, and video. This allows you to query a single Pinecone index and retrieve relevant content regardless of its original modality.

---

## 🛠 Prerequisites

1.  **GCP Project**: A Google Cloud project with the **Vertex AI API** enabled.
2.  **Service Account**: A GCP service account with `Vertex AI User` and `Storage Object Viewer` roles. Download the JSON key file.
3.  **Pinecone Index**: A serverless or pod-based index with **1408 dimensions** and **Cosine similarity**.
4.  **Python 3.10+**: Ensure you have Python installed locally.

---

## ⚙️ Configuration (.env)

Create a `.env` file in the `use-cases/vertexai-pinecone/` directory.

```bash
# Pinecone Settings
PINECONE_API_KEY="your-api-key"
# You can use the Index Name OR the Full Host URL
PINECONE_INDEX_VERTEX_1408="vertexai-index-demo"
PINECONE_NAMESPACE="default"

# GCP Settings
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"
GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"

# (Optional) GCS bucket for large video uploads
VERTEX_VIDEO_GCS_BUCKET="your-bucket-name"
```

---

## 📥 Ingestion Flow

The ingestion process supports both **local files** and **GCP Storage (GCS)**.

### 1. Local Storage

By default, the script scans a local `data/` folder structured as follows:

- `data/txt/`: `.txt`, `.pdf`, `.docx`
- `data/image/`: `.jpg`, `.png`, `.webp`
- `data/video/`: `.mp4`, `.avi`, `.mov`
- `data/audio/`: `.mp3`, `.wav`

**Run Ingestion:**

```bash
python3 main.py --ingest --data-dir data --namespace app-data
```

### 2. GCP Storage (Video)

For high-quality video ingestion, the pipeline can upload files to GCS and provide the `gs://` URI to Vertex AI. This is more reliable than local frame sampling for large files.

- Ensure `VERTEX_VIDEO_GCS_BUCKET` is set in your `.env`.

---

## 🖼 Multimodal Handling

### Text

Text is split into chunks (e.g., 1000 characters) and embedded directly.

### Images

Images are encoded to Base64 and sent to the Vertex AI embedding model.

### Video

- **Primary Path**: Upload to GCS -> Vertex AI retrieves features from the video stream.
- **Fallback**: The pipeline uses **OpenCV** to sample 4 keyframes from the video, embeds each as an image, and calculates the **mean vector**.

### Audio (Immersive interpretation)

The pipeline uses **Vertex AI Gemini 2.5 Flash** (2026-ready) to interpret raw audio and generate a rich, dense semantic description of the "reality" within the audio (soundscapes, voices, animal sounds, etc.).

- This description is then embedded into the unified 1408d space using the multimodal embedding model.
- See `GOOGLE_VERTEX_GEMINI_MODEL` in your configuration.

---

## 🔍 Retrieval (Querying)

Queries are processed as text embeddings in the same 1408d space. Pinecone returns the top-K matches based on cosine similarity, which could be a mix of text, images, and video frames.

**Run Query:**

```bash
python3 main.py --query "Show me travel memories" --top-k 5
```

---

## 💡 Developer Tips

### 1. Type Compatibility

**Important**: Pinecone requires vectors to be standard Python `float` types. The current implementation automatically converts `numpy.float64` (common in video processing) to standard floats to avoid API errors.

### 2. Host URLs

You can provide either the Pinecone **Index Name** (e.g., `my-index`) or the **Host URL** (e.g., `https://my-index...pinecone.io`). The `pinecone_client.py` is configured to handle both.

### 3. Application Integration

- **Flutter**: Use the `pinecone` and `google_cloud_auth` packages or call the Python backend via FastAPI.
- **Web**: Integrate using the official Pinecone and Google Cloud SDKs for Node.js or Python.

---

## 🐛 Troubleshooting

- **401 Unauthorized**: Check your `GOOGLE_APPLICATION_CREDENTIALS` path or ensure your access token hasn't expired.
- **404 Not Found**: Ensure your Pinecone index name or host URL is correct and matches the region.
- **Dimension Mismatch**: Verify the index is exactly **1408 dimensions**.
