# pinecone-aws

AWS Bedrock Nova multimodal provider pipeline.

## 1) Create Pinecone index

Create one serverless index:
- Cosine metric
- Dimension `1024`
- Name: `PINECONE_INDEX_AWS_NOVA_1024`

## 2) Configure env

```bash
cp providers/pinecone-aws/.env.example providers/pinecone-aws/.env
```

Required keys:
- `PINECONE_API_KEY`
- `PINECONE_INDEX_AWS_NOVA_1024`
- AWS credentials with Bedrock access (`AWS_REGION` + auth)

## 3) Ingest data

```bash
python providers/pinecone-aws/entry_ingest.py --namespace global
```

## 4) Query data

```bash
python providers/pinecone-aws/entry_query.py --namespace global --query "Find key events in travel videos"
```

## 5) Backend integration

Set backend env:
- `MULTIMODAL_PROVIDER=aws_nova`
- Use `/v1/memories/*` or `/v1/providers/aws/*`.
