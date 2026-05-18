"""Pre-pipeline safety classifier.

Runs BEFORE the four-head reasoning call (idea.md §9.1). Catches crisis
signals, means-restriction asks, ED-numerical asks. If anything fires, the
orchestrator short-circuits to the corresponding fixed template; the critic
still runs to verify template adherence.

Two implementations:
- `fixture`: deterministic regex/keyword detection. Used in dev + CI.
- `live`: Gemini Flash with a tight prompt + the regex layer as a backstop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from ..config import Settings


class SafetyCategory(str, Enum):
    NONE = "none"
    ACTIVE_SUICIDAL_IDEATION = "active_suicidal_ideation"
    SELF_HARM_INTENT = "self_harm_intent"
    MEDICAL_ACUTE = "medical_acute"
    ASKING_FOR_METHODS = "asking_for_methods"
    ASKING_FOR_NUMBERS = "asking_for_numbers"
    USER_REQUESTED_RESOURCES = "user_requested_resources"


@dataclass(frozen=True, slots=True)
class SafetyClassification:
    """Result of the pre-pipeline safety scan.

    `primary` is the most-acute category detected. `all_detected` may include
    multiple categories — the template-selection function picks the highest-
    priority one.
    """

    primary: SafetyCategory
    all_detected: list[SafetyCategory] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)
    model_id: str = "deterministic"

    @property
    def any_fired(self) -> bool:
        return self.primary != SafetyCategory.NONE


# --- Deterministic patterns ---
# These are pre-pipeline INPUT scans. They are intentionally over-inclusive:
# false positives just trigger a careful response. False negatives are far
# worse. Each pattern is a compiled regex with re.IGNORECASE.
#
# These DO NOT cover everything. The classifier's job is to catch the obvious
# cases the LLM might mishandle if it ran the full pipeline. The reasoning
# layer is expected to surface additional signals via the plan's safety_flags.
#
# These patterns are reviewed by clinical advisor before launch. Treat any
# change as a clinical-review change, not a code change.

_PATTERNS: dict[SafetyCategory, list[re.Pattern[str]]] = {
    SafetyCategory.ACTIVE_SUICIDAL_IDEATION: [
        re.compile(r"\b(?:kill myself|end my life|take my (?:own )?life|don't want to (?:be alive|exist|live))\b", re.IGNORECASE),
        re.compile(r"\b(?:better off dead|wish (?:i (?:were|was)|to be) dead)\b", re.IGNORECASE),
        re.compile(r"\b(?:i (?:want|need) to die|ending it|ending things)\b", re.IGNORECASE),
        re.compile(r"\bsuicid(?:e|al)\b(?!.*\b(?:thought i (?:had|might)|in the past long ago|history of family|article|news|movie|book)\b)", re.IGNORECASE),
    ],
    SafetyCategory.SELF_HARM_INTENT: [
        re.compile(r"\b(?:cut(?:ting)?|burn(?:ing)?|hurt(?:ing)?) myself\b", re.IGNORECASE),
        re.compile(r"\bself[- ]?harm(?:ing)?\b", re.IGNORECASE),
        re.compile(r"\b(?:want|going|planning) to hurt myself\b", re.IGNORECASE),
    ],
    SafetyCategory.MEDICAL_ACUTE: [
        re.compile(r"\b(?:fainted|fainting|passed out|blacked? out|syncope)\b", re.IGNORECASE),
        re.compile(r"\bvomit(?:ing|ed)? blood\b", re.IGNORECASE),
        re.compile(r"\bblood in (?:my )?(?:vomit|stool)\b", re.IGNORECASE),
        re.compile(r"\bchest pain\b", re.IGNORECASE),
        re.compile(r"\bheart (?:racing|pounding|skipping)\b.*\b(?:hours|all day|won.?t stop)\b", re.IGNORECASE),
        re.compile(r"\bhaven.?t eaten (?:in|for) \d+\s*days?\b", re.IGNORECASE),
        re.compile(r"\b(?:dizzy|lightheaded|weak)\b.*\b(?:every time|constantly|all the time|standing|walking)\b", re.IGNORECASE),
    ],
    SafetyCategory.ASKING_FOR_METHODS: [
        # NEVER provide methods — even framed as harm reduction or removal-of-access.
        re.compile(r"\b(?:how (?:can|do|should) i|what.?s the (?:best|easiest|fastest) way to)\b.*\b(?:kill (?:myself|me)|end (?:it|my life)|hurt myself|self[- ]?harm)\b", re.IGNORECASE),
        re.compile(r"\bwhat.?s a (?:safe|safer|painless) way to\b", re.IGNORECASE),
        re.compile(r"\b(?:tell me|show me|list|recommend) (?:a |the )?(?:methods?|ways?|tools?) (?:for|to)\b.*\b(?:harm|die|end|suicid)\b", re.IGNORECASE),
        # Purging-method asks
        re.compile(r"\bhow (?:can|do|should) i (?:make myself )?(?:throw up|vomit|purge)\b", re.IGNORECASE),
        re.compile(r"\bbest (?:way|method) to (?:throw up|vomit|purge|restrict|fast)\b", re.IGNORECASE),
    ],
    SafetyCategory.ASKING_FOR_NUMBERS: [
        # NEVER provide numerical guidance on calories/weight/exercise duration/fasting.
        re.compile(r"\b(?:how many|what.?s the) calor(?:ies|ie)\b", re.IGNORECASE),
        re.compile(r"\bcalorie (?:target|limit|count|goal|deficit)\b", re.IGNORECASE),
        re.compile(r"\b(?:is|are|was|were) \d{2,5}\s*(?:cal|cals|calories|kcal)\b", re.IGNORECASE),
        re.compile(r"\bgoal weight\b", re.IGNORECASE),
        re.compile(r"\bideal (?:weight|bmi|body fat)\b", re.IGNORECASE),
        re.compile(r"\b(?:what|how (?:long|much|many))\b.*\b(?:should i|to)\s+(?:exercise|run|workout|work out|fast|restrict)\b", re.IGNORECASE),
        re.compile(r"\bhow (?:long|many hours|many days) (?:should|can) i (?:fast|go without|not eat)\b", re.IGNORECASE),
    ],
    SafetyCategory.USER_REQUESTED_RESOURCES: [
        re.compile(r"\b(?:crisis|hotline|988|crisis text|emergency)\s*(?:line|resources?|number|contacts?)?\b.*\b(?:please|need|can you|share|give|what)\b", re.IGNORECASE),
        re.compile(r"\b(?:where|how) (?:can|do) i (?:get|find) (?:help|support|a therapist|treatment)\b", re.IGNORECASE),
    ],
}


# Priority order — when multiple categories fire, this picks the response.
_PRIORITY = [
    SafetyCategory.ACTIVE_SUICIDAL_IDEATION,
    SafetyCategory.SELF_HARM_INTENT,
    SafetyCategory.ASKING_FOR_METHODS,
    SafetyCategory.MEDICAL_ACUTE,
    SafetyCategory.ASKING_FOR_NUMBERS,
    SafetyCategory.USER_REQUESTED_RESOURCES,
]


def _scan_deterministic(text: str) -> SafetyClassification:
    detected: list[SafetyCategory] = []
    matched: list[str] = []
    for category in _PRIORITY:
        for pat in _PATTERNS[category]:
            if pat.search(text):
                detected.append(category)
                matched.append(pat.pattern)
                break
    if not detected:
        return SafetyClassification(primary=SafetyCategory.NONE)
    return SafetyClassification(
        primary=detected[0],
        all_detected=detected,
        matched_patterns=matched,
    )


async def classify_safety_signals(
    utterance_text: str,
    settings: Settings,
) -> SafetyClassification:
    """Run the pre-pipeline safety scan.

    In fixture mode and as a backstop in live mode, runs deterministic
    pattern matching. In live mode, additionally calls Gemini Flash with
    the crisis-classifier prompt and unions the results.
    """
    deterministic = _scan_deterministic(utterance_text)
    if settings.is_fixture:
        return deterministic

    # TODO(Track D live-wire): call Gemini Flash with crisis classifier prompt
    # and union with deterministic result. For now, return deterministic only.
    return deterministic
