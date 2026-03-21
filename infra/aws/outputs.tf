output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "kubeconfig_command" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "ecr_backend_url" {
  description = "ECR URL for backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "ECR URL for frontend image"
  value       = aws_ecr_repository.frontend.repository_url
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.nexus.primary_endpoint_address
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 storage bucket name"
  value       = aws_s3_bucket.nexus_storage.bucket
}

output "route53_nameservers" {
  description = "Route 53 nameservers — update your domain registrar to use these"
  value       = aws_route53_zone.nexus.name_servers
}

output "efs_file_system_id" {
  description = "EFS file system ID for CAD output (RWX)"
  value       = aws_efs_file_system.cad.id
}

output "waf_web_acl_arn" {
  description = "WAF Web ACL ARN — attach to ALB"
  value       = aws_wafv2_web_acl.nexus.arn
}
