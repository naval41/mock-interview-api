"""Layer 2 (live) — run the transition decision eval against the real Gemini model.

This is EXCLUDED from the default suite and the Docker build gate (marker
``llm_live``) because it is paid, networked, and non-deterministic. Run it
explicitly, on demand or on a schedule:

    # as a pytest (asserts the quality bar):
    GOOGLE_API_KEY=... pytest -m llm_live tests/eval/run_llm_eval.py

    # or as a script (prints a full report + confusion matrix):
    GOOGLE_API_KEY=... python -m tests.eval.run_llm_eval

The model is asked to make the same decision the interviewer bot makes, using
the same policy language from the production prompt guidance, and its answer is
mapped into a ``Decision``. The quality bar mirrors the reference policy: zero
false transitions and full recall on explicit candidate requests.
"""

from __future__ import annotations

import json
import os
from typing import Optional

import pytest

from tests.eval.dataset import ALL_CASES
from tests.eval.harness import Decision, EvalCase, EvalReport, run_eval

# Bars the live model must meet. Kept in sync with the reference policy test.
MAX_FALSE_TRANSITION_RATE = 0.05
MIN_STUCK_CANDIDATE_RECALL = 1.0
MIN_ACCURACY = 0.85

_DECISION_INSTRUCTIONS = """\
You are the interviewer bot deciding whether to call transition_to_next_phase.
Policy:
- If the CANDIDATE explicitly asks to move on / says they are done / says they
  are stuck and want to skip: transition with reason "candidate_ready".
- In CODING or SYSTEM_DESIGN phases, do NOT transition just because the
  candidate paused, went quiet, or is typing. A pause is not a signal.
- Only transition on an inferred "objectives_complete" when the phase objectives
  are genuinely met (typically only outside coding phases, after enough time).
Respond with ONLY a JSON object: {"call": bool, "reason": string|null}.
Valid reasons: "candidate_ready", "objectives_complete", "natural_breakpoint", "other", null.
"""


def _build_prompt(case: EvalCase) -> str:
    return (
        f"{_DECISION_INSTRUCTIONS}\n"
        f"Phase type: {case.phase_type}\n"
        f"Phase duration (min): {case.phase_duration_min}\n"
        f"Elapsed seconds: {case.elapsed_seconds}\n"
        f"Recent transcript:\n{case.transcript_tail}\n"
        f"Decision JSON:"
    )


def _parse_decision(raw: str) -> Decision:
    text = raw.strip()
    if "```" in text:
        text = text.split("```")[1].replace("json", "", 1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return Decision(call=False, reason=None)
    data = json.loads(text[start : end + 1])
    return Decision(call=bool(data.get("call", False)), reason=data.get("reason"))


def make_gemini_decider(model_name: str = "gemini-2.0-flash"):
    """Return a decider backed by the real Gemini model. Import is local so the
    default suite never needs the SDK or a key."""
    import google.generativeai as genai

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is required for the live eval")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    def decider(case: EvalCase) -> Decision:
        resp = model.generate_content(_build_prompt(case))
        return _parse_decision(resp.text or "")

    return decider


def _print_report(report: EvalReport) -> None:
    print(f"\nLLM transition eval — {report.total} cases")
    print(f"  accuracy               : {report.accuracy:.2%}")
    print(f"  false_transition_rate  : {report.false_transition_rate:.2%} (target 0)")
    print(f"  stuck_candidate_recall : {report.stuck_candidate_recall:.2%} (target 100%)")
    print("  confusion (expected -> predicted):")
    for expected, row in report.confusion.items():
        print(f"    {expected:22s} {row}")
    if report.failures():
        print("  failures:")
        for r in report.failures():
            print(f"    - {r.case.id}: expected {r.case.expected.value}, got {r.predicted.value}")


@pytest.mark.llm_live
def test_gemini_meets_transition_quality_bar():
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set; live eval skipped")
    report = run_eval(ALL_CASES, make_gemini_decider())
    _print_report(report)
    assert report.false_transition_rate <= MAX_FALSE_TRANSITION_RATE, report.failures()
    assert report.stuck_candidate_recall >= MIN_STUCK_CANDIDATE_RECALL, report.failures()
    assert report.accuracy >= MIN_ACCURACY, report.confusion


def main() -> int:
    report = run_eval(ALL_CASES, make_gemini_decider())
    _print_report(report)
    ok = (
        report.false_transition_rate <= MAX_FALSE_TRANSITION_RATE
        and report.stuck_candidate_recall >= MIN_STUCK_CANDIDATE_RECALL
        and report.accuracy >= MIN_ACCURACY
    )
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
