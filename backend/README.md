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

- **`fixture`** (default for dev + CI): no external calls, deterministic stubs. Pipeline wiring is testable without a Gemini key or a GCP project.
- **`live`**: real Gemini + Vertex + Firestore. Requires `gcloud auth application-default login` and a project with billing enabled.

Toggled by `EGOSYN_RUNTIME_MODE`.

## Status

Phase 1 scaffolding landed (Track B). The pipeline modules are stubs in fixture
mode and `NotImplementedError` in live mode — they'll be filled in by Tracks D
(prompts) and E (safety), then wired together (pipeline-wiring task).
