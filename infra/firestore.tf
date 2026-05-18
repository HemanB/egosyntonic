# Firestore — state document and audit-log storage.
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
