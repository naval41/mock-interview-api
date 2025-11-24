"""
Interview Gate Processor for filtering frames after interview completion.
"""

from app.interview_playground.processors.base_processor import BaseProcessor
from pipecat.frames.frames import SystemFrame, ControlFrame, StartFrame, EndFrame
import structlog


class InterviewGateProcessor(BaseProcessor):
    """Gate processor that blocks user/data frames after interview completion.
    
    This processor acts as a gate that:
    - Allows all frames to pass through during normal interview operation
    - After interview completion, only allows SystemFrame and ControlFrame instances
    - Blocks all user input frames, data frames, and LLM frames
    """
    
    def __init__(self):
        super().__init__()
        self.interview_completed = False
        self.logger = structlog.get_logger()
    
    async def process_custom_frame(self, frame, direction):
        """Process frames based on interview completion status."""
        # Always allow StartFrame and EndFrame to pass through
        if isinstance(frame, (StartFrame, EndFrame)):
            await self.push_frame(frame, direction)
            return
        
        if self.interview_completed:
            # ALLOW: System frames and Control frames
            if isinstance(frame, (SystemFrame, ControlFrame)):
                await self.push_frame(frame, direction)
                self.logger.debug(f"Gate: Allowed system/control frame: {type(frame)}")
            else:
                # BLOCK: Everything else (user frames, data frames, LLM frames)
                self.logger.debug(f"Gate: Blocked frame after completion: {type(frame)}")
        else:
            # Normal flow - pass all frames
            await self.push_frame(frame, direction)
    
    def mark_interview_completed(self):
        """Mark interview as completed to activate the gate."""
        self.interview_completed = True
        self.logger.info("🚪 Interview gate activated - blocking user and data frames")
    
    def get_gate_status(self) -> dict:
        """Get current gate status for debugging."""
        return {
            "interview_completed": self.interview_completed,
            "gate_active": self.interview_completed
        }
