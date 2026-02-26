# GCP Cloud Run Deployment

Deploy the RAG backend to Google Cloud Run with Secret Manager.

## Quick Start

```bash
# 1. Build and push Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/rag-backend ../..

# 2. Initialize Terraform
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# 3. Deploy
terraform init
terraform plan
terraform apply
```

## What Gets Created

- **Cloud Run** service (auto-scaling, HTTPS)
- **Secret Manager** secrets for API keys
- **Artifact Registry** repository for Docker images
- **IAM** service account with least-privilege access
