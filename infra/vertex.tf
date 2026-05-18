# Vertex AI Vector Search — utterance memory.
#
# An index + a deployed index endpoint. text-embedding-005 produces 768-dim
# vectors; cosine distance fits semantic similarity over normalized embeddings.
#
# NOTE: index creation takes ~30 min wall-clock. Deploy this resource and
# attend to other work while it propagates.

resource "google_vertex_ai_index" "utterances" {
  provider = google-beta

  project      = var.project_id
  region       = var.region
  display_name = "egosyntonic-utterances-${var.env}"
  description  = "Per-user utterance embeddings (idea.md §4.1)."
  labels       = local.labels

  metadata {
    config {
      dimensions                  = var.vector_index_dimensions
      approximate_neighbors_count = 50
      distance_measure_type       = "COSINE_DISTANCE"
      feature_norm_type           = "UNIT_L2_NORM"

      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 1000
          leaf_nodes_to_search_percent = 10
        }
      }
    }
  }

  # Streaming updates so new utterances are searchable within seconds
  index_update_method = "STREAM_UPDATE"

  depends_on = [google_project_service.required]
}

resource "google_vertex_ai_index_endpoint" "utterances" {
  provider = google-beta

  project              = var.project_id
  region               = var.region
  display_name         = "egosyntonic-utterances-${var.env}"
  description          = "Endpoint for the utterances index."
  labels               = local.labels
  public_endpoint_enabled = true

  depends_on = [google_project_service.required]
}

# Deployment binds the index to the endpoint with a unique deployed_index_id.
# Updating this resource in-place triggers a redeploy (slow). Treat changes
# as a planned operation.
resource "google_vertex_ai_index_endpoint_deployed_index" "utterances" {
  provider = google-beta

  index_endpoint    = google_vertex_ai_index_endpoint.utterances.id
  deployed_index_id = "utterances_${var.env}"
  display_name      = "egosyntonic-utterances-${var.env}"

  index = google_vertex_ai_index.utterances.id

  automatic_resources {
    min_replica_count = 1
    max_replica_count = var.env == "prod" ? 4 : 1
  }
}
