"""Fixed safety-response templates.

idea.md §9.1: when a safety signal fires, response generation follows a fixed
template — not a creative LLM-generated response. Each template is reviewed by
the clinical advisor before launch. Versioned, immutable per deploy.

DRAFT STATUS: these template strings are v0 placeholders authored by the
build agent. They MUST be reviewed and finalized by the project's clinical
advisor before any external user touches the system. The CI release gate
should refuse production deploys until a `clinical_advisor_signoff.yaml`
file accompanies each template version.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .classifier import SafetyCategory


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    CLINICAL_REVIEW_PENDING = "clinical_review_pending"
    APPROVED = "approved"


@dataclass(frozen=True, slots=True)
class SafetyTemplate:
    template_id: str
    version: str
    status: TemplateStatus
    body: str
    category: SafetyCategory


CRISIS_RESOURCES = (
    "If you are in immediate danger, please call 988 (Suicide & Crisis Lifeline) "
    "or text HOME to 741741 (Crisis Text Line). "
    "If you're outside the US, you can find a local helpline at findahelpline.com."
)

APP_LIMITATION_REMINDER = (
    "I'm not a crisis service and I'm not a substitute for professional care."
)


# --- Templates ---
#
# Tone: validate, surface resources, recommend professional support, name the
# limitation. Per idea.md §9.1: NO attempts to "talk the user down" or apply
# therapeutic techniques.

_ACTIVE_SI_TEMPLATE = SafetyTemplate(
    template_id="active_suicidal_ideation",
    version="0.1.0-draft",
    status=TemplateStatus.CLINICAL_REVIEW_PENDING,
    category=SafetyCategory.ACTIVE_SUICIDAL_IDEATION,
    body=(
        "Thank you for telling me. What you're describing sounds painful, "
        "and it's the kind of thing that deserves a person, not an app.\n\n"
        f"{CRISIS_RESOURCES}\n\n"
        "If you're working with a therapist or care team, please let them "
        f"know what's happening for you. {APP_LIMITATION_REMINDER}"
    ),
)

_SELF_HARM_TEMPLATE = SafetyTemplate(
    template_id="self_harm_intent",
    version="0.1.0-draft",
    status=TemplateStatus.CLINICAL_REVIEW_PENDING,
    category=SafetyCategory.SELF_HARM_INTENT,
    body=(
        "I'm glad you're talking about this rather than keeping it to yourself. "
        "Hurting yourself is something to bring to a person who can be there "
        "with you in real time.\n\n"
        f"{CRISIS_RESOURCES}\n\n"
        f"{APP_LIMITATION_REMINDER}"
    ),
)

_METHODS_TEMPLATE = SafetyTemplate(
    template_id="asking_for_methods",
    version="0.1.0-draft",
    status=TemplateStatus.CLINICAL_REVIEW_PENDING,
    category=SafetyCategory.ASKING_FOR_METHODS,
    body=(
        "I won't go into specifics there, even if you're asking for what feels "
        "like a practical reason. That's not me being cagey — it's a line I "
        "hold for everyone who uses this app.\n\n"
        "If the underlying experience is one you'd like to talk through, I'm "
        "here for that.\n\n"
        f"{CRISIS_RESOURCES}\n\n"
        f"{APP_LIMITATION_REMINDER}"
    ),
)

_MEDICAL_TEMPLATE = SafetyTemplate(
    template_id="medical_acute",
    version="0.1.0-draft",
    status=TemplateStatus.CLINICAL_REVIEW_PENDING,
    category=SafetyCategory.MEDICAL_ACUTE,
    body=(
        "What you're describing is something to get medical attention for, "
        "not because I'm being alarmist but because the signals you're "
        "naming can be signs of something a clinician should look at.\n\n"
        "If you have a primary care doctor or a treatment team, please "
        "reach out to them today. If you can't reach them, urgent care or "
        "an emergency department is the right call. In the US, you can "
        "also dial 911 if you feel unsafe right now.\n\n"
        f"{APP_LIMITATION_REMINDER} I'm here to keep listening when you're "
        "ready to come back."
    ),
)

_NUMBERS_TEMPLATE = SafetyTemplate(
    template_id="asking_for_numbers",
    version="0.1.0-draft",
    status=TemplateStatus.CLINICAL_REVIEW_PENDING,
    category=SafetyCategory.ASKING_FOR_NUMBERS,
    body=(
        "I don't give specific numbers — calories, weights, exercise minutes, "
        "fasting hours. That's a stance, not a gap. Numbers in this domain can "
        "be triggering or directly harmful even when they sound like neutral "
        "information.\n\n"
        "If you're working with a treatment team, those targets are theirs to "
        "set with you. If you're not, that's a conversation worth having with "
        "a registered dietitian or a clinician who can hold the whole picture.\n\n"
        "If what's underneath the ask is something else — anxiety about a "
        "meal, comparing yourself to something, trying to make a decision — "
        "I can be useful there."
    ),
)

_RESOURCES_TEMPLATE = SafetyTemplate(
    template_id="user_requested_resources",
    version="0.1.0-draft",
    status=TemplateStatus.CLINICAL_REVIEW_PENDING,
    category=SafetyCategory.USER_REQUESTED_RESOURCES,
    body=(
        "Here are a few places to start.\n\n"
        f"{CRISIS_RESOURCES}\n\n"
        "For ongoing support, NEDA's helpline (1-800-931-2237 in the US, "
        "Mon–Thu 11am–9pm ET, Fri 11am–5pm ET) can help with referrals to "
        "eating-disorder–informed clinicians. Psychology Today's therapist "
        "directory is also searchable by specialty and insurance.\n\n"
        f"{APP_LIMITATION_REMINDER}"
    ),
)

# Minimal validating fallback used after two failed regenerations
# (idea.md §3.4). Intentionally low-content.
_FALLBACK_MINIMAL = SafetyTemplate(
    template_id="fallback_minimal",
    version="0.1.0-draft",
    status=TemplateStatus.CLINICAL_REVIEW_PENDING,
    category=SafetyCategory.NONE,
    body=(
        "Thank you for sharing that. I'm here and I'm listening."
    ),
)


_TEMPLATES_BY_CATEGORY: dict[SafetyCategory, SafetyTemplate] = {
    SafetyCategory.ACTIVE_SUICIDAL_IDEATION: _ACTIVE_SI_TEMPLATE,
    SafetyCategory.SELF_HARM_INTENT: _SELF_HARM_TEMPLATE,
    SafetyCategory.ASKING_FOR_METHODS: _METHODS_TEMPLATE,
    SafetyCategory.MEDICAL_ACUTE: _MEDICAL_TEMPLATE,
    SafetyCategory.ASKING_FOR_NUMBERS: _NUMBERS_TEMPLATE,
    SafetyCategory.USER_REQUESTED_RESOURCES: _RESOURCES_TEMPLATE,
}


def get_template_for_classification(category: SafetyCategory) -> SafetyTemplate | None:
    return _TEMPLATES_BY_CATEGORY.get(category)


def get_fallback_template() -> SafetyTemplate:
    return _FALLBACK_MINIMAL
