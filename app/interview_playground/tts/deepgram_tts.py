"""
Deepgram TTS implementation that extends BaseTTS.
"""

from pipecat.processors.frame_processor import FrameProcessor
from app.interview_playground.tts.base_tts import BaseTTS
from pipecat.services.deepgram.tts import DeepgramTTSService


class DeepgramTTS(BaseTTS):
    """Deepgram TTS implementation."""
    
    def __init__(self, api_key: str, voice: str = "aura-2-andromeda-en"):
        """Initialize Deepgram TTS.
        
        Args:
            api_key: Deepgram API key
            voice: Voice name for synthesis
        """
        self.api_key = api_key
        self.voice = voice
        
    def setup_processor(self) -> FrameProcessor:
        """Setup the Deepgram TTS FrameProcessor instance.
        
        Returns:
            FrameProcessor configured for Deepgram TTS
        """
        # For now, return a simple FrameProcessor
        # In real implementation, this would return a Deepgram-specific processor
        from pipecat.processors.frame_processor import FrameProcessor
        
        return DeepgramTTSService(
                api_key=self.api_key,
                voice=self.voice
            )