terraform {
  required_version = ">= 1.7.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.20"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.20"
    }
  }

  backend "gcs" {
    bucket = "nexus-terraform-state-gcp"   # create first: gsutil mb gs://nexus-terraform-state-gcp
    prefix = "nexus/production"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ── Enable Required APIs ──────────────────────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "container.googleapis.com",       # GKE
    "redis.googleapis.com",           # Memorystore
    "storage.googleapis.com",         # GCS
    "artifactregistry.googleapis.com",# Artifact Registry
    "dns.googleapis.com",             # Cloud DNS
    "secretmanager.googleapis.com",   # Secret Manager
    "monitoring.googleapis.com",      # Cloud Monitoring
    "logging.googleapis.com",         # Cloud Logging
    "cloudtrace.googleapis.com",      # Cloud Trace (OTLP)
    "certificatemanager.googleapis.com",
    "compute.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# ── VPC ──────────────────────────────────────────────────────────────────────────
resource "google_compute_network" "nexus" {
  name                    = "${var.project_name}-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "gke" {
  name          = "${var.project_name}-gke-subnet"
  network       = google_compute_network.nexus.id
  region        = var.region
  ip_cidr_range = "10.0.0.0/20"

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.16.0.0/14"
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.20.0.0/20"
  }

  private_ip_google_access = true
}

resource "google_compute_router" "nexus" {
  name    = "${var.project_name}-router"
  network = google_compute_network.nexus.id
  region  = var.region
}

resource "google_compute_router_nat" "nexus" {
  name                               = "${var.project_name}-nat"
  router                             = google_compute_router.nexus.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# ── GKE Autopilot Cluster ─────────────────────────────────────────────────────────
resource "google_container_cluster" "nexus" {
  provider         = google-beta
  name             = var.cluster_name
  location         = var.region
  enable_autopilot = true             # fully managed nodes, automatic scaling

  network    = google_compute_network.nexus.id
  subnetwork = google_compute_subnetwork.gke.id

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  master_authorized_networks_config {
    dynamic "cidr_blocks" {
      for_each = var.allowed_cidr_blocks
      content {
        cidr_block   = cidr_blocks.value
        display_name = "authorized"
      }
    }
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  release_channel {
    channel = "REGULAR"
  }

  cluster_autoscaling {
    auto_provisioning_defaults {
      management {
        auto_repair  = true
        auto_upgrade = true
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# ── Memorystore Redis ─────────────────────────────────────────────────────────────
resource "google_redis_instance" "nexus" {
  name               = "${var.project_name}-redis"
  tier               = "STANDARD_HA"        # HA with automatic failover
  memory_size_gb     = 2
  region             = var.region
  redis_version      = "REDIS_7_0"
  auth_enabled       = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"
  authorized_network = google_compute_network.nexus.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time { hours = 3; minutes = 0; seconds = 0; nanos = 0 }
    }
  }
  depends_on = [google_project_service.apis]
}

# ── GCS Storage Bucket ───────────────────────────────────────────────────────────
resource "google_storage_bucket" "nexus" {
  name          = "${var.project_name}-storage-${var.project_id}"
  location      = var.region
  force_destroy = false
  storage_class = "STANDARD"
  uniform_bucket_level_access = true

  versioning { enabled = true }

  encryption {
    default_kms_key_name = google_kms_crypto_key.nexus.id
  }

  lifecycle_rule {
    condition { age = 30; matches_prefix = ["cad_output/"] }
    action    { type = "Delete" }
  }

  lifecycle_rule {
    condition { age = 7; matches_prefix = ["cad_output/"] }
    action    { type = "SetStorageClass"; storage_class = "NEARLINE" }
  }
}

# ── KMS ───────────────────────────────────────────────────────────────────────────
resource "google_kms_key_ring" "nexus" {
  name     = "${var.project_name}-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "nexus" {
  name            = "${var.project_name}-key"
  key_ring        = google_kms_key_ring.nexus.id
  rotation_period = "7776000s"   # 90 days
}

# ── Artifact Registry ─────────────────────────────────────────────────────────────
resource "google_artifact_registry_repository" "nexus" {
  location      = var.region
  repository_id = var.project_name
  format        = "DOCKER"
  description   = "NEXUS platform container images"

  cleanup_policies {
    id     = "keep-last-20"
    action = "KEEP"
    most_recent_versions { keep_count = 20 }
  }

  depends_on = [google_project_service.apis]
}

# ── Cloud DNS ─────────────────────────────────────────────────────────────────────
resource "google_dns_managed_zone" "nexus" {
  name        = "${var.project_name}-zone"
  dns_name    = "${var.domain_name}."
  description = "NEXUS platform DNS zone"
  depends_on  = [google_project_service.apis]
}

# ── Secret Manager ────────────────────────────────────────────────────────────────
resource "google_secret_manager_secret" "openai_key" {
  secret_id = "${var.project_name}-openai-key"
  replication { auto {} }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "openai_key" {
  secret      = google_secret_manager_secret.openai_key.id
  secret_data = var.openai_api_key
}

resource "google_secret_manager_secret" "langfuse" {
  secret_id  = "${var.project_name}-langfuse"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "langfuse" {
  secret      = google_secret_manager_secret.langfuse.id
  secret_data = jsonencode({
    public_key = var.langfuse_public_key
    secret_key = var.langfuse_secret_key
  })
}

# ── Cloud Monitoring Alert Policies ──────────────────────────────────────────────
resource "google_monitoring_alert_policy" "backend_down" {
  display_name = "NEXUS Backend Down"
  combiner     = "OR"
  conditions {
    display_name = "GKE pod not running"
    condition_threshold {
      filter          = "metric.type=\"kubernetes.io/container/uptime\" resource.label.\"namespace_name\"=\"nexus\""
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      duration        = "60s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  notification_channels = var.notification_channels
}

resource "google_monitoring_uptime_check_config" "nexus" {
  display_name = "NEXUS Health Check"
  timeout      = "10s"
  period       = "60s"
  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }
  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = var.domain_name
    }
  }
}
