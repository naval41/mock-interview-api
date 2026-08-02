"""A rule-based reference decider for the transition eval.

This is NOT the product model. It encodes the *policy we want* so that:

1. the harness, dataset, and metrics can be validated deterministically (and
   thus gate the build without any network call), and
2. it serves as the baseline bar the live Gemini decider must meet or beat in
   ``run_llm_eval.py``.

The rule is deliberately simple and mirrors the server-side guard:
* explicit candidate request in the transcript tail -> CALL(candidate_ready)
* coding/design phase with only an inferred signal -> NO_CALL
* non-coding phase past ~its natural point with objectives met -> CALL(inferred)
"""

from __future__ import annotations

from tests.eval.harness import Decision, EvalCase

_CODING_PHASES = {"CODING", "AI_ASSISTED_CODING", "SYSTEM_DESIGN"}

# Phrases that signal an explicit candidate request to move on / being done.
_REQUEST_PHRASES = (
    "move on",
    "next problem",
    "can we skip",
    "i'm done",
    "im done",
    "i am done",
    "let's continue",
    "lets continue",
    "let's start",
    "ready to start",
    "that covers it",
)


def _candidate_requested(transcript_tail: str) -> bool:
    text = transcript_tail.lower()
    # Only count phrases attributed to the candidate, not the interviewer.
    candidate_lines = [
        line for line in text.splitlines() if line.strip().startswith("candidate:")
    ]
    hay = "\n".join(candidate_lines) if candidate_lines else text
    return any(phrase in hay for phrase in _REQUEST_PHRASES)


def reference_decider(case: EvalCase) -> Decision:
    if _candidate_requested(case.transcript_tail):
        return Decision(call=True, reason="candidate_ready")

    # No explicit request: coding/design phases never transition on inference.
    if case.phase_type in _CODING_PHASES:
        return Decision(call=False)

    # Non-coding phase: allow an inferred completion once most of the (short)
    # phase has elapsed.
    if case.elapsed_seconds >= 0.5 * case.phase_duration_min * 60:
        return Decision(call=True, reason="objectives_complete")

    return Decision(call=False)
