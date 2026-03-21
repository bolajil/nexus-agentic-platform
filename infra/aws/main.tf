terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
  }

  # Remote state — S3 + DynamoDB locking
  backend "s3" {
    bucket         = "nexus-terraform-state"   # create this bucket first
    key            = "nexus/production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "nexus-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "nexus-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── Data Sources ────────────────────────────────────────────────────────────────
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# ── VPC ─────────────────────────────────────────────────────────────────────────
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.5"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = [for i in range(3) : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets  = [for i in range(3) : cidrsubnet(var.vpc_cidr, 4, i + 4)]
  intra_subnets   = [for i in range(3) : cidrsubnet(var.vpc_cidr, 4, i + 8)]  # EKS control plane

  enable_nat_gateway     = true
  single_nat_gateway     = false           # one NAT per AZ for HA
  one_nat_gateway_per_az = true
  enable_dns_hostnames   = true
  enable_dns_support     = true

  # Required tags for EKS
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"             = 1
    "kubernetes.io/cluster/${var.cluster_name}"   = "shared"
  }
  public_subnet_tags = {
    "kubernetes.io/role/elb"                      = 1
    "kubernetes.io/cluster/${var.cluster_name}"   = "shared"
  }
}

# ── EKS Cluster ──────────────────────────────────────────────────────────────────
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.8"

  cluster_name    = var.cluster_name
  cluster_version = "1.29"

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true
  # Restrict public endpoint to your CI/CD IP ranges
  cluster_endpoint_public_access_cidrs = var.allowed_cidr_blocks

  cluster_addons = {
    coredns                = { most_recent = true }
    kube-proxy             = { most_recent = true }
    vpc-cni                = { most_recent = true }
    aws-ebs-csi-driver     = { most_recent = true }
    aws-efs-csi-driver     = { most_recent = true }  # RWX volumes for CAD output
  }

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.intra_subnets

  # KMS encryption for secrets at rest
  cluster_encryption_config = {
    resources        = ["secrets"]
    provider_key_arn = aws_kms_key.eks.arn
  }

  # Managed node groups
  eks_managed_node_groups = {
    # On-demand nodes — always-on baseline capacity
    system = {
      name           = "nexus-system"
      instance_types = ["m6i.xlarge"]
      min_size       = 2
      max_size       = 4
      desired_size   = 3
      labels = {
        role = "system"
      }
      taints = []
    }

    # Spot nodes — cost-optimised burst capacity for pipeline workloads
    pipeline = {
      name           = "nexus-pipeline-spot"
      instance_types = ["m6i.2xlarge", "m5.2xlarge", "m5d.2xlarge"]
      capacity_type  = "SPOT"
      min_size       = 0
      max_size       = 20
      desired_size   = 2
      labels = {
        role = "pipeline"
      }
    }
  }

  # Enable IRSA
  enable_irsa = true
}

# ── KMS Key for EKS Secrets ──────────────────────────────────────────────────────
resource "aws_kms_key" "eks" {
  description             = "EKS secret encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${var.project_name}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

# ── ElastiCache Redis (HA, Multi-AZ) ────────────────────────────────────────────
resource "aws_elasticache_subnet_group" "nexus" {
  name       = "${var.project_name}-redis-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
}

resource "aws_elasticache_replication_group" "nexus" {
  replication_group_id = "${var.project_name}-redis"
  description          = "NEXUS session + BM25 cache"
  node_type            = "cache.r7g.medium"
  port                 = 6379
  num_cache_clusters   = 2               # primary + 1 replica per AZ
  automatic_failover_enabled = true
  multi_az_enabled           = true
  subnet_group_name          = aws_elasticache_subnet_group.nexus.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token
  engine_version             = "7.1"
  parameter_group_name       = "default.redis7"
  snapshot_retention_limit   = 7
  snapshot_window            = "03:00-04:00"
  maintenance_window         = "sun:05:00-sun:06:00"
}

# ── S3 — CAD output + backups ────────────────────────────────────────────────────
resource "aws_s3_bucket" "nexus_storage" {
  bucket        = "${var.project_name}-storage-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "nexus_storage" {
  bucket = aws_s3_bucket.nexus_storage.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "nexus_storage" {
  bucket = aws_s3_bucket.nexus_storage.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.eks.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "nexus_storage" {
  bucket                  = aws_s3_bucket.nexus_storage.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "nexus_storage" {
  bucket = aws_s3_bucket.nexus_storage.id
  rule {
    id     = "cad-expiry"
    status = "Enabled"
    filter { prefix = "cad_output/" }
    expiration { days = 30 }
    transition {
      days          = 7
      storage_class = "INTELLIGENT_TIERING"
    }
  }
}

# ── ECR Repositories ─────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}/backend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "KMS" }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}/frontend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "KMS" }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 20 images"
      selection     = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 20 }
      action        = { type = "expire" }
    }]
  })
}

# ── Route 53 + ACM ───────────────────────────────────────────────────────────────
resource "aws_route53_zone" "nexus" {
  name = var.domain_name
}

resource "aws_acm_certificate" "nexus" {
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"
  lifecycle { create_before_destroy = true }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.nexus.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }
  zone_id         = aws_route53_zone.nexus.zone_id
  name            = each.value.name
  records         = [each.value.record]
  type            = each.value.type
  ttl             = 60
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "nexus" {
  certificate_arn         = aws_acm_certificate.nexus.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

# ── AWS Secrets Manager ──────────────────────────────────────────────────────────
resource "aws_secretsmanager_secret" "nexus" {
  name                    = "${var.project_name}/production"
  description             = "NEXUS platform secrets"
  kms_key_id              = aws_kms_key.eks.arn
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "nexus" {
  secret_id = aws_secretsmanager_secret.nexus.id
  secret_string = jsonencode({
    OPENAI_API_KEY      = var.openai_api_key
    LANGFUSE_PUBLIC_KEY = var.langfuse_public_key
    LANGFUSE_SECRET_KEY = var.langfuse_secret_key
    REDIS_AUTH_TOKEN    = var.redis_auth_token
  })
}

# ── CloudWatch Container Insights ────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "nexus" {
  name              = "/aws/eks/${var.cluster_name}/nexus"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "eks_control_plane" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = 90
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "nexus" {
  dashboard_name = "${var.project_name}-production"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6,
        properties = {
          title  = "EKS Pod CPU"
          period = 60
          metrics = [["ContainerInsights", "pod_cpu_utilization", "ClusterName", var.cluster_name, "Namespace", "nexus"]]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6,
        properties = {
          title  = "EKS Pod Memory"
          period = 60
          metrics = [["ContainerInsights", "pod_memory_utilization", "ClusterName", var.cluster_name, "Namespace", "nexus"]]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6,
        properties = {
          title   = "ElastiCache Redis Connections"
          metrics = [["AWS/ElastiCache", "CurrConnections", "ReplicationGroupId", "${var.project_name}-redis"]]
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.project_name}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "EngineCPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 120
  statistic           = "Average"
  threshold           = 75
  alarm_description   = "Redis CPU > 75%"
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.nexus.id
  }
}

# ── WAF for Application Load Balancer ────────────────────────────────────────────
resource "aws_wafv2_web_acl" "nexus" {
  name  = "${var.project_name}-waf"
  scope = "REGIONAL"

  default_action { allow {} }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1
    override_action { none {} }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "RateLimit"
    priority = 2
    action { block {} }
    statement {
      rate_based_statement {
        limit              = 2000   # req per 5 min per IP
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "NexusRateLimitMetric"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "NexusWAFMetric"
    sampled_requests_enabled   = true
  }
}

# ── EFS for RWX CAD output storage ───────────────────────────────────────────────
resource "aws_efs_file_system" "cad" {
  creation_token   = "${var.project_name}-cad-efs"
  encrypted        = true
  kms_key_id       = aws_kms_key.eks.arn
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"
  lifecycle_policy {
    transition_to_ia = "AFTER_7_DAYS"
  }
}

resource "aws_efs_mount_target" "cad" {
  for_each        = toset(module.vpc.private_subnets)
  file_system_id  = aws_efs_file_system.cad.id
  subnet_id       = each.value
  security_groups = [module.eks.node_security_group_id]
}
