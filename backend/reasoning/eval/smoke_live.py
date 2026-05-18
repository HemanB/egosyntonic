"""Run a single live-LLM turn end-to-end. Useful for hand-validation of
CoT quality before the full eval harness runs against fixtures.

Usage:
    cd backend
    uv run python -m reasoning.eval.smoke_live "I'm not sure how to feel about today."

Reads `EGOSYN_RUNTIME_MODE` from your env (.env.local). Set to `live_llm`
for a real Gemini call without GCP. Requires `GEMINI_API_KEY` in
`.env.local`.
"""

from __future__ import annotations

import asyncio
import json
import sys

from ..config import get_settings
from ..logging_setup import configure_logging, get_logger
from ..pipeline.orchestrator import run_turn
from ..pipeline.types import TurnInput

log = get_logger(__name__)


async def main(utterance: str) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)

    log.info(
        "smoke_starting",
        runtime_mode=settings.runtime_mode.value,
        utterance_chars=len(utterance),
    )

    turn = TurnInput(
        user_id=settings.dev_bypass_user_id,
        session_id="smoke-live",
        utterance_text=utterance,
    )
    result = await run_turn(turn, settings)

    print("\n========== TURN RESULT ==========")
    print(f"turn_id: {result.turn_id}")
    print(f"latency_ms: {result.latency_ms}")
    print(f"used_safety_template: {result.used_safety_template}")
    print(f"regeneration_attempts: {result.regeneration_attempts}")
    print(f"critic.passed: {result.critic.passed}")
    if result.critic.flags:
        print(f"critic.flags: {result.critic.flags}")
        print(f"critic.notes: {result.critic.notes}")
    print(f"\nplan.receptivity: {result.plan.receptivity.score:.2f} "
          f"({result.plan.receptivity.categorical_state})")
    print(f"plan.orchestration.intensity: {result.plan.orchestration.intervention_intensity}")
    print(f"plan.orchestration.safety_flags: {result.plan.orchestration.safety_flags}")

    print("\n--- RESPONSE ---")
    print(result.response_text)
    print("--- END ---\n")

    if "--json" in sys.argv:
        print("\n========== FULL JSON ==========")
        print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m reasoning.eval.smoke_live \"<utterance>\" [--json]", file=sys.stderr)
        sys.exit(2)
    utterance = sys.argv[1]
    sys.exit(asyncio.run(main(utterance)))
