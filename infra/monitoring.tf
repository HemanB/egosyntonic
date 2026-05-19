# Monitoring — cost and latency alerts.
#
# v1: lightweight. Two alerts (latency, error rate) and a log-based metric
# for per-turn cost (populated from structured log entries by the service).
# Full SLO + budget alerts come in v2 once we have baseline usage data.

resource "google_logging_project_bucket_config" "default_retention" {
  project        = var.project_id
  location       = "global"
  retention_days = var.log_retention_days
  bucket_id      = "_Default"

  depends_on = [google_project_service.required]
}

# Log-based metric: per-turn cost in micro-dollars, emitted by the orchestrator
# in a structured log field. Becomes meaningful once Track B-live wiring lands.

resource "google_logging_metric" "turn_cost" {
  project = var.project_id
  name    = "egosyntonic/turn_cost_microcents"
  filter  = "jsonPayload.event=\"turn_completed\" AND jsonPayload.cost_microcents>0"

  # DISTRIBUTION required when a value_extractor is set (GCP constraint).
  # Exponential buckets covering 1 microcent → ~10^9 microcents ($10K) handle
  # everything from cheap Flash embedding calls to runaway-cost outliers.
  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    unit         = "1"
    display_name = "egosyntonic per-turn cost (microcents)"
  }

  value_extractor = "EXTRACT(jsonPayload.cost_microcents)"

  bucket_options {
    exponential_buckets {
      num_finite_buckets = 32
      growth_factor      = 2
      scale              = 1
    }
  }

  depends_on = [google_project_service.required]
}

# Notification channel placeholder — populated out-of-band with your email/Slack.
# Comment in once you have a real channel ID.
#
# resource "google_monitoring_notification_channel" "primary" {
#   project      = var.project_id
#   display_name = "primary on-call (${var.env})"
#   type         = "email"
#   labels = { email_address = "you@example.com" }
# }

# Alert: Cloud Run 5xx rate > 5% over 5 min
resource "google_monitoring_alert_policy" "reasoning_5xx" {
  project      = var.project_id
  display_name = "egosyntonic reasoning 5xx rate (${var.env})"
  combiner     = "OR"

  conditions {
    display_name = "5xx ratio > 5%"
    condition_threshold {
      filter = join(" AND ", [
        "resource.type = \"cloud_run_revision\"",
        "resource.labels.service_name = \"${var.service_name}-${var.env}\"",
        "metric.type = \"run.googleapis.com/request_count\"",
        "metric.labels.response_code_class = \"5xx\"",
      ])
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  documentation {
    content   = "Cloud Run 5xx rate exceeded 5% for 5 minutes. Check Cloud Trace for the failing turn IDs."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }

  # notification_channels = [google_monitoring_notification_channel.primary.id]

  depends_on = [google_project_service.required]
}
