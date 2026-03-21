output "cluster_name" {
  value = google_container_cluster.nexus.name
}

output "kubeconfig_command" {
  value = "gcloud container clusters get-credentials ${google_container_cluster.nexus.name} --region ${var.region} --project ${var.project_id}"
}

output "artifact_registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.project_name}"
}

output "redis_host" {
  value     = google_redis_instance.nexus.host
  sensitive = true
}

output "gcs_bucket_name" {
  value = google_storage_bucket.nexus.name
}

output "dns_name_servers" {
  value       = google_dns_managed_zone.nexus.name_servers
  description = "Update your domain registrar to point to these nameservers"
}
