"""
Custom frames for interview management.
"""

from dataclasses import dataclass
from pipecat.frames.frames import SystemFrame


@dataclass
class InterviewClosureFrame(SystemFrame):
    """System frame for interview closure that bypasses the gate.
    
    This frame is used to deliver the final interview closing message
    and will be allowed through the interview gate processor even after
    the interview is completed.
    """
    message: str
    session_duration: int
    completion_reason: str = "timer_expired"
    final_message: bool = True
