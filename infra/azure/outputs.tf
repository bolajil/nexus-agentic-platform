output "cluster_name" {
  value = azurerm_kubernetes_cluster.nexus.name
}

output "kubeconfig_command" {
  value = "az aks get-credentials --resource-group ${azurerm_resource_group.nexus.name} --name ${azurerm_kubernetes_cluster.nexus.name}"
}

output "acr_login_server" {
  value = azurerm_container_registry.nexus.login_server
}

output "redis_hostname" {
  value     = azurerm_redis_cache.nexus.hostname
  sensitive = true
}

output "storage_account_name" {
  value = azurerm_storage_account.nexus.name
}

output "appgw_public_ip" {
  value = azurerm_public_ip.appgw.ip_address
}

output "dns_nameservers" {
  value       = azurerm_dns_zone.nexus.name_servers
  description = "Update your domain registrar to point to these Azure nameservers"
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.nexus.workspace_id
}
