# AWS ECS Fargate Deployment

Deploy the RAG backend to AWS ECS Fargate with Secrets Manager.

## Quick Start

```bash
# 1. Build and push Docker image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker build -t rag-backend ../..
docker tag rag-backend:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/rag-backend:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/rag-backend:latest

# 2. Initialize Terraform
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars

# 3. Deploy
terraform init && terraform apply
```

## What Gets Created

- **ECS Cluster** + **Fargate Service** (serverless containers)
- **ECR** repository for Docker images
- **Secrets Manager** for API keys
- **IAM** roles with Bedrock invoke access for Nova embeddings
- **CloudWatch** logs
