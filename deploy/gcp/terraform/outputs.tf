output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "service_account_email" {
  description = "Backend service account email"
  value       = google_service_account.backend.email
}

output "artifact_registry_url" {
  description = "Container image registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}"
}
