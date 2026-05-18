"""Gemini client wrapper + Jinja2 prompt loader.

Single entry point for all LLM calls. Each pipeline stage routes through
`call_structured()` (JSON-schema-constrained output) or `call_text()` (free
text). Prompt templates live in `reasoning/prompts/*.j2` and are loaded by
template ID.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ValidationError

from .config import Settings
from .logging_setup import get_logger

log = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"

_jinja_env = Environment(
    loader=FileSystemLoader(_PROMPTS_DIR),
    undefined=StrictUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


T = TypeVar("T", bound=BaseModel)


# --- Prompt loading ---


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    template_id: str
    template_version: str
    body: str


def render_prompt(template_filename: str, **kwargs: Any) -> RenderedPrompt:
    """Render a Jinja2 template by filename (e.g. 'extraction.v1.j2').

    The template's version is parsed from the filename: `<id>.v<major>.j2`
    → template_version = "<major>.0.0". Major-version bumps are explicit
    file renames so prompt changes are visible in git diff and CI cache.
    """
    template = _jinja_env.get_template(template_filename)
    body = template.render(**kwargs)
    stem = template_filename.replace(".j2", "")  # e.g. "extraction.v1"
    parts = stem.split(".")
    template_id = parts[0]
    version_part = parts[1] if len(parts) > 1 else "v1"
    template_version = version_part.lstrip("v") + ".0.0"
    return RenderedPrompt(
        template_id=template_id,
        template_version=template_version,
        body=body,
    )


# --- Gemini client (lazy init) ---


_client = None  # type: ignore[var-annotated]


def _get_client(settings: Settings):  # noqa: ANN202 — return type depends on optional dep
    global _client
    if _client is not None:
        return _client

    from google import genai  # noqa: PLC0415

    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Put it in backend/.env.local (gitignored). "
            "Get a key at https://aistudio.google.com/apikey."
        )

    _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


# --- Call wrappers ---


@dataclass(frozen=True, slots=True)
class CallMeta:
    model_id: str
    prompt_template_version: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None


async def call_structured(
    model_id: str,
    prompt: RenderedPrompt,
    response_model: type[T],
    settings: Settings,
    *,
    response_schema: dict[str, Any] | None = None,
) -> tuple[T, CallMeta]:
    """Call Gemini with response_mime_type=application/json and parse into `response_model`.

    `response_schema` is optional but recommended — providing the JSON schema
    tightens output adherence. Pydantic models can produce a schema via
    `response_model.model_json_schema()`; we keep it as a separate arg so the
    caller can adapt the schema if Gemini's response-schema dialect rejects
    something (e.g. `$ref`, advanced composition).
    """
    client = _get_client(settings)
    started = time.perf_counter()

    config: dict[str, Any] = {"response_mime_type": "application/json"}
    if response_schema is not None:
        config["response_schema"] = response_schema

    response = client.models.generate_content(
        model=model_id,
        contents=prompt.body,
        config=config,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    raw_text = (response.text or "").strip()
    if not raw_text:
        log.error(
            "structured_call_empty_response",
            model=model_id,
            template=prompt.template_id,
            finish_reason=getattr(response.candidates[0], "finish_reason", None) if response.candidates else None,
        )
        raise RuntimeError(f"empty response from {model_id} for {prompt.template_id}")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        log.error("structured_call_invalid_json", model=model_id, template=prompt.template_id, error=str(exc), excerpt=raw_text[:200])
        raise RuntimeError(f"invalid JSON from {model_id} for {prompt.template_id}") from exc

    try:
        parsed = response_model.model_validate(payload)
    except ValidationError as exc:
        log.error("structured_call_schema_mismatch", model=model_id, template=prompt.template_id, error=str(exc))
        raise RuntimeError(
            f"schema mismatch from {model_id} for {prompt.template_id}"
        ) from exc

    usage = getattr(response, "usage_metadata", None)
    meta = CallMeta(
        model_id=model_id,
        prompt_template_version=prompt.template_version,
        latency_ms=latency_ms,
        input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
        output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
    )
    log.debug(
        "structured_call_complete",
        model=model_id,
        template=prompt.template_id,
        latency_ms=latency_ms,
        input_tokens=meta.input_tokens,
        output_tokens=meta.output_tokens,
    )
    return parsed, meta


async def call_text(
    model_id: str,
    prompt: RenderedPrompt,
    settings: Settings,
) -> tuple[str, CallMeta]:
    """Free-text generation. Used by the generation stage."""
    client = _get_client(settings)
    started = time.perf_counter()

    response = client.models.generate_content(
        model=model_id,
        contents=prompt.body,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    text = (response.text or "").strip()
    if not text:
        # Gemini's safety filters can return an empty body. Caller decides what to do.
        log.warning("text_call_empty_response", model=model_id, template=prompt.template_id)

    usage = getattr(response, "usage_metadata", None)
    meta = CallMeta(
        model_id=model_id,
        prompt_template_version=prompt.template_version,
        latency_ms=latency_ms,
        input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
        output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
    )
    return text, meta


# --- Schema utilities ---


def pydantic_to_gemini_schema(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic model JSON schema to one Gemini accepts.

    Gemini's response-schema dialect rejects `$defs`, `$ref`, `oneOf`, and a
    few other JSON-Schema features. This helper inlines `$ref` recursively
    and strips unsupported keywords. Good enough for v1; revisit if schemas
    grow more complex.
    """
    full = model_cls.model_json_schema()
    return _inline_refs(full)


def _inline_refs(node: Any, defs: dict[str, Any] | None = None) -> Any:
    if defs is None:
        defs = node.get("$defs", {}) if isinstance(node, dict) else {}

    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            # only handle local refs like "#/$defs/Name"
            if ref.startswith("#/$defs/"):
                key = ref.removeprefix("#/$defs/")
                target = defs.get(key, {})
                return _inline_refs(target, defs)
            return node
        return {
            k: _inline_refs(v, defs)
            for k, v in node.items()
            if k not in ("$defs", "$schema", "title")
        }
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    return node
