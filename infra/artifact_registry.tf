# Docker registry for the reasoning service container image.

resource "google_artifact_registry_repository" "containers" {
  project       = var.project_id
  location      = var.region
  repository_id = local.artifact_repo
  format        = "DOCKER"
  description   = "egosyntonic container images (${var.env})"
  labels        = local.labels

  depends_on = [google_project_service.required]
}

# CI service account can push images
resource "google_artifact_registry_repository_iam_member" "ci_writer" {
  project    = google_artifact_registry_repository.containers.project
  location   = google_artifact_registry_repository.containers.location
  repository = google_artifact_registry_repository.containers.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.github_ci.email}"
}

# Cloud Run runtime SA can pull images
resource "google_artifact_registry_repository_iam_member" "runtime_reader" {
  project    = google_artifact_registry_repository.containers.project
  location   = google_artifact_registry_repository.containers.location
  repository = google_artifact_registry_repository.containers.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.reasoning_runtime.email}"
}
