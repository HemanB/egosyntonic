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
