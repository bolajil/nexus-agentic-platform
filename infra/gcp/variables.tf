variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "project_name" {
  description = "Resource name prefix"
  type        = string
  default     = "nexus"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "nexus-production"
}

variable "domain_name" {
  description = "Primary domain name"
  type        = string
  default     = "nexus.yourdomain.com"
}

variable "allowed_cidr_blocks" {
  description = "CIDRs allowed to access GKE master endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "notification_channels" {
  description = "Cloud Monitoring notification channel IDs for alerts"
  type        = list(string)
  default     = []
}

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
