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
    free_text_mode: bool = False,
) -> tuple[T, CallMeta]:
    """Call Gemini and parse the response into `response_model`.

    Three constraint modes:

    1. `response_schema` set: strictest. Gemini's structured-output mode with
       a JSON schema. Maximum adherence; minimum reasoning flexibility. The
       model becomes constraint-fitting.
    2. Default (response_mime_type=application/json, no schema): the model
       emits valid JSON but is otherwise free. We use this for extraction
       and critic — cases where output structure is simple.
    3. `free_text_mode=True`: NO mime type, NO schema. The model emits prose
       freely; we extract the first balanced JSON object out of the response
       via a brace counter. This is for the reasoning call, where ADR-0002
       eval data showed the model collapses to constant outputs even under
       (2) — apparently any JSON-mode hint is enough to bias toward
       defensive constants. Free-text mode trades parsing fragility for
       reasoning elasticity.
    """
    client = _get_client(settings)
    started = time.perf_counter()

    if free_text_mode:
        config: dict[str, Any] = {}
    else:
        config = {"response_mime_type": "application/json"}
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

    if free_text_mode:
        # Dump full raw response for diagnosis — invaluable when the model
        # emits prose + JSON in unexpected shapes. Stays gitignored.
        import os as _os  # noqa: PLC0415
        from pathlib import Path as _Path  # noqa: PLC0415
        from datetime import datetime as _datetime  # noqa: PLC0415
        diag_dir = _Path(_os.environ.get("EGOSYN_LLM_RAW_DIR", "/tmp/egosyn-llm-raw"))
        diag_dir.mkdir(parents=True, exist_ok=True)
        ts_id = _datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
        (diag_dir / f"{ts_id}_{prompt.template_id}.txt").write_text(raw_text, encoding="utf-8")

        json_str = _extract_first_json_object(raw_text)
        if json_str is None:
            log.error("free_text_no_json_found", model=model_id, template=prompt.template_id, excerpt=raw_text[:300])
            raise RuntimeError(f"no JSON object found in free-text response from {model_id} for {prompt.template_id}")
        raw_text = json_str

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        log.error("structured_call_invalid_json", model=model_id, template=prompt.template_id, error=str(exc), excerpt=raw_text[:200])
        raise RuntimeError(f"invalid JSON from {model_id} for {prompt.template_id}") from exc

    # Permissive normalization: Gemini emits the head dicts under varying
    # wrapper keys ("plan", "heads", "sections", etc.) and sometimes
    # partially — e.g. heads nested but orchestration at top level. Walk
    # one level deep and lift any sub-dict whose keys overlap with the
    # canonical plan top-level keys. Also apply field-name aliases on
    # confirmed observed variations.
    if isinstance(payload, dict):
        _lift_plan_wrappers(payload)
        _normalize_plan_field_aliases(payload)

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


_PLAN_HEAD_KEYS = {"receptivity", "dynamical_state", "network", "sdt", "orchestration"}


def _lift_plan_wrappers(payload: dict[str, Any]) -> None:
    """Lift head dicts out of any wrapper key into the top-level payload.

    Gemini in free-text mode wraps the head dicts under varying keys
    (`plan`, `heads`, `sections`) and sometimes prefixes them
    (`head_receptivity`). This walks one level deep, strips `head_` prefixes,
    and lifts any sub-dict whose keys overlap with canonical head names.
    Mutates payload in place. Only lifts; never demotes.
    """
    # First pass: strip `head_` prefix on top-level keys.
    for old_key in list(payload.keys()):
        if old_key.startswith("head_"):
            new_key = old_key.removeprefix("head_")
            if new_key in _PLAN_HEAD_KEYS and new_key not in payload:
                payload[new_key] = payload.pop(old_key)

    # Second pass: lift wrappers.
    to_lift: list[str] = []
    for key, value in payload.items():
        if key in _PLAN_HEAD_KEYS:
            continue
        if not isinstance(value, dict):
            continue
        # Also strip head_ prefix on the sub-dict's keys to detect overlap
        sub_keys = {k.removeprefix("head_") if k.startswith("head_") else k for k in value.keys()}
        if sub_keys & _PLAN_HEAD_KEYS:
            to_lift.append(key)
    for key in to_lift:
        inner = payload.pop(key)
        for sub_key in list(inner.keys()):
            canonical = sub_key.removeprefix("head_") if sub_key.startswith("head_") else sub_key
            if canonical in _PLAN_HEAD_KEYS and canonical not in payload:
                payload[canonical] = inner[sub_key]


def _normalize_plan_field_aliases(payload: dict[str, Any]) -> None:
    """Coerce common field-name variations the model emits into canonical names.

    Mutates payload in place. Each rule was added in response to a real eval
    failure; do not generalize without evidence of need. The model is
    creative — expect this list to grow.
    """
    # --- receptivity ---
    recept = payload.get("receptivity")
    if isinstance(recept, dict):
        if "categorical_state" not in recept and "state" in recept:
            recept["categorical_state"] = recept.pop("state")
        # actionability has been seen as: `actionability`, `actionability_granted`,
        # `is_actionable`, plus a separate `actionability_confidence` numeric field.
        # Truth signal is whichever boolean field is present.
        if "actionability" not in recept:
            for alt in ("actionability_granted", "is_actionable", "can_act_now"):
                if alt in recept:
                    val = recept.pop(alt)
                    if isinstance(val, bool):
                        recept["actionability"] = val
                    elif isinstance(val, (int, float)):
                        recept["actionability"] = bool(val)
                    break
        # Drop confidence-like fields that aren't in the schema (don't trip extra="forbid"; we use ignore by default but keep clean)
        recept.pop("actionability_confidence", None)

    # --- dynamical_state ---
    dyn = payload.get("dynamical_state")
    if isinstance(dyn, dict):
        if "current_loop_id" not in dyn and "loop_id" in dyn:
            dyn["current_loop_id"] = dyn.pop("loop_id")
        if "current_loop_label" not in dyn and "loop_label" in dyn:
            dyn["current_loop_label"] = dyn.pop("loop_label")

    # --- network ---
    # Two observed variations: `activation` (per old plan.schema.json) vs canonical
    # `evidence_strength`; `id` (terse) vs canonical `node_id`.
    # candidate_patterns: `type` vs canonical `pattern_type`.
    net = payload.get("network")
    if isinstance(net, dict):
        for node in net.get("active_nodes") or []:
            if not isinstance(node, dict):
                continue
            if "evidence_strength" not in node and "activation" in node:
                node["evidence_strength"] = node.pop("activation")
            if "node_id" not in node and "id" in node:
                node["node_id"] = node.pop("id")
        for cp in net.get("candidate_patterns") or []:
            if not isinstance(cp, dict):
                continue
            if "pattern_type" not in cp and "type" in cp:
                cp["pattern_type"] = cp.pop("type")
            # Some captures put evidence under `evidence` or `involved_nodes`
            # instead of `evidence_utterance_ids`. Drop to avoid extras-tripping.
            cp.pop("evidence", None)
            cp.pop("involved_nodes", None)
            cp.pop("id", None)

    # --- sdt ---
    # thwarted_in has been seen as both dicts {need, domain} and lists [need, domain].
    sdt = payload.get("sdt")
    if isinstance(sdt, dict):
        thwarted = sdt.get("thwarted_in")
        if isinstance(thwarted, list):
            normalized: list[dict[str, Any]] = []
            for item in thwarted:
                if isinstance(item, dict):
                    normalized.append(item)
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    normalized.append({"need": item[0], "domain": item[1]})
                # else: skip unrecognized shape
            sdt["thwarted_in"] = normalized

    # --- orchestration ---
    # safety_flags has been seen as: list[str] (canonical), single str, dict-with-flags-key,
    # or null. Coerce to list[str].
    orch = payload.get("orchestration")
    if isinstance(orch, dict):
        sf = orch.get("safety_flags")
        if sf is None:
            orch["safety_flags"] = []
        elif isinstance(sf, str):
            orch["safety_flags"] = [sf] if sf else []
        elif isinstance(sf, dict):
            # E.g. {"active_suicidal_ideation": true, ...}
            orch["safety_flags"] = [k for k, v in sf.items() if v]


def _extract_first_json_object(text: str) -> str | None:
    """Extract the first balanced top-level JSON object from a free-text response.

    Walks character-by-character counting brace depth, respecting strings and
    escaped quotes. Returns the substring from the first `{` to its matching
    `}`, or None if not found. Tolerates surrounding prose, markdown fences,
    or "Here's the plan:" preambles that Gemini sometimes emits.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


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
