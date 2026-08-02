"""Layer 1 — deterministic guard tests for the premature phase-transition fix.

These pin the *code enforcement* in ``InterviewTimerMonitor``:

* Guard #1: inferred LLM transitions are rejected before a phase has run long
  enough (stricter floor for coding/design phases).
* The escape hatch: an explicit candidate request (``candidate_ready``) always
  passes, so a stuck candidate is never trapped and never loses time on the
  next problem.
* The timer-expiry path is never gated by the guard.

Pure logic, no network, no model — these run in milliseconds and gate the
Docker image build.
"""

import pytest

from app.interview_playground.timer.interview_timer_monitor import (
    MIN_ELAPSED_FLOOR_SECONDS,
    MIN_ELAPSED_FRACTION_CODING,
    MIN_ELAPSED_FRACTION_DEFAULT,
)
from app.models.enums import ToolName
from tests.support.builders import (
    make_context,
    make_planner_field,
    make_timer_monitor,
)

pytestmark = pytest.mark.unit

CODE_TOOLS = [ToolName.CODE_EDITOR]
DESIGN_TOOLS = [ToolName.DESIGN_EDITOR]
NO_TOOLS: list = []  # behavioral / intro / qna

CAND_ID = "cand-1"


def _two_phase_context(*, current_duration_min: int, current_tools, current_seq: int = 2):
    """A context with a current phase (seq=2) and a next phase (seq=3) so a
    transition target always exists."""
    fields = [
        make_planner_field(sequence=current_seq, duration_minutes=current_duration_min, tools=current_tools),
        make_planner_field(sequence=current_seq + 1, duration_minutes=25, tools=CODE_TOOLS),
    ]
    return make_context(fields, current_sequence=current_seq, candidate_interview_id=CAND_ID)


# --------------------------------------------------------------------------- #
# Minimum-duration computation
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "duration_min, tools, expected_min_seconds",
    [
        # Coding: 50% of duration, floored at 60s.
        (25, CODE_TOOLS, int(25 * 60 * MIN_ELAPSED_FRACTION_CODING)),   # 750
        (10, CODE_TOOLS, int(10 * 60 * MIN_ELAPSED_FRACTION_CODING)),   # 300
        (1, CODE_TOOLS, MIN_ELAPSED_FLOOR_SECONDS),                      # 30s -> floored to 60
        # Design uses the coding fraction too.
        (20, DESIGN_TOOLS, int(20 * 60 * MIN_ELAPSED_FRACTION_CODING)),  # 600
        # Non-coding: 20% of duration, floored at 60s.
        (25, NO_TOOLS, int(25 * 60 * MIN_ELAPSED_FRACTION_DEFAULT)),     # 300
        (5, NO_TOOLS, MIN_ELAPSED_FLOOR_SECONDS),                        # 60s -> floor
    ],
)
def test_minimum_elapsed_seconds_by_phase_type(duration_min, tools, expected_min_seconds):
    ctx = _two_phase_context(current_duration_min=duration_min, current_tools=tools)
    monitor = make_timer_monitor(ctx, elapsed_seconds=0)
    assert monitor._minimum_elapsed_seconds_for_current_phase() == expected_min_seconds


# --------------------------------------------------------------------------- #
# The core behavior table: (phase, duration, elapsed, reason) -> allow?
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "label, duration_min, tools, elapsed_s, reason, expected_allow",
    [
        # --- Behavior 1: inferred transitions on coding phases are gated ---
        ("coding inferred, too early", 25, CODE_TOOLS, 189, "natural_breakpoint", False),
        ("coding inferred, just under 50%", 25, CODE_TOOLS, 749, "objectives_complete", False),
        ("coding inferred, at 50%", 25, CODE_TOOLS, 750, "objectives_complete", True),
        ("coding inferred, well past 50%", 25, CODE_TOOLS, 1200, "natural_breakpoint", True),
        ("coding 'other' reason, early", 25, CODE_TOOLS, 100, "other", False),
        ("coding reason=None, early", 25, CODE_TOOLS, 100, None, False),

        # --- Behavior 2: explicit candidate request bypasses the floor ---
        ("stuck candidate asks to move on, 3s in", 25, CODE_TOOLS, 3, "candidate_ready", True),
        ("candidate ready, mid-phase", 25, CODE_TOOLS, 400, "candidate_ready", True),
        ("candidate ready on design phase, early", 20, DESIGN_TOOLS, 10, "candidate_ready", True),

        # --- Non-coding phases: looser 20% floor ---
        ("intro inferred, past floor", 5, NO_TOOLS, 217, "objectives_complete", True),
        ("intro inferred, under 60s floor", 5, NO_TOOLS, 30, "objectives_complete", False),
        ("behavioral inferred, under 20%", 25, NO_TOOLS, 200, "natural_breakpoint", False),
        ("behavioral inferred, past 20%", 25, NO_TOOLS, 301, "natural_breakpoint", True),
    ],
)
def test_can_transition_behavior_table(
    label, duration_min, tools, elapsed_s, reason, expected_allow
):
    ctx = _two_phase_context(current_duration_min=duration_min, current_tools=tools)
    monitor = make_timer_monitor(ctx, elapsed_seconds=elapsed_s)

    allowed = monitor.can_transition(CAND_ID, current_phase_sequence=2, transition_reason=reason)
    assert allowed is expected_allow, f"case failed: {label}"


# --------------------------------------------------------------------------- #
# Golden regression: the exact interview that triggered this work
# --------------------------------------------------------------------------- #

def test_golden_regression_interview_60abce19():
    """Reproduces candidate_interview_id 60abce19-b7b8-4a5e-99eb-27941b9c25c8.

    Problem 1 was a 25-minute CODING phase. The LLM called
    transition_to_next_phase with an inferred 'natural_breakpoint' after only
    189 seconds (~12.6%), abandoning the candidate mid-problem. The guard must
    reject that transition.
    """
    ctx = _two_phase_context(current_duration_min=25, current_tools=CODE_TOOLS)
    monitor = make_timer_monitor(ctx, elapsed_seconds=189)

    # The bug: inferred transition 189s into a 25-min problem -> must be rejected.
    assert monitor.can_transition(CAND_ID, 2, transition_reason="natural_breakpoint") is False

    # The fairness requirement: had the candidate *asked* to move on at the same
    # moment (e.g. "I don't know this one"), it must be honored immediately.
    assert monitor.can_transition(CAND_ID, 2, transition_reason="candidate_ready") is True


# --------------------------------------------------------------------------- #
# Guard must not mask the pre-existing validity checks
# --------------------------------------------------------------------------- #

def test_rejects_on_candidate_id_mismatch_even_when_time_ok():
    ctx = _two_phase_context(current_duration_min=25, current_tools=CODE_TOOLS)
    monitor = make_timer_monitor(ctx, elapsed_seconds=1200)  # well past the floor
    assert monitor.can_transition("someone-else", 2, transition_reason="candidate_ready") is False


def test_rejects_on_sequence_mismatch():
    ctx = _two_phase_context(current_duration_min=25, current_tools=CODE_TOOLS)
    monitor = make_timer_monitor(ctx, elapsed_seconds=1200)
    assert monitor.can_transition(CAND_ID, 99, transition_reason="candidate_ready") is False


def test_rejects_when_no_next_phase_available():
    """Last phase has no successor; even a candidate request cannot transition."""
    fields = [make_planner_field(sequence=2, duration_minutes=25, tools=CODE_TOOLS)]
    ctx = make_context(fields, current_sequence=2, candidate_interview_id=CAND_ID)
    monitor = make_timer_monitor(ctx, elapsed_seconds=1200)
    assert monitor.can_transition(CAND_ID, 2, transition_reason="candidate_ready") is False
