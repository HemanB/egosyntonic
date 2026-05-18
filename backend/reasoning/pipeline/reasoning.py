"""The 4-head CoT reasoning call (idea.md §3.2).

Single Gemini Pro invocation that outputs a structured ReasoningPlan with one
section per head plus an orchestration section. Chain-of-thought reasoning is
elicited via prompt instruction; the model emits structured JSON via response
schema.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from ..config import Settings
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


async def reason(
    turn: TurnInput,
    extraction: ExtractionResult,
    retrieval: RetrievalBundle,
    settings: Settings,
) -> ReasoningPlan:
    if settings.is_fixture:
        return _fixture_plan(turn, extraction, retrieval, settings)
    # TODO(Track D, Track B-live): build reasoning prompt + Gemini Pro call with response schema
    raise NotImplementedError("live-mode reasoning not yet implemented")


def _fixture_plan(
    turn: TurnInput,
    extraction: ExtractionResult,
    retrieval: RetrievalBundle,
    settings: Settings,
) -> ReasoningPlan:
    """Conservative fixture plan: low receptivity, presence-only posture.

    Means generation falls back to a safe presence response in fixture mode.
    """
    _ = turn, extraction, retrieval  # unused in fixture
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
