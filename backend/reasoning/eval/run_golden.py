"""Run the live pipeline against every fixture in backend/eval/golden/
and check each fixture's assertions. Produces a pass/fail summary plus a
markdown report with per-fixture detail.

This is Phase 1 exit verification (task #11). Reuses the prompts under
backend/reasoning/prompts/ via the live_llm mode (no GCP storage needed).

Each fixture supplies its own `state_summary` and `retrieved_items_by_head`,
so the runner BYPASSES the actual retrieval + state-document layers and
feeds those inputs directly to the reasoning prompt. This is intentional:
it isolates prompt quality from the storage layer (which is still being
wired in tasks #14/#15).

Usage:
    cd backend
    uv run python -m reasoning.eval.run_golden            # all fixtures
    uv run python -m reasoning.eval.run_golden crisis     # only IDs matching 'crisis'
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import Settings, get_settings
from ..logging_setup import configure_logging, get_logger
from ..pipeline import critic, extraction, generation, reasoning
from ..pipeline.types import (
    GenerationOutput,
    ReasoningPlan,
    RetrievalBundle,
    RetrievedItem,
    TurnInput,
)
from ..safety import (
    SafetyCategory,
    classify_safety_signals,
    get_template_for_classification,
)

log = get_logger(__name__)

# backend/reasoning/eval/run_golden.py → parents[2] = backend/
_BACKEND = Path(__file__).resolve().parents[2]
_FIXTURES_DIR = _BACKEND / "eval" / "golden"
_REPORTS_DIR = _BACKEND / "eval" / "reports"
_RUNS_DIR = _BACKEND / "eval" / "runs"
_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
_RUNS_DIR.mkdir(parents=True, exist_ok=True)


# --- Fixture model ---


@dataclass(slots=True)
class FixtureResult:
    fixture_id: str
    category: str
    passed: bool
    assertion_results: list[tuple[str, bool, str]]  # (label, passed, detail)
    turn_latency_ms: int
    used_safety_template: bool
    safety_flags: list[str]
    intervention_intensity: str
    receptivity_score: float
    receptivity_state: str
    critic_passed: bool
    critic_flags: list[str]
    response_text: str
    extraction_summary: dict[str, Any]
    error: str | None = None


# --- Pipeline driver that respects fixture-supplied state ---


def _build_retrieval_bundle(items_by_head: dict[str, list[dict[str, Any]]]) -> RetrievalBundle:
    bundle: dict[str, list[RetrievedItem]] = {}
    for head, items in items_by_head.items():
        bundle[head] = [
            RetrievedItem(
                ref_type=item.get("ref_type", "utterance"),
                ref_id=item["ref_id"],
                excerpt=item["excerpt"],
                occurred_at=datetime.fromisoformat(item["occurred_at"].replace("Z", "+00:00")),
                score=item.get("score", 0.5),
                head_origin=head,  # type: ignore[arg-type]
            )
            for item in items
        ]
    # Ensure all four heads present
    for head in ("receptivity", "dynamical", "network", "sdt"):
        bundle.setdefault(head, [])
    return RetrievalBundle(items_by_head=bundle)


async def _run_fixture(
    fixture: dict[str, Any],
    settings: Settings,
) -> tuple[str, ReasoningPlan, GenerationOutput, Any, dict[str, Any], int, bool]:
    """Run the pipeline for a single fixture. Returns
    (response_text, plan, generation, critic_verdict, extraction_dict, latency_ms, used_safety_template).
    """
    inp = fixture["input"]
    started = time.perf_counter()

    turn = TurnInput(
        user_id="golden-runner",
        session_id=f"golden-{fixture['fixture_id']}",
        utterance_text=inp["utterance_text"],
    )

    # Pre-pipeline safety classifier (real, deterministic regex)
    safety = await classify_safety_signals(turn.utterance_text, settings)
    if safety.any_fired:
        template = get_template_for_classification(safety.primary)
        # Synthesize a plan stamped with the safety flag (matches orchestrator behavior)
        from ..pipeline.types import (  # noqa: PLC0415
            DynamicalHead,
            NetworkHead,
            Orchestration,
            ReceptivityHead,
            SDTHead,
        )
        flag_map = {
            SafetyCategory.ACTIVE_SUICIDAL_IDEATION: "active_suicidal_ideation",
            SafetyCategory.SELF_HARM_INTENT: "self_harm_intent",
            SafetyCategory.MEDICAL_ACUTE: "medical_instability",
            SafetyCategory.ASKING_FOR_METHODS: "asking_for_methods",
            SafetyCategory.ASKING_FOR_NUMBERS: "asking_for_numbers",
        }
        flag = flag_map.get(safety.primary)
        plan = ReasoningPlan(
            turn_id=f"golden-{fixture['fixture_id']}",
            produced_at=datetime.now(UTC),
            model_id="safety-classifier",
            prompt_template_version="0",
            receptivity=ReceptivityHead(
                score=0.0,
                categorical_state="crisis",
                actionability=False,
                rationale="safety classifier short-circuit",
            ),
            dynamical_state=DynamicalHead(
                current_loop_id=None,
                stability=0.0,
                posture="support",
                rationale="bypassed",
            ),
            network=NetworkHead(active_nodes=[], rationale="bypassed"),
            sdt=SDTHead(thwarted_in=[], rationale="bypassed"),
            orchestration=Orchestration(
                rationale="Safety classifier short-circuit; reasoning bypassed.",
                intervention_intensity="none",
                safety_flags=[flag] if flag else [],
            ),
        )
        gen = GenerationOutput(
            response_text=template.body if template else "",
            surfaced_memory_ref_ids=[],
        )
        verdict = await critic.audit(turn, plan, gen, settings, used_safety_template=True)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return (gen.response_text, plan, gen, verdict, {}, latency_ms, True)

    # Standard path: extraction → (fixture retrieval) → reasoning → generation → critic
    extracted = await extraction.extract_features(
        turn,
        settings,
        conversational_context=inp.get("conversational_context", []),
        condition_pack=inp.get("condition_pack", "eating_disorder"),
    )

    retrieved = _build_retrieval_bundle(inp.get("retrieved_items_by_head", {}))

    plan = await reasoning.reason(
        turn,
        extracted,
        retrieved,
        settings,
        state_document_summary=inp.get("state_summary", "(empty)"),
        condition_pack=inp.get("condition_pack", "eating_disorder"),
        user_intensity_setting=inp.get("user_intensity_setting", "moderate"),
    )

    # If reasoning surfaced safety flags, use safety template for generation
    template_body = None
    if plan.orchestration.safety_flags:
        flag_to_category = {
            "active_suicidal_ideation": SafetyCategory.ACTIVE_SUICIDAL_IDEATION,
            "self_harm_intent": SafetyCategory.SELF_HARM_INTENT,
            "medical_instability": SafetyCategory.MEDICAL_ACUTE,
            "asking_for_methods": SafetyCategory.ASKING_FOR_METHODS,
            "asking_for_numbers": SafetyCategory.ASKING_FOR_NUMBERS,
        }
        for flag in plan.orchestration.safety_flags:
            cat = flag_to_category.get(flag)
            if cat:
                tpl = get_template_for_classification(cat)
                if tpl:
                    template_body = tpl.body
                    break

    gen = await generation.generate(
        turn,
        plan,
        settings,
        safety_template=template_body,
    )
    verdict = await critic.audit(
        turn, plan, gen, settings, used_safety_template=template_body is not None
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    extraction_summary = {
        "behaviors_referenced": [
            {"behavior_id": b.behavior_id, "stance": b.stance}
            for b in extracted.behaviors_referenced
        ],
        "network_nodes_activated": [n.node_id for n in extracted.network_nodes_activated],
        "implicated_need_states": [
            {"need": n.need, "domain": n.domain, "polarity": n.polarity}
            for n in extracted.implicated_need_states
        ],
        "safety_signals_active": extracted.safety_signals.any_active,
    }

    used_safety_template = template_body is not None
    return (gen.response_text, plan, gen, verdict, extraction_summary, latency_ms, used_safety_template)


# --- Assertion checking ---


def _check_assertions(
    fixture: dict[str, Any],
    response_text: str,
    plan: ReasoningPlan,
    verdict: Any,
    extraction_summary: dict[str, Any],
    used_safety_template: bool,
) -> list[tuple[str, bool, str]]:
    """Returns list of (label, passed, detail).

    When `used_safety_template=True`, extraction and most plan.* assertions
    are skipped — those stages were bypassed by the safety classifier
    short-circuit and any expectations on them are not meaningful. We still
    check the safety-relevant fields (safety_flags, critic.passed,
    generation forbidden phrases, used_safety_template itself).
    """
    results: list[tuple[str, bool, str]] = []
    expected = fixture.get("expected", {})

    # --- Extraction --- (skip entirely on safety short-circuit)
    ext_exp = expected.get("extraction", {}) if not used_safety_template else {}
    must_contain = ext_exp.get("must_contain", {})
    if "behaviors_referenced" in must_contain:
        expected_behaviors = must_contain["behaviors_referenced"]
        seen = {(b["behavior_id"], b["stance"]) for b in extraction_summary.get("behaviors_referenced", [])}
        missing = [b for b in expected_behaviors if (b["behavior_id"], b["stance"]) not in seen]
        results.append((
            "extraction.behaviors_referenced",
            not missing,
            f"missing: {missing}" if missing else "ok",
        ))
    if "network_nodes_activated" in must_contain:
        expected_nodes = set(must_contain["network_nodes_activated"])
        seen = set(extraction_summary.get("network_nodes_activated", []))
        missing = expected_nodes - seen
        results.append((
            "extraction.network_nodes_activated",
            not missing,
            f"missing: {sorted(missing)}" if missing else "ok",
        ))

    # --- Plan ---
    # On safety short-circuit, the reasoning heads were bypassed; only
    # `plan.orchestration.safety_flags_*` assertions remain meaningful.
    plan_exp = expected.get("plan", {})
    rcp_exp = plan_exp.get("receptivity", {}) if not used_safety_template else {}
    net_exp = plan_exp.get("network", {}) if not used_safety_template else {}
    orc_exp = plan_exp.get("orchestration", {})
    # receptivity score bounds
    if "score_max" in rcp_exp:
        ok = plan.receptivity.score <= rcp_exp["score_max"]
        results.append((
            "plan.receptivity.score_max",
            ok,
            f"got {plan.receptivity.score:.2f}, max {rcp_exp['score_max']}",
        ))
    if "score_min" in rcp_exp:
        ok = plan.receptivity.score >= rcp_exp["score_min"]
        results.append((
            "plan.receptivity.score_min",
            ok,
            f"got {plan.receptivity.score:.2f}, min {rcp_exp['score_min']}",
        ))
    if "categorical_state_in" in rcp_exp:
        ok = plan.receptivity.categorical_state in rcp_exp["categorical_state_in"]
        results.append((
            "plan.receptivity.categorical_state",
            ok,
            f"got {plan.receptivity.categorical_state}, allowed {rcp_exp['categorical_state_in']}",
        ))
    # network upstream target
    if "upstream_target_node_id_in" in net_exp:
        got = plan.network.upstream_target_node_id
        allowed = net_exp["upstream_target_node_id_in"]
        ok = got in allowed
        results.append((
            "plan.network.upstream_target_node_id",
            ok,
            f"got {got!r}, allowed {allowed}",
        ))
    # orchestration intensity
    if "intervention_intensity_in" in orc_exp:
        ok = plan.orchestration.intervention_intensity in orc_exp["intervention_intensity_in"]
        results.append((
            "plan.orchestration.intervention_intensity",
            ok,
            f"got {plan.orchestration.intervention_intensity}, allowed {orc_exp['intervention_intensity_in']}",
        ))
    if "intervention_intensity_max" in orc_exp:
        ladder = ["none", "presence", "light_reflection", "pattern_surfacing", "direct_invitation"]
        got_idx = ladder.index(plan.orchestration.intervention_intensity) if plan.orchestration.intervention_intensity in ladder else -1
        max_idx = ladder.index(orc_exp["intervention_intensity_max"])
        ok = got_idx <= max_idx
        results.append((
            "plan.orchestration.intervention_intensity_max",
            ok,
            f"got {plan.orchestration.intervention_intensity}, max {orc_exp['intervention_intensity_max']}",
        ))
    if "safety_flags_subset" in orc_exp:
        expected_flags = set(orc_exp["safety_flags_subset"])
        got_flags = set(plan.orchestration.safety_flags)
        missing = expected_flags - got_flags
        ok = not missing
        results.append((
            "plan.orchestration.safety_flags_subset",
            ok,
            f"missing: {sorted(missing)}" if missing else "ok",
        ))
    if "safety_flags_must_not_contain" in orc_exp:
        forbidden = set(orc_exp["safety_flags_must_not_contain"])
        got_flags = set(plan.orchestration.safety_flags)
        violations = forbidden & got_flags
        ok = not violations
        results.append((
            "plan.orchestration.safety_flags_must_not_contain",
            ok,
            f"present: {sorted(violations)}" if violations else "ok",
        ))

    # --- Generation ---
    gen_exp = expected.get("generation", {})
    forbidden_phrases = gen_exp.get("must_not_contain_phrases", [])
    if forbidden_phrases:
        violations = [p for p in forbidden_phrases if p.lower() in response_text.lower()]
        ok = not violations
        results.append((
            "generation.must_not_contain_phrases",
            ok,
            f"present: {violations}" if violations else "ok",
        ))
    must_contain_strings = gen_exp.get("must_contain_strings", [])
    if must_contain_strings:
        missing = [s for s in must_contain_strings if s.lower() not in response_text.lower()]
        ok = not missing
        results.append((
            "generation.must_contain_strings",
            ok,
            f"missing: {missing}" if missing else "ok",
        ))
    must_match = gen_exp.get("must_match_regex", [])
    for pat in must_match:
        ok = bool(re.search(pat, response_text, re.IGNORECASE))
        results.append((
            f"generation.must_match_regex:{pat[:30]}",
            ok,
            "match" if ok else "no match",
        ))

    # --- Critic ---
    crit_exp = expected.get("critic", {})
    if "passed" in crit_exp:
        ok = verdict.passed == crit_exp["passed"]
        results.append((
            "critic.passed",
            ok,
            f"got {verdict.passed}, expected {crit_exp['passed']}",
        ))
    if "flags_must_not_contain" in crit_exp:
        forbidden_flags = set(crit_exp["flags_must_not_contain"])
        got_flags = set(verdict.flags)
        violations = forbidden_flags & got_flags
        ok = not violations
        results.append((
            "critic.flags_must_not_contain",
            ok,
            f"present: {sorted(violations)}" if violations else "ok",
        ))

    # --- Safety template (implicit) ---
    if expected.get("used_safety_template") is not None:
        expected_used = expected["used_safety_template"]
        ok = used_safety_template == expected_used
        results.append((
            "used_safety_template",
            ok,
            f"got {used_safety_template}, expected {expected_used}",
        ))

    return results


async def _run_one(
    fixture_path: Path,
    settings: Settings,
) -> FixtureResult:
    fixture = json.loads(fixture_path.read_text())
    fixture_id = fixture["fixture_id"]
    category = fixture.get("category", "unknown")
    try:
        (
            response_text,
            plan,
            gen,
            verdict,
            extraction_summary,
            latency_ms,
            used_safety_template,
        ) = await _run_fixture(fixture, settings)
    except Exception as exc:  # noqa: BLE001
        log.exception("fixture_run_failed", fixture_id=fixture_id)
        return FixtureResult(
            fixture_id=fixture_id,
            category=category,
            passed=False,
            assertion_results=[],
            turn_latency_ms=0,
            used_safety_template=False,
            safety_flags=[],
            intervention_intensity="",
            receptivity_score=0.0,
            receptivity_state="",
            critic_passed=False,
            critic_flags=[],
            response_text="",
            extraction_summary={},
            error=str(exc),
        )

    assertions = _check_assertions(
        fixture,
        response_text,
        plan,
        verdict,
        extraction_summary,
        used_safety_template,
    )
    passed = all(a[1] for a in assertions)

    return FixtureResult(
        fixture_id=fixture_id,
        category=category,
        passed=passed,
        assertion_results=assertions,
        turn_latency_ms=latency_ms,
        used_safety_template=used_safety_template,
        safety_flags=list(plan.orchestration.safety_flags),
        intervention_intensity=plan.orchestration.intervention_intensity,
        receptivity_score=plan.receptivity.score,
        receptivity_state=plan.receptivity.categorical_state,
        critic_passed=verdict.passed,
        critic_flags=list(verdict.flags),
        response_text=response_text,
        extraction_summary=extraction_summary,
    )


async def main(filter_substr: str | None = None) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.llm_is_live:
        print("ERROR: needs EGOSYN_RUNTIME_MODE=live_llm (or live) in .env.local", file=sys.stderr)
        return 2

    fixture_paths = sorted(_FIXTURES_DIR.glob("*.json"))
    if filter_substr:
        fixture_paths = [p for p in fixture_paths if filter_substr in p.stem]

    if not fixture_paths:
        print(f"No fixtures matched filter {filter_substr!r}", file=sys.stderr)
        return 2

    print(f"Running {len(fixture_paths)} fixtures...\n")
    started = time.perf_counter()

    # Run sequentially to keep cost predictable + logs readable
    results: list[FixtureResult] = []
    for path in fixture_paths:
        result = await _run_one(path, settings)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        failed_assertions = [a for a in result.assertion_results if not a[1]]
        detail = (
            f" ({len(failed_assertions)} failed assertion{'s' if len(failed_assertions) != 1 else ''})"
            if failed_assertions
            else ""
        )
        print(f"  {status:4s}  {result.fixture_id}{detail}  ({result.turn_latency_ms} ms)")

    elapsed = time.perf_counter() - started

    # Write artifacts
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = _RUNS_DIR / f"golden-{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    turns_path = run_dir / "results.jsonl"
    with turns_path.open("w") as f:
        for r in results:
            f.write(json.dumps({
                "fixture_id": r.fixture_id,
                "category": r.category,
                "passed": r.passed,
                "assertion_results": r.assertion_results,
                "turn_latency_ms": r.turn_latency_ms,
                "used_safety_template": r.used_safety_template,
                "safety_flags": r.safety_flags,
                "intervention_intensity": r.intervention_intensity,
                "receptivity_score": r.receptivity_score,
                "receptivity_state": r.receptivity_state,
                "critic_passed": r.critic_passed,
                "critic_flags": r.critic_flags,
                "response_text": r.response_text,
                "extraction_summary": r.extraction_summary,
                "error": r.error,
            }) + "\n")

    report_path = _REPORTS_DIR / f"golden-{ts}.md"
    _write_report(report_path, results, elapsed)

    # Summary line
    passed_n = sum(1 for r in results if r.passed)
    print(f"\n{passed_n}/{len(results)} fixtures passed in {elapsed:.1f}s")
    print(f"  results: {turns_path.relative_to(_BACKEND)}")
    print(f"  report:  {report_path.relative_to(_BACKEND)}")
    return 0 if passed_n == len(results) else 1


def _write_report(path: Path, results: list[FixtureResult], elapsed_s: float) -> None:
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    md = [
        f"# Golden fixture eval — {datetime.now(UTC).isoformat()}",
        "",
        f"**Pass rate:** {passed}/{total} ({passed / max(total, 1):.0%})  ",
        f"**Elapsed:** {elapsed_s:.1f}s  ",
        "",
    ]

    # Category-level summary
    cat_counts: Counter[str] = Counter(r.category for r in results)
    cat_passes: Counter[str] = Counter(r.category for r in results if r.passed)
    md += [
        "## By category",
        "",
        "| Category | n | pass | rate |",
        "|---|---:|---:|---:|",
    ]
    for cat in sorted(cat_counts):
        n = cat_counts[cat]
        p = cat_passes[cat]
        md.append(f"| `{cat}` | {n} | {p} | {p / max(n, 1):.0%} |")

    # Latency
    latencies = sorted(r.turn_latency_ms for r in results if r.turn_latency_ms > 0)
    if latencies:
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        md += ["", f"**Latency** — p50 {p50}ms, p95 {p95}ms", ""]

    # Detail per fixture
    md += ["", "## Per-fixture detail", ""]
    for r in results:
        emoji = "PASS" if r.passed else "FAIL"
        md.append(f"### `{r.fixture_id}` — {emoji} ({r.category})")
        md.append("")
        if r.error:
            md.append(f"**Error:** `{r.error}`")
            md.append("")
            continue
        md.append(f"- intensity: `{r.intervention_intensity}` | receptivity: {r.receptivity_score:.2f} ({r.receptivity_state})")
        md.append(f"- safety_template_fired: {r.used_safety_template} | safety_flags: {r.safety_flags}")
        md.append(f"- critic.passed: {r.critic_passed} | critic.flags: {r.critic_flags}")
        md.append(f"- latency: {r.turn_latency_ms}ms")
        md.append("")
        md.append("**Assertions:**")
        for label, ok, detail in r.assertion_results:
            mark = "OK  " if ok else "FAIL"
            md.append(f"- `{mark}` `{label}` — {detail}")
        md.append("")
        md.append("**Response:**")
        md.append("```")
        md.append(r.response_text.strip())
        md.append("```")
        md.append("")
        md.append("**Extraction summary:**")
        md.append("```json")
        md.append(json.dumps(r.extraction_summary, indent=2))
        md.append("```")
        md.append("")
        md.append("---")
        md.append("")

    path.write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    filter_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(asyncio.run(main(filter_arg)))
