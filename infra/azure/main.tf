terraform {
  required_version = ">= 1.7.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
  }

  backend "azurerm" {
    resource_group_name  = "nexus-terraform-state-rg"  # create first
    storage_account_name = "nexustfstate"
    container_name       = "tfstate"
    key                  = "nexus/production/terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}

data "azurerm_client_config" "current" {}

# ── Resource Group ────────────────────────────────────────────────────────────────
resource "azurerm_resource_group" "nexus" {
  name     = "${var.project_name}-production-rg"
  location = var.location
  tags = {
    Project     = "nexus-platform"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# ── VNet ──────────────────────────────────────────────────────────────────────────
resource "azurerm_virtual_network" "nexus" {
  name                = "${var.project_name}-vnet"
  address_space       = ["10.0.0.0/8"]
  location            = azurerm_resource_group.nexus.location
  resource_group_name = azurerm_resource_group.nexus.name
}

resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.nexus.name
  virtual_network_name = azurerm_virtual_network.nexus.name
  address_prefixes     = ["10.240.0.0/16"]
}

resource "azurerm_subnet" "appgw" {
  name                 = "appgw-subnet"
  resource_group_name  = azurerm_resource_group.nexus.name
  virtual_network_name = azurerm_virtual_network.nexus.name
  address_prefixes     = ["10.241.0.0/24"]
}

resource "azurerm_subnet" "redis" {
  name                 = "redis-subnet"
  resource_group_name  = azurerm_resource_group.nexus.name
  virtual_network_name = azurerm_virtual_network.nexus.name
  address_prefixes     = ["10.242.0.0/24"]
}

# ── Key Vault ─────────────────────────────────────────────────────────────────────
resource "azurerm_key_vault" "nexus" {
  name                        = "${var.project_name}-kv-${substr(data.azurerm_client_config.current.tenant_id, 0, 8)}"
  location                    = azurerm_resource_group.nexus.location
  resource_group_name         = azurerm_resource_group.nexus.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  enabled_for_disk_encryption = true
  soft_delete_retention_days  = 7
  purge_protection_enabled    = true

  network_acls {
    bypass         = "AzureServices"
    default_action = "Deny"
    ip_rules       = var.allowed_ip_ranges
  }

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id
    secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
    key_permissions    = ["Get", "List", "Create", "Delete", "Rotate"]
  }
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.nexus.id
}

resource "azurerm_key_vault_secret" "langfuse_secret" {
  name         = "langfuse-secret-key"
  value        = var.langfuse_secret_key
  key_vault_id = azurerm_key_vault.nexus.id
}

resource "azurerm_key_vault_secret" "langfuse_public" {
  name         = "langfuse-public-key"
  value        = var.langfuse_public_key
  key_vault_id = azurerm_key_vault.nexus.id
}

# ── Azure Container Registry ──────────────────────────────────────────────────────
resource "azurerm_container_registry" "nexus" {
  name                = "${replace(var.project_name, "-", "")}acr"
  resource_group_name = azurerm_resource_group.nexus.name
  location            = azurerm_resource_group.nexus.location
  sku                 = "Premium"          # geo-replication + private link
  admin_enabled       = false

  network_rule_policy {
    default_action = "Deny"
    ip_rule {
      action   = "Allow"
      ip_range = "0.0.0.0/0"    # restrict to build agents in production
    }
  }
}

# ── AKS Cluster ───────────────────────────────────────────────────────────────────
resource "azurerm_kubernetes_cluster" "nexus" {
  name                = var.cluster_name
  location            = azurerm_resource_group.nexus.location
  resource_group_name = azurerm_resource_group.nexus.name
  dns_prefix          = var.project_name
  kubernetes_version  = "1.29"
  sku_tier            = "Standard"         # SLA-backed control plane

  default_node_pool {
    name                = "system"
    node_count          = 3
    vm_size             = "Standard_D4s_v5"
    os_disk_size_gb     = 128
    os_disk_type        = "Ephemeral"
    vnet_subnet_id      = azurerm_subnet.aks.id
    enable_auto_scaling = true
    min_count           = 2
    max_count           = 6
    type                = "VirtualMachineScaleSets"
    zones               = ["1", "2", "3"]   # spread across AZs
    node_labels = {
      role = "system"
    }
  }

  identity { type = "SystemAssigned" }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
    service_cidr      = "10.0.0.0/16"
    dns_service_ip    = "10.0.0.10"
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.nexus.id
  }

  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  azure_policy_enabled = true

  api_server_access_profile {
    authorized_ip_ranges = var.allowed_ip_ranges
  }

  auto_scaler_profile {
    balance_similar_node_groups  = true
    expander                     = "random"
    scale_down_delay_after_add   = "10m"
    scale_down_unneeded          = "5m"
  }
}

# Spot node pool for pipeline workloads
resource "azurerm_kubernetes_cluster_node_pool" "pipeline" {
  name                  = "pipeline"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.nexus.id
  vm_size               = "Standard_D8s_v5"
  priority              = "Spot"
  eviction_policy       = "Delete"
  spot_max_price        = -1                # pay up to on-demand price
  enable_auto_scaling   = true
  min_count             = 0
  max_count             = 20
  vnet_subnet_id        = azurerm_subnet.aks.id
  zones                 = ["1", "2", "3"]
  node_labels = {
    role                                    = "pipeline"
    "kubernetes.azure.com/scalesetpriority" = "spot"
  }
  node_taints = ["kubernetes.azure.com/scalesetpriority=spot:NoSchedule"]
}

# Attach ACR to AKS
resource "azurerm_role_assignment" "aks_acr" {
  scope                = azurerm_container_registry.nexus.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.nexus.kubelet_identity[0].object_id
}

# ── Azure Cache for Redis ─────────────────────────────────────────────────────────
resource "azurerm_redis_cache" "nexus" {
  name                          = "${var.project_name}-redis"
  location                      = azurerm_resource_group.nexus.location
  resource_group_name           = azurerm_resource_group.nexus.name
  capacity                      = 2
  family                        = "P"                # Premium for persistence + VNet
  sku_name                      = "Premium"
  enable_non_ssl_port           = false
  minimum_tls_version           = "1.2"
  public_network_access_enabled = false

  redis_configuration {
    maxmemory_reserved              = 125
    maxmemory_delta                 = 125
    maxmemory_policy                = "allkeys-lru"
    rdb_backup_enabled              = true
    rdb_backup_frequency            = 60
    rdb_backup_max_snapshot_count   = 1
    rdb_storage_connection_string   = azurerm_storage_account.nexus.primary_blob_connection_string
  }

  subnet_id = azurerm_subnet.redis.id
}

# ── Storage Account ───────────────────────────────────────────────────────────────
resource "azurerm_storage_account" "nexus" {
  name                     = "${replace(var.project_name, "-", "")}storage"
  resource_group_name      = azurerm_resource_group.nexus.name
  location                 = azurerm_resource_group.nexus.location
  account_tier             = "Standard"
  account_replication_type = "ZRS"           # zone-redundant
  min_tls_version          = "TLS1_2"
  enable_https_traffic_only = true
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled  = true
    delete_retention_policy {
      days = 30
    }
  }
}

resource "azurerm_storage_container" "cad" {
  name                  = "cad-output"
  storage_account_name  = azurerm_storage_account.nexus.name
  container_access_type = "private"
}

# Azure Files share for RWX (CAD output across pods)
resource "azurerm_storage_share" "cad_rwx" {
  name                 = "nexus-cad-rwx"
  storage_account_name = azurerm_storage_account.nexus.name
  quota                = 50
}

# ── Log Analytics + Azure Monitor ─────────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "nexus" {
  name                = "${var.project_name}-logs"
  location            = azurerm_resource_group.nexus.location
  resource_group_name = azurerm_resource_group.nexus.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_monitor_action_group" "nexus" {
  name                = "${var.project_name}-alerts"
  resource_group_name = azurerm_resource_group.nexus.name
  short_name          = "nexus"

  email_receiver {
    name          = "devops"
    email_address = var.alert_email
  }
}

resource "azurerm_monitor_metric_alert" "redis_cpu" {
  name                = "${var.project_name}-redis-cpu"
  resource_group_name = azurerm_resource_group.nexus.name
  scopes              = [azurerm_redis_cache.nexus.id]
  severity            = 2

  criteria {
    metric_namespace = "Microsoft.Cache/Redis"
    metric_name      = "percentProcessorTime"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 75
  }

  action {
    action_group_id = azurerm_monitor_action_group.nexus.id
  }
}

# ── Azure DNS ─────────────────────────────────────────────────────────────────────
resource "azurerm_dns_zone" "nexus" {
  name                = var.domain_name
  resource_group_name = azurerm_resource_group.nexus.name
}

# ── Application Gateway (Layer 7 WAF LB) ─────────────────────────────────────────
resource "azurerm_public_ip" "appgw" {
  name                = "${var.project_name}-appgw-pip"
  resource_group_name = azurerm_resource_group.nexus.name
  location            = azurerm_resource_group.nexus.location
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]
}

resource "azurerm_application_gateway" "nexus" {
  name                = "${var.project_name}-appgw"
  resource_group_name = azurerm_resource_group.nexus.name
  location            = azurerm_resource_group.nexus.location

  sku {
    name     = "WAF_v2"
    tier     = "WAF_v2"
    capacity = 2
  }

  autoscale_configuration {
    min_capacity = 2
    max_capacity = 10
  }

  waf_configuration {
    enabled          = true
    firewall_mode    = "Prevention"
    rule_set_type    = "OWASP"
    rule_set_version = "3.2"
  }

  zones = ["1", "2", "3"]

  gateway_ip_configuration {
    name      = "appgw-ip"
    subnet_id = azurerm_subnet.appgw.id
  }

  frontend_port {
    name = "https"
    port = 443
  }

  frontend_ip_configuration {
    name                 = "appgw-frontend-ip"
    public_ip_address_id = azurerm_public_ip.appgw.id
  }

  backend_address_pool {
    name = "nexus-backend-pool"
  }

  backend_http_settings {
    name                  = "nexus-http-settings"
    cookie_based_affinity = "Disabled"
    port                  = 80
    protocol              = "Http"
    request_timeout       = 300
    probe_name            = "nexus-health-probe"
  }

  probe {
    name                = "nexus-health-probe"
    protocol            = "Http"
    path                = "/health"
    interval            = 15
    timeout             = 10
    unhealthy_threshold = 3
    host                = var.domain_name
    match {
      status_code = ["200-399"]
    }
  }

  http_listener {
    name                           = "nexus-https-listener"
    frontend_ip_configuration_name = "appgw-frontend-ip"
    frontend_port_name             = "https"
    protocol                       = "Https"
    ssl_certificate_name           = "nexus-ssl-cert"
  }

  ssl_certificate {
    name                = "nexus-ssl-cert"
    key_vault_secret_id = azurerm_key_vault_certificate.nexus.secret_id
  }

  request_routing_rule {
    name                       = "nexus-routing"
    rule_type                  = "Basic"
    http_listener_name         = "nexus-https-listener"
    backend_address_pool_name  = "nexus-backend-pool"
    backend_http_settings_name = "nexus-http-settings"
    priority                   = 1
  }
}

# App Gateway managed SSL certificate (Azure-managed, auto-renews)
resource "azurerm_key_vault_certificate" "nexus" {
  name         = "${var.project_name}-ssl-cert"
  key_vault_id = azurerm_key_vault.nexus.id

  certificate_policy {
    issuer_parameters { name = "Self" }
    key_properties {
      exportable = true
      key_size   = 2048
      key_type   = "RSA"
      reuse_key  = true
    }
    secret_properties { content_type = "application/x-pkcs12" }
    x509_certificate_properties {
      extended_key_usage = ["1.3.6.1.5.5.7.3.1"]
      key_usage          = ["cRLSign", "dataEncipherment", "digitalSignature", "keyAgreement", "keyEncipherment", "keyCertSign"]
      subject            = "CN=${var.domain_name}"
      validity_in_months = 12
    }
  }
}
