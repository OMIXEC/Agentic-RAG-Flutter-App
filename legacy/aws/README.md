# AWS Nova Separated Pipeline

```bash
cp aws/.env.example aws/.env
python aws/pinecone-aws-load.py --load
python aws/pinecone-aws-load.py --query "Find travel videos and related notes"
```

Uses only `PINECONE_INDEX_AWS_NOVA_1024` and AWS folder paths.
