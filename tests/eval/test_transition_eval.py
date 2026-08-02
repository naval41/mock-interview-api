"""Layer 2 (deterministic) — validate the eval harness, dataset, and metrics.

These tests run in the build gate. They do NOT call any model. They assert:

* the dataset is well-formed and covers all three target behaviors,
* the harness scoring/metrics compute correctly (including on a deliberately
  buggy decider), and
* the reference policy achieves the quality bar on the dataset — which pins the
  bar the live Gemini eval must meet.

The real-model run lives in ``tests/eval/run_llm_eval.py`` (marked ``llm_live``,
excluded from the default suite).
"""

import pytest

from tests.eval.dataset import ALL_CASES
from tests.eval.harness import Decision, EvalCase, Label, run_eval
from tests.eval.reference_decider import reference_decider

pytestmark = pytest.mark.eval


# --------------------------------------------------------------------------- #
# Dataset integrity
# --------------------------------------------------------------------------- #

def test_dataset_ids_are_unique():
    ids = [c.id for c in ALL_CASES]
    assert len(ids) == len(set(ids)), "duplicate case ids in dataset"


def test_dataset_covers_all_three_behaviors():
    labels = {c.expected for c in ALL_CASES}
    assert Label.NO_CALL in labels
    assert Label.CALL_CANDIDATE_READY in labels
    assert Label.CALL_INFERRED in labels


def test_dataset_fields_are_sane():
    for c in ALL_CASES:
        assert c.phase_duration_min > 0
        assert c.elapsed_seconds >= 0
        assert c.transcript_tail.strip()


def test_golden_regression_case_present_and_labeled_no_call():
    golden = [c for c in ALL_CASES if c.id == "golden_60abce19_problem1_premature"]
    assert len(golden) == 1
    assert golden[0].expected == Label.NO_CALL


# --------------------------------------------------------------------------- #
# Harness / metric correctness (using synthetic deciders)
# --------------------------------------------------------------------------- #

def test_metrics_on_perfect_decider():
    perfect = run_eval(ALL_CASES, lambda case: _oracle(case))
    assert perfect.accuracy == 1.0
    assert perfect.false_transition_rate == 0.0
    assert perfect.stuck_candidate_recall == 1.0


def test_false_transition_rate_detects_the_original_bug():
    # A decider that always transitions on an inferred reason -> every NO_CALL
    # case becomes a false transition.
    always_inferred = run_eval(ALL_CASES, lambda case: Decision(call=True, reason="natural_breakpoint"))
    assert always_inferred.false_transition_rate == 1.0
    # And it never honors an explicit request as such.
    assert always_inferred.stuck_candidate_recall == 0.0


def test_stuck_candidate_recall_detects_trapping():
    # A decider that never calls -> traps every stuck candidate.
    never = run_eval(ALL_CASES, lambda case: Decision(call=False))
    assert never.stuck_candidate_recall == 0.0
    # But it also never falsely transitions.
    assert never.false_transition_rate == 0.0


# --------------------------------------------------------------------------- #
# The quality bar — pinned to the reference policy on the dataset.
# --------------------------------------------------------------------------- #

def test_reference_policy_meets_quality_bar():
    report = run_eval(ALL_CASES, reference_decider)
    assert report.false_transition_rate == 0.0, report.failures()
    assert report.stuck_candidate_recall == 1.0, report.failures()
    assert report.accuracy >= 0.95, report.confusion


def _oracle(case: EvalCase) -> Decision:
    """A perfect decider derived from the labels (for metric self-tests)."""
    if case.expected == Label.NO_CALL:
        return Decision(call=False)
    if case.expected == Label.CALL_CANDIDATE_READY:
        return Decision(call=True, reason="candidate_ready")
    return Decision(call=True, reason="objectives_complete")
