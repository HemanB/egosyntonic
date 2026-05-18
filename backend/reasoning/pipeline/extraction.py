"""Write-time feature extraction (idea.md §4.2).

In fixture mode returns deterministic stubs. Live mode calls Gemini Flash with
the extraction prompt and parses against the ExtractionResult schema.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from ..config import Settings
from .types import (
    AffectiveValence,
    ExtractionResult,
    SafetySignals,
    TurnInput,
)


async def extract_features(turn: TurnInput, settings: Settings) -> ExtractionResult:
    if settings.is_fixture:
        return _fixture_extraction(turn, settings)
    # TODO(Track D, Track B-live): wire google-genai client + extraction prompt
    raise NotImplementedError("live-mode extraction not yet implemented")


def _fixture_extraction(turn: TurnInput, settings: Settings) -> ExtractionResult:
    """Deterministic, content-free stub for fixture-mode testing.

    Real semantic extraction lands when Track D's prompts merge.
    """
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
