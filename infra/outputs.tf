output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}

output "cloud_run_url" {
  description = "Reasoning service Cloud Run URL."
  value       = google_cloud_run_v2_service.reasoning.uri
}

output "cloud_run_service_name" {
  value = google_cloud_run_v2_service.reasoning.name
}

output "reasoning_runtime_sa" {
  description = "Cloud Run runtime service account email."
  value       = google_service_account.reasoning_runtime.email
}

output "github_ci_sa" {
  description = "CI service account email (impersonated via WIF)."
  value       = google_service_account.github_ci.email
}

output "wif_pool_name" {
  description = "Full resource name of the WIF pool — copy into the GitHub Action workflow."
  value       = google_iam_workload_identity_pool.github.name
}

output "wif_provider_name" {
  description = "Full resource name of the WIF OIDC provider — copy into the GitHub Action workflow."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "artifact_registry_repo" {
  description = "Docker registry URI for pushing container images."
  value       = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}"
}

output "vertex_index_endpoint_id" {
  value = google_vertex_ai_index_endpoint.utterances.id
}

output "vertex_index_id" {
  value = google_vertex_ai_index.utterances.id
}

output "vertex_deployed_index_id" {
  value = google_vertex_ai_index_endpoint_deployed_index.utterances.deployed_index_id
}

output "gemini_secret_name" {
  description = "Secret Manager secret ID for the Gemini API key — add versions out-of-band."
  value       = google_secret_manager_secret.gemini_api_key.secret_id
}
