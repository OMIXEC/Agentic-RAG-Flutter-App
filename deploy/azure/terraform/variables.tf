variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "app_name" {
  description = "Application name prefix"
  type        = string
  default     = "rag-backend"
}

variable "cpu" {
  description = "CPU cores for container"
  type        = number
  default     = 0.25
}

variable "memory" {
  description = "Memory for container (e.g. 0.5Gi)"
  type        = string
  default     = "0.5Gi"
}

variable "min_replicas" {
  description = "Minimum container replicas"
  type        = number
  default     = 0
}

variable "max_replicas" {
  description = "Maximum container replicas"
  type        = number
  default     = 3
}

variable "env_vars" {
  description = "Non-secret environment variables"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secret values for Key Vault"
  type        = map(string)
  default     = {}
  sensitive   = true
}
