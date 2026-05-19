# Secret Manager — Gemini key and any future signing keys.
#
# Secrets are created EMPTY by Terraform. Add the version with the actual
# secret value out-of-band:
#
#   printf "%s" "$NEW_KEY" | gcloud secrets versions add gemini-api-key \
#     --project=PROJECT --data-file=-
#
# Terraform does not store the secret value. Rotation is just a new version.

resource "google_secret_manager_secret" "gemini_api_key" {
  project   = var.project_id
  secret_id = "gemini-api-key"

  labels = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

# Runtime SA can access this specific secret only (least privilege).
resource "google_secret_manager_secret_iam_member" "runtime_gemini_access" {
  project   = google_secret_manager_secret.gemini_api_key.project
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.reasoning_runtime.email}"
}

# Cloud Run v2 uses the Google-managed serverless-robot service agent to
# materialize Secret-Manager secrets into container env vars at deploy time
# (distinct from the runtime SA above, which the *running* container uses).
# Without this binding, Cloud Run deploys that reference Secret Manager fail
# at revision-create with a permission error. Bringing the binding into IaC
# so destroy/recreate cycles on the secret don't strand future deploys.
data "google_project" "current" {
  project_id = var.project_id
}

resource "google_secret_manager_secret_iam_member" "cloud_run_agent_gemini_access" {
  project   = google_secret_manager_secret.gemini_api_key.project
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:service-${data.google_project.current.number}@serverless-robot-prod.iam.gserviceaccount.com"
}
