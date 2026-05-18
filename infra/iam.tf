# Service accounts and IAM bindings.
#
# Two service accounts:
# - reasoning-runtime: Cloud Run service runtime identity.
# - github-ci:        Used by GitHub Actions via Workload Identity Federation
#                     (no JSON keys, no long-lived credentials).

# --- Runtime SA for the Cloud Run reasoning service ---

resource "google_service_account" "reasoning_runtime" {
  project      = var.project_id
  account_id   = "egosyn-reasoning-${local.resource_suffix}"
  display_name = "egosyntonic reasoning runtime (${var.env})"
  description  = "Cloud Run service identity for the reasoning service."

  depends_on = [google_project_service.required]
}

# Firestore access — read/write the state document and audit logs
resource "google_project_iam_member" "runtime_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.reasoning_runtime.email}"
}

# Vertex AI access — embeddings + Vector Search
resource "google_project_iam_member" "runtime_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.reasoning_runtime.email}"
}

# Cloud Tasks — enqueue async state-update jobs
resource "google_project_iam_member" "runtime_cloudtasks" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.reasoning_runtime.email}"
}

# Cloud Trace + Logging
resource "google_project_iam_member" "runtime_trace" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.reasoning_runtime.email}"
}

resource "google_project_iam_member" "runtime_logwriter" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.reasoning_runtime.email}"
}

# Secret access is scoped to specific secrets in secrets.tf (least privilege).

# --- CI service account (consumed via WIF) ---

resource "google_service_account" "github_ci" {
  project      = var.project_id
  account_id   = "egosyn-gh-ci-${local.resource_suffix}"
  display_name = "egosyntonic GitHub Actions CI (${var.env})"
  description  = "Used by GitHub Actions via Workload Identity Federation."

  depends_on = [google_project_service.required]
}

# CI deploys Cloud Run revisions
resource "google_project_iam_member" "ci_runadmin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_ci.email}"
}

# CI needs to actAs the runtime SA when deploying a service that uses it
resource "google_service_account_iam_member" "ci_actas_runtime" {
  service_account_id = google_service_account.reasoning_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_ci.email}"
}

# --- Workload Identity Federation for GitHub Actions ---
#
# Lets GitHub Actions exchange an OIDC token for short-lived GCP credentials.
# No JSON service-account keys anywhere.

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "egosyn-gh-${local.resource_suffix}"
  display_name              = "GitHub Actions (${var.env})"
  description               = "WIF pool for ${var.github_org}/${var.github_repo}."

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"
  description                        = "Issues credentials to ${var.github_org}/${var.github_repo} actions."

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
    "attribute.workflow"   = "assertion.workflow"
  }

  # Hard constraint: only this repo can use this pool
  attribute_condition = "assertion.repository == \"${var.github_org}/${var.github_repo}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Bind the CI SA to the WIF pool — only the named repo can impersonate it
resource "google_service_account_iam_member" "ci_wif_binding" {
  service_account_id = google_service_account.github_ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_org}/${var.github_repo}"
}
