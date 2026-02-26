# GCP Vertex Separated Pipeline

```bash
cp gcp/.env.example gcp/.env
python gcp/pinecone-vertex-load.py --load
python gcp/pinecone-vertex-load.py --query "Summarize my latest memories"
```

Uses only `PINECONE_INDEX_VERTEX_1408` and Vertex folder paths.
