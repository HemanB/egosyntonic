# backend

Python 3.12 + FastAPI service running the CoT reasoning pipeline against Gemini.

## Layout

```
backend/
├── reasoning/
│   ├── main.py              # FastAPI app factory + ASGI entry
│   ├── config.py            # Pydantic Settings, env-var loaded
│   ├── auth.py              # Firebase ID-token verification + dev bypass
│   ├── logging_setup.py     # structlog → JSON to stdout (Cloud Logging picks up)
│   ├── telemetry.py         # OpenTelemetry → Cloud Trace (opt-in)
│   ├── routes/              # FastAPI routers (health, turn)
│   ├── pipeline/            # extraction → retrieval → reasoning → generation → critic → state
│   ├── prompts/             # Jinja2 templates (Track D)
│   └── safety/              # crisis classifier + templates (Track E)
├── tests/
├── pyproject.toml           # uv-managed
├── Dockerfile
└── .env.example
```

## Local dev

```sh
# One-time
cd backend
uv sync

# Run in fixture mode (no external calls)
cp .env.example .env
uv run uvicorn reasoning.main:app --reload --port 8080

# Smoke test
curl http://localhost:8080/health
curl -X POST http://localhost:8080/turn \
  -H "content-type: application/json" \
  -d '{"user_id":"x","session_id":"s1","utterance_text":"hello"}'

# Tests + lints + types
uv run pytest
uv run ruff check
uv run pyright
```

## Runtime modes

Toggled by `EGOSYN_RUNTIME_MODE`:

- **`fixture`** (default): no external calls, deterministic stubs. Tests + CI run here.
- **`live_llm`**: real Gemini calls; retrieval + state stay in-memory. No GCP needed. **This is the mode for testing CoT quality before the GCP project lands.** Just put `GEMINI_API_KEY=...` and `EGOSYN_RUNTIME_MODE=live_llm` in `.env.local`.
- **`live`**: full GCP — Gemini + Vertex Vector Search + Firestore. Requires `gcloud auth application-default login`, a project with billing, and a populated Secret Manager entry.

`.env.local` is loaded after `.env` with higher precedence — keep personal overrides (API keys, project IDs) there.

## Running a live-LLM smoke turn

```sh
# .env.local must contain:
#   EGOSYN_RUNTIME_MODE=live_llm
#   GEMINI_API_KEY=<your rotated key>

cd backend
uv run python -m reasoning.eval.smoke_live "I'm not sure how to feel about today."
uv run python -m reasoning.eval.smoke_live "How many calories should I eat?"  # expect safety template
uv run python -m reasoning.eval.smoke_live "I want to die." --json            # full plan + critic
```

This is the fastest way to hand-validate the prompts before the eval harness runs against the full golden fixture set.

## Status

Phase 1 scaffolding landed (Track B). The pipeline modules are stubs in fixture
mode and `NotImplementedError` in live mode — they'll be filled in by Tracks D
(prompts) and E (safety), then wired together (pipeline-wiring task).
