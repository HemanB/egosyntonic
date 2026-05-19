"""Pipeline orchestrator. Runs a single user turn through:

    safety classifier
        │
        ├─► fires? ──► safety template (verbatim) → critic → state
        │
        └─► clean ──► extraction → retrieval → reasoning → generation → critic → state

idea.md §3.1, §9.1. In-process, hardcoded DAG. No learned routing in v1.
"""

from __future__ import annotations

import asyncio
import time

from ..config import Settings
from ..logging_setup import get_logger
from ..safety import (
    SafetyCategory,
    SafetyClassification,
    classify_safety_signals,
    get_template_for_classification,
)
from . import critic, extraction, generation, reasoning, retrieval, state
from .reasoning import summarize_state
from .types import (
    CriticVerdict,
    DynamicalHead,
    ExtractionResult,
    GenerationOutput,
    NetworkHead,
    Orchestration,
    ReasoningPlan,
    ReceptivityHead,
    SafetyFlag,
    SDTHead,
    TurnInput,
    TurnResult,
)

log = get_logger(__name__)

MAX_REGENERATIONS = 2


# Map safety-classifier categories → plan safety_flags so the plan is
# consistent with what fired pre-pipeline.
_CATEGORY_TO_FLAG: dict[SafetyCategory, SafetyFlag | None] = {
    SafetyCategory.ACTIVE_SUICIDAL_IDEATION: "active_suicidal_ideation",
    SafetyCategory.SELF_HARM_INTENT: "self_harm_intent",
    SafetyCategory.MEDICAL_ACUTE: "medical_instability",
    SafetyCategory.ASKING_FOR_METHODS: "asking_for_methods",
    SafetyCategory.ASKING_FOR_NUMBERS: "asking_for_numbers",
    SafetyCategory.USER_REQUESTED_RESOURCES: None,  # template, but not a "flag" per se
}


async def run_turn(turn: TurnInput, settings: Settings) -> TurnResult:
    started = time.perf_counter()
    log.info("turn_started", user_id=turn.user_id, session_id=turn.session_id)

    # --- Pre-pipeline safety classifier ---
    safety = await classify_safety_signals(turn.utterance_text, settings)
    if safety.any_fired:
        log.warning(
            "safety_classifier_fired",
            primary=safety.primary.value,
            all_detected=[c.value for c in safety.all_detected],
        )
        return await _run_safety_short_circuit(turn, safety, settings, started)

    # --- Standard pipeline path ---
    current_state = await state.read_state(turn.user_id, settings)
    state_summary = summarize_state(current_state)
    condition_pack = current_state.get("condition_pack", "eating_disorder")
    intensity_setting = (
        current_state.get("user_preferences", {}).get("insight_intensity", "moderate")
    )

    extracted = await extraction.extract_features(
        turn,
        settings,
        condition_pack=condition_pack,
    )
    log.debug("extraction_complete", utterance_id=extracted.utterance_id)

    retrieved = await retrieval.retrieve_for_all_heads(turn, extracted, settings)
    log.debug("retrieval_complete", retrieved_count=len(retrieved.all_items()))

    plan = await reasoning.reason(
        turn,
        extracted,
        retrieved,
        settings,
        state_document_summary=state_summary,
        condition_pack=condition_pack,
        user_intensity_setting=intensity_setting,
    )
    log.debug(
        "reasoning_complete",
        turn_id=plan.turn_id,
        receptivity=plan.receptivity.score,
        posture=plan.dynamical_state.posture,
        intensity=plan.orchestration.intervention_intensity,
        safety_flags=plan.orchestration.safety_flags,
    )

    # If the reasoning step itself surfaced safety flags (LLM caught something
    # the deterministic classifier missed), short-circuit to the matching
    # template instead of running generation.
    if plan.orchestration.safety_flags:
        return await _run_post_reasoning_safety_short_circuit(turn, plan, settings, started)

    generated, verdict, attempts = await _generate_with_critic_loop(turn, plan, settings)

    latency_ms = int((time.perf_counter() - started) * 1000)

    # State update fires-and-forgets — does not block the response.
    asyncio.create_task(_post_turn_state_update(turn, plan, generated, verdict, settings))

    log.info(
        "turn_completed",
        user_id=turn.user_id,
        turn_id=plan.turn_id,
        latency_ms=latency_ms,
        regenerations=attempts,
        used_safety_template=False,
    )

    return TurnResult(
        turn_id=plan.turn_id,
        response_text=generated.response_text,
        plan=plan,
        critic=verdict,
        regeneration_attempts=attempts,
        used_safety_template=False,
        latency_ms=latency_ms,
    )


async def _run_safety_short_circuit(
    turn: TurnInput,
    safety: SafetyClassification,
    settings: Settings,
    started: float,
) -> TurnResult:
    template = get_template_for_classification(safety.primary)
    if template is None:
        log.error("no_template_for_safety_category", category=safety.primary.value)
        return _crash_safe_response(turn, started)

    # Synthesize a minimal plan describing what happened, for the critic +
    # state update + downstream eval. No reasoning call was made.
    flag = _CATEGORY_TO_FLAG.get(safety.primary)
    plan = _safety_synthetic_plan(turn, safety, flag)

    generated = GenerationOutput(
        response_text=template.body,
        surfaced_memory_ref_ids=[],
    )
    verdict = await critic.audit(turn, plan, generated, settings, used_safety_template=True)

    latency_ms = int((time.perf_counter() - started) * 1000)
    asyncio.create_task(_post_turn_state_update(turn, plan, generated, verdict, settings))

    log.info(
        "turn_completed_via_safety_template",
        user_id=turn.user_id,
        turn_id=plan.turn_id,
        latency_ms=latency_ms,
        template_id=template.template_id,
    )
    return TurnResult(
        turn_id=plan.turn_id,
        response_text=template.body,
        plan=plan,
        critic=verdict,
        regeneration_attempts=0,
        used_safety_template=True,
        latency_ms=latency_ms,
    )


async def _run_post_reasoning_safety_short_circuit(
    turn: TurnInput,
    plan: ReasoningPlan,
    settings: Settings,
    started: float,
) -> TurnResult:
    # Map the highest-priority flag the LLM raised to a template
    priority_order: list[SafetyFlag] = [
        "active_suicidal_ideation",
        "self_harm_intent",
        "medical_instability",
        "asking_for_methods",
        "asking_for_numbers",
        "egosyntonic_collusion_risk",
        "boundary_disclosure_needed",
    ]
    flag_to_cat: dict[str, SafetyCategory] = {
        "active_suicidal_ideation": SafetyCategory.ACTIVE_SUICIDAL_IDEATION,
        "self_harm_intent": SafetyCategory.SELF_HARM_INTENT,
        "medical_instability": SafetyCategory.MEDICAL_ACUTE,
        "asking_for_methods": SafetyCategory.ASKING_FOR_METHODS,
        "asking_for_numbers": SafetyCategory.ASKING_FOR_NUMBERS,
    }

    flag = next((f for f in priority_order if f in plan.orchestration.safety_flags), None)
    category = flag_to_cat.get(flag) if flag else None
    template = get_template_for_classification(category) if category else None

    if template is None:
        # Reasoning surfaced a flag (e.g. egosyntonic_collusion_risk) that
        # doesn't have its own short-circuit template — fall through to
        # generation, which sees the flag in the plan and adjusts.
        log.debug("safety_flag_without_short_circuit", flag=flag)
        generated, verdict, attempts = await _generate_with_critic_loop(turn, plan, settings)
        latency_ms = int((time.perf_counter() - started) * 1000)
        asyncio.create_task(_post_turn_state_update(turn, plan, generated, verdict, settings))
        return TurnResult(
            turn_id=plan.turn_id,
            response_text=generated.response_text,
            plan=plan,
            critic=verdict,
            regeneration_attempts=attempts,
            used_safety_template=False,
            latency_ms=latency_ms,
        )

    generated = GenerationOutput(response_text=template.body, surfaced_memory_ref_ids=[])
    verdict = await critic.audit(turn, plan, generated, settings, used_safety_template=True)
    latency_ms = int((time.perf_counter() - started) * 1000)
    asyncio.create_task(_post_turn_state_update(turn, plan, generated, verdict, settings))
    return TurnResult(
        turn_id=plan.turn_id,
        response_text=template.body,
        plan=plan,
        critic=verdict,
        regeneration_attempts=0,
        used_safety_template=True,
        latency_ms=latency_ms,
    )


def _safety_synthetic_plan(
    turn: TurnInput,
    safety: SafetyClassification,
    flag: SafetyFlag | None,
) -> ReasoningPlan:
    """Plan stamped on safety-short-circuit turns. Reasoning wasn't run."""
    import uuid as _uuid
    from datetime import UTC as _UTC, datetime as _datetime

    safety_flags: list[SafetyFlag] = [flag] if flag else []
    return ReasoningPlan(
        turn_id=str(_uuid.uuid4()),
        produced_at=_datetime.now(_UTC),
        model_id="safety-classifier",
        prompt_template_version=safety.model_id,
        receptivity=ReceptivityHead(
            score=0.0,
            categorical_state="crisis" if flag in ("active_suicidal_ideation", "self_harm_intent") else "active_distress",
            actionability=False,
            rationale=f"Pre-pipeline safety classifier: {safety.primary.value}",
        ),
        dynamical_state=DynamicalHead(
            current_loop_id=None,
            stability=0.0,
            posture="support",
            rationale="Bypassed full reasoning due to safety classifier.",
        ),
        network=NetworkHead(active_nodes=[], rationale="bypassed"),
        sdt=SDTHead(thwarted_in=[], rationale="bypassed"),
        orchestration=Orchestration(
            rationale=f"Pre-pipeline safety classifier short-circuit: {safety.primary.value}",
            intervention_intensity="none",
            safety_flags=safety_flags,
        ),
    )


def _crash_safe_response(turn: TurnInput, started: float) -> TurnResult:
    """Last-resort fallback when something went so wrong we have no template."""
    import uuid as _uuid
    from datetime import UTC as _UTC, datetime as _datetime

    latency_ms = int((time.perf_counter() - started) * 1000)
    plan = ReasoningPlan(
        turn_id=str(_uuid.uuid4()),
        produced_at=_datetime.now(_UTC),
        model_id="crash-safe-fallback",
        prompt_template_version="0",
        receptivity=ReceptivityHead(score=0.0, categorical_state="active_distress", actionability=False, rationale="fallback"),
        dynamical_state=DynamicalHead(current_loop_id=None, stability=0.0, posture="support", rationale="fallback"),
        network=NetworkHead(active_nodes=[], rationale="fallback"),
        sdt=SDTHead(thwarted_in=[], rationale="fallback"),
        orchestration=Orchestration(rationale="crash-safe fallback", intervention_intensity="presence", safety_flags=[]),
    )
    _ = turn
    return TurnResult(
        turn_id=plan.turn_id,
        response_text="Thank you for sharing that. I'm here and I'm listening.",
        plan=plan,
        critic=CriticVerdict(passed=True, flags=[], notes="crash-safe fallback"),
        regeneration_attempts=0,
        used_safety_template=True,
        latency_ms=latency_ms,
    )


async def _generate_with_critic_loop(
    turn: TurnInput,
    plan: ReasoningPlan,
    settings: Settings,
) -> tuple[GenerationOutput, CriticVerdict, int]:
    generated = await generation.generate(turn, plan, settings)
    verdict = await critic.audit(turn, plan, generated, settings)
    attempts = 0
    while not verdict.passed and attempts < MAX_REGENERATIONS:
        attempts += 1
        log.warning("critic_regeneration", attempt=attempts, flags=verdict.flags)
        generated = await generation.generate(
            turn, plan, settings, critic_notes=verdict.notes
        )
        verdict = await critic.audit(turn, plan, generated, settings)
    if not verdict.passed:
        log.error("critic_fallback_engaged", flags=verdict.flags)
        # Final fallback: presence response. Better than shipping a flagged turn.
        generated = GenerationOutput(
            response_text="Thank you for sharing that. I'm here and I'm listening.",
            surfaced_memory_ref_ids=[],
        )
    return generated, verdict, attempts


async def _post_turn_state_update(
    turn: TurnInput,
    plan: ReasoningPlan,
    generated: GenerationOutput,
    verdict: CriticVerdict,
    settings: Settings,
) -> None:
    _ = generated, verdict  # full prompt-driven state update lands separately
    try:
        await state.update_state(
            turn.user_id,
            {"_last_turn_id": plan.turn_id},
            settings,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("state_update_failed", user_id=turn.user_id, error=str(exc))
