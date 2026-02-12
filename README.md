# Flutter RAG Demo v2

A Retrieval-Augmented Generation demo with:
- Flutter frontend (modern blue/white UI)
- Pinecone vector search
- Google Vertex AI `multimodalembedding@001` for embeddings
- Gemini (`gemini-2.5-flash` by default) for final responses

## Project Layout
- `pinecone-db.py`: v2 load/query CLI for indexing and retrieval.
- `txts/`: text files used for indexing.
- `flutter_frontend/`: Flutter client.
- `.env.example`: complete v2 environment template.

## 1) Setup
```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp .env flutter_frontend/.env
```

## 2) Configure Environment
Update `.env` values:
- `PINECONE_API_KEY`, `PINECONE_INDEX`, `PINECONE_BASE_URL`
- `GOOGLE_API_KEY`, `GEMINI_MODEL`
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
- `GOOGLE_VERTEX_MODEL=multimodalembedding@001`
- `GOOGLE_VERTEX_EMBEDDING_DIMENSION=1408`
- Auth for Vertex:
  - preferred: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json`
  - demo fallback: `GOOGLE_VERTEX_ACCESS_TOKEN=$(gcloud auth print-access-token)`

## 3) Index Data
```bash
python pinecone-db.py --load
```

## 4) Query from CLI
```bash
python pinecone-db.py --query "What is AI?"
```

## 5) Run Flutter Frontend
```bash
cd flutter_frontend
flutter pub get
flutter run
```

## Notes
- Flutter embedding requests use `GOOGLE_VERTEX_ACCESS_TOKEN` (short-lived token). Refresh when it expires.
- Keep API keys and tokens out of git.
