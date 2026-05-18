variable "project_id" {
  description = "GCP project ID. Created out-of-band per docs/setup.md GCP walkthrough."
  type        = string
}

variable "env" {
  description = "Environment name. Used to suffix resources and select tfvars."
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env must be 'dev' or 'prod'."
  }
}

variable "region" {
  description = "Default GCP region. Single-region in v1."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "egosyntonic-reasoning"
}

variable "container_image" {
  description = "Reasoning service container image (full URI including digest or tag). Empty string deploys a placeholder image."
  type        = string
  default     = ""
}

variable "github_org" {
  description = "GitHub org/user that owns the repo. Used to constrain Workload Identity Federation."
  type        = string
}

variable "github_repo" {
  description = "GitHub repo name. Used for WIF and Cloud Build trigger principal."
  type        = string
  default     = "egosyntonic"
}

variable "firebase_project_id" {
  description = "Firebase project ID. v1: same as project_id (Firebase linked to the same GCP project)."
  type        = string
  default     = ""
}

variable "vector_index_dimensions" {
  description = "Embedding vector dimensions. text-embedding-005 is 768."
  type        = number
  default     = 768
}

variable "log_retention_days" {
  description = "Days to retain Cloud Logging entries. 30 is sufficient for v1 ops; audit-log subset is retained longer (TODO)."
  type        = number
  default     = 30
}

locals {
  resource_suffix = var.env
  artifact_repo   = "egosyntonic-${var.env}"
  effective_firebase_project_id = var.firebase_project_id != "" ? var.firebase_project_id : var.project_id

  # Common labels applied to all resources for cost/owner attribution
  labels = {
    app         = "egosyntonic"
    component   = "reasoning"
    env         = var.env
    managed_by  = "terraform"
  }
}
