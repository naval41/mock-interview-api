"""Labeled dataset for the phase-transition decision eval.

Each case describes a moment in an interview and the decision a correct bot
should make. Cases are grouped by the behavior they probe. Real production
transcripts can be appended here (see ``scripts/mine_transition_cases.py`` idea
in the README) — the ``golden_*`` cases below are harvested from actual
incidents and must never regress.

Keep this dataset in code (not a loose JSON blob) so it is type-checked and
reviewed like any other source.
"""

from __future__ import annotations

from typing import List

from tests.eval.harness import EvalCase, Label

# --------------------------------------------------------------------------- #
# Behavior 1: DO NOT transition on an inferred signal (pause / silence / typing)
# during a coding or design phase.
# --------------------------------------------------------------------------- #
_STAY_ON_CODING: List[EvalCase] = [
    EvalCase(
        id="pause_while_coding_early",
        phase_type="CODING",
        phase_duration_min=25,
        elapsed_seconds=180,
        transcript_tail=(
            "INTERVIEWER: Take your time, let me know when you're ready to discuss.\n"
            "CANDIDATE: (silence, typing)"
        ),
        expected=Label.NO_CALL,
        notes="A pause while coding is normal, not a signal to move on.",
        tags=("coding", "pause"),
    ),
    EvalCase(
        id="thinking_out_loud_midphase",
        phase_type="CODING",
        phase_duration_min=25,
        elapsed_seconds=420,
        transcript_tail=(
            "CANDIDATE: Hmm, let me think about the edge cases here...\n"
            "CANDIDATE: (long pause)"
        ),
        expected=Label.NO_CALL,
        notes="Candidate is actively reasoning; stay.",
        tags=("coding", "pause"),
    ),
    EvalCase(
        id="candidate_notices_new_problem_loaded",
        phase_type="CODING",
        phase_duration_min=25,
        elapsed_seconds=90,
        transcript_tail=(
            "CANDIDATE: Oh, I see a new problem showed up on the screen.\n"
            "INTERVIEWER: Yes, that's the problem for this phase."
        ),
        expected=Label.NO_CALL,
        notes="Noticing the editor loaded is not a request to move on.",
        tags=("coding",),
    ),
    EvalCase(
        id="design_quiet_while_drawing",
        phase_type="SYSTEM_DESIGN",
        phase_duration_min=30,
        elapsed_seconds=300,
        transcript_tail="CANDIDATE: (drawing on the canvas, quiet)",
        expected=Label.NO_CALL,
        tags=("design", "pause"),
    ),
]

# --------------------------------------------------------------------------- #
# Behavior 2: DO transition promptly when the candidate explicitly asks to move
# on — including the "I'm stuck" case, even very early in the phase.
# --------------------------------------------------------------------------- #
_CANDIDATE_REQUESTS: List[EvalCase] = [
    EvalCase(
        id="stuck_candidate_asks_to_skip",
        phase_type="CODING",
        phase_duration_min=25,
        elapsed_seconds=150,
        transcript_tail=(
            "CANDIDATE: Honestly I have no idea how to approach this one. "
            "Can we move on to the next problem?"
        ),
        expected=Label.CALL_CANDIDATE_READY,
        notes="Stuck candidate; honoring this preserves time for the next problem.",
        tags=("coding", "explicit-request", "stuck"),
    ),
    EvalCase(
        id="candidate_says_done",
        phase_type="CODING",
        phase_duration_min=25,
        elapsed_seconds=900,
        transcript_tail=(
            "CANDIDATE: I've tested it and I'm happy with this solution. "
            "I'm done, we can move on."
        ),
        expected=Label.CALL_CANDIDATE_READY,
        tags=("coding", "explicit-request"),
    ),
    EvalCase(
        id="candidate_ready_after_intro",
        phase_type="INTRO",
        phase_duration_min=5,
        elapsed_seconds=140,
        transcript_tail="CANDIDATE: That's me in a nutshell — ready to start the coding.",
        expected=Label.CALL_CANDIDATE_READY,
        tags=("intro", "explicit-request"),
    ),
    EvalCase(
        id="behavioral_candidate_nothing_to_add",
        phase_type="BEHAVIORAL",
        phase_duration_min=15,
        elapsed_seconds=600,
        transcript_tail=(
            "INTERVIEWER: Anything you'd like to add?\n"
            "CANDIDATE: No, I think that covers it. Let's continue."
        ),
        expected=Label.CALL_CANDIDATE_READY,
        tags=("behavioral", "explicit-request"),
    ),
]

# --------------------------------------------------------------------------- #
# Behavior 3 (positive control): genuine completion of a non-coding phase after
# enough time is a legitimate inferred transition.
# --------------------------------------------------------------------------- #
_LEGIT_INFERRED: List[EvalCase] = [
    EvalCase(
        id="intro_complete_after_reasonable_time",
        phase_type="INTRO",
        phase_duration_min=5,
        elapsed_seconds=210,
        transcript_tail=(
            "CANDIDATE: ...and that's my background.\n"
            "INTERVIEWER: Great, thanks for sharing."
        ),
        expected=Label.CALL_INFERRED,
        notes="Intro objectives met after most of the short phase elapsed.",
        tags=("intro",),
    ),
]

# --------------------------------------------------------------------------- #
# Golden cases harvested from real incidents — must never regress.
# --------------------------------------------------------------------------- #
_GOLDEN: List[EvalCase] = [
    EvalCase(
        id="golden_60abce19_problem1_premature",
        phase_type="CODING",
        phase_duration_min=25,
        elapsed_seconds=189,
        transcript_tail=(
            "INTERVIEWER: I see a small typo in your second loop.\n"
            "CANDIDATE: (working through the sets)\n"
            "# Bot then wrongly transitioned to problem 2 here (natural_breakpoint)."
        ),
        expected=Label.NO_CALL,
        notes=(
            "candidate_interview_id 60abce19-b7b8-4a5e-99eb-27941b9c25c8: LLM "
            "transitioned off a 25-min coding problem after 189s on an inferred "
            "'natural_breakpoint'. Must be NO_CALL."
        ),
        tags=("coding", "golden", "regression"),
    ),
]


ALL_CASES: List[EvalCase] = (
    _STAY_ON_CODING + _CANDIDATE_REQUESTS + _LEGIT_INFERRED + _GOLDEN
)


def cases_by_tag(tag: str) -> List[EvalCase]:
    return [c for c in ALL_CASES if tag in c.tags]
