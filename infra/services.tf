# Enable the GCP APIs the project depends on.
#
# disable_dependent_services = false: leave APIs enabled if Terraform later
# removes them from this list. We never want a `terraform destroy` to silently
# disable APIs that may still be in use by other parts of the project.

locals {
  required_services = [
    "run.googleapis.com",                    # Cloud Run
    "firestore.googleapis.com",              # Firestore (incl. vector search)
    "generativelanguage.googleapis.com",     # Gemini API (chat + embeddings)
    "secretmanager.googleapis.com",          # Secret Manager
    "cloudbuild.googleapis.com",             # Cloud Build (for image builds)
    "artifactregistry.googleapis.com",       # Docker registry
    "logging.googleapis.com",                # Cloud Logging
    "cloudtrace.googleapis.com",             # Cloud Trace
    "monitoring.googleapis.com",             # Cloud Monitoring (for alerts)
    "iam.googleapis.com",                    # IAM
    "iamcredentials.googleapis.com",         # WIF
    "sts.googleapis.com",                    # WIF token exchange
    "cloudtasks.googleapis.com",             # async state-update jobs
    "cloudresourcemanager.googleapis.com",   # project introspection
    "firebase.googleapis.com",               # Firebase
    "identitytoolkit.googleapis.com",        # Firebase Auth
  ]
}

resource "google_project_service" "required" {
  for_each = toset(local.required_services)

  project = var.project_id
  service = each.value

  disable_dependent_services = false
  disable_on_destroy         = false
}
