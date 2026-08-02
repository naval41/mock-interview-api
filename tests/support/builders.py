"""Test builders for phase-transition tests.

These construct **real** ``InterviewContext`` / ``PlannerField`` objects (not
mocks) so the tests exercise the same validation and accessors the production
code uses. Only the wall-clock (``get_timer_status``) is stubbed, because that is
the single non-deterministic input to the transition guard.
"""

from __future__ import annotations

from typing import List, Optional

from app.entities.interview_context import InterviewContext, PlannerField
from app.interview_playground.timer.interview_timer_monitor import InterviewTimerMonitor
from app.models.enums import ToolName


def make_planner_field(
    *,
    sequence: int,
    duration_minutes: int,
    tools: Optional[List[ToolName]] = None,
    tool_properties: Optional[dict] = None,
    question_id: str = "q-1",
) -> PlannerField:
    """Build a PlannerField with sensible defaults for tests."""
    return PlannerField(
        question_id=question_id,
        knowledge_bank_id="kb-1",
        interview_instructions="do the thing",
        duration=duration_minutes,
        tool_name=list(tools) if tools else [],
        tool_properties=tool_properties,
        sequence=sequence,
    )


def make_context(
    planner_fields: List[PlannerField],
    *,
    current_sequence: int,
    candidate_interview_id: str = "cand-1",
) -> InterviewContext:
    """Build an InterviewContext positioned at ``current_sequence``."""
    ctx = InterviewContext(
        mock_interview_id="mock-1",
        user_id="user-1",
        session_id="sess-1",
        interview_planner_id="planner-1",
        candidate_interview_id=candidate_interview_id,
        current_workflow_step_sequence=current_sequence,
        planner_fields=list(planner_fields),
    )
    return ctx


def make_timer_monitor(
    context: InterviewContext,
    *,
    elapsed_seconds: int,
) -> InterviewTimerMonitor:
    """Build a timer monitor for ``context`` whose elapsed clock is pinned.

    The monitor is created without running its asyncio timer machinery; we only
    need the pure decision logic (``can_transition`` / ``_check_minimum_duration``
    / ``_minimum_elapsed_seconds_for_current_phase``). ``get_timer_status`` — the
    only source of wall-clock time in that path — is replaced with a stub so
    tests are fully deterministic.
    """
    monitor = InterviewTimerMonitor(interview_context=context)
    monitor.get_timer_status = lambda: {  # type: ignore[method-assign]
        "elapsed_time_seconds": elapsed_seconds,
        "is_running": True,
        "is_paused": False,
    }
    return monitor
