# Cloud Run reasoning service.
#
# Initially deploys a placeholder image (hello container) if var.container_image
# is empty — lets the rest of the infra come up cleanly. CI replaces the image
# on subsequent revisions.

locals {
  placeholder_image = "us-docker.pkg.dev/cloudrun/container/hello"
  effective_image   = var.container_image != "" ? var.container_image : local.placeholder_image
}

resource "google_cloud_run_v2_service" "reasoning" {
  project  = var.project_id
  location = var.region
  name     = "${var.service_name}-${var.env}"
  labels   = local.labels

  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = var.env == "prod"

  template {
    service_account = google_service_account.reasoning_runtime.email

    scaling {
      min_instance_count = 0
      max_instance_count = var.env == "prod" ? 20 : 4
    }

    containers {
      image = local.effective_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "EGOSYN_RUNTIME_MODE"
        value = "live"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = local.effective_firebase_project_id
      }
      env {
        name  = "EGOSYN_OTEL_ENABLED"
        value = "true"
      }
      env {
        name  = "EGOSYN_DEV_AUTH_BYPASS"
        value = "false"
      }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 0
        timeout_seconds       = 5
        period_seconds        = 5
        failure_threshold     = 6
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        timeout_seconds   = 5
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    timeout                          = "60s"
    max_instance_request_concurrency = 40
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # Image is updated out-of-band by CI; ignore drift on the image tag.
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_project_service.required,
    google_firestore_index.utterances_vector,
    google_secret_manager_secret_iam_member.runtime_gemini_access,
  ]
}

# Authenticated access only — iOS client sends Firebase ID token; auth
# middleware in the service verifies. NO public unauth invocation.
# (We expose ingress=ALL because the iOS app calls directly, but the service
# itself rejects requests without a valid bearer token.)
#
# If you ever want unauthenticated browser access for a dashboard, add a
# separate allUsers binding ONLY on a sidecar.

resource "google_cloud_run_v2_service_iam_member" "ci_deployer" {
  project  = google_cloud_run_v2_service.reasoning.project
  location = google_cloud_run_v2_service.reasoning.location
  name     = google_cloud_run_v2_service.reasoning.name
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.github_ci.email}"
}
