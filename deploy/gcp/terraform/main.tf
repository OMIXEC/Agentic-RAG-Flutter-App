terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ─── Secret Manager ───────────────────────────────────────
resource "google_secret_manager_secret" "app_secrets" {
  for_each  = var.secrets
  secret_id = each.key

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "app_secrets" {
  for_each    = var.secrets
  secret      = google_secret_manager_secret.app_secrets[each.key].id
  secret_data = each.value
}

# ─── Container Registry (Artifact Registry) ──────────────
resource "google_artifact_registry_repository" "backend" {
  location      = var.region
  repository_id = "${var.app_name}-backend"
  format        = "DOCKER"
}

# ─── Cloud Run Service ───────────────────────────────────
resource "google_cloud_run_v2_service" "backend" {
  name     = "${var.app_name}-backend"
  location = var.region

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}/backend:latest"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app_secrets[env.key].secret_id
              version = "latest"
            }
          }
        }
      }
    }

    service_account = google_service_account.backend.email
  }

  depends_on = [google_secret_manager_secret_version.app_secrets]
}

# ─── Service Account ─────────────────────────────────────
resource "google_service_account" "backend" {
  account_id   = "${var.app_name}-backend-sa"
  display_name = "${var.app_name} Backend Service Account"
}

resource "google_secret_manager_secret_iam_member" "backend_access" {
  for_each  = var.secrets
  secret_id = google_secret_manager_secret.app_secrets[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

# ─── Public Access ────────────────────────────────────────
resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.allow_public_access ? 1 : 0
  name     = google_cloud_run_v2_service.backend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
