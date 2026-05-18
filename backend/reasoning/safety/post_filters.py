"""Deterministic post-generation safety filters.

Belt-and-suspenders backstop to the critic (idea.md §9 implementation note).
Runs on every generated response. If anything fires, the orchestrator forces
critic failure and triggers regeneration with the filter's notes in context.

These filters are intentionally conservative. They MUST NOT pass through
content that violates the safety architecture, even if the surrounding
generation seems benign. False positives are fine — they just cost a
regeneration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class PostFilterCategory(str, Enum):
    NUMERICAL_ED_CONTENT = "numerical_ed_content"
    CLINICAL_JARGON = "clinical_jargon"
    METHOD_MENTION = "method_mention"
    DIAGNOSIS_LANGUAGE = "diagnosis_language"


@dataclass(frozen=True, slots=True)
class PostFilterResult:
    passed: bool
    flagged: list[PostFilterCategory] = field(default_factory=list)
    matched_excerpts: list[str] = field(default_factory=list)
    notes: str = ""


# --- Numerical ED content ---
# Calorie/weight/exercise-duration/fasting numbers in any guise. Triggers
# regardless of framing — "for general knowledge", "what's healthy", etc.

_NUMERICAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b\d{2,5}\s*(?:cal|cals|calories|kcal)\b", re.IGNORECASE),
    re.compile(r"\b\d{1,4}\s*(?:lb|lbs|pounds|kg|kilo|kilos|kilograms)\b", re.IGNORECASE),
    re.compile(r"\bbmi\s+(?:of\s+)?\d{1,2}(?:\.\d+)?\b", re.IGNORECASE),
    re.compile(r"\b(?:fast|fasting)\s+(?:for\s+)?\d+\s*(?:hours?|hrs|days?)\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*(?:minutes?|mins?|hours?|hrs)\s+(?:of\s+)?(?:cardio|exercise|running|hiit)\b", re.IGNORECASE),
    # Range expressions like "between 1200 and 1500 calories"
    re.compile(r"\bbetween\s+\d+\s+and\s+\d+\s*(?:cal|calories|lb|lbs|kg|minutes)\b", re.IGNORECASE),
]


# --- Clinical jargon ---
# Phrases the model should never use to the user. Curated from idea.md §3.4
# and §5.5. Some terms are fine in internal rationale; the post-filter checks
# the user-facing generation only.

_CLINICAL_JARGON_TERMS: list[str] = [
    "cognitive distortion",
    "cognitive distortions",
    "compensatory behavior",
    "compensatory behaviors",
    "maladaptive coping",
    "maladaptive behaviors?",
    "negative affect",
    "positive affect",
    "egosyntonic",
    "ego-syntonic",
    "ego syntonic",
    "ego-dystonic",
    "ego dystonic",
    "autonomy thwarting",
    "competence thwarting",
    "relatedness thwarting",
    "thwarted autonomy",
    "thwarted competence",
    "thwarted relatedness",
    "symptom network",
    "feedback loop",  # often clinically loaded in this domain
    "schema therapy",
    "schema-driven",
    "DSM",
    "ICD",
    "anorexia nervosa",
    "bulimia nervosa",
    "binge eating disorder",
    "OCD",
    "BPD",
    "comorbid",
    "comorbidity",
    "patient",  # users are not patients in this product
    "patients",
]

_JARGON_REGEXES: list[re.Pattern[str]] = [
    re.compile(rf"\b{term}\b", re.IGNORECASE) for term in _CLINICAL_JARGON_TERMS
]


# --- Method mention ---
# Even if the user didn't ask, generation must not name self-harm or
# purging methods.

_METHOD_REGEXES: list[re.Pattern[str]] = [
    re.compile(r"\b(?:cutting|burning|overdosing|hanging|suffocating|drowning)\b\s+(?:yourself|oneself|themselves)?", re.IGNORECASE),
    re.compile(r"\bself[- ]induced vomiting\b", re.IGNORECASE),
    re.compile(r"\b(?:ipecac|diuretics?|laxatives?)\s+(?:to|for)\b", re.IGNORECASE),
    re.compile(r"\b(?:method|methods?|tool|tools?) (?:of|for) (?:self[- ]?harm|suicide|purging)\b", re.IGNORECASE),
]


# --- Diagnosis language ---
# The app is wellness-positioned — it does NOT diagnose (idea.md §1).

_DIAGNOSIS_REGEXES: list[re.Pattern[str]] = [
    re.compile(r"\byou (?:have|are) (?:suffering|struggling) (?:from|with)\s+(?:an?\s+)?(?:anorexia|bulimia|BED|binge eating|eating disorder|depression|anxiety disorder|OCD|borderline)\b", re.IGNORECASE),
    re.compile(r"\byou meet (?:the )?criteria for\b", re.IGNORECASE),
    re.compile(r"\bi (?:diagnose|am diagnosing|would diagnose)\b", re.IGNORECASE),
    re.compile(r"\byour diagnosis (?:is|would be)\b", re.IGNORECASE),
]


def _scan(
    text: str,
    patterns: list[re.Pattern[str]],
) -> list[str]:
    """Return matched substrings (up to 5)."""
    matches: list[str] = []
    for pat in patterns:
        for m in pat.finditer(text):
            matches.append(m.group(0))
            if len(matches) >= 5:
                return matches
    return matches


def check_response_safety(response_text: str) -> PostFilterResult:
    """Audit the generated response. Returns a PostFilterResult.

    A passing result has `passed=True` and no flagged categories.
    """
    flagged: list[PostFilterCategory] = []
    matches: list[str] = []

    numerical = _scan(response_text, _NUMERICAL_PATTERNS)
    if numerical:
        flagged.append(PostFilterCategory.NUMERICAL_ED_CONTENT)
        matches.extend(numerical)

    jargon = _scan(response_text, _JARGON_REGEXES)
    if jargon:
        flagged.append(PostFilterCategory.CLINICAL_JARGON)
        matches.extend(jargon)

    method = _scan(response_text, _METHOD_REGEXES)
    if method:
        flagged.append(PostFilterCategory.METHOD_MENTION)
        matches.extend(method)

    diagnosis = _scan(response_text, _DIAGNOSIS_REGEXES)
    if diagnosis:
        flagged.append(PostFilterCategory.DIAGNOSIS_LANGUAGE)
        matches.extend(diagnosis)

    if not flagged:
        return PostFilterResult(passed=True)

    notes = (
        "Deterministic post-filter caught: "
        + ", ".join(c.value for c in flagged)
        + ". Excerpts: "
        + " | ".join(repr(m) for m in matches[:10])
    )
    return PostFilterResult(
        passed=False,
        flagged=flagged,
        matched_excerpts=matches,
        notes=notes,
    )
