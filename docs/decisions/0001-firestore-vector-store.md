# ADR-0001: Firestore vector search (not Vertex AI Vector Search)

- Status: Accepted
- Date: 2026-05-19
- Supersedes: §"Vector Store" of the tech-stack plan (`~/.claude/plans/wondrous-stirring-brooks.md`), which named Vertex AI Vector Search.

## Context

The tech-stack plan and the Track A Terraform (`infra/vertex.tf`) provisioned Vertex AI Vector Search for the utterance memory described in `docs/idea.md §4.1` — a 768-dim cosine index, streaming updates, public endpoint, with a deployed index pinned to `min_replica_count = 1`.

A deployed Vertex AI Vector Search index bills per node-hour for the endpoint compute, *regardless of query volume*. A single small-replica deployment at `us-central1` runs roughly **$150–360/mo idle**. Project traffic in Phase 1 will be tens of queries/day at most; the constant-on cost dominates by orders of magnitude.

Three realistic alternatives were considered:

1. **Firestore vector search.** Native vector field on documents + `FindNearest()` queries. Pay-per-operation (~$0.06 per 100K reads), $0 idle cost. Vector index dimension cap is currently 2048; we use 768. Performance: sub-100ms for collections under a few million vectors. Already in the stack — Firestore is provisioned for state/audit storage regardless.

2. **Cloud SQL with pgvector.** Minimum `db-f1-micro` is ~$10/mo. Mature tooling, but adds an unrelated database to operate and a network hop the rest of the stack doesn't need.

3. **Skip retrieval entirely for Phase 1.** Fixture mode is the default for local dev anyway (`docs/setup.md §3.4`); real retrieval isn't blocking anything. Defer the decision until traffic shape is known.

A related decision: embeddings.

- **Vertex AI text-embedding-005** (the original plan choice) — requires `aiplatform.googleapis.com` enabled and a `roles/aiplatform.user` IAM grant on the runtime SA. Pay-per-call; effectively cents/month at Phase 1 scale.
- **Gemini API `gemini-embedding-001`** — uses the AI Studio API key we already manage in Secret Manager. No additional IAM. Same cost order.

## Decision

1. **Firestore vector search** replaces Vertex AI Vector Search for the utterance retrieval path. The Terraform `infra/vertex.tf` is deleted; a `google_firestore_index` with `vector_config` is added in `infra/firestore.tf` to back the `utterances` collection.

2. **Gemini API for embeddings** replaces Vertex AI embeddings. `aiplatform.googleapis.com` is removed from the required-services list and the runtime SA's `roles/aiplatform.user` binding is removed. Embedding calls go to `generativelanguage.googleapis.com` using `GEMINI_API_KEY` from Secret Manager — the same auth path as the rest of the LLM pipeline.

3. The embedding dimension stays at 768 to keep the vector index lean and well under Firestore's current cap. `gemini-embedding-001` supports Matryoshka truncation to 768.

## Consequences

**Positive**

- Idle infra cost drops from ~$150–360/mo to ~$0. Vector search bills only when used.
- One fewer GCP API surface (no Vertex AI). IAM is simpler; the runtime SA needs only Firestore + Cloud Tasks + Trace + Logging + secret access.
- The embedding and chat-completion paths share a single auth — `GEMINI_API_KEY` — making local-dev/prod parity tighter and onboarding shorter.
- No 30-minute initial-provisioning wait. Firestore indexes build in seconds to minutes.

**Negative**

- Firestore vector search scales to a few million vectors per collection; Vertex Vector Search scales to billions. If utterance volume grows past that, we'll migrate — but that's a problem at a scale this project may never reach.
- Fewer ranking features than Vertex (no hybrid sparse-dense, no learned-quantization tuning). Cosine-distance nearest-neighbor is the only option, which suffices for `docs/idea.md §4.1`'s use case.
- One vendor risk consolidation: both LLM inference and embeddings now flow through the same AI Studio API key. Rotation incidents affect both. Mitigation: the key is in Secret Manager with versioning.

**Neutral**

- The `live_llm` runtime mode (real Gemini, in-memory retrieval) is unaffected; it never touched Vertex.
- Fixture mode is unaffected.

## Implementation notes

Concrete file changes are tracked in the commit that lands alongside this ADR. The shape:

- `infra/vertex.tf` — deleted.
- `infra/firestore.tf` — `google_firestore_index` added for the `utterances` collection with `(user_id ASC, embedding vector_config{dimension=768, flat{}})`.
- `infra/services.tf` — `aiplatform.googleapis.com` removed.
- `infra/iam.tf` — `runtime_aiplatform` binding removed.
- `infra/cloudrun.tf` — `VERTEX_VECTOR_INDEX_*` env vars removed; `VERTEX_REGION` removed (no Vertex client to configure).
- `infra/outputs.tf` — three vertex outputs removed.
- `infra/variables.tf` — `vector_index_dimensions` retained (still used for the Firestore index).
- `backend/reasoning/config.py` — `vertex_vector_index_*` and `vertex_region` settings removed.
- `backend/reasoning/pipeline/retrieval.py` — module docstring updated; live-mode TODO retargeted at the Firestore client.
- `backend/.env.example` — VERTEX section replaced with a one-line note that retrieval reads from Firestore in live mode.
- `docs/setup.md` — env-var TODO and §3.6 "What does not run locally" updated.
