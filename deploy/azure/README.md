# Azure Container Apps Deployment

Deploy the RAG backend to Azure Container Apps with Key Vault.

## Quick Start

```bash
# 1. Build and push Docker image
az acr login --name YOUR_ACR
docker build -t YOUR_ACR.azurecr.io/backend:latest ../..
docker push YOUR_ACR.azurecr.io/backend:latest

# 2. Initialize Terraform
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars

# 3. Deploy
terraform init && terraform apply
```

## What Gets Created

- **Container App** with auto-scaling (0→3 replicas)
- **Key Vault** for secrets
- **Container Registry** for Docker images
- **Log Analytics** workspace for monitoring
