"""Write-time feature extraction (idea.md §4.2).

In fixture mode returns deterministic stubs. Live mode calls Gemini Flash
with the extraction prompt and parses against the ExtractionResult schema.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .. import vocab
from ..config import Settings
from ..llm import call_structured, render_prompt
from ..logging_setup import get_logger
from .types import (
    AffectiveValence,
    ExtractionResult,
    SafetySignals,
    TurnInput,
)

log = get_logger(__name__)


async def extract_features(
    turn: TurnInput,
    settings: Settings,
    *,
    conversational_context: list[dict[str, str]] | None = None,
    condition_pack: str = "eating_disorder",
) -> ExtractionResult:
    if settings.is_fixture or not settings.llm_is_live:
        return _fixture_extraction(turn, settings)

    prompt = render_prompt(
        "extraction.v1.j2",
        utterance_text=turn.utterance_text,
        conversational_context=conversational_context or [],
        behaviors_vocab=vocab.behaviors_for_pack(condition_pack),
        network_nodes_vocab=vocab.network_nodes_for_pack(condition_pack),
        need_domains_vocab=vocab.need_domains(),
    )

    try:
        parsed, meta = await call_structured(
            settings.model_extraction,
            prompt,
            ExtractionResult,
            settings,
        )
    except Exception:
        log.exception("extraction_live_call_failed_falling_back_to_fixture")
        return _fixture_extraction(turn, settings)

    # Stamp identity fields the model can't know
    parsed = parsed.model_copy(update={
        "utterance_id": str(uuid.uuid4()),
        "extracted_at": datetime.now(UTC),
        "model_id": meta.model_id,
        "prompt_template_version": meta.prompt_template_version,
    })
    log.debug(
        "extraction_complete",
        utterance_id=parsed.utterance_id,
        behaviors=len(parsed.behaviors_referenced),
        nodes=len(parsed.network_nodes_activated),
        latency_ms=meta.latency_ms,
    )
    return parsed


def _fixture_extraction(turn: TurnInput, settings: Settings) -> ExtractionResult:
    """Deterministic, content-free stub for fixture-mode testing."""
    return ExtractionResult(
        utterance_id=str(uuid.uuid4()),
        extracted_at=datetime.now(UTC),
        model_id=f"fixture::{settings.model_extraction}",
        prompt_template_version="fixture-0",
        affective_valence=AffectiveValence(
            valence=0.0,
            arousal=0.0,
            confidence=0.0,
        ),
        behaviors_referenced=[],
        network_nodes_activated=[],
        implicated_need_states=[],
        safety_signals=SafetySignals(),
        low_information=len(turn.utterance_text.strip()) < 10,
    )
