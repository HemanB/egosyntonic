# Developer Setup

*How to get a working local environment for the egosyntonic backend. The repo is in Phase 1 (backend-only; no iOS work yet). Most sections here describe the structure of the bootstrap; sections that aren't yet implementable are marked with `TODO` and the track that will land them.*

The canonical product spec is `docs/idea.md`. The tech-stack plan is in `~/.claude/plans/wondrous-stirring-brooks.md`. Read both before changing anything load-bearing.

---

## 1. Prerequisites

You need a recent macOS machine. The build is not tested on Linux or Windows yet (Linux should work for backend-only work; not officially supported).

### 1.1 System tooling

- **macOS 14+** (Sonoma or later).
- **Homebrew.** Install from https://brew.sh if you don't have it.
- **Xcode Command Line Tools.** `xcode-select --install`. Required for `git`, compilers, and most native Python build dependencies.
- **Full Xcode** is not required for Phase 1 (no iOS work yet). It will be required for Phase 2.

### 1.2 Languages and runtimes

- **Python 3.12.** Install via `uv` (recommended) or `pyenv`. The repo uses `uv` for dependency management; `uv` will install and manage the project's Python version itself if you use `uv python install 3.12`.
- **`uv`** — fast Python package and project manager. `brew install uv`.

### 1.3 Cloud and infra tooling

- **`gcloud` CLI.** `brew install --cask google-cloud-sdk`. Required for any work that touches GCP. After install:
  - `gcloud auth login` (browser-based, human-only step).
  - `gcloud auth application-default login` (so local Python clients can pick up credentials).
- **`terraform`.** `brew tap hashicorp/tap && brew install hashicorp/tap/terraform`. (HashiCorp pulled Terraform from the default Homebrew formulas after the BSL relicense; the tap is now the canonical install path.) Required for `infra/` work.
- **`gh`** (GitHub CLI). `brew install gh`. Used for PR workflow.

### 1.4 Editor and pre-commit

- Any editor is fine. The repo uses Ruff and Pyright; configure your editor to use them or rely on pre-commit/CI.
- **`pre-commit`** — `brew install pre-commit`, then `pre-commit install` in the repo root. > TODO: filled in when Track B (backend skeleton) lands the `.pre-commit-config.yaml`.

---

## 2. Repository

### 2.1 Clone

```
git clone <remote-url> egosyntonic
cd egosyntonic
```

> TODO: filled in when the remote is created. The plan references that the remote may be created via `gh repo create` at the first-commit step.

### 2.2 Branch model

- **Trunk-based** on `main`.
- **One feature branch per track** during the parallel-build phases: `track/A-infra`, `track/B-backend-skeleton`, etc.
- **Short-lived branches.** Squash-merge to `main` on green CI.
- **Schema-change PRs** must update generated artifacts on both sides (backend and, in Phase 2, iOS) in the same PR. A CI check enforces this.
- **Plan-of-record updates** that change the tech-stack plan are documented as a new ADR under `docs/decisions/`, referenced in the PR body.

### 2.3 Layout

The high-level repo layout (full plan in `~/.claude/plans/wondrous-stirring-brooks.md`):

```
egosyntonic/
├── app/                  # SwiftUI iOS client (Phase 2)
├── backend/
│   ├── reasoning/        # Pipeline orchestration (FastAPI)
│   ├── extraction/       # Feature extraction worker
│   ├── eval/             # Offline eval harness, golden sets
│   └── pyproject.toml
├── shared/
│   ├── schemas/          # JSON Schema for state doc, plan, etc.
│   └── vocabularies/     # Behaviors, network nodes, need domains
├── infra/                # Terraform: GCP project, Cloud Run, Firestore, Vertex AI, IAM
├── docs/                 # Product, eval, safety, privacy, terms, this file
└── .github/workflows/    # CI
```

---

## 3. Backend local development

### 3.1 Bootstrap a working environment

From the repo root:

```
cd backend
uv sync
```

`uv sync` reads `backend/pyproject.toml` and `backend/uv.lock`, installs the project's Python (3.12) if needed, and creates a `.venv` in `backend/`.

> TODO: filled in when Track B lands `backend/pyproject.toml` and `backend/uv.lock`.

### 3.2 Environment variables

Local development reads from `backend/.env.local` (gitignored). The canonical list of expected env vars lives in `backend/.env.example`, which is committed.

> TODO: filled in when Track B lands `backend/.env.example`. The expected list, based on the plan:
>
> - `GCP_PROJECT_ID` — `egosyntonic-dev` for local work.
> - `GCP_REGION` — `us-central1` for v1.
> - `GEMINI_API_KEY` — AI Studio key for fixture-mode dev; **never** committed, never pasted into chat. Pulled from Secret Manager in deployed environments.
> - `FIREBASE_PROJECT_ID` — linked to the GCP project.
> - `FIREBASE_AUTH_EMULATOR_HOST` — set when using the Firebase Auth emulator locally.
> - `FIRESTORE_EMULATOR_HOST` — set when using the Firestore emulator locally.
> - `EGOSYN_UTTERANCES_COLLECTION` — Firestore collection backing vector retrieval (`utterances` by default; see ADR-0001).
> - `PIPELINE_FIXTURE_MODE` — `true` to short-circuit Gemini calls with deterministic fixture outputs (see §3.4).
> - `LOG_LEVEL` — `DEBUG` for local, `INFO` in deployed environments.

### 3.3 Run the FastAPI service locally

```
cd backend
uv run uvicorn reasoning.main:app --reload --port 8080
```

The service binds to `http://localhost:8080`. Health check at `GET /health`.

> TODO: filled in when Track B lands `backend/reasoning/main.py` and the health endpoint.

### 3.4 Fixture mode (no real Gemini calls)

For most local development, especially for anything in the pipeline that's expensive or rate-limited, run the service in **fixture mode**:

```
PIPELINE_FIXTURE_MODE=true uv run uvicorn reasoning.main:app --reload --port 8080
```

In fixture mode:
- Every Gemini call is intercepted before it hits the network.
- The interceptor returns a deterministic response keyed off the prompt-template name and the hash of the input.
- Responses are loaded from `backend/eval/golden/fixtures/responses/` (mapping of `(template_name, input_hash) -> response`).
- New fixtures can be captured by setting `PIPELINE_FIXTURE_CAPTURE=true` once, running a real Gemini call, and committing the captured response.

Fixture mode is the default mode for any developer who is not actively iterating on prompts or running an end-to-end smoke. It removes the need for a Gemini key, removes rate-limit friction, and produces deterministic test outputs.

> TODO: filled in when Track B + Track D land the fixture-mode interceptor and the initial fixture set.

### 3.5 Emulators for Firebase / Firestore

For local work against Firebase services without hitting prod:

```
gcloud components install cloud-firestore-emulator
firebase emulators:start --only firestore,auth
```

> TODO: filled in when Track A or Track B lands `firebase.json` with emulator config.

Set `FIRESTORE_EMULATOR_HOST=localhost:8081` and `FIREBASE_AUTH_EMULATOR_HOST=localhost:9099` in `backend/.env.local` so the service routes to the emulators rather than prod Firestore.

### 3.6 What does not run locally

- **Firestore vector search.** The Firestore emulator does not yet implement `FindNearest`. Local dev runs in fixture mode for retrieval, or against the real `egosyntonic-dev` Firestore for end-to-end smoke tests. Vector indexes build in seconds, so there is no long initial-provisioning wait (unlike the prior Vertex-based design — see ADR-0001).
- **Cloud Run.** Local dev runs the service directly via uvicorn. The Docker image is built and run only for deploy or local container smoke tests.
- **Cloud Tasks.** Local dev runs state-update jobs synchronously in-process, not via Cloud Tasks. > TODO: confirm when Track B wires the async state-update path.

---

## 4. GCP project bootstrap

The plan's "GCP first-time setup walkthrough" is the canonical step-by-step. This section is the durable home for that walkthrough; the walkthrough should be lifted here when it is executed in real time.

> TODO: filled in when the project bootstrap is run for real. Until then, see `~/.claude/plans/wondrous-stirring-brooks.md` "GCP first-time setup walkthrough" for the live procedure.

Summary of what the bootstrap covers (per the plan):

1. Install and authenticate `gcloud`.
2. Create the `egosyntonic-dev` project (and later `egosyntonic-prod`).
3. Enable billing on the project (human-only, in the console).
4. Enable required APIs: Cloud Run, Firestore, Vertex AI, Secret Manager, Cloud Build, Artifact Registry, Cloud Logging, Cloud Trace, IAM, Cloud Tasks.
5. Link a Firebase project to the same GCP project.
6. Configure Firebase Auth providers (Sign in with Apple).
7. Create a service account and configure Workload Identity Federation for GitHub Actions.
8. Bootstrap the Terraform state bucket (GCS with versioning + uniform access).
9. Run the first `terraform apply` for Cloud Run, Firestore, Vertex AI Vector Search index, IAM.
10. Store the rotated Gemini key in Secret Manager.

The Gemini API key is never committed, never pasted into chat, and is rotated whenever it has been exposed (including pasting into an LLM context).

---

## 5. Running the eval golden set locally

The eval harness lives in `backend/eval/`. The methodology is in `docs/eval_methodology.md`.

### 5.1 Run the fast CI subset

```
cd backend
uv run pytest eval/ -m "ci"
```

This runs the same subset that CI runs on every PR: all safety-adversarial fixtures, a rotating slice of synthetic fixtures, schema-validation tests, lexicon checks. Target wall-clock: under 5 minutes in fixture mode.

> TODO: filled in when Track D lands the eval test scaffolding and the `ci` pytest marker.

### 5.2 Run the full nightly suite

```
cd backend
uv run pytest eval/ -m "nightly"
```

Slower (up to ~60 minutes), runs the full golden set, retrieval-relevance scoring, multi-turn fixtures. Cost a small amount of LLM spend when not in fixture mode.

### 5.3 Run a single fixture

```
cd backend
uv run pytest eval/ -k "fixture_name"
```

Useful when iterating on a specific failure mode.

### 5.4 Capture a new fixture

> TODO: filled in when Track D defines the fixture-capture workflow. Expected shape: `uv run python -m eval.capture --session-id <id>` produces a fixture YAML in `backend/eval/golden/fixtures/captured/` for review and promotion.

---

## 6. Tests and linters

### 6.1 Lint

```
cd backend
uv run ruff check .
uv run ruff format --check .
```

### 6.2 Type check

```
cd backend
uv run pyright
```

### 6.3 Unit tests

```
cd backend
uv run pytest --ignore=eval
```

`--ignore=eval` runs the fast unit tests without the golden eval set.

### 6.4 Pre-commit

`pre-commit run --all-files` runs lint, format-check, and type-check across the whole tree. CI runs the same hooks.

> TODO: filled in when Track B lands `.pre-commit-config.yaml`.

---

## 7. Troubleshooting

### 7.1 Gemini safety filter rejections

**Symptom:** an LLM call returns a blocked response with a `SAFETY` finish reason rather than content.

**Why it happens:** Gemini's safety filters are aggressive on ED-related content (`idea.md` §11.1). Eating-disorder vocabulary, even when used appropriately by the reasoning pipeline, can trip the filter.

**What the pipeline does:**
- **Extraction calls** (cheap, low-stakes): retry with a rephrasing wrapper, then fall back to Gemini Pro for re-extraction.
- **Reasoning and critic calls:** a blocked response surfaces as an internal safety flag and triggers the fixed safety template. The user never sees a "blocked" error; they see a safe, validated, supportive response.

**What you do locally:**
- If you're iterating on prompts and seeing frequent safety blocks on benign fixtures, log the full request including the `safetySettings` parameter and confirm the thresholds.
- The `safetySettings` thresholds for the pipeline are committed in code, not configured per-environment. Don't loosen them in a personal branch without a PR conversation.

> TODO: filled in when Track E lands the safety-filter handling code and the canonical thresholds.

### 7.2 Firestore vector index missing

**Symptom:** `FindNearest` returns `FAILED_PRECONDITION` complaining about a missing index.

**Why it happens:** Firestore vector indexes are declared as composite indexes (a non-vector field followed by a `vector_config` field). Without the matching declaration in Terraform (`infra/firestore.tf`), the runtime query can't find a usable index.

**What you do:**
- Verify the `utterances_vector` `google_firestore_index` resource exists in `infra/firestore.tf` and was applied (`terraform apply` includes it).
- Firestore vector indexes build in seconds-to-minutes — much faster than the prior Vertex AI Vector Search design (which took ~30 min). See ADR-0001 for the migration rationale.
- For CI eval, use fixture mode for retrieval. The relevance of real retrieval is evaluated in nightly runs, not per-PR.

### 7.3 Firebase Auth token verification in dev

**Symptom:** the backend rejects a request with a 401 when you're sending what looks like a valid Firebase ID token.

**Causes and fixes:**
- **Wrong project.** The token was issued by `egosyntonic-prod` but the backend is configured for `egosyntonic-dev`. Confirm `FIREBASE_PROJECT_ID` matches the token issuer.
- **Token expired.** Firebase ID tokens expire after one hour. Refresh and retry.
- **Emulator mode mismatch.** If using the Auth emulator, the backend must be configured to skip signature verification and trust the emulator. Set `FIREBASE_AUTH_EMULATOR_HOST` and confirm the backend's auth middleware honors it. > TODO: filled in when Track B lands the auth middleware.
- **Clock skew.** Local machine clock is more than a few minutes off. `sudo sntp -sS time.apple.com`.

### 7.4 `uv sync` fails on native dependencies

**Symptom:** Python package install fails compiling a native extension.

**Fix:** install Xcode Command Line Tools (`xcode-select --install`). If it's already installed, `sudo xcode-select --reset`.

### 7.5 Application Default Credentials not found

**Symptom:** Python clients (`google-genai`, `google-cloud-firestore`) throw `DefaultCredentialsError`.

**Fix:** `gcloud auth application-default login`. Then verify the credentials file exists at `~/.config/gcloud/application_default_credentials.json`.

For services that should use a service account locally (rarely needed; prefer ADC), set `GOOGLE_APPLICATION_CREDENTIALS` to a tightly-scoped key file. Service account keys are not committed.

### 7.6 Cost runaway during local dev

**Symptom:** an iteration session against real Gemini surprises you with a bill.

**Prevention:**
- Default to fixture mode (`PIPELINE_FIXTURE_MODE=true`).
- When running against real Gemini, watch the cost dashboard.
- The per-user-per-day budget alarm in GCP pages on cost spikes; configure your local dev project under your own user with a tight budget if you're iterating heavily.

> TODO: filled in when Track A lands the budget alarm Terraform.

---

## 8. Open items

- > TODO: backend Dockerfile build instructions, once `backend/Dockerfile` lands.
- > TODO: iOS setup section (Phase 2; Tuist project generation, generated Swift client from OpenAPI).
- > TODO: end-to-end smoke procedure once the pipeline is wired end-to-end.
- > TODO: workflow identity federation setup steps for CI, once Track A lands.
