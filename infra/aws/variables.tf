variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project identifier — used as prefix for all resources"
  type        = string
  default     = "nexus"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "nexus-production"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "domain_name" {
  description = "Primary domain name (Route 53 hosted zone)"
  type        = string
  default     = "nexus.yourdomain.com"
}

variable "allowed_cidr_blocks" {
  description = "CIDRs allowed to reach the EKS public endpoint (CI/CD, VPN)"
  type        = list(string)
  default     = ["0.0.0.0/0"]   # restrict to your office/VPN IPs in production
}

# ── Secrets (pass via TF_VAR_ env vars — never hard-code) ────────────────────────
variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "langfuse_public_key" {
  description = "Langfuse public key"
  type        = string
  sensitive   = true
}

variable "langfuse_secret_key" {
  description = "Langfuse secret key"
  type        = string
  sensitive   = true
}

variable "redis_auth_token" {
  description = "Redis AUTH token for ElastiCache (min 16 chars)"
  type        = string
  sensitive   = true
}
