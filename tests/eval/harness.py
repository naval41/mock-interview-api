"""Layer 2 — phase-transition decision eval harness.

Frames the LLM behavior we care about as a classification problem:

    input   : { phase_type, elapsed_seconds, phase_duration, transcript_tail }
    decision: NO_CALL | CALL(candidate_ready) | CALL(inferred)
    expected: the label a correct interviewer bot should produce

This module holds the **framework** (types, scoring, aggregation). It is model
agnostic: a "decider" is any callable ``EvalCase -> Decision``. The deterministic
tests use a rule-based reference decider (so they gate the build with no network);
``run_llm_eval.py`` plugs in the real Gemini model.

Metrics are chosen around the two harms from the incident:
* ``false_transition_rate`` — inferred CALL when the answer was NO_CALL
  (the original bug: abandoning a candidate mid-problem).
* ``stuck_candidate_recall`` — of the cases where the candidate explicitly asked
  to move on, how many were honored with CALL(candidate_ready). A miss here is
  the "stuck candidate loses time on the next problem" harm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


class Label(str, Enum):
    """Expected/target decision classes."""

    NO_CALL = "NO_CALL"                       # stay in the current phase
    CALL_CANDIDATE_READY = "CALL_CANDIDATE_READY"  # explicit request -> move on
    CALL_INFERRED = "CALL_INFERRED"           # objectives genuinely complete -> move on


# Transition reasons that count as an explicit candidate request.
CANDIDATE_REQUESTED_REASONS = {"candidate_ready"}


@dataclass(frozen=True)
class Decision:
    """A decider's output for one case."""

    call: bool
    reason: Optional[str] = None  # transition_reason when call is True

    def to_label(self) -> Label:
        if not self.call:
            return Label.NO_CALL
        if self.reason in CANDIDATE_REQUESTED_REASONS:
            return Label.CALL_CANDIDATE_READY
        return Label.CALL_INFERRED


@dataclass(frozen=True)
class EvalCase:
    """One labeled scenario the interviewer bot must react to."""

    id: str
    phase_type: str            # "CODING" | "SYSTEM_DESIGN" | "BEHAVIORAL" | "INTRO" | ...
    phase_duration_min: int
    elapsed_seconds: int
    transcript_tail: str       # last few conversational turns
    expected: Label
    notes: str = ""
    tags: tuple = field(default_factory=tuple)


Decider = Callable[[EvalCase], Decision]


@dataclass
class CaseResult:
    case: EvalCase
    decision: Decision
    predicted: Label

    @property
    def correct(self) -> bool:
        return self.predicted == self.case.expected


@dataclass
class EvalReport:
    results: List[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def accuracy(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.correct for r in self.results) / self.total

    @property
    def false_transition_rate(self) -> float:
        """Fraction of NO_CALL cases where the decider wrongly transitioned on an
        inferred signal. This is the original bug; target is 0."""
        denom = [r for r in self.results if r.case.expected == Label.NO_CALL]
        if not denom:
            return 0.0
        bad = [r for r in denom if r.predicted == Label.CALL_INFERRED]
        return len(bad) / len(denom)

    @property
    def stuck_candidate_recall(self) -> float:
        """Of cases where the candidate explicitly asked to move on, the fraction
        honored. A miss traps a stuck candidate; target is 1.0."""
        denom = [r for r in self.results if r.case.expected == Label.CALL_CANDIDATE_READY]
        if not denom:
            return 1.0
        hit = [r for r in denom if r.predicted == Label.CALL_CANDIDATE_READY]
        return len(hit) / len(denom)

    @property
    def confusion(self) -> Dict[str, Dict[str, int]]:
        labels = [l.value for l in Label]
        matrix = {a: {b: 0 for b in labels} for a in labels}
        for r in self.results:
            matrix[r.case.expected.value][r.predicted.value] += 1
        return matrix

    def failures(self) -> List[CaseResult]:
        return [r for r in self.results if not r.correct]


def run_eval(cases: List[EvalCase], decider: Decider) -> EvalReport:
    """Run every case through ``decider`` and collect a scored report."""
    results = []
    for case in cases:
        decision = decider(case)
        results.append(
            CaseResult(case=case, decision=decision, predicted=decision.to_label())
        )
    return EvalReport(results=results)
