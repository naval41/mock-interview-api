"""
Interview Closure Handler for converting closure frames to LLM text frames.
"""

from app.interview_playground.processors.base_processor import BaseProcessor
from app.interview_playground.frames.interview_frames import InterviewClosureFrame
from pipecat.frames.frames import LLMMessagesAppendFrame, LLMTextFrame, StartFrame, EndFrame
from pipecat.processors.frame_processor import FrameDirection
import structlog


class InterviewClosureHandler(BaseProcessor):
    """Converts InterviewClosureFrame to LLMTextFrame for TTS processing.
    
    This processor sits between the gate and the LLM service to handle
    the special InterviewClosureFrame and convert it to a regular
    LLMTextFrame that can be processed by the TTS service.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = structlog.get_logger()
    
    async def process_custom_frame(self, frame, direction):
        """Process frames, converting InterviewClosureFrame to LLMTextFrame."""
        # Always allow StartFrame and EndFrame to pass through
        if isinstance(frame, (StartFrame, EndFrame)):
            await self.push_frame(frame, direction)
            return
            
        if isinstance(frame, InterviewClosureFrame):                
            messages = [
                    {
                        "role": "user", 
                        "content": frame.message
                    }
                ]

            self.logger.info("🔄 Converted InterviewClosureFrame to LLMMessagesAppendFrame", 
                           message_length=len(frame.message),
                           session_duration=frame.session_duration,
                           completion_reason=frame.completion_reason)
                
            await self.push_frame(LLMMessagesAppendFrame(messages=messages, run_llm=True), direction)
        else:
            # Pass through other frames unchanged
            await self.push_frame(frame, direction)
    
    def get_handler_status(self) -> dict:
        """Get handler status for debugging."""
        return {
            "handler_type": "InterviewClosureHandler",
            "purpose": "Convert InterviewClosureFrame to LLMTextFrame"
        }
