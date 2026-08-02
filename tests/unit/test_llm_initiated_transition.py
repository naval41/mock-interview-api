"""Layer 1 (async) — behavior of ``handle_llm_initiated_transition``.

Verifies the *outcome contract* the LLM sees, not just the boolean guard:

* A premature inferred transition returns ``status="rejected"`` and does NOT
  advance the phase (so the interview keeps running the current problem).
* An explicit candidate request advances the phase even early.

The transition side effects (timer teardown, instruction injection, SSE) are
stubbed so the test stays hermetic and focuses on the decision + contract.
"""

import pytest

from app.models.enums import ToolName
from tests.support.builders import make_context, make_planner_field, make_timer_monitor

pytestmark = pytest.mark.unit

CAND_ID = "cand-1"
CODE_TOOLS = [ToolName.CODE_EDITOR]


def _monitor_at(elapsed_seconds: int):
    fields = [
        make_planner_field(sequence=2, duration_minutes=25, tools=CODE_TOOLS),
        make_planner_field(sequence=3, duration_minutes=25, tools=CODE_TOOLS),
    ]
    ctx = make_context(fields, current_sequence=2, candidate_interview_id=CAND_ID)
    monitor = make_timer_monitor(ctx, elapsed_seconds=elapsed_seconds)

    # Stub the side-effecting parts of a real transition so we can assert on the
    # decision/contract without asyncio timers, DB, or SSE.
    async def _noop(*args, **kwargs):
        return None

    monitor.stop_current_timer = _noop  # type: ignore[method-assign]

    transitioned = {"called": False, "initiated_by": None}

    async def _fake_transition(initiated_by: str = "timer"):
        transitioned["called"] = True
        transitioned["initiated_by"] = initiated_by
        monitor.interview_context.move_to_next_sequence()

    monitor.transition_to_next_planner = _fake_transition  # type: ignore[method-assign]
    return monitor, transitioned


async def test_premature_inferred_transition_is_rejected_and_does_not_advance():
    monitor, transitioned = _monitor_at(elapsed_seconds=189)

    result = await monitor.handle_llm_initiated_transition(
        candidate_interview_id=CAND_ID,
        current_phase_sequence=2,
        transition_reason="natural_breakpoint",
    )

    assert result["status"] == "rejected"
    assert transitioned["called"] is False
    # Phase must not have advanced.
    assert monitor.interview_context.current_workflow_step_sequence == 2
    # The message must steer the model toward the candidate_ready escape hatch.
    assert "candidate_ready" in result["message"]


async def test_candidate_request_transitions_even_when_early():
    monitor, transitioned = _monitor_at(elapsed_seconds=5)

    result = await monitor.handle_llm_initiated_transition(
        candidate_interview_id=CAND_ID,
        current_phase_sequence=2,
        transition_reason="candidate_ready",
    )

    assert result["status"] == "success"
    assert transitioned["called"] is True
    assert transitioned["initiated_by"] == "llm"
    assert monitor.interview_context.current_workflow_step_sequence == 3
