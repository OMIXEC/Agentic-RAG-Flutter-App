output "container_app_url" {
  description = "Container App FQDN"
  value       = azurerm_container_app.backend.latest_revision_fqdn
}

output "acr_login_server" {
  description = "Azure Container Registry login server"
  value       = azurerm_container_registry.main.login_server
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}
