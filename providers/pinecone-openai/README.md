# pinecone-openai

OpenAI provider pipeline (text + media) for this RAG app.

## 1) Create Pinecone indexes

Create two serverless indexes:
- Text index (cosine, dimension `3072`): `PINECONE_INDEX_OPENAI_TEXT_3072`
- Media index (cosine, dimension `512`): `PINECONE_INDEX_OPENAI_CLIP_512`

Do not reuse the same index for both dimensions.

## 2) Configure env

```bash
cp providers/pinecone-openai/.env.example providers/pinecone-openai/.env
```

Required keys:
- `PINECONE_API_KEY`
- `OPENAI_API_KEY`
- `PINECONE_INDEX_OPENAI_TEXT_3072`
- `PINECONE_INDEX_OPENAI_CLIP_512`

## 3) Ingest data

```bash
python providers/pinecone-openai/entry_ingest.py --namespace global
```

## 4) Query data

```bash
python providers/pinecone-openai/entry_query.py --namespace global --query "Summarize latest worldwide news"
```

## 5) Backend integration

Set backend env:
- `MULTIMODAL_PROVIDER=openai_clip`
- Use `/v1/memories/*` (unified) or `/v1/providers/openai/*` (provider-explicit).
