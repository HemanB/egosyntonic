# infra

Terraform managing all GCP resources for egosyntonic.

## Resources provisioned

- **Service enablement** (`services.tf`) — Cloud Run, Firestore, Generative Language (Gemini API), Secret Manager, Artifact Registry, Cloud Tasks, Cloud Logging, Cloud Trace, Cloud Monitoring, IAM, WIF, Firebase, Firebase Auth.
- **Cloud Run** (`cloudrun.tf`) — `egosyntonic-reasoning-<env>` service. Authenticated only; iOS client sends Firebase ID tokens. Min instances = 0 (scales to zero).
- **Firestore** (`firestore.tf`) — Native mode, point-in-time recovery enabled, delete protection on prod. Also hosts the `utterances` vector index (768-dim, cosine via `FindNearest`) replacing Vertex AI Vector Search — see `docs/decisions/0001-firestore-vector-store.md`.
- **Secret Manager** (`secrets.tf`) — `gemini-api-key` secret, created empty. Values added out-of-band via `gcloud secrets versions add`.
- **Artifact Registry** (`artifact_registry.tf`) — Docker repo for the reasoning service image.
- **IAM** (`iam.tf`) — Two service accounts:
  - `egosyn-reasoning-<env>`: Cloud Run runtime identity. Scoped to Firestore, Cloud Tasks, Trace, Logging, and the specific Gemini secret. (Gemini API uses the secret-managed API key — no aiplatform IAM needed.)
  - `egosyn-gh-ci-<env>`: Used by GitHub Actions via Workload Identity Federation. Can deploy Cloud Run revisions and push container images. **No JSON keys exist anywhere.**
- **Monitoring** (`monitoring.tf`) — `_Default` log bucket retention, log-based metric for per-turn cost, and a 5xx-rate alert policy (notification channel left as a placeholder).

## Bootstrap

A few one-time steps before `terraform init`:

```sh
# 1. Authenticate
gcloud auth login
gcloud auth application-default login

# 2. Create the GCP project (manual; or via gcloud projects create)
#    Enable billing in the console.

# 3. Bootstrap the Terraform state bucket
PROJECT=egosyntonic-dev
gsutil mb -p "$PROJECT" -l us-central1 "gs://egosyntonic-tfstate-dev"
gsutil versioning set on "gs://egosyntonic-tfstate-dev"
gsutil ubla set on "gs://egosyntonic-tfstate-dev"

# 4. Init Terraform with the state backend
cd infra
terraform init \
  -backend-config="bucket=egosyntonic-tfstate-dev" \
  -backend-config="prefix=infra"

# 5. Plan + apply
cp envs/dev.tfvars.example envs/dev.tfvars
terraform plan  -var-file=envs/dev.tfvars
terraform apply -var-file=envs/dev.tfvars

# 6. Add the Gemini key as a secret version (do NOT commit the key)
printf "%s" "$NEW_KEY" | gcloud secrets versions add gemini-api-key \
  --project="$PROJECT" --data-file=-
```

## Two environments

Separate GCP projects, separate state buckets, separate `tfvars`. No shared resources between `dev` and `prod` — including service accounts, secrets, and Firestore databases.

## What this Terraform does NOT do

- **Does NOT create the GCP project itself.** Projects are created out-of-band (the walkthrough in `docs/setup.md`). This is intentional — project creation requires org-level perms that vary across users and is one-time, not a Terraform-managed lifecycle.
- **Does NOT enable billing.** Done by you in the console.
- **Does NOT link Firebase to the GCP project.** Done once in the Firebase console.
- **Does NOT push container images.** That's CI's job; Terraform only provisions the registry and the runtime identity that pulls.
- **Does NOT store secret values.** Secret resources are created empty; versions are added out-of-band.

## CI integration

GitHub Actions exchanges its OIDC token for the `egosyn-gh-ci-<env>` SA via the WIF provider. The workflow needs these two values, both available as Terraform outputs:

```yaml
# .github/workflows/backend.yml (deploy job, future)
permissions:
  id-token: write   # OIDC
  contents: read

steps:
  - uses: google-github-actions/auth@v2
    with:
      workload_identity_provider: <output wif_provider_name>
      service_account:           <output github_ci_sa>
```

## Status

v1 scaffold. Not yet applied. The user's first `terraform apply` happens after the GCP project + billing exist.
