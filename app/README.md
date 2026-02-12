# Flutter Frontend (v2)

This app queries Pinecone with Google Vertex `multimodalembedding@001` vectors and renders responses from Gemini.

## Run
```bash
flutter pub get
flutter run
```

## Required `.env` keys
```env
PINECONE_API_KEY=
PINECONE_INDEX=
PINECONE_BASE_URL=
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_VERTEX_MODEL=multimodalembedding@001
GOOGLE_VERTEX_EMBEDDING_DIMENSION=1408
GOOGLE_VERTEX_ACCESS_TOKEN=
```

For local demos, generate token with:
```bash
gcloud auth print-access-token
```
