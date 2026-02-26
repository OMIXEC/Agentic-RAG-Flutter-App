# pinecone-gcp-vertex

Google Vertex multimodal provider pipeline.

## 1) Create Pinecone index

Create one serverless index:
- Cosine metric
- Dimension `1408`
- Name: `PINECONE_INDEX_VERTEX_1408`

## 2) Configure env

```bash
cp providers/pinecone-gcp-vertex/.env.example providers/pinecone-gcp-vertex/.env
```

Required keys:
- `PINECONE_API_KEY`
- `PINECONE_INDEX_VERTEX_1408`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_VERTEX_ACCESS_TOKEN`

## 3) Ingest data

```bash
python providers/pinecone-gcp-vertex/entry_ingest.py --namespace global
```

## 4) Query data

```bash
python providers/pinecone-gcp-vertex/entry_query.py --namespace global --query "Summarize recent global headlines"
```

## 5) Backend integration

Set backend env:
- `MULTIMODAL_PROVIDER=vertex`
- Use `/v1/memories/*` or `/v1/providers/vertex/*`.
