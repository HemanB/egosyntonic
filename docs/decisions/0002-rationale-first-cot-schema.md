# ADR-0002: Rationale-first chain-of-thought via schema field ordering

- Status: Accepted
- Date: 2026-05-19
- Supersedes: implicit prompt-engineering choice in `reasoning.v1.j2` v1.0.0
- Related: idea.md §3.2 ("The reasoning prompt instructs the model to reason explicitly about each head before producing the structured output, leveraging chain-of-thought capability.")

## Context

The first live eval against the 15 golden fixtures (`backend/eval/reports/golden-20260519T231301Z.md`) revealed a structural failure pattern, not a regex / vocab / individual-prompt issue:

- The receptivity head returned `score=0.30, categorical_state="open_to_reflection"` for **five** very different inputs (active SI, dissociation, active distress, explicit reflection invitation, neutral journaling). Five points in receptivity space, one output.
- The orchestration head returned `safety_flags=[]` even when the fixture's state document explicitly teed up egosyntonic-collusion content — *and* the network head had identified `pride_restriction`, `pride_control`, `cognition_rules_as_identity` as active nodes.

This was structured-output-vs-chain-of-thought conflict. The Gemini Pro reasoning call runs with `response_mime_type=application/json` plus a Pydantic-derived schema. In strict JSON mode the model emits tokens in schema-property order. Our v1 schema put `rationale` LAST in each head:

```
ReceptivityHead { score, categorical_state, actionability, rationale }
```

So the model committed to `score` and `categorical_state` *before* it had reasoned about them, then wrote a plausible-sounding `rationale` that didn't actually drive the answer. The result: structured fields default to the safest-looking values (low intensity, no flags, mid receptivity), and the rationale becomes ornamental.

## Decision

1. **Reorder schemas so `rationale` is the FIRST property** (and first in the `required` array) in every head and in `orchestration`. The model must emit rationale text before any structured commitment, which forces CoT to actually drive the structured fields.
2. **Mirror the reorder in `backend/reasoning/pipeline/types.py`** Pydantic Field declarations — Pydantic's JSON schema generation walks Field order, which propagates to the schema passed to Gemini.
3. **Rewrite `backend/reasoning/prompts/reasoning.v1.j2` around CoT-first principles**: calibration tables with score ranges per categorical state, 4–5 worked input→rationale→output examples per head, explicit "write rationale citing evidence, then commit" instruction, and explicit safety_flags trigger rules with collusion-risk examples.
4. **Add `rationale` as a required field on `Orchestration`** (it was absent in v1.0.0). The intensity + safety_flags choices need their own CoT — that's where egosyntonic_collusion_risk gets caught.

## Consequences

**Positive**
- The receptivity head's output distribution should mirror the input distribution rather than collapsing to a constant. Validated against the eval's five canonical cases (SI, dissociation, distress, reflection-invitation, neutral) in worked examples in the prompt.
- safety_flags become discoverable from the prompt's worked examples, not just from prose descriptions of the enum.
- The `rationale` fields become readable diagnostic surface — they explain why a turn was scored where it was, which is the kind of thing the eval reports + later clinical-advisor reviews need.

**Negative**
- Output token count per turn goes up modestly (rationales are longer when they actually drive the answer). Cost impact: probably 5–15% on the reasoning call; small in absolute terms.
- Five reasoning sections × meaningful rationale ≈ more text the model has to keep coherent across. If the receptivity head still flattens after this, the next move is splitting the four heads into separate Gemini calls in parallel (a real refactor; deferred unless needed).

**Neutral**
- `schema_version` stays at `1.0.0` — no consumer has shipped yet, this is in-flight design evolution. Prompt template version bumps to `2.0.0` for clarity.
- The four heads + orchestration in one call architecture stays. We're tuning the prompt, not splitting.

## Verification

Re-run `uv run python -m reasoning.eval.run_golden` after this lands. The baseline was 3/15 passing. Target for this change alone: ≥10/15. If the receptivity head still produces a constant after rationale-first + worked examples, the next ADR will propose splitting heads into parallel Gemini calls.

Also closes two false-positive runner bugs that ADR-0001-era eval surfaced:

1. `backend/reasoning/pipeline/critic.py` now accepts `used_safety_template: bool` and skips the critic LLM call when the response is a safety template (the post-filter still runs). Fixed-text templates aren't subject to the critic's intensity / insight judgments.
2. `backend/reasoning/eval/run_golden.py` skips `extraction.*` and reasoning-head plan assertions when `used_safety_template=True` — those stages were bypassed and assertions on them aren't meaningful.
