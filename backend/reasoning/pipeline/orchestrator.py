"""Pipeline orchestrator. Runs a single user turn through:

    extraction → retrieval → reasoning → generation → critic [→ regen] → state

idea.md §3.1. In-process, hardcoded DAG. No learned routing in v1.
"""

from __future__ import annotations

import asyncio
import time

from ..config import Settings
from ..logging_setup import get_logger
from . import critic, extraction, generation, reasoning, retrieval, state
from .types import CriticVerdict, GenerationOutput, ReasoningPlan, TurnInput, TurnResult

log = get_logger(__name__)

MAX_REGENERATIONS = 2


async def run_turn(turn: TurnInput, settings: Settings) -> TurnResult:
    started = time.perf_counter()
    log.info("turn_started", user_id=turn.user_id, session_id=turn.session_id)

    extracted = await extraction.extract_features(turn, settings)
    log.debug("extraction_complete", utterance_id=extracted.utterance_id)

    retrieved = await retrieval.retrieve_for_all_heads(turn, extracted, settings)
    log.debug("retrieval_complete", retrieved_count=len(retrieved.all_items()))

    plan = await reasoning.reason(turn, extracted, retrieved, settings)
    log.debug(
        "reasoning_complete",
        turn_id=plan.turn_id,
        receptivity=plan.receptivity.score,
        posture=plan.dynamical_state.posture,
        intensity=plan.orchestration.intervention_intensity,
        safety_flags=plan.orchestration.safety_flags,
    )

    generated, verdict, attempts = await _generate_with_critic_loop(turn, plan, settings)

    latency_ms = int((time.perf_counter() - started) * 1000)
    used_safety_template = bool(plan.orchestration.safety_flags)

    # State update runs in the background — does not block the response.
    asyncio.create_task(_post_turn_state_update(turn, plan, generated, verdict, settings))

    log.info(
        "turn_completed",
        user_id=turn.user_id,
        turn_id=plan.turn_id,
        latency_ms=latency_ms,
        regenerations=attempts,
        used_safety_template=used_safety_template,
    )

    return TurnResult(
        turn_id=plan.turn_id,
        response_text=generated.response_text,
        plan=plan,
        critic=verdict,
        regeneration_attempts=attempts,
        used_safety_template=used_safety_template,
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
        generated = await generation.generate(turn, plan, settings, critic_notes=verdict.notes)
        verdict = await critic.audit(turn, plan, generated, settings)
    if not verdict.passed:
        # Track E will own the minimal-validating fallback template.
        log.error("critic_fallback_engaged", flags=verdict.flags)
    return generated, verdict, attempts


async def _post_turn_state_update(
    turn: TurnInput,
    plan: ReasoningPlan,
    generated: GenerationOutput,
    verdict: CriticVerdict,
    settings: Settings,
) -> None:
    _ = generated, verdict  # full update logic lands with state-update prompt
    try:
        await state.update_state(
            turn.user_id,
            {"_last_turn_id": plan.turn_id},
            settings,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("state_update_failed", user_id=turn.user_id, error=str(exc))
