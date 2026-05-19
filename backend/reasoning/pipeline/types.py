"""Pipeline data types. Pydantic models mirror the JSON Schemas in shared/schemas/.

These types are the in-process representations passed between pipeline stages.
The schemas in shared/schemas/ are the wire/storage representations; codegen will
keep them in sync (TODO: schema-validation CI check).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# --- Turn input ---


class TurnInput(BaseModel):
    """User turn coming in over HTTP."""

    user_id: str
    session_id: str
    utterance_text: str
    client_timestamp: datetime | None = None


# --- Extraction output (mirrors extraction.schema.json) ---


class AffectiveValence(BaseModel):
    valence: float = Field(ge=-1, le=1)
    arousal: float = Field(ge=-1, le=1)
    dominance: float | None = Field(default=None, ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)


class BehaviorReference(BaseModel):
    behavior_id: str
    stance: Literal[
        "engaged_in",
        "considered",
        "resisted",
        "described_as_past",
        "described_in_others",
        "ambiguous",
    ]
    temporal_marker: str | None = None


class NetworkNodeActivation(BaseModel):
    node_id: str
    evidence_strength: float = Field(ge=0, le=1)


class NeedStateImplication(BaseModel):
    need: Literal["autonomy", "competence", "relatedness"]
    domain: str
    polarity: Literal["satisfied", "thwarted", "ambiguous"]
    confidence: float = Field(ge=0, le=1)


class SafetySignals(BaseModel):
    active_si: bool = False
    self_harm_intent: bool = False
    medical_acute: bool = False
    asking_for_methods: bool = False
    asking_for_numbers: bool = False

    @property
    def any_active(self) -> bool:
        return any(
            (
                self.active_si,
                self.self_harm_intent,
                self.medical_acute,
                self.asking_for_methods,
                self.asking_for_numbers,
            )
        )


class ExtractionResult(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    utterance_id: str
    extracted_at: datetime
    model_id: str
    prompt_template_version: str

    affective_valence: AffectiveValence
    behaviors_referenced: list[BehaviorReference] = Field(default_factory=list)
    cognitive_content_distortions: list[str] = Field(default_factory=list)
    cognitive_content_themes: list[str] = Field(default_factory=list)
    cognitive_content_key_phrases: list[str] = Field(default_factory=list, max_length=5)
    network_nodes_activated: list[NetworkNodeActivation] = Field(default_factory=list)
    implicated_need_states: list[NeedStateImplication] = Field(default_factory=list)

    safety_signals: SafetySignals = Field(default_factory=SafetySignals)
    low_information: bool = False


# --- Retrieval ---


class RetrievedItem(BaseModel):
    ref_type: Literal["utterance", "behavior_log", "summary"]
    ref_id: str
    excerpt: str
    occurred_at: datetime
    score: float
    head_origin: Literal["receptivity", "dynamical", "network", "sdt"]


class RetrievalBundle(BaseModel):
    items_by_head: dict[str, list[RetrievedItem]] = Field(default_factory=dict)

    def all_items(self) -> list[RetrievedItem]:
        return [item for items in self.items_by_head.values() for item in items]


# --- Plan (mirrors plan.schema.json) ---


# Rationale-first ordering across all heads: Pydantic Field declaration
# order drives the JSON Schema property order, which Gemini's structured
# output respects. Forcing rationale FIRST means the model emits its chain
# of thought BEFORE committing to the structured values that the rationale
# justifies. Without this, rationale becomes post-hoc justification and the
# structured fields default to safe-looking constants.


class ReceptivityHead(BaseModel):
    rationale: str
    score: float = Field(ge=0, le=1)
    categorical_state: Literal[
        "open_to_reflection",
        "active_distress",
        "crisis",
        "dissociated_or_disengaged",
        "seeking_practical_support",
    ]
    actionability: bool


class DynamicalHead(BaseModel):
    rationale: str
    current_loop_id: str | None
    current_loop_label: str | None = None
    stability: float = Field(ge=0, le=1)
    transition_signals: list[str] = Field(default_factory=list)
    posture: Literal["interrupt", "support", "consolidate", "none"]


class CandidatePattern(BaseModel):
    pattern_type: Literal["pattern", "echo", "shift", "context"]
    summary: str
    evidence_utterance_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class NetworkHead(BaseModel):
    rationale: str
    active_nodes: list[NetworkNodeActivation] = Field(default_factory=list)
    upstream_target_node_id: str | None = None
    candidate_patterns: list[CandidatePattern] = Field(default_factory=list)


class ThwartedNeed(BaseModel):
    need: Literal["autonomy", "competence", "relatedness"]
    domain: str
    confidence: float = Field(ge=0, le=1)


class SDTHead(BaseModel):
    rationale: str
    thwarted_in: list[ThwartedNeed] = Field(default_factory=list)
    framing_language_hint: str | None = None


SafetyFlag = Literal[
    "active_suicidal_ideation",
    "self_harm_intent",
    "medical_instability",
    "asking_for_methods",
    "asking_for_numbers",
    "egosyntonic_collusion_risk",
    "boundary_disclosure_needed",
]


class Orchestration(BaseModel):
    rationale: str
    intervention_intensity: Literal[
        "none", "presence", "light_reflection", "pattern_surfacing", "direct_invitation"
    ]
    safety_flags: list[SafetyFlag] = Field(default_factory=list)
    content_focus_node_id: str | None = None
    content_focus_pattern_index: int | None = None
    framing_sdt_language: str | None = None
    user_register_excerpts: list[str] = Field(default_factory=list)
    memory_reference_ids: list[str] = Field(default_factory=list)


class ReasoningPlan(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    turn_id: str
    produced_at: datetime
    model_id: str
    prompt_template_version: str

    receptivity: ReceptivityHead
    dynamical_state: DynamicalHead
    network: NetworkHead
    sdt: SDTHead
    orchestration: Orchestration


# --- Generation & critic ---


class GenerationOutput(BaseModel):
    response_text: str
    surfaced_memory_ref_ids: list[str] = Field(default_factory=list)


CriticFlag = Literal[
    "validated_egosyntonic_framing",
    "used_clinical_language",
    "colluded_with_disorder_logic",
    "missed_safety_signal",
    "over_delivered_insight_at_low_receptivity",
    "memory_reference_felt_surveilling",
]


class CriticVerdict(BaseModel):
    passed: bool
    flags: list[CriticFlag] = Field(default_factory=list)
    notes: str = ""


# --- Turn output ---


class TurnResult(BaseModel):
    turn_id: str
    response_text: str
    plan: ReasoningPlan
    critic: CriticVerdict
    regeneration_attempts: int = 0
    used_safety_template: bool = False
    latency_ms: int
