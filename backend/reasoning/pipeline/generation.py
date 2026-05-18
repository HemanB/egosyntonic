"""Response generation conditioned on the reasoning plan (idea.md §3.3).

Generation receives the plan and produces user-facing text. Writes in the
user's register, references surfaced memories naturally, avoids clinical jargon.
"""

from __future__ import annotations

from ..config import Settings
from .types import GenerationOutput, ReasoningPlan, TurnInput


PRESENCE_FALLBACK = (
    "Thanks for telling me. I'm here and I'm listening."
)


async def generate(
    turn: TurnInput,
    plan: ReasoningPlan,
    settings: Settings,
    critic_notes: str | None = None,
) -> GenerationOutput:
    if settings.is_fixture:
        return _fixture_generation(turn, plan)
    # TODO(Track D, Track B-live): build generation prompt + Gemini Flash call
    _ = critic_notes  # passed through on regeneration
    raise NotImplementedError("live-mode generation not yet implemented")


def _fixture_generation(turn: TurnInput, plan: ReasoningPlan) -> GenerationOutput:
    _ = turn
    if plan.orchestration.safety_flags:
        # Safety templates are owned by Track E; fixture mode returns a placeholder
        # that the safety layer will overwrite when wired.
        return GenerationOutput(
            response_text="[safety-template-placeholder]",
            surfaced_memory_ref_ids=[],
        )

    return GenerationOutput(
        response_text=PRESENCE_FALLBACK,
        surfaced_memory_ref_ids=[],
    )
