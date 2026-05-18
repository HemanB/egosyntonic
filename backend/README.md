# backend

Python 3.12 + FastAPI service running the CoT reasoning pipeline against Gemini.

## Layout

```
backend/
├── reasoning/
│   ├── main.py              # FastAPI entrypoint
│   ├── pipeline/            # extraction, retrieval, reasoning, generation, critic, state
│   ├── prompts/             # Jinja2 templates (versioned in code)
│   └── safety/              # crisis classifier, templates, post-filters
├── extraction/              # write-time feature extraction worker
├── eval/                    # golden-set harness + fixtures
├── pyproject.toml           # uv-managed
└── Dockerfile
```

## Status

Phase 1 scaffolding in progress. See top-level plan and `docs/decisions/` for the live architecture record.
