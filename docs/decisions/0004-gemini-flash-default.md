# ADR-0004: Gemini 2.5 Flash (thinking on) as the default for every pipeline stage

- Status: Accepted
- Date: 2026-05-19
- Amends: `docs/idea.md` §11 (which named "Gemini 2.5 Pro for reasoning and critic calls, Gemini Flash for feature extraction and generation")

## Context

After ADR-0003 unblocked the reasoning parser and the golden eval reflected real model behavior (12/15 PASS, 9.6 min wall clock, ~$2 spend on Pro), the next concern was latency. `docs/idea.md` §11.2 names a "user-visible response within 5s at p95" target, but Gemini 2.5 family models default to thinking mode, which puts every Pro reasoning + critic call in the 10–30s range. Median per-turn wall clock on the golden eval was 42s.

Two A/B experiments ran against the 15 golden fixtures:

| Config | Pass | Median | Mean | Cost (rel) |
|---|---:|---:|---:|---:|
| Gemini 2.5 Pro + thinking | 12/15 | 42.5s | 44.2s | ~10× |
| Gemini 2.5 Flash + thinking | 11/15 | 37.9s | 35.5s | 1× |
| Gemini 2.5 Flash + `thinking_budget=0` | 9/15 | 14.1s | 14.2s | ~0.3× |

The single fixture lost between Pro+thinking and Flash+thinking is `low-receptivity-dissociation` — Flash misjudged dissociation cues that Pro caught. The three additional fixtures lost between Flash+thinking and Flash+no-thinking are all *orchestration-synthesis* cases — `egosyntonic-restriction-as-control`, `general-egosyntonic-overwork`, `ed-numerical-exercise-duration` — where the model needs to integrate the four head outputs and arrive at correct safety_flags from indirect phrasing. Thinking is doing real work there.

## Decision

1. **Set Gemini 2.5 Flash as the default for every pipeline stage** — reasoning, critic, extraction, generation. All four default to `gemini-2.5-flash` via `backend/reasoning/config.py`.
2. **Keep thinking on (SDK default).** A new `EGOSYN_THINKING_BUDGET` env var allows per-deploy override (set to `0` to disable, or a positive integer to cap), but unset means SDK default. The 11/15 → 9/15 drop without thinking is too large for a wellness-positioned product where the failing cases are exactly the ones that test the egosyntonic-collusion thesis.
3. **Document Pro as an opt-in upgrade** for specific stages where quality regression is observed. The `EGOSYN_MODEL_*` env vars are per-stage overridable; if eval data on a future regression points at the reasoning head specifically, we can flip just that stage to Pro.

## Consequences

**Positive**
- Per-call cost drops ~10×. Phase 1 corpus eval (200 utterances) would cost ~$0.20 instead of ~$2, and per-user-per-day cost stays well under budget.
- Median latency drops 25% vs Pro, bringing per-turn cost-of-attention slightly under 40s. Still over the `idea.md` §11.2 target of 5s, but in a better neighborhood.
- The pipeline becomes single-tier on the model side. Operations, billing, rate-limit management all simplify.

**Negative**
- One fixture (`low-receptivity-dissociation`) regressed from PASS on Pro to FAIL on Flash. Low-receptivity dissociation detection is a real product concern but the failure was a 1-assertion miss on receptivity-state categorization, not a safety-critical misclassification. Tracked; tunable via prompt rather than model swap.
- We accept the latency target in `idea.md` §11.2 is not achievable at v1 with thinking-mode LLMs. The 5s target predates this generation of models. Real options for closing the gap are SSE generation streaming (cheap, perceived-latency win) or a complexity router (real refactor); both deferred.

**Neutral**
- `EGOSYN_THINKING_BUDGET` env var is added but unset by default. The infrastructure to disable thinking is in place if a future deploy wants to trade quality for latency on a specific stage.
- `EGOSYN_MODEL_REASONING` etc. remain per-stage overridable. Anyone running a high-stakes evaluation can flip a stage back to Pro for a clean A/B.

## Verification

Re-run `uv run python -m reasoning.eval.run_golden` against the new defaults. Target: 11/15 PASS, median latency ~38s. Variations on the three fixtures that fail with both Pro and Flash (`behavior-log-loose-lunch`, `egosyntonic-proud-of-discipline`, `established-echo-eligible`) are independent of this decision and will be addressed via prompt/fixture tuning.

## Lessons

- **Thinking is a knob, not a model property.** Treating "use Pro" as the latency variable conflated two things; the actual lever is `thinking_budget`. Capturing this in code (the new env var) means we don't conflate them again.
- **The 5s target in `idea.md` §11.2 is from a pre-thinking-mode design.** Either we ship streaming generation for perceived latency, or we update the target. Defer until we have user-facing evidence on which matters more.
- **Pro is now a precision tool**, not a default. Use it where a specific eval regression points to a specific stage. The 10× cost differential makes default-Pro unattractive at the volume Phase 1 will see.
