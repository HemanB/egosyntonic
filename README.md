# egosyntonic

A wellness-positioned reflective journaling app with longitudinal therapeutic memory, designed around the navigation of egosyntonic content in mental-health conditions where motivational-interviewing approaches benefit from delving into the function the symptoms serve.

> **Wellness-positioned, not a digital therapeutic.** Does not diagnose, does not claim to treat. See [`docs/idea.md`](docs/idea.md) for the canonical product spec.

---

## Monorepo layout

```
egosyntonic/
├── backend/        # Python 3.12 + FastAPI on Cloud Run — the CoT reasoning pipeline
├── shared/         # JSON Schemas + controlled vocabularies (contract surface)
├── infra/          # Terraform: GCP project, Cloud Run, Firestore, Vertex AI, IAM
├── docs/           # Design docs, ADRs, safety templates, policy drafts
└── app/            # SwiftUI iOS client — deferred to Phase 2
```

## Phasing

- **Phase 1 (active)**: CoT reasoning backend. Pipeline: feature extraction → multi-head retrieval → 4-head reasoning (receptivity / dynamical / network / SDT) → generation → critic → state update. Exit criteria in the approved plan.
- **Phase 2**: SwiftUI iOS app, gated on Phase 1 exit criteria.
- **Phase 3**: Closed beta with clinical advisor sign-off.

No iOS code is written in Phase 1. The `app/` directory exists as a placeholder.

## Stack

| Layer | Choice |
|---|---|
| Backend runtime | Python 3.12 on Cloud Run |
| HTTP framework | FastAPI |
| LLM provider | Google Gemini 2.5 Pro (reasoning, critic) + Flash (extraction, generation) |
| Vector store | Vertex AI Vector Search |
| State storage | Firestore |
| Auth | Firebase Auth (Sign in with Apple) |
| Observability | Cloud Logging + Cloud Trace + OpenTelemetry |
| IaC | Terraform |
| CI | GitHub Actions |
| Client (Phase 2) | SwiftUI iOS 17+, native |

All PHI-adjacent services are BAA-eligible — architecture is HIPAA-ready though v1 is wellness-positioned.

## Development

> Setup docs are written as Phase 1 lands. The bootstrap is non-trivial (GCP project, Firebase link, Vertex AI Vector Search index, Workload Identity Federation for CI). Walk-through is in `docs/setup.md` (TBA).

## Safety

The reasoning pipeline runs a fixed safety architecture (`docs/idea.md` §9). Means-restriction language, ED-specific numerical content, and crisis signals are handled by deterministic templates layered on top of LLM-level instruction. Templates are clinical-advisor-reviewed before any external user touches the system.

If you or someone you know is in crisis:
- **988** Suicide & Crisis Lifeline (US, call or text)
- **Crisis Text Line**: text HOME to 741741 (US/UK/CA)

## License

See [LICENSE](LICENSE).
