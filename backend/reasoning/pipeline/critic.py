"""Critic layer (idea.md §3.4).

Separate LLM call that audits the generated response against the plan and a
fixed set of failure modes. Triggers regeneration when flags fire.
"""

from __future__ import annotations

from ..config import Settings
from ..llm import call_structured, render_prompt
from ..logging_setup import get_logger
from ..safety import check_response_safety
from .types import (
    CriticVerdict,
    GenerationOutput,
    ReasoningPlan,
    TurnInput,
)

log = get_logger(__name__)


async def audit(
    turn: TurnInput,
    plan: ReasoningPlan,
    generation: GenerationOutput,
    settings: Settings,
) -> CriticVerdict:
    # Deterministic post-filter ALWAYS runs first — belt and suspenders per
    # idea.md §9 implementation note. If it fires, we fail without spending
    # the LLM call.
    post = check_response_safety(generation.response_text)
    if not post.passed:
        return CriticVerdict(
            passed=False,
            flags=["missed_safety_signal"],
            notes=post.notes,
        )

    if settings.is_fixture or not settings.llm_is_live:
        return CriticVerdict(passed=True, flags=[], notes="fixture-mode auto-pass")

    prompt = render_prompt(
        "critic.v1.j2",
        original_utterance=turn.utterance_text,
        plan_json=plan.model_dump_json(indent=2),
        generated_response_text=generation.response_text,
    )

    try:
        verdict, meta = await call_structured(
            settings.model_critic,
            prompt,
            CriticVerdict,
            settings,
        )
    except Exception:
        log.exception("critic_live_call_failed_passing_through")
        # Critic failure should NOT block the user. Pass-through with a note.
        return CriticVerdict(passed=True, flags=[], notes="critic_call_failed; passed through")

    log.debug(
        "critic_complete",
        passed=verdict.passed,
        flags=verdict.flags,
        latency_ms=meta.latency_ms,
    )
    return verdict
