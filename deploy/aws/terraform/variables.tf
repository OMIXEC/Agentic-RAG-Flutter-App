variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application name prefix"
  type        = string
  default     = "rag-backend"
}

variable "cpu" {
  description = "Fargate task CPU (in CPU units)"
  type        = string
  default     = "256"
}

variable "memory" {
  description = "Fargate task memory (in MiB)"
  type        = string
  default     = "512"
}

variable "desired_count" {
  description = "Number of ECS tasks"
  type        = number
  default     = 1
}

variable "env_vars" {
  description = "Non-secret environment variables"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secret values for AWS Secrets Manager"
  type        = map(string)
  default     = {}
  sensitive   = true
}
