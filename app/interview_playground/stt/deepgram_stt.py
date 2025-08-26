"""
Deepgram STT implementation that extends BaseSTT.
"""

from pipecat.processors.frame_processor import FrameProcessor
from app.interview_playground.stt.base_stt import BaseSTT
from pipecat.services.deepgram.stt import DeepgramSTTService


class DeepgramSTT(BaseSTT):
    """Deepgram STT implementation."""
    
    def __init__(self, api_key: str, language: str = "en"):
        """Initialize Deepgram STT.
        
        Args:
            api_key: Deepgram API key
            language: Language code for transcription
        """
        self.api_key = api_key
        self.language = language
        
    def setup_processor(self) -> FrameProcessor:
        """Setup the Deepgram FrameProcessor instance.
        
        Returns:
            FrameProcessor configured for Deepgram STT
        """
        
        # For now, return a simple FrameProcessor
        # In real implementation, this would return a Deepgram-specific processor
        from pipecat.processors.frame_processor import FrameProcessor
        
        return DeepgramSTTService(api_key=self.api_key)