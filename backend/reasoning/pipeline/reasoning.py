"""The 4-head CoT reasoning call (idea.md §3.2).

Single Gemini Pro invocation that outputs a structured ReasoningPlan with one
section per head plus an orchestration section.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from ..config import Settings
from ..llm import call_structured, render_prompt
from ..logging_setup import get_logger
from .types import (
    DynamicalHead,
    ExtractionResult,
    NetworkHead,
    Orchestration,
    ReasoningPlan,
    ReceptivityHead,
    RetrievalBundle,
    SDTHead,
    TurnInput,
)

log = get_logger(__name__)


async def reason(
    turn: TurnInput,
    extraction: ExtractionResult,
    retrieval: RetrievalBundle,
    settings: Settings,
    *,
    state_document_summary: str = "(empty — new user or fixture mode)",
    condition_pack: str = "eating_disorder",
    user_intensity_setting: str = "moderate",
) -> ReasoningPlan:
    if settings.is_fixture or not settings.llm_is_live:
        return _fixture_plan(turn, extraction, retrieval, settings)

    retrieved_items_by_head = {
        head: [
            {
                "ref_id": item.ref_id,
                "occurred_at": item.occurred_at.isoformat(),
                "excerpt": item.excerpt,
            }
            for item in items
        ]
        for head, items in retrieval.items_by_head.items()
    }

    prompt = render_prompt(
        "reasoning.v1.j2",
        utterance_text=turn.utterance_text,
        extraction_json=extraction.model_dump_json(indent=2),
        state_document_summary=state_document_summary,
        retrieved_items_by_head=retrieved_items_by_head,
        condition_pack=condition_pack,
        user_intensity_setting=user_intensity_setting,
        current_datetime_iso=datetime.now(UTC).isoformat(),
    )

    try:
        parsed, meta = await call_structured(
            settings.model_reasoning,
            prompt,
            ReasoningPlan,
            settings,
        )
    except Exception:
        log.exception("reasoning_live_call_failed_falling_back_to_fixture")
        return _fixture_plan(turn, extraction, retrieval, settings)

    parsed = parsed.model_copy(update={
        "turn_id": str(uuid.uuid4()),
        "produced_at": datetime.now(UTC),
        "model_id": meta.model_id,
        "prompt_template_version": meta.prompt_template_version,
    })

    # Enforce the receptivity gate (idea.md §3.2 first paragraph). Even if the
    # model wrote a higher intensity, low receptivity caps it here.
    parsed = _enforce_receptivity_gate(parsed)

    log.debug(
        "reasoning_complete",
        turn_id=parsed.turn_id,
        receptivity=parsed.receptivity.score,
        intensity=parsed.orchestration.intervention_intensity,
        safety_flags=parsed.orchestration.safety_flags,
        latency_ms=meta.latency_ms,
    )
    return parsed


_INTENSITY_LADDER = {
    "none": 0,
    "presence": 1,
    "light_reflection": 2,
    "pattern_surfacing": 3,
    "direct_invitation": 4,
}


def _enforce_receptivity_gate(plan: ReasoningPlan) -> ReasoningPlan:
    """Cap intervention intensity by receptivity score.

    score <= 0.4 → cap at presence.
    score <= 0.6 → cap at light_reflection.
    Anything above → no cap.
    """
    cap: str | None = None
    if plan.receptivity.score <= 0.4 or plan.receptivity.categorical_state in (
        "active_distress",
        "crisis",
        "dissociated_or_disengaged",
    ):
        cap = "presence"
    elif plan.receptivity.score <= 0.6:
        cap = "light_reflection"

    if cap is None:
        return plan

    if _INTENSITY_LADDER[plan.orchestration.intervention_intensity] > _INTENSITY_LADDER[cap]:
        return plan.model_copy(update={
            "orchestration": plan.orchestration.model_copy(update={"intervention_intensity": cap}),
        })
    return plan


def _fixture_plan(
    turn: TurnInput,
    extraction: ExtractionResult,
    retrieval: RetrievalBundle,
    settings: Settings,
) -> ReasoningPlan:
    _ = turn, extraction, retrieval
    return ReasoningPlan(
        turn_id=str(uuid.uuid4()),
        produced_at=datetime.now(UTC),
        model_id=f"fixture::{settings.model_reasoning}",
        prompt_template_version="fixture-0",
        receptivity=ReceptivityHead(
            score=0.3,
            categorical_state="open_to_reflection",
            actionability=False,
            rationale="Fixture stub: defaulting to low receptivity to keep generation conservative.",
        ),
        dynamical_state=DynamicalHead(
            current_loop_id=None,
            stability=0.5,
            posture="support",
            rationale="Fixture stub: no loop identified.",
        ),
        network=NetworkHead(
            active_nodes=[],
            candidate_patterns=[],
            rationale="Fixture stub: no active nodes.",
        ),
        sdt=SDTHead(
            thwarted_in=[],
            framing_language_hint=None,
            rationale="Fixture stub: no SDT inference.",
        ),
        orchestration=Orchestration(
            intervention_intensity="presence",
            safety_flags=[],
        ),
    )


def summarize_state(state: dict[str, Any]) -> str:
    """Produce a human-readable plain-text summary of a state document.

    The reasoning prompt expects this as `state_document_summary` — NOT the
    raw JSON. Keeping summarization here (not in the prompt) lets us control
    exactly what the model sees about each user.
    """
    lines: list[str] = []
    cc = state.get("stated_chief_complaint", {})
    cc_text = (cc.get("text") or "").strip()
    lines.append(f"Stated chief complaint: {cc_text or '(not yet stated)'}")

    cond = state.get("condition_pack", "eating_disorder")
    lines.append(f"Condition pack: {cond}")

    density = state.get("network_state", {}).get("data_density", {})
    lines.append(
        f"Data density: {density.get('utterance_count', 0)} utterances, "
        f"{density.get('weeks_of_use', 0)} weeks of use"
    )

    intake = state.get("intake_completed_at")
    lines.append(f"Intake completed: {intake or 'not yet'}")

    receptivity = state.get("receptivity_history") or []
    if receptivity:
        recent = receptivity[-3:]
        avg = sum(r.get("score", 0) for r in recent) / len(recent)
        lines.append(f"Recent receptivity (last {len(recent)} turns): avg {avg:.2f}")

    active_flags = state.get("safety_state", {}).get("active_flags") or []
    if active_flags:
        lines.append(f"Active safety flags: {', '.join(active_flags)}")

    prefs = state.get("user_preferences", {})
    lines.append(f"Insight intensity setting: {prefs.get('insight_intensity', 'moderate')}")

    return "\n".join(lines)
