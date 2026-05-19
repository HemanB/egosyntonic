# Firestore — state document, audit-log storage, and vector retrieval.
#
# Native mode. Single region (us-central1) in v1. Multi-region is a v2 problem.
# CMEK is not required for HIPAA per se but is a common ask; left to v2.

resource "google_firestore_database" "main" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  # Point-in-time recovery — cheap insurance against accidental writes
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"

  # Delete protection on prod
  delete_protection_state = var.env == "prod" ? "DELETE_PROTECTION_ENABLED" : "DELETE_PROTECTION_DISABLED"

  depends_on = [google_project_service.required]
}

# Vector index for utterance memory retrieval (idea.md §4.1).
#
# Composite (user_id ASC, embedding vector). Lets per-user nearest-neighbor
# queries prefix-filter on user_id, then rank by cosine distance on `embedding`.
# Replaces Vertex AI Vector Search — see docs/decisions/0001-firestore-vector-store.md.
resource "google_firestore_index" "utterances_vector" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "utterances"
  api_scope  = "ANY_API"

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  # Firestore inserts __name__ between filter fields and the vector field on
  # composite vector indexes. Declaring it explicitly keeps Terraform's plan
  # clean against the server-side index shape.
  fields {
    field_path = "__name__"
    order      = "ASCENDING"
  }

  fields {
    field_path = "embedding"
    vector_config {
      dimension = var.vector_index_dimensions
      flat {}
    }
  }
}
