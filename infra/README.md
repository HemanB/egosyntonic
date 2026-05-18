# infra

Terraform managing all GCP resources for egosyntonic.

## Status

Scaffolding in progress. Modules planned:

- `cloudrun.tf` — reasoning service deployment
- `firestore.tf` — state document + audit log database
- `vertex.tf` — Vector Search index endpoint
- `iam.tf` — service accounts, Workload Identity Federation for GitHub Actions
- `secrets.tf` — Secret Manager (Gemini key, Firebase admin creds)
- `artifact_registry.tf` — Docker images
- `monitoring.tf` — cost/latency alerts, log-based metrics

State lives in a GCS bucket bootstrapped before first apply.

Environments: `egosyntonic-dev` and `egosyntonic-prod`, separate GCP projects, separate state.
