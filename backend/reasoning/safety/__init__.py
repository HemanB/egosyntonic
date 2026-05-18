"""Safety layer.

idea.md §9 is non-negotiable. This module provides:

1. A pre-pipeline classifier (`classifier.py`) that catches crisis signals,
   means-restriction asks, and ED-numerical asks BEFORE the heavy reasoning
   call. When it fires, the pipeline short-circuits to a fixed safety
   template.
2. Fixed safety response templates (`templates.py`) — the EXACT text the
   user sees in a flagged moment. Reviewed by clinical advisor before
   any external user touches the app. Versioned, immutable per deploy.
3. Deterministic post-generation filters (`post_filters.py`) — lexicon
   and regex checks that run on every generated response as a backstop
   to the critic. Belt-and-suspenders per idea.md §9 implementation note.

The safety layer never tries to "talk the user down" or apply therapeutic
techniques. Its job is to bridge to appropriate human support.
"""

from .classifier import (
    SafetyClassification,
    SafetyCategory,
    classify_safety_signals,
)
from .post_filters import (
    PostFilterResult,
    check_response_safety,
)
from .templates import (
    SafetyTemplate,
    get_template_for_classification,
)

__all__ = [
    "SafetyCategory",
    "SafetyClassification",
    "SafetyTemplate",
    "check_response_safety",
    "classify_safety_signals",
    "get_template_for_classification",
    "PostFilterResult",
]
