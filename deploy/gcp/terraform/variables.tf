variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run"
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "Application name prefix"
  type        = string
  default     = "rag-backend"
}

variable "min_instances" {
  description = "Minimum Cloud Run instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum Cloud Run instances"
  type        = number
  default     = 3
}

variable "cpu" {
  description = "CPU limit per instance"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory limit per instance"
  type        = string
  default     = "512Mi"
}

variable "allow_public_access" {
  description = "Allow unauthenticated access to Cloud Run"
  type        = bool
  default     = false
}

variable "env_vars" {
  description = "Non-secret environment variables"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secret values to store in Secret Manager and inject as env vars"
  type        = map(string)
  default     = {}
  sensitive   = true
}
