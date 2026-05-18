"""Critic layer (idea.md §3.4).

Separate LLM call that audits the generated response against the plan and a
fixed set of failure modes. Triggers regeneration if flags fire. After two
regeneration attempts, falls back to a minimal validating response.
"""

from __future__ import annotations

from ..config import Settings
from .types import (
    CriticVerdict,
    GenerationOutput,
    ReasoningPlan,
    TurnInput,
)


async def audit(
    turn: TurnInput,
    plan: ReasoningPlan,
    generation: GenerationOutput,
    settings: Settings,
) -> CriticVerdict:
    if settings.is_fixture:
        return CriticVerdict(passed=True, flags=[], notes="fixture-mode auto-pass")
    # TODO(Track D, Track B-live): build critic prompt + Gemini Pro call
    _ = turn, plan, generation  # noqa: F841
    raise NotImplementedError("live-mode critic not yet implemented")
