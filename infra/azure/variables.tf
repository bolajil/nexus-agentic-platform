variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "project_name" {
  description = "Resource name prefix"
  type        = string
  default     = "nexus"
}

variable "cluster_name" {
  description = "AKS cluster name"
  type        = string
  default     = "nexus-production"
}

variable "domain_name" {
  description = "Primary domain name"
  type        = string
  default     = "nexus.yourdomain.com"
}

variable "allowed_ip_ranges" {
  description = "IP ranges allowed to access AKS API server"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "alert_email" {
  description = "Email address for Azure Monitor alerts"
  type        = string
  default     = "devops@yourdomain.com"
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "langfuse_public_key" {
  type      = string
  sensitive = true
}

variable "langfuse_secret_key" {
  type      = string
  sensitive = true
}
