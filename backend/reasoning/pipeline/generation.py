"""Response generation conditioned on the reasoning plan (idea.md §3.3).

Generation receives the plan and produces user-facing text. Writes in the
user's register, references surfaced memories naturally, avoids clinical
jargon. When a safety template is provided, it is used VERBATIM.
"""

from __future__ import annotations

from ..config import Settings
from ..llm import call_text, render_prompt
from ..logging_setup import get_logger
from .types import GenerationOutput, ReasoningPlan, TurnInput

log = get_logger(__name__)


PRESENCE_FALLBACK = "Thanks for telling me. I'm here and I'm listening."


async def generate(
    turn: TurnInput,
    plan: ReasoningPlan,
    settings: Settings,
    *,
    critic_notes: str | None = None,
    safety_template: str | None = None,
    user_register_excerpts: list[str] | None = None,
    surfaced_memories: list[dict[str, str]] | None = None,
) -> GenerationOutput:
    # Safety-template short-circuit: skip the LLM entirely. The template is
    # the response, verbatim. Critic still runs to verify it survived intact.
    if safety_template:
        return GenerationOutput(
            response_text=safety_template,
            surfaced_memory_ref_ids=[],
        )

    if settings.is_fixture or not settings.llm_is_live:
        return _fixture_generation(turn, plan)

    prompt = render_prompt(
        "generation.v1.j2",
        utterance_text=turn.utterance_text,
        plan_json=plan.model_dump_json(indent=2),
        user_register_excerpts=user_register_excerpts or plan.orchestration.user_register_excerpts,
        surfaced_memories=surfaced_memories or [],
        safety_template="",
        critic_notes=critic_notes or "",
    )

    try:
        text, meta = await call_text(settings.model_generation, prompt, settings)
    except Exception:
        log.exception("generation_live_call_failed_falling_back_to_presence")
        return GenerationOutput(response_text=PRESENCE_FALLBACK, surfaced_memory_ref_ids=[])

    if not text:
        # Empty body usually means the safety filter blocked. Fall back to
        # presence to keep the user-facing experience graceful; the critic
        # will register the issue.
        log.warning("generation_returned_empty_body")
        return GenerationOutput(response_text=PRESENCE_FALLBACK, surfaced_memory_ref_ids=[])

    log.debug("generation_complete", chars=len(text), latency_ms=meta.latency_ms)
    return GenerationOutput(
        response_text=text,
        surfaced_memory_ref_ids=plan.orchestration.memory_reference_ids,
    )


def _fixture_generation(turn: TurnInput, plan: ReasoningPlan) -> GenerationOutput:
    _ = turn
    if plan.orchestration.safety_flags:
        return GenerationOutput(
            response_text="[safety-template-placeholder]",
            surfaced_memory_ref_ids=[],
        )
    return GenerationOutput(
        response_text=PRESENCE_FALLBACK,
        surfaced_memory_ref_ids=[],
    )
